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
st.write("Upload a 3D model file to automatically extract bounding box dimensions, surface area, and volume.")

# Sidebar for Model Unit Selection (เพิ่มตัวเลือก Decimeters / 10 cm)
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
    scale_to_m = 0.1  # แปลงสเกล 14.172 ให้กลายเป็น 1.417 m
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
# NEW: Shape complexity / detail-level analysis
# ---------------------------------------------------------------------------
def analyze_complexity(mesh, is_point_cloud):
    """
    Estimate how visually/geometrically complex (detailed) a shape is, using
    ONLY the outer surface geometry — no volume, no watertightness required.
    This matters because sculpture scans/exports are often not perfectly
    sealed, which makes volume-based measures unreliable.

    Two signals, each naturally >= 1.0 for a perfectly plain convex shape:

    1) Area excess ratio = mesh.area / convex_hull.area
       A plain convex blob (egg, smooth stone) scores close to 1.0 — its
       surface is almost the same as its own outer envelope. A surface full
       of folds, ridges, or fine texture has much MORE actual surface area
       than its envelope, so this ratio climbs well above 1.0.

    2) Total curvature ratio = sum(|vertex_defects|) / (4*pi)
       `vertex_defects` is a standard discrete-geometry measure of how sharp
       the surface bends at each point (angle deficit vs. a flat 360°).
       By the Gauss-Bonnet theorem, a smooth convex shape (sphere, egg, even
       a cube) totals to close to 4*pi regardless of size. Shapes with lots
       of alternating bumps, creases, and hollows accumulate much more total
       curvature than that baseline, so the ratio climbs above 1.0.

    Both signals are combined into a single 0-100% "detail score" and
    bucketed into a human-readable level.

    Calibration note: the ratio-to-percent mapping below (CURVE_STEEPNESS
    constants) is a reasonable starting guess, not a proven scale. Run this
    against 5-10 real pieces whose difficulty you already know, and adjust
    AREA_RATIO_K / CURVATURE_RATIO_K until the scores match your own sense
    of "simple vs. highly detailed" before using it to price real jobs.

    Limitations (be upfront about these with the business):
    - These are geometric PROXIES, not a literal measure of artistic effort.
    - Very fine surface texture only shows up if the mesh was exported at
      high enough resolution to actually contain that geometry — a
      decimated/low-poly export of a detailed sculpture will under-score
      here even though the original artwork is detailed.
    - `vertex_defects` assumes a reasonably clean, manifold mesh; very messy
      or self-intersecting meshes may give noisy results.
    """
    if is_point_cloud or not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
        return {"score": None, "level": None,
                "error": "ไฟล์นี้เป็น point cloud (มีแต่จุด ไม่มีข้อมูลหน้า/face) จึงไม่มีพื้นผิวให้วิเคราะห์"}

    if len(mesh.faces) == 0:
        return {"score": None, "level": None,
                "error": "mesh นี้ไม่มีข้อมูลหน้า (faces) แม้จะมีจุด (vertices) อยู่ก็ตาม"}

    area = mesh.area
    if area <= 0:
        return {"score": None, "level": None, "error": "พื้นที่ผิวรวมคำนวณได้เท่ากับ 0"}

    # --- Signal 1: area excess ratio — compute independently, don't let it
    #     block signal 2 if it fails ---
    area_ratio = None
    area_error = None
    try:
        hull = mesh.convex_hull
        hull_area = hull.area
        if hull_area > 0:
            area_ratio = float(area / hull_area)
        else:
            area_error = "พื้นที่ผิวของ convex hull เท่ากับ 0"
    except Exception as e:
        # สาเหตุที่พบบ่อย: ไม่ได้ติดตั้ง scipy (trimesh ต้องใช้คำนวณ convex hull)
        area_error = f"คำนวณ convex hull ไม่สำเร็จ: {e}"

    # --- Signal 2: total curvature ratio — also independent ---
    curvature_ratio = None
    curvature_error = None
    try:
        total_abs_curvature = float(np.sum(np.abs(mesh.vertex_defects)))
        curvature_ratio = total_abs_curvature / (4.0 * np.pi)
    except Exception as e:
        curvature_error = f"คำนวณ curvature (vertex_defects) ไม่สำเร็จ: {e}"

    if area_ratio is None and curvature_ratio is None:
        combined_error = " | ".join(filter(None, [area_error, curvature_error]))
        return {"score": None, "level": None, "error": combined_error or "ไม่ทราบสาเหตุ"}

    # --- Map open-ended ratios (>= ~1.0) onto a saturating 0-100% score ---
    # Tune these two constants against real samples (see calibration note above).
    AREA_RATIO_K = 1.2       # higher = score climbs faster with area_ratio
    CURVATURE_RATIO_K = 0.6  # higher = score climbs faster with curvature_ratio

    def _ratio_to_pct(ratio, k):
        return float(np.clip(1 - np.exp(-k * max(ratio - 1.0, 0.0)), 0.0, 1.0)) * 100

    components = []
    if area_ratio is not None:
        components.append(_ratio_to_pct(area_ratio, AREA_RATIO_K))
    if curvature_ratio is not None:
        components.append(_ratio_to_pct(curvature_ratio, CURVATURE_RATIO_K))

    detail_score = round(sum(components) / len(components), 1)

    if detail_score < 15:
        level = "เรียบง่าย (Simple)"
    elif detail_score < 35:
        level = "รายละเอียดปานกลาง (Moderate)"
    elif detail_score < 60:
        level = "มีรายละเอียดมาก (Detailed)"
    else:
        level = "รายละเอียดสูงมาก (Highly Detailed)"

    return {
        "score": detail_score,
        "level": level,
        "area_ratio": round(area_ratio, 3) if area_ratio is not None else None,
        "curvature_ratio": round(curvature_ratio, 3) if curvature_ratio is not None else None,
        "area_error": area_error,
        "curvature_error": curvature_error,
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

            # 1. Bounding Box Dimensions (เน้นหน่วย Meter และ Centimeter)
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

            # 3. NEW: Complexity / detail-level analysis
            complexity = analyze_complexity(mesh, is_point_cloud)

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

            # NEW: Complexity / detail-level section
            st.markdown("---")
            st.subheader("🔍 Shape Complexity / Detail Level")
            if complexity and complexity.get("score") is not None:
                st.metric("Estimated Detail Level", complexity["level"], f"{complexity['score']}%")
                st.progress(complexity["score"] / 100)
                with st.expander("ตัวชี้วัดที่ใช้คำนวณ (สำหรับผู้ที่สนใจรายละเอียด)"):
                    if complexity['area_ratio'] is not None:
                        st.write(f"- **Area excess ratio** (พื้นที่ผิวจริง ÷ พื้นที่ผิว convex hull): {complexity['area_ratio']} — 1.0 คือผิวเรียบเนียนเท่าเปลือกห่อภายนอกพอดี ยิ่งสูงยิ่งมีริ้ว/รอยพับ/รายละเอียดเยอะ")
                    else:
                        st.write(f"- **Area excess ratio**: คำนวณไม่ได้ ({complexity.get('area_error')})")
                    if complexity['curvature_ratio'] is not None:
                        st.write(f"- **Total curvature ratio** (ความโค้ง/สันรวมทั้งผิว ÷ ค่าฐานของทรงนูนเรียบ): {complexity['curvature_ratio']} — ยิ่งสูงยิ่งมีมุมแหลม/สัน/หลุมสลับกันเยอะ")
                    else:
                        st.write(f"- **Total curvature ratio**: คำนวณไม่ได้ ({complexity.get('curvature_error')})")
                    st.caption(
                        "หมายเหตุ: ตัวเลขนี้คำนวณจากรูปทรงพื้นผิวล้วนๆ ไม่ใช้ปริมาตรเลย จึงใช้ได้แม้ไฟล์ไม่ปิดสนิท (non-watertight) "
                        "แต่ยังเป็นตัวชี้วัดเชิงเรขาคณิต ไม่ใช่การวัด 'ความประณีตของฝีมือ' โดยตรง "
                        "หากไฟล์ถูกลดความละเอียด (decimate) มาก พื้นผิวที่มีลวดลายละเอียดจริงอาจได้คะแนนต่ำกว่าความเป็นจริง "
                        "— แนะนำให้ลองปรับค่า AREA_RATIO_K / CURVATURE_RATIO_K ในโค้ดให้เข้ากับชิ้นงานจริงของธุรกิจก่อนใช้ตัดสินราคา"
                    )
            else:
                error_msg = complexity.get("error") if complexity else "ไม่ทราบสาเหตุ"
                st.warning(f"⚠️ ไม่สามารถวิเคราะห์ระดับความซับซ้อนของโมเดลนี้ได้\n\nสาเหตุ: {error_msg}")
                if error_msg and "scipy" in error_msg.lower():
                    st.info("💡 ลองรัน `pip install scipy` แล้วรีสตาร์ทแอปใหม่ — trimesh ต้องใช้ scipy ในการคำนวณ convex hull")

    except Exception as e:
        st.error(f"An error occurred while processing the file: {str(e)}")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
