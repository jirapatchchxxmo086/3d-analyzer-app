import streamlit as st
import trimesh
import numpy as np
import tempfile
import os
import base64
from string import Template
import streamlit.components.v1 as components

# Page configuration
st.set_page_config(page_title="3D Model Analyzer", page_icon="📦", layout="wide")

st.title("📦 3D Model Dimension & Surface Area Analyzer")
st.write("Upload a 3D model file to automatically extract bounding box dimensions, surface area, volume, and surface detail complexity.")

# Sidebar for Model Unit Selection
st.sidebar.header("⚙️ Unit Settings")
unit_input = st.sidebar.selectbox(
    "Select Model File Unit",
    options=[
        "Meters (m)", 
        "Decimeters / 10 cm (dm)", 
        "Centimeters (cm)", 
        "Millimeters (mm)"
    ],
    index=0,
    help="3D formats (OBJ, STL, PLY) store raw numbers without units. Select the unit used when creating the model."
)

# Scaling Factor to standard Meters
if unit_input == "Meters (m)":
    scale_to_m = 1.0
elif unit_input == "Decimeters / 10 cm (dm)":
    scale_to_m = 0.1
elif unit_input == "Centimeters (cm)":
    scale_to_m = 0.01
else:  # Millimeters (mm)
    scale_to_m = 0.001

st.sidebar.divider()

def process_and_clean_mesh(loaded_data):
    if isinstance(loaded_data, trimesh.Scene):
        geometries = []
        for node_name in loaded_data.graph.nodes_geometry:
            transform, geometry_name = loaded_data.graph[node_name]
            geom = loaded_data.geometry[geometry_name].copy()
            geom.apply_transform(transform)
            geometries.append(geom)

        if geometries:
            mesh = trimesh.util.concatenate(geometries)
        else:
            mesh = trimesh.Trimesh()
    else:
        mesh = loaded_data

    if isinstance(mesh, trimesh.Trimesh):
        try:
            mesh.update_faces(mesh.unique_faces())
        except Exception:
            pass

        try:
            mesh.remove_degenerate_faces()
        except Exception:
            pass

        try:
            mesh.remove_infinite_values()
        except Exception:
            pass

    return mesh

