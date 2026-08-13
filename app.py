import streamlit as st
import trimesh
import numpy as np
import tempfile
import os
import base64
import streamlit.components.v1 as components

# Page configuration
st.set_page_config(page_title="3D Model Analyzer & Viewer", page_icon="📦", layout="wide")

st.title("📦 3D Model Dimension & Surface Area Analyzer")
st.write("อัปโหลดไฟล์ 3D เพื่อคำนวณพื้นที่ผิว ขนาด Bounding Box และแสดงผลโมเดลสามมิติแบบ Real-time")

# Sidebar for Model Unit Selection
st.sidebar.header("⚙️ Unit Settings")
unit_input = st.sidebar.selectbox(
    "Select Model File Unit",
    options=["Millimeters (mm)", "Centimeters (cm)", "Meters (m)"],
    index=0,  # Default เป็น mm เหมาะกับไฟล์วิศวกรรม/3D Print ส่วนใหญ่
    help="3D formats (OBJ, STL, PLY) store raw numbers without units. Select the unit used when creating the model."
)

# Scaling Factor to standard Meters
if unit_input == "Meters (m)":
    scale_to_m = 1.0
elif unit_input == "Millimeters (mm)":
    scale_to_m = 0.001
else:  # Centimeters (cm)
    scale_to_m = 0.01

st.sidebar.divider()
st.sidebar.info("💡 **Tips:** ระบบทำการ Clean Mesh อัตโนมัติ (ลบหน้าซ้อน และรวมพิกัด Scene) เพื่อให้ได้พื้นที่ผิวที่แม่นยำที่สุด")

# Helper function: Process & Clean Mesh Accurately
def process_and_clean_mesh(loaded_data):
    """
    แปลง Scene ให้เป็น Single Mesh โดยรวม Transform Matrix ของทุกชิ้นส่วนอย่างถูกต้อง
    และทำการ Clean Mesh ลบหน้าซ้อนทับ
    """
    if isinstance(loaded_data, trimesh.Scene):
        geometries = []
        # ดึง Node และ Apply Transform ของแต่ละชิ้นส่วนใน Scene
        for node_name in loaded_data.graph.nodes_geometry:
            transform, geometry_name = loaded_data.graph[node_name]
            geom = loaded_data.geometry[geometry_name].copy()
            geom.apply_transform(transform)
            geometries.append(geom)
            
        if geometries:
            # รวม Geometry ทั้งหมดเข้าด้วยกัน
            mesh = trimesh.util.concatenate(geometries)
        else:
            mesh = trimesh.Trimesh()
    else:
        mesh = loaded_data

    # ทำการ Clean Mesh หากเป็น Trimesh
    if isinstance(mesh, trimesh.Trimesh):
        mesh.remove_duplicate_faces()
        mesh.remove_degenerate_faces()
        mesh.remove_infinite_values()
        
    return mesh

