import streamlit as st
import trimesh
import numpy as np
import tempfile
import os
import base64
import pandas as pd
from string import Template
import streamlit.components.v1 as components

# ==========================================
# ⚙️ 1. Page Configuration
# ==========================================
st.set_page_config(page_title="3D Model Analyzer & Cost Estimator", page_icon="📦", layout="wide")

# ==========================================
# 🔄 2. Session State Initialization
# ==========================================
if "surface_area_sqm" not in st.session_state:
    st.session_state["surface_area_sqm"] = 0.0
if "dimensions_str" not in st.session_state:
    st.session_state["dimensions_str"] = "0 * 0 * 0"
if "width_x_mm" not in st.session_state:
    st.session_state["width_x_mm"] = 0.0
if "length_y_mm" not in st.session_state:
    st.session_state["length_y_mm"] = 0.0
if "height_z_mm" not in st.session_state:
    st.session_state["height_z_mm"] = 0.0
if "file_name" not in st.session_state:
    st.session_state["file_name"] = "ยังไม่ได้เลือกไฟล์"

# List สำหรับเก็บบันทึกรายการวัสดุที่เลือกในหน้า 2
if "selected_materials" not in st.session_state:
    st.session_state["selected_materials"] = []

# ==========================================
# 🧭 3. Sidebar Navigation
# ==========================================
st.sidebar.title("📌 เมนูหลัก")
page = st.sidebar.radio(
    "เลือกหน้าต่างทำงาน:",
    ["📦 หน้า 1: วิเคราะห์โมเดล 3D & พื้นที่ผิว", "💰 หน้าที่ 2: คำนวณราคา & ใบประเมิน"]
)

st.sidebar.divider()

# ==========================================
# 📦 หน้า 1: วิเคราะห์โมเดล 3D
# ==========================================
if page == "📦 หน้า 1: วิเคราะห์โมเดล 3D & พื้นที่ผิว":
    st.title("📦 3D Model Dimension & Surface Area Analyzer")
    st.write("Upload a 3D model file to automatically extract bounding box dimensions, surface area, volume, and surface detail complexity.")

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

    if unit_input == "Meters (m)":
        scale_to_m = 1.0
    elif unit_input == "Decimeters / 10 cm (dm)":
        scale_to_m = 0.1
    elif unit_input == "Centimeters (cm)":
        scale_to_m = 0.01
    else:
        scale_to_m = 0.001

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

    def analyze_surface_complexity(mesh, scale_to_m, is_point_cloud):
        if is_point_cloud or not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
            return {"score": None, "level": None, "error": "ไฟล์นี้เป็น Point Cloud จึงไม่มีข้อมูลโครงสร้างพื้นผิว (Faces) ให้วิเคราะห์"}

        if len(mesh.faces) == 0:
            return {"score": None, "level": None, "error": "Mesh ไม่มีข้อมูลหน้า (Faces) สำหรับประเมินพื้นผิว"}

        area_raw = mesh.area
        if area_raw <= 0:
            return {"score": None, "level": None, "error": "พื้นที่ผิวรวมมีค่าเป็น 0"}

        area_m2 = area_raw * (scale_to_m ** 2)

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

        surface_roughness = None
        roughness_error = None
        try:
            face_adjacency = mesh.face_adjacency
            if len(face_adjacency) > 0:
                normals = mesh.face_normals
                n0 = normals[face_adjacency[:, 0]]
                n1 = normals[face_adjacency[:, 1]]
                
                dot_products = np.clip(np.sum(n0 * n1, axis=1), -1.0, 1.0)
                angles_rad = np.arccos(dot_products)
                
                surface_roughness = float(np.mean(angles_rad))
            else:
                surface_roughness = 0.0
        except Exception as e:
            roughness_error = f"คำนวณความผันผวนระนาบผิวไม่สำเร็จ: {e}"

        face_density_per_m2 = float(len(mesh.faces) / area_m2) if area_m2 > 0 else 0.0

        score_components = []

        if area_ratio is not None:
            s_area = float(np.clip(1 - np.exp(-1.2 * max(area_ratio - 1.0, 0.0)), 0.0, 1.0)) * 100
            score_components.append(s_area)

        if surface_roughness is not None:
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

                extents_raw = mesh.extents
                width_x_m = extents_raw[0] * scale_to_m
                length_y_m = extents_raw[1] * scale_to_m
                height_z_m = extents_raw[2] * scale_to_m

                width_x_cm = width_x_m * 100.0
                length_y_cm = length_y_m * 100.0
                height_z_cm = height_z_m * 100.0

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

                complexity = analyze_surface_complexity(mesh, scale_to_m, is_point_cloud)

                st.session_state["surface_area_sqm"] = surface_area_m2
                st.session_state["dimensions_str"] = f"{width_x_m*1000:.0f}*{length_y_m*1000:.0f}*{height_z_m*1000:.0f}"
                st.session_state["width_x_mm"] = width_x_m * 1000
                st.session_state["length_y_mm"] = length_y_m * 1000
                st.session_state["height_z_mm"] = height_z_m * 1000
                st.session_state["file_name"] = uploaded_file.name

            st.success("✅ File processed successfully! Data passed to Page 2.")
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

                st.markdown("---")
                st.subheader("🔍 Surface Detail Complexity")
                if complexity and complexity.get("score") is not None:
                    st.metric("Surface Detail Score", complexity["level"], f"{complexity['score']}%")
                    st.progress(complexity["score"] / 100)
                    
                    with st.expander("รายละเอียดตัวชี้วัดพื้นผิว (Surface Metrics)"):
                        if complexity['area_ratio'] is not None:
                            st.write(f"- **Surface Area Excess Ratio:** `{complexity['area_ratio']}`")
                        if complexity['surface_roughness_deg'] is not None:
                            st.write(f"- **Average Surface Normal Deviation:** `{complexity['surface_roughness_deg']}°`")
                        st.write(f"- **Surface Polygon Density:** `{complexity['face_density']:,.0f}` Faces/sq.m")
                else:
                    error_msg = complexity.get("error") if complexity else "ไม่ทราบสาเหตุ"
                    st.warning(f"⚠️ ไม่สามารถวิเคราะห์ระดับความซับซ้อนของพื้นผิวได้\n\nสาเหตุ: {error_msg}")

        except Exception as e:
            st.error(f"An error occurred while processing the file: {str(e)}")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# ==========================================