# ---------------------------------------------------------------------------
# Surface Area & Detail Complexity Analysis
# ---------------------------------------------------------------------------
def analyze_surface_complexity(mesh, scale_to_m, is_point_cloud):
    """
    ประเมินระดับความซับซ้อน/รายละเอียดของชิ้นงานโดยพิจารณาจาก "ลักษณะและรายละเอียดของพื้นที่ผิว" (Surface Detail)
    """
    if is_point_cloud or not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
        return {"score": None, "level": None, "error": "ไฟล์นี้เป็น Point Cloud จึงไม่มีข้อมูลโครงสร้างพื้นผิว (Faces) ให้วิเคราะห์"}

    if len(mesh.faces) == 0:
        return {"score": None, "level": None, "error": "Mesh ไม่มีข้อมูลหน้า (Faces) สำหรับประเมินพื้นผิว"}

    area_raw = mesh.area
    if area_raw <= 0:
        return {"score": None, "level": None, "error": "พื้นที่ผิวรวมมีค่าเป็น 0"}

    area_m2 = area_raw * (scale_to_m ** 2)

    # 1. Area Fold Ratio (พื้นที่ผิวจริง เทียบกับ พื้นที่ผิวเปลือกห่อหุ้มภายนอก)
    area_ratio = None
    area_error = None
    try:
        hull = mesh.convex_hull
        hull_area = hull.area
        if hull_area > 0:
            area_ratio = float(area_raw / hull_area)
        else:
            area_error = "พื้นที่ผิว Convex Hull เท่ากับ 0"
    except Exception as e:
        area_error = f"คำนวณ Convex Hull ไม่สำเร็จ: {e}"

    # 2. Surface Roughness / Normal Variation (ความผันผวนของทิศทางระนาบผิว)
    surface_roughness = None
    roughness_error = None
    try:
        # คำนวณความต่างของทิศทาง Face Normals ของระนาบผิวเพื่อนบ้าน (Face Adjacency)
        face_adjacency = mesh.face_adjacency
        if len(face_adjacency) > 0:
            normals = mesh.face_normals
            n0 = normals[face_adjacency[:, 0]]
            n1 = normals[face_adjacency[:, 1]]
            
            # Dot product ระหว่างระนาบติดกัน -> แปลงเป็นมุม (Radians)
            dot_products = np.clip(np.sum(n0 * n1, axis=1), -1.0, 1.0)
            angles_rad = np.arccos(dot_products)
            
            # ค่าเฉลี่ยการเปลี่ยนทิศทางของผิว (ยิ่งสูง = ผิวมีความขรุขระ/ลวดลาย/สันซับซ้อน)
            surface_roughness = float(np.mean(angles_rad))
        else:
            surface_roughness = 0.0
    except Exception as e:
        roughness_error = f"คำนวณความผันผวนระนาบผิวไม่สำเร็จ: {e}"

    # 3. Surface Polygon Density (ความหนาแน่นของ Face ต่อพื้นที่ผิวจริง)
    face_density_per_m2 = float(len(mesh.faces) / area_m2) if area_m2 > 0 else 0.0

    # แปลงค่าดัชนีผิวสัมผัสเป็นเปอร์เซ็นต์คะแนนความซับซ้อน (0 - 100%)
    score_components = []

    # Map Area Ratio (ค่าตั้งแต่ 1.0 ขึ้นไป)
    if area_ratio is not None:
        # ยิ่งเกิน 1.0 มาก แสดงว่ามีลวดลายซอกพับบนพื้นผิวมาก
        s_area = float(np.clip(1 - np.exp(-1.2 * max(area_ratio - 1.0, 0.0)), 0.0, 1.0)) * 100
        score_components.append(s_area)

    # Map Surface Roughness (ค่ามุมเฉลี่ย 0 ถึง pi/2 rad)
    if surface_roughness is not None:
        # ค่ามุมเปลี่ยนเกิน ~0.5 rad (ประมาณ 28 องศา) บ่งบอกถึงผิวมีความขรุขระ/รายละเอียดสูง
        s_rough = float(np.clip(1 - np.exp(-2.5 * surface_roughness), 0.0, 1.0)) * 100
        score_components.append(s_rough)

    if not score_components:
        return {"score": None, "level": None, "error": f"{area_error} | {roughness_error}"}

    detail_score = round(sum(score_components) / len(score_components), 1)

    if detail_score < 20:
        level = "ผิวเรียบง่าย (Simple Surface)"
    elif detail_score < 45:
        level = "ผิวมีรายละเอียดปานกลาง (Moderate Surface)"
    elif detail_score < 70:
        level = "ผิวมีรายละเอียดสูง (Detailed Surface)"
    else:
        level = "ผิวมีความซับซ้อน/ลวดลายสูงมาก (Highly Complex Surface)"

    return {
        "score": detail_score,
        "level": level,
        "area_ratio": round(area_ratio, 3) if area_ratio is not None else None,
        "surface_roughness_deg": round(np.degrees(surface_roughness), 2) if surface_roughness is not None else None,
        "face_density": round(face_density_per_m2, 1),
        "total_faces": len(mesh.faces),
        "area_error": area_error,
        "roughness_error": roughness_error
    }