# Helper function: Generate Three.js HTML Viewer via Base64
def render_3d_viewer(mesh_obj):
    """
    Export mesh เป็น STL Binary แล้วแปลงเป็น Base64 ส่งให้ Three.js STLLoader Render
    """
    # ถ้าเป็น PointCloud หรือ Mesh ว่างเปล่า ไม่ต้องสร้าง Viewer
    if isinstance(mesh_obj, trimesh.PointCloud) or len(mesh_obj.vertices) == 0:
        return None

    # Export เป็น STL binary byte
    stl_bytes = mesh_obj.export(file_type='stl')
    b64_stl = base64.b64encode(stl_bytes).decode('utf-8')

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
        <style>
            body {{ margin: 0; overflow: hidden; background-color: #1a1a1a; }}
            #viewer-container {{ width: 100%; height: 500px; position: relative; }}
            #loading {{
                position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                color: #ffffff; font-family: sans-serif; font-size: 14px; pointer-events: none;
            }}
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
            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(container.clientWidth, 500);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;

            // Lighting setup
            const ambientLight = new THREE.AmbientLight(0x777777);
            scene.add(ambientLight);

            const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight1.position.set(1, 1, 1).normalize();
            scene.add(dirLight1);

            const dirLight2 = new THREE.DirectionalLight(0x555555, 0.5);
            dirLight2.position.set(-1, -1, -1).normalize();
            scene.add(dirLight2);

            // Base64 to ArrayBuffer decoder
            function base64ToArrayBuffer(base64) {{
                var binary_string = window.atob(base64);
                var len = binary_string.length;
                var bytes = new Uint8Array(len);
                for (var i = 0; i < len; i++) {{
                    bytes[i] = binary_string.charCodeAt(i);
                }}
                return bytes.buffer;
            }}

            // Load STL from Base64
            try {{
                const loader = new THREE.STLLoader();
                const arrayBuffer = base64ToArrayBuffer("{b64_stl}");
                const geometry = loader.parse(arrayBuffer);
                
                geometry.center();
                geometry.computeVertexNormals();

                const material = new THREE.MeshStandardMaterial({{ 
                    color: 0x2196F3, 
                    roughness: 0.3, 
                    metalness: 0.2 
                }});
                const mesh = new THREE.Mesh(geometry, material);
                scene.add(mesh);

                // Auto-fit Camera
                geometry.computeBoundingSphere();
                const radius = geometry.boundingSphere.radius;
                camera.position.set(radius * 2.2, radius * 2.2, radius * 2.2);
                camera.lookAt(0, 0, 0);
                controls.update();

                loading.style.display = 'none';
            }} catch (err) {{
                loading.innerText = 'Failed to load 3D preview';
                console.error(err);
            }}

            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }}
            animate();

            // Handle Resize
            window.addEventListener('resize', () => {{
                camera.aspect = container.clientWidth / 500;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, 500);
            }});
        </script>
    </body>
    </html>
    """
    return html_code

st.divider()

# File uploader component
uploaded_file = st.file_uploader(
    "Select a 3D model file", 
    type=["stl", "obj", "ply", "off", "3mf"]
)

if uploaded_file is not None:
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        with st.spinner("Processing & cleaning 3D model file..."):
            # Load & Process Mesh
            loaded_data = trimesh.load(tmp_path)
            mesh = process_and_clean_mesh(loaded_data)

            # Check object type
            is_point_cloud = isinstance(mesh, trimesh.PointCloud)

            # 1. Calculate Bounding Box Dimensions
            extents_raw = mesh.extents  # Raw values from file
            width_x_m = extents_raw[0] * scale_to_m
            length_y_m = extents_raw[1] * scale_to_m
            height_z_m = extents_raw[2] * scale_to_m

            width_x_mm = width_x_m * 1000.0
            length_y_mm = length_y_m * 1000.0
            height_z_mm = height_z_m * 1000.0

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

        st.success("✅ File processed successfully!")
        
        # Split Layout: Left Column = 3D Viewer / Right Column = Metrics
        col_viewer, col_metrics = st.columns([1.2, 1])

        with col_viewer:
            st.subheader("🖥️ 3D Model Interactive Viewer")
            st.caption("คลิกลากเพื่อหมุน | สกรอลล์เพื่อซูม | คลิกขวาลากเพื่อ pan มุมมอง")
            html_viewer = render_3d_viewer(mesh)
            if html_viewer:
                components.html(html_viewer, height=510)
            else:
                st.info("No 3D Geometry available for rendering.")

        with col_metrics:
            # Display Dimensions
            st.subheader("📐 Model Dimensions")
            dim_col1, dim_col2, dim_col3 = st.columns(3)
            dim_col1.metric("Width (X)", f"{width_x_mm:.2f} mm", f"{width_x_m:.4f} m")
            dim_col2.metric("Length (Y)", f"{length_y_mm:.2f} mm", f"{length_y_m:.4f} m")
            dim_col3.metric("Height (Z)", f"{height_z_mm:.2f} mm", f"{height_z_m:.4f} m")

            st.markdown("---")

            # Display Surface Area & Volume
            st.subheader("📊 Surface Area & Volume")
            res_a, res_b = st.columns(2)
            res_a.metric("Total Surface Area", f"{surface_area_cm2:,.2f} cm²", f"{surface_area_m2:.6f} m²")
            
            if is_watertight:
                res_b.metric("Volume (Exact)", f"{volume_cm3:,.2f} cm³", f"{volume_m3:.6f} m³")
            elif used_convex_hull and volume_m3 > 0:
                res_b.metric("Volume (Convex Hull)", f"{volume_cm3:,.2f} cm³", f"{volume_m3:.6f} m³")
                st.info("💡 **Note:** Model is non-watertight or Point Cloud. Volume calculated using Convex Hull approximation.")
            else:
                res_b.info("Model mesh is non-watertight and volume couldn't be calculated.")

            # Mesh Info
            if not is_point_cloud and isinstance(mesh, trimesh.Trimesh):
                st.markdown("---")
                st.write(f"**Polygons (Faces):** `{len(mesh.faces):,}` | **Vertices:** `{len(mesh.vertices):,}`")

    except Exception as e:
        st.error(f"An error occurred while processing the file: {str(e)}")
    
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