# 💰 หน้าที่ 2: คำนวณราคา & ใบประเมิน
# ==========================================
elif page == "💰 หน้าที่ 2: คำนวณราคา & ใบประเมิน":
    st.title("Costing & Cost Estimate")
    st.caption("ระบบดึงข้อมูลพื้นที่ผิวจากหน้าแรกมาประมวลผลร่วมกับสูตรคำนวณ Robot และ Material Master Data")

    st.info(f"📌 **ข้อมูลโมเดลปัจจุบันจากหน้าแรก:** ไฟล์ `{st.session_state['file_name']}` | ขนาด `{st.session_state['dimensions_str']}` mm | พื้นที่ผิว `{st.session_state['surface_area_sqm']:.3f}` ตร.ม.")

    # ------------------------------------------
    # 🗂️ ฐานข้อมูลวัสดุ (Material Master Data)
    # ------------------------------------------
    MATERIAL_MASTER_DB = {
        "หมวด Foam": {
            "Foam 0.8 lb.": {"price": 2300, "cost": 2300},
            "Foam 1.0 lb.": {"price": 2850, "cost": 2850},
            "Foam 1.25 lb.": {"price": 3550, "cost": 3550},
            "Foam 1.5 lb.": {"price": 4100, "cost": 4100},
            "Foam 2.0 lb.": {"price": 6000, "cost": 6000},
            "Foam eva 50 มม.": {"price": 2520, "cost": 2100},
            "EVA แผ่น 30 มม.": {"price": 1440, "cost": 1200},
            "EVA แผ่นหนา 7mm": {"price": 13200, "cost": 11000},
        },
        "หมวด 3D Print / Resin": {
            "PLA Gray": {"price": 600, "cost": 500},
            "Resin Gray": {"price": 1200, "cost": 1000},
            "Resin ( 1000 / 1 sq.m. )": {"price": 1200, "cost": 1000},
            "เรซินใสหล่อพิเศษ 1kg": {"price": 350, "cost": 290},
            "เรซินใสหล่อพิเศษ 5kg": {"price": 960, "cost": 800},
            "Crystal resin": {"price": 1700, "cost": 1415},
        },
        "หมวด อะคริลิค (Acrylic)": {
            "อะคริลิคใส 1.5 3*6 ฟุต": {"price": 576, "cost": 480},
            "อะคริลิคใส 3 มม.": {"price": 2160, "cost": 1800},
            "Acrylic ใส 5 มม.": {"price": 3000, "cost": 2500},
            "Acrylic ใส 10 มม.": {"price": 5760, "cost": 4800},
            "Acrylic 2 mm.": {"price": 1440, "cost": 1200},
            "อะคริลิคขาว 5 มม.": {"price": 3000, "cost": 2500},
            "Acrylic 10 mm.": {"price": 5760, "cost": 4800},
            "Acrylic mirror 2 mm.": {"price": 2400, "cost": 2000},
            "อะคริลิค 25 มม.": {"price": 8640, "cost": 7200},
            "อะคริลิคแท่งใส 10 มม. 1.2 ม.": {"price": 456, "cost": 380},
            "แผ่นอะคริลิค 1 มม.": {"price": 450, "cost": 450},
            "แผ่นอะคริลิค 1.5 มม.": {"price": 750, "cost": 750},
            "แผ่นอะคริลิค 3 มม.": {"price": 1350, "cost": 1350},
            "แผ่นอะคริลิค 4 มม.": {"price": 2220, "cost": 1850},
            "แผ่นอะครีลิค 6 มม.": {"price": 6240, "cost": 5200},
            "แผ่นอะคลิลิกใส 5mm": {"price": 5000, "cost": 4160},
            "อะคริลิค 12 มม.": {"price": 5712, "cost": 4760},
        },
        "หมวด ไม้ / MDF / HMR / พลาสวูด": {
            "MDF 6 mm.": {"price": 300, "cost": 250},
            "MDF 10 mm.": {"price": 360, "cost": 300},
            "MDF 12 mm.": {"price": 420, "cost": 350},
            "MDF 15 mm.": {"price": 540, "cost": 450},
            "MDF 18 mm.": {"price": 660, "cost": 550},
            "MDF 25 mm.": {"price": 900, "cost": 750},
            "HMR 4 mm.": {"price": 255, "cost": 255},
            "HMR 6 mm.": {"price": 350, "cost": 350},
            "HMR 9 mm.": {"price": 475, "cost": 475},
            "Hmr 12 mm.": {"price": 635, "cost": 635},
            "Hmr 15 mm.": {"price": 780, "cost": 780},
            "Hmr 18 mm.": {"price": 910, "cost": 910},
            "HMR 25 mm.": {"price": 1150, "cost": 1150},
            "HMR Laminate 15 mm.": {"price": 2160, "cost": 1800},
            "HMR Laminate 18 mm.": {"price": 2400, "cost": 2000},
            "ไม้อัด 3 มม.": {"price": 180, "cost": 150},
            "ไม้อัด 6 มม.": {"price": 360, "cost": 300},
            "ไม้อัด 12 มม": {"price": 456, "cost": 380},
            "ไม้อัด 20 มม.": {"price": 1200, "cost": 1000},
            "ไม้อัดดัดโค้ง 6 มม.": {"price": 1080, "cost": 900},
            "ไม้อัดดัดโค้ง 10 มม.": {"price": 1308, "cost": 1090},
            "ไม้อัดยางมารีน 20mm": {"price": 4000, "cost": 3330},
            "ไม้จอยส์ ( 10 เส้น )": {"price": 320, "cost": 320},
            "ไม้โครง": {"price": 120, "cost": 100},
            "ไม้โอ๊ค veneer": {"price": 4000, "cost": 5600},
            "Plastwood 3 mm.": {"price": 420, "cost": 350},
            "Plastwood 4 mm.": {"price": 480, "cost": 400},
            "Plastwood 6 mm.": {"price": 660, "cost": 550},
            "Plastwood 10 mm.": {"price": 1440, "cost": 1200},
            "Plastwood 15 mm.": {"price": 1800, "cost": 1500},
            "Plastwood 20 mm.": {"price": 2400, "cost": 2000},
            "Plastwood 25 mm.": {"price": 3000, "cost": 2500},
        },
        "หมวด เหล็ก / สแตนเลส / โลหะ": {
            "เหล็กแผ่น 1 มม.": {"price": 850, "cost": 850},
            "เหล็กแผ่น 1.2 มม.": {"price": 1200, "cost": 1000},
            "เหล็กแผ่น 1.5 มม.": {"price": 1440, "cost": 1200},
            "เหล็กแผ่น 1.5 มม. 5*8": {"price": 2880, "cost": 2400},
            "เหล็กแผ่น 2 มม.": {"price": 1050, "cost": 1050},
            "เหล็กแผ่น 2.5 มม.": {"price": 2160, "cost": 1800},
            "เหล็กแผ่น 3 มม.": {"price": 2520, "cost": 2100},
            "เหล็กแผ่น 4 มม.": {"price": 3240, "cost": 2700},
            "เหล็กแผ่น 6 มม.": {"price": 3750, "cost": 3750},
            "เหล็กแผ่น 8 มม.": {"price": 6240, "cost": 5200},
            "เหล็กแผ่น 10 มม.": {"price": 5795, "cost": 5795},
            "เหล็กแผ่น 12 มม.": {"price": 6950, "cost": 6950},
            "เหล็กเส้น 4 มม. 1300": {"price": 100, "cost": 100},
            "เหล็กเส้น 10มม. 10ม.": {"price": 240, "cost": 200},
            "เหล็กกล่อง 1.25\" ( 32 มม.)": {"price": 600, "cost": 500},
            "เหล็กกล่อง 2*3 นิ้ว": {"price": 1200, "cost": 1000},
            "เหล็กท่อกลม 2 นิ้ว": {"price": 600, "cost": 500},
            "เหล็กท่อกลม 8 มม.": {"price": 120, "cost": 100},
            "เหล็กท่อกลม 6 นิ้ว": {"price": 1800, "cost": 1800},
            "เหล็กท่อกลม 20mm": {"price": 480, "cost": 400},
            "ท่อเหล็ก 1 นิ้ว": {"price": 216, "cost": 180},
            "ท่อเหล็ก 90 มม.": {"price": 5400, "cost": 4500},
            "ท่อเหล็ก 100 มม.": {"price": 6240, "cost": 5200},
            "เหล็กกลม 25mm ดัดโค้ง 2ชิ้น 1 ชุด": {"price": 4500, "cost": 3750},
            "เหล็กกลม 25mm ดัดโค้ง 2ชิ้น 10 ชุด": {"price": 4300, "cost": 3580},
            "เหล็กกลม 25mm ดัดโค้ง 2ชิ้น 20 ชุด": {"price": 4000, "cost": 3330},
            "Stainless แท่ง 10 มม. 1 ม.": {"price": 180, "cost": 150},
            "เพลาสแตนเลส 1/4 นิ้ว ( 6.35 มม. )": {"price": 270, "cost": 225},
            "เพลาสแตนเลส 3/16 นิ้ว ( 4.762 มม. )": {"price": 156, "cost": 130},
            "ท่อStainless 0.5 นิ้ว": {"price": 1800, "cost": 1500},
            "ท่อStainless 1 นิ้ว": {"price": 3000, "cost": 2500},
            "ท่อStainless 1.5 นิ้ว": {"price": 4200, "cost": 3500},
            "ท่อStainless 2 นิ้ว": {"price": 5400, "cost": 4500},
        },
        "หมวด แผ่นพลาสติก / พีวีซี / กระดาษ": {
            "แผ่น PVC": {"price": 70, "cost": 70},
            "แผ่น PVC ใส 5 มม.": {"price": 4200, "cost": 3500},
            "แผ่น PET 0.5 มม.": {"price": 65, "cost": 65},
            "แผ่น PET 1 มม.": {"price": 105, "cost": 105},
            "แผ่น PP": {"price": 100, "cost": 100},
            "แผ่นกระดาษ": {"price": 70, "cost": 70},
        },
        "หมวด สี / สารเคมี / งานปิดผิว": {
            "สีทากระดานดำ": {"price": 250, "cost": 200},
            "สีทองกลิตเตอร์ 1 ลิตร": {"price": 1440, "cost": 1200},
            "ตัวเคลือบ 2K 168 -3ลิตร": {"price": 3360, "cost": 2800},
            "Epoxy + PU Coating กันสนิม": {"price": 500, "cost": 415},
            "Walltex TOA 1 ถัง": {"price": 2148, "cost": 1790},
            "Texture ( 26A )": {"price": 340, "cost": 280},
            "ลามิเนตลายหินอ่อน": {"price": 1500, "cost": 1250},
            "Interior film ลายหินอ่อน 1*1 m.": {"price": 480, "cost": 400},
            "แผ่นปิดทอง ( 1 ตร.ม. )": {"price": 168, "cost": 140},
        },
        "หมวด ระบบไฟ / อุปกรณ์ไฟฟ้า": {
            "Strip light ( 1 m. )": {"price": 132, "cost": 110},
            "Strip light 4500k ( 1m. )": {"price": 600, "cost": 500},
            "Strip light 3000k ( 1m.)": {"price": 420, "cost": 350},
            "หม้อแปลง strip light": {"price": 1500, "cost": 1500},
            "Neon flex 12V ( 1 m.)": {"price": 180, "cost": 150},
            "Track light 4000K": {"price": 1800, "cost": 1500},
            "หลอดไฟกลม E27 Warm": {"price": 180, "cost": 150},
            "Light box 1 set": {"price": 5500, "cost": 4580},
            "Light box 10 set": {"price": 4500, "cost": 3750},
            "Light box 20 set": {"price": 4000, "cost": 3330},
        },
        "หมวด ฟิตติ้ง / อุปกรณ์ตกแต่ง / อื่นๆ": {
            "กระจก ( 5000 / 1 sq.m. )": {"price": 6000, "cost": 5000},
            "ท่อ PVC 25mm. 2.9 m.": {"price": 84, "cost": 70},
            "ท่อ pvc 1นิ้ว": {"price": 180, "cost": 150},
            "ข้อต่อเกรียวใน 1.5 นิ้ว": {"price": 120, "cost": 100},
            "เกรียวนอก 36 มม. 1ม.": {"price": 1200, "cost": 1000},
            "เชือกฟาง": {"price": 240, "cost": 200},
            "ชุดเข็มนาฬิกา": {"price": 300, "cost": 250},
            "แม่เหล็ก": {"price": 90, "cost": 75},
            "แม่เหล็ก ( 5*15*150 )": {"price": 300, "cost": 250},
            "ผ้าม่าน ( 1 ตร.ม. )": {"price": 1800, "cost": 1500},
            "สลิง 6 มม. ( 1 เมตร )": {"price": 120, "cost": 100},
            "หญ้าเทียม 50 sq.m.": {"price": 9600, "cost": 8000},
            "หญ้าเทียม 1 sq.m.": {"price": 192, "cost": 160},
            "Mechanic small": {"price": 36000, "cost": 30000},
            "Mechanic Large": {"price": 120000, "cost": 100000},
            "บานพับ": {"price": 360, "cost": 300},
            "บานพับแสตนเลส": {"price": 200, "cost": 165},
            "ผ้า canvas 1 เมตร": {"price": 216, "cost": 180},
            "ผ้า 210T": {"price": 120, "cost": 100},
            "ล้อ": {"price": 240, "cost": 200},
            "Cement board 12 มม.": {"price": 720, "cost": 600},
            "ยางกันลื่น 3มม. (1.2*1ม.)": {"price": 720, "cost": 600},
            "ทุ่งดอกหญ้า 1 ตร.ม.": {"price": 120, "cost": 100},
            "มือจับฝัง": {"price": 200, "cost": 165},
            "ลวดดัดโครง 4mm": {"price": 240, "cost": 200},
        }
    }

    LEVEL_FACTORS = {1: 1.0, 2: 1.5, 3: 2.5, 4: 3.5, 5: 5.0, 6: 6.5, 7: 8.0, 8: 10.0, 9: 12.0, 10: 15.0}
    HARDCOAT_RATES = {"ไม่มี (None)": 0, "Polyurea": 1350, "Mold Fiber": 1520, "Fiberglass (Work)": 1090, "Epoxy": 600}
    COLOR_RATES = {"ไม่มี (None)": 0, "Normal": 1440, "Chromium": 4800, "The Code": 1800, "Gold leaves": 168, "Sticker": 1200}

    # 1. ข้อมูลทั่วไป
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        project_name = st.text_input("ชื่อชิ้นงาน / ลูกค้า", value=st.session_state["file_name"])
        complexity_level = st.slider("ระดับความซับซ้อน (Level 1-10)", min_value=1, max_value=10, value=5)
        
    with col_in2:
        calc_area = st.number_input(
            "พื้นที่ทำสี/เคลือบผิว (sq.m.)", 
            min_value=0.0, 
            value=float(st.session_state["surface_area_sqm"]), 
            step=0.1
        )

    st.markdown("##### ⚙️ เลือกกระบวนการเครื่องจักร (Operations)")
    c_op1, c_op2, c_op3, c_op4 = st.columns(4)

    with c_op1:
        st.markdown("**1. Robot Milling**")
        use_robot = st.checkbox("ใช้งาน Robot", value=True)
        robot_rate = st.number_input("ค่าเครื่อง (฿/Hr)", value=300)
        robot_prog = st.number_input("Program (Hr)", value=0.5, key="r_p")
        robot_setup = st.number_input("Setup (Hr)", value=0.5, key="r_s")
        auto_robot_mch = calc_area * LEVEL_FACTORS.get(complexity_level, 5.0)
        robot_mch = st.number_input("Machine (Hr)", value=float(auto_robot_mch), key="r_m")

    with c_op2:
        st.markdown("**2. 3D Print FDM**")
        use_fdm = st.checkbox("ใช้งาน 3D Print", value=False)
        fdm_rate = st.number_input("ค่าเครื่อง FDM (฿/Hr)", value=50)
        fdm_prog = st.number_input("Program (Hr)", value=0.5, key="f_p")
        fdm_setup = st.number_input("Setup (Hr)", value=0.5, key="f_s")
        fdm_mch = st.number_input("Machine (Hr)", value=17.0, key="f_m")

    with c_op3:
        st.markdown("**3. Structure & Assembly**")
        use_struct = st.checkbox("งานโครงสร้าง", value=False)

    with c_op4:
        st.markdown("**4. Fiber Laser N2**")
        use_laser = st.checkbox("ใช้งาน Laser", value=False)
        laser_rate = st.number_input("ค่าเครื่อง Laser (฿/Hr)", value=2400)
        laser_prog = st.number_input("Program (Hr)", value=0.5, key="l_p")
        laser_setup = st.number_input("Setup (Hr)", value=0.5, key="l_s")
        laser_mch = st.number_input("Machine (Hr)", value=0.5, key="l_m")

    # ==========================================
    # 📦 ระบบเลือกวัสดุจาก Master Data
    # ==========================================
    st.markdown("---")
    st.markdown("##### 📦 ระบบเลือกรายการวัสดุสำหรับผลิตชิ้นงาน (Material Master Selection)")

    with st.expander("➕ คลิกเพื่อเลือกและเพิ่มรายการวัสดุลงในชิ้นงาน", expanded=True):
        m_col1, m_col2, m_col3, m_col4 = st.columns([1.5, 2, 1, 1])
        
        with m_col1:
            selected_cat = st.selectbox("เลือกหมวดหมู่วัสดุ", list(MATERIAL_MASTER_DB.keys()))
        
        with m_col2:
            materials_in_cat = list(MATERIAL_MASTER_DB[selected_cat].keys())
            selected_mat_item = st.selectbox("เลือกรายการวัสดุ", materials_in_cat)
            
        unit_price = MATERIAL_MASTER_DB[selected_cat][selected_mat_item]["price"]
        unit_cost = MATERIAL_MASTER_DB[selected_cat][selected_mat_item]["cost"]

        with m_col3:
            mat_qty = st.number_input("จำนวน / หน่วย", min_value=1.0, value=1.0, step=1.0)
            st.caption(f"ราคาขาย: ฿{unit_price:,.2f} | ทุน: ฿{unit_cost:,.2f}")

        with m_col4:
            st.write(" ")
            st.write(" ")
            if st.button("➕ เพิ่มวัสดุ", use_container_width=True):
                final_price = unit_price
                final_cost = unit_cost
                if selected_mat_item == "ไม้อัดยางมารีน 20mm" and mat_qty >= 100:
                    final_price = 3500.0
                    st.toast("🎉 ปรับราคาไม้อัดยางมารีน 20mm เป็นราคาโปรโมชั่น 3,500 บาท/แผ่น")

                new_item = {
                    "cat": selected_cat,
                    "name": selected_mat_item,
                    "qty": mat_qty,
                    "unit_price": final_price,
                    "unit_cost": final_cost,
                    "total_price": final_price * mat_qty,
                    "total_cost": final_cost * mat_qty
                }
                st.session_state["selected_materials"].append(new_item)
                st.toast(f"เพิ่ม {selected_mat_item} จำนวน {mat_qty} เรียบร้อยแล้ว")

    # แสดงตารางวัสดุที่เลือก
    if st.session_state["selected_materials"]:
        st.markdown("###### 📋 รายการวัสดุที่เลือกในชิ้นงานนี้")
        mat_df = pd.DataFrame(st.session_state["selected_materials"])
        
        # Display table formatted
        display_df = mat_df[["cat", "name", "qty", "unit_price", "total_price"]].copy()
        display_df.columns = ["หมวดหมู่", "ชื่อวัสดุ", "จำนวน", "ราคา/หน่วย (฿)", "ราคารวม (฿)"]
        st.dataframe(display_df, use_container_width=True)

        col_clear, col_stat = st.columns([1, 3])
        with col_clear:
            if st.button("🗑️ ล้างรายการวัสดุทั้งหมด"):
                st.session_state["selected_materials"] = []
                st.rerun()

    # ==========================================
    # 🎨 งานเคลือบผิว & งานทำสี (Hardcoat & Painting)
    # ==========================================
    st.markdown("---")
    st.markdown("##### 🎨 งานเคลือบผิวแข็ง & งานทำสี (Finishing & Painting)")
    c_hc1, c_hc2 = st.columns(2)
    
    with c_hc1:
        selected_hardcoat = st.selectbox("ประเภท Hardcoat / เคลือบผิว", list(HARDCOAT_RATES.keys()))
        hardcoat_rate = HARDCOAT_RATES[selected_hardcoat]
        hardcoat_cost = hardcoat_rate * calc_area
        st.caption(f"อัตราค่าบริการ: ฿{hardcoat_rate:,.2f} / ตร.ม. | ราคารวม: ฿{hardcoat_cost:,.2f}")

    with c_hc2:
        selected_color = st.selectbox("ประเภทการทำสี / ปิดผิว", list(COLOR_RATES.keys()))
        color_rate = COLOR_RATES[selected_color]
        color_cost = color_rate * calc_area
        st.caption(f"อัตราค่าบริการ: ฿{color_rate:,.2f} / ตร.ม. | ราคารวม: ฿{color_cost:,.2f}")

    # ==========================================
    # 🧮 การคำนวณสรุปราคาและต้นทุนรวม
    # ==========================================
    st.markdown("---")
    st.subheader("📊 สรุปประมาณการราคาผลิต (Costing & Price Summary)")

    # 1. ค่าเครื่องจักร
    robot_total = (robot_prog + robot_setup + robot_mch) * robot_rate if use_robot else 0.0
    fdm_total = (fdm_prog + fdm_setup + fdm_mch) * fdm_rate if use_fdm else 0.0
    laser_total = (laser_prog + laser_setup + laser_mch) * laser_rate if use_laser else 0.0
    machine_total = robot_total + fdm_total + laser_total

    # 2. ค่าวัดถุดิบ (จากรายการที่เลือก)
    material_total_price = sum(item["total_price"] for item in st.session_state["selected_materials"])
    material_total_cost = sum(item["total_cost"] for item in st.session_state["selected_materials"])

    # 3. ค่าทำสี/เคลือบผิว
    finishing_total = hardcoat_cost + color_cost

    # ราคารวมประเมินเบื้องต้น
    subtotal = machine_total + material_total_price + finishing_total

    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("ค่าประมวลผลเครื่องจักร", f"฿{machine_total:,.2f}")
    col_res2.metric("ค่าวัสดุและอุปกรณ์", f"฿{material_total_price:,.2f}")
    col_res3.metric("ค่าเคลือบผิว & ทำสี", f"฿{finishing_total:,.2f}")

    st.markdown("### 🏷️ ราคารวมประมาณการ (Grand Total)")
    st.title(f"฿ {subtotal:,.2f} บาท")