# Template HTML สำหรับแสดงผล 3D Interactive Viewer ด้วย Three.js
HTML_TEMPLATE = Template("""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
    <style>
        body { margin: 0; overflow: hidden; background-color: #1a1a1a; }
        #viewer-container { width: 100%; height: 500px; position: relative; }
        #loading {
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            color: #ffffff; font-family: sans-serif; font-size: 14px; pointer-events: none;
        }
    </style>
</head>
<body>
    <div id="viewer-container">
        <div id="loading">Loading 3D Model...</div>
    </div>
    <script>
        const container = document.getElementById('viewer-container');
        const loading = document.getElementById('loading');

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x1a1a1a);

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 500, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(container.clientWidth, 500);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;

        const ambientLight = new THREE.AmbientLight(0x777777);
        scene.add(ambientLight);

        const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight1.position.set(1, 1, 1).normalize();
        scene.add(dirLight1);

        const dirLight2 = new THREE.DirectionalLight(0x555555, 0.5);
        dirLight2.position.set(-1, -1, -1).normalize();
        scene.add(dirLight2);

        function base64ToArrayBuffer(base64) {
            var binary_string = window.atob(base64);
            var len = binary_string.length;
            var bytes = new Uint8Array(len);
            for (var i = 0; i < len; i++) {
                bytes[i] = binary_string.charCodeAt(i);
            }
            return bytes.buffer;
        }

        try {
            const loader = new THREE.STLLoader();
            const arrayBuffer = base64ToArrayBuffer("$b64_stl");
            const geometry = loader.parse(arrayBuffer);

            geometry.center();
            geometry.computeVertexNormals();

            const material = new THREE.MeshStandardMaterial({
                color: 0x2196F3,
                roughness: 0.3,
                metalness: 0.2
            });
            const mesh = new THREE.Mesh(geometry, material);
            scene.add(mesh);

            geometry.computeBoundingSphere();
            const radius = geometry.boundingSphere.radius;
            camera.position.set(radius * 2.2, radius * 2.2, radius * 2.2);
            camera.lookAt(0, 0, 0);
            controls.update();

            loading.style.display = 'none';
        } catch (err) {
            loading.innerText = 'Failed to load 3D preview';
            console.error(err);
        }

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
        animate();
    </script>
</body>
</html>
""")

def render_3d_viewer(mesh_obj):
    try:
        if isinstance(mesh_obj, trimesh.PointCloud) or len(mesh_obj.vertices) == 0:
            return None
        stl_bytes = mesh_obj.export(file_type='stl')
        b64_stl = base64.b64encode(stl_bytes).decode('utf-8')
        return HTML_TEMPLATE.substitute(b64_stl=b64_stl)
    except Exception as e:
        st.warning(f"Unable to render 3D preview: {e}")
        return None


# File uploader component
uploaded_file = st.file_uploader(
    "Select a 3D model file",
    type=["stl", "obj", "ply", "off", "3mf"]
)

