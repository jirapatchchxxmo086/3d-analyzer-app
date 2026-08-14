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
# 📦 หน้า 1: วิเคราะห์โมเดล 3D (คงโค้ดเดิมไว้ 100%)
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
# 💰 หน้าที่ 2: คำนวณราคา (ปรับปรุงการรวมวัสดุอื่นๆ)
# ==========================================
elif page == "💰 หน้าที่ 2: คำนวณราคา & ใบประเมิน":
    st.title("💰 หน้าที่ 2: คำนวณต้นทุนและออกใบประเมินราคา")
    st.caption("ระบบดึงข้อมูลพื้นที่ผิวจากหน้าแรกมาประมวลผลร่วมกับสูตรคำนวณ Robot และ Master Data")

    st.info(f"📌 **ข้อมูลโมเดลปัจจุบันจากหน้าแรก:** ไฟล์ `{st.session_state['file_name']}` | ขนาด `{st.session_state['dimensions_str']}` mm | พื้นที่ผิว `{st.session_state['surface_area_sqm']:.3f}` ตร.ม.")

    # Master Data Rates
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

    st.markdown("##### ⚙️ เลือกกระบวนการเครื่องจักรและรายการวัสดุ (Operations & Materials)")
    c_op1, c_op2, c_op3, c_op4 = st.columns(4)

    with c_op1:
        st.markdown("**1. Robot Milling**")
        use_robot = st.checkbox("ใช้งาน Robot", value=True)
        robot_rate = st.number_input("ค่าเครื่อง (฿/Hr)", value=300)
        robot_prog = st.number_input("Program (Hr)", value=0.5, key="r_p")
        robot_setup = st.number_input("Setup (Hr)", value=0.5, key="r_s")
        auto_robot_mch = calc_area * LEVEL_FACTORS.get(complexity_level, 5.0)
        robot_mch = st.number_input("Machine (Hr)", value=float(auto_robot_mch), key="r_m")
        robot_mat = st.number_input("ค่าโฟม/โฟมแท่ง (฿)", value=2850)

    with c_op2:
        st.markdown("**2. 3D Print FDM**")
        use_fdm = st.checkbox("ใช้งาน 3D Print", value=False)
        fdm_rate = st.number_input("ค่าเครื่อง FDM (฿/Hr)", value=50)
        fdm_prog = st.number_input("Program (Hr)", value=0.5, key="f_p")
        fdm_setup = st.number_input("Setup (Hr)", value=0.5, key="f_s")
        fdm_mch = st.number_input("Machine (Hr)", value=17.0, key="f_m")
        fdm_mat = st.number_input("ค่าเส้นพลาสติก (฿)", value=480)

    with c_op3:
        st.markdown("**3. Structure & Assembly**")
        use_struct = st.checkbox("งานโครงสร้าง", value=False)
        struct_mat = st.number_input("ค่าเหล็ก/โครงสร้าง (฿)", value=720)

    with c_op4:
        st.markdown("**4. Fiber Laser N2**")
        use_laser = st.checkbox("ใช้งาน Laser", value=False)
        laser_rate = st.number_input("ค่าเครื่อง Laser (฿/Hr)", value=2400)
        laser_prog = st.number_input("Program (Hr)", value=0.5, key="l_p")
        laser_setup = st.number_input("Setup (Hr)", value=0.5, key="l_s")
        laser_mch = st.number_input("Machine (Hr)", value=0.5, key="l_m")
        laser_mat = st.number_input("ค่าแผ่นแผ่นเลเซอร์ (฿)", value=648)

    # 📦 รวมส่วนวัสดุอื่นๆ (ไม้อัดยางมารีน 20mm + อุปกรณ์ประกอบเพิ่มเติม)
    st.markdown("---")
    st.markdown("##### 📦 วัสดุอื่นๆ (Other Materials / Plywood)")
    col_mat_other1, col_mat_other2 = st.columns(2)
    
    with col_mat_other1:
        use_plywood = st.checkbox("ไม้อัดยางมารีน 20mm", value=False)
        plywood_total = 0.0
        if use_plywood:
            plywood_qty = st.number_input("จำนวนแผ่นไม้อัด", min_value=1, value=1)
            # ปรับส่วนลดกรณีสั่งซื้อขั้นต่ำ ≥ 100 แผ่น
            if plywood_qty >= 100:
                plywood_unit_price = 3500
                st.caption("🎉 ได้รับราคาสั่งซื้อขั้นต่ำ (≥ 100 แผ่น): 3,500 บาท/แผ่น")
            else:
                plywood_unit_price = 4000
                st.caption("ราคาปกติ (< 100 แผ่น): 4,000 บาท/แผ่น")
            plywood_total = plywood_qty * plywood_unit_price

    with col_mat_other2:
        general_mat_cost = st.number_input("ค่าวัสดุและอุปกรณ์อื่นๆ เพิ่มเติม (บาท)", min_value=0.0, value=0.0, step=100.0)

    # รวมยอดหมวดวัสดุอื่นๆ
    other_materials_total = plywood_total + general_mat_cost

    st.markdown("##### 🎨 งานเคลือบผิวและทำสี (Hard Coat & Finishing)")
    c_coat1, c_coat2 = st.columns(2)
    with c_coat1:
        sel_hardcoat = st.selectbox("ประเภท Hard Coat", list(HARDCOAT_RATES.keys()))
    with c_coat2:
        sel_color = st.selectbox("ประเภทการทำสี (Color Type)", list(COLOR_RATES.keys()))

    st.divider()

    # ==========================================
    # 🧮 การคำนวณราคาสรุป
    # ==========================================
    r_time = (robot_prog + robot_setup + robot_mch) if use_robot else 0
    r_mch_cost = r_time * robot_rate if use_robot else 0
    r_mat_cost = robot_mat if use_robot else 0

    f_time = (fdm_prog + fdm_setup + fdm_mch) if use_fdm else 0
    f_mch_cost = f_time * fdm_rate if use_fdm else 0
    f_mat_cost = fdm_mat if use_fdm else 0

    s_mat_cost = struct_mat if use_struct else 0

    l_time = (laser_prog + laser_setup + laser_mch) if use_laser else 0
    l_mch_cost = l_time * laser_rate if use_laser else 0
    l_mat_cost = laser_mat if use_laser else 0

    # ยอดรวมค่าเครื่องจักร และ วัสดุทั้งหมด
    total_mch_cost = r_mch_cost + f_mch_cost + l_mch_cost
    total_mat_cost = r_mat_cost + f_mat_cost + s_mat_cost + l_mat_cost + other_materials_total
    prototype_cost = total_mch_cost + total_mat_cost

    hardcoat_cost = calc_area * HARDCOAT_RATES[sel_hardcoat]
    color_cost = calc_area * COLOR_RATES[sel_color]

    grand_total = prototype_cost + hardcoat_cost + color_cost

    # ==========================================
    # 📋 ตารางสรุปผล
    # ==========================================
    st.subheader(f"📋 สรุปใบประเมินราคา: {project_name}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ชั่วโมง Robot รวม", f"{r_time:.1f} ชม.")
    m2.metric("ค่าเครื่องจักรรวม", f"฿{total_mch_cost:,.2f}")
    m3.metric("ค่าวัสดุทั้งหมด", f"฿{total_mat_cost:,.2f}")
    m4.metric("💰 ราคาสรุปสุทธิ (Grand Total)", f"฿{grand_total:,.2f}")

    df_summary = pd.DataFrame({
        "หมวดหมู่กระบวนการ / วัสดุ": [
            "1. Robot Milling", 
            "2. 3D Print FDM", 
            "3. Structure", 
            "4. Fiber Laser N2", 
            "5. วัสดุอื่นๆ (ไม้อัดยางมารีน / อื่นๆ)"
        ],
        "เวลารวม (Hr)": [f"{r_time:.1f}", f"{f_time:.1f}", "-", f"{l_time:.1f}", "-"],
        "ค่าเครื่องจักร (Baht)": [f"฿{r_mch_cost:,.2f}", f"฿{f_mch_cost:,.2f}", "฿0.00", f"฿{l_mch_cost:,.2f}", "฿0.00"],
        "ค่าวัสดุ (Baht)": [f"฿{r_mat_cost:,.2f}", f"฿{f_mat_cost:,.2f}", f"฿{s_mat_cost:,.2f}", f"฿{l_mat_cost:,.2f}", f"฿{other_materials_total:,.2f}"]
    })
    st.table(df_summary)

    st.markdown(f"""
    > **งานตกแต่งผิว & สี:**
    > * **Hard Coat ({sel_hardcoat}):** {calc_area:.2f} sq.m. × ฿{HARDCOAT_RATES[sel_hardcoat]:,} = **฿{hardcoat_cost:,.2f}**
    > * **Color ({sel_color}):** {calc_area:.2f} sq.m. × ฿{COLOR_RATES[sel_color]:,} = **฿{color_cost:,.2f}**
    """)