if uploaded_file is not None:
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        with st.spinner("Processing 3D model file..."):
            loaded_data = trimesh.load(tmp_path)
            mesh = process_and_clean_mesh(loaded_data)

            is_point_cloud = isinstance(mesh, trimesh.PointCloud)

            # 1. Bounding Box Dimensions
            extents_raw = mesh.extents
            width_x_m = extents_raw[0] * scale_to_m
            length_y_m = extents_raw[1] * scale_to_m
            height_z_m = extents_raw[2] * scale_to_m

            width_x_cm = width_x_m * 100.0
            length_y_cm = length_y_m * 100.0
            height_z_cm = height_z_m * 100.0

            # 2. Surface Area and Volume Calculations
            surface_area_m2 = 0.0
            volume_m3 = 0.0
            is_watertight = False
            used_convex_hull = False

            if is_point_cloud:
                hull = mesh.convex_hull
                surface_area_m2 = hull.area * (scale_to_m ** 2)
                volume_m3 = hull.volume * (scale_to_m ** 3)
                used_convex_hull = True
            else:
                surface_area_m2 = mesh.area * (scale_to_m ** 2)
                is_watertight = getattr(mesh, 'is_watertight', False)

                if is_watertight:
                    volume_m3 = mesh.volume * (scale_to_m ** 3)
                else:
                    try:
                        hull = mesh.convex_hull
                        volume_m3 = hull.volume * (scale_to_m ** 3)
                        used_convex_hull = True
                    except Exception:
                        volume_m3 = 0.0

            surface_area_cm2 = surface_area_m2 * 10_000.0
            volume_cm3 = volume_m3 * 1_000_000.0

            # 3. Surface Detail Complexity Analysis
            complexity = analyze_surface_complexity(mesh, scale_to_m, is_point_cloud)

        st.success("✅ File processed successfully!")
        st.divider()

        col_viewer, col_metrics = st.columns([1.2, 1])

        with col_viewer:
            st.subheader("🖥️ 3D Model Interactive Viewer")
            st.caption("Rotate: Left Click | Zoom: Scroll | Pan: Right Click")
            html_viewer = render_3d_viewer(mesh)
            if html_viewer:
                components.html(html_viewer, height=510)
            else:
                st.info("No 3D Viewer preview available for this model type.")

        with col_metrics:
            st.subheader("📐 Model Dimensions")
            dim_col1, dim_col2, dim_col3 = st.columns(3)
            dim_col1.metric("Width (X)", f"{width_x_m:.3f} m", f"{width_x_cm:.1f} cm")
            dim_col2.metric("Length (Y)", f"{length_y_m:.3f} m", f"{length_y_cm:.1f} cm")
            dim_col3.metric("Height (Z)", f"{height_z_m:.3f} m", f"{height_z_cm:.1f} cm")

            # เช็กข้อจำกัดของโรงงาน (น้อยกว่า 10 cm / 0.1 m)
            min_dimension_m = min(width_x_m, length_y_m, height_z_m)
            if min_dimension_m < 0.10:
                st.warning(f"⚠️ **Notice:** Model has dimensions smaller than 10 cm ({min_dimension_m*100:.1f} cm). Please verify factory manufacturing limits.")

            st.markdown("---")

            st.subheader("📊 Surface Area & Volume")
            res_a, res_b = st.columns(2)

            res_a.metric("Total Surface Area", f"{surface_area_m2:.4f} sq.m", f"{surface_area_cm2:,.1f} sq.cm")

            if is_watertight:
                res_b.metric("Volume (Exact)", f"{volume_m3:.4f} cu.m", f"{volume_cm3:,.1f} cu.cm")
            elif used_convex_hull and volume_m3 > 0:
                res_b.metric("Volume (Convex Hull)", f"{volume_m3:.4f} cu.m", f"{volume_cm3:,.1f} cu.cm")
                st.info("💡 **Note:** Model is non-watertight or Point Cloud. Volume calculated using Convex Hull approximation.")
            else:
                res_b.info("Model mesh is non-watertight and volume couldn't be calculated.")

            # Surface Detail Complexity Display
            st.markdown("---")
            st.subheader("🔍 Surface Detail Complexity")
            if complexity and complexity.get("score") is not None:
                st.metric("Surface Detail Score", complexity["level"], f"{complexity['score']}%")
                st.progress(complexity["score"] / 100)
                
                with st.expander("รายละเอียดตัวชี้วัดพื้นผิว (Surface Metrics)"):
                    if complexity['area_ratio'] is not None:
                        st.write(f"- **Surface Area Excess Ratio:** `{complexity['area_ratio']}` (พื้นที่ผิวจริง ÷ พื้นที่ผิวภายนอกเรียบ) — ค่ามากกว่า 1.0 แสดงถึงรอยย่น ลวดลาย หรือซอกรอยพับบนพื้นผิว")
                    if complexity['surface_roughness_deg'] is not None:
                        st.write(f"- **Average Surface Normal Deviation:** `{complexity['surface_roughness_deg']}°` — มุมการเปลี่ยนทิศทางเฉลี่ยของระนาบผิวติดกัน ยิ่งสูงแสดงว่าผิวมีสัน/รอยขรุขระผันผวนมาก")
                    st.write(f"- **Surface Polygon Density:** `{complexity['face_density']:,.0f}` Faces/sq.m (จำนวน Faces ทั้งหมด {complexity['total_faces']:,} ชิ้น)")
            else:
                error_msg = complexity.get("error") if complexity else "ไม่ทราบสาเหตุ"
                st.warning(f"⚠️ ไม่สามารถวิเคราะห์ระดับความซับซ้อนของพื้นผิวได้\n\nสาเหตุ: {error_msg}")

    except Exception as e:
        st.error(f"An error occurred while processing the file: {str(e)}")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
