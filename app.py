import streamlit as st
import trimesh
import tempfile
import os

# Page configuration
st.set_page_config(page_title="3D Model Analyzer", page_icon="📦", layout="centered")

st.title("📦 3D Model Dimension & Surface Area Analyzer")
st.write("Upload a 3D model file to automatically extract bounding box dimensions, surface area, and volume.")

# Sidebar for Model Unit Selection (แก้ปัญหาไฟล์ 3D ไม่มีระบุหน่วยวัด)
st.sidebar.header("⚙️ Unit Settings")
unit_input = st.sidebar.selectbox(
    "Select Model File Unit",
    options=["Meters (m)", "Millimeters (mm)", "Centimeters (cm)"],
    index=0,  # ตั้ง Default เป็น Meters (m) ตามมาตรฐานไฟล์ OBJ/PLY
    help="3D formats (OBJ, STL, PLY) store raw numbers without units. Select the unit used when creating the model."
)

# Scaling Factor to standard Meters
if unit_input == "Meters (m)":
    scale_to_m = 1.0
elif unit_input == "Millimeters (mm)":
    scale_to_m = 0.001
else:  # Centimeters (cm)
    scale_to_m = 0.01

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
        with st.spinner("Processing 3D model file..."):
            # Load 3D model
            loaded_data = trimesh.load(tmp_path)
            
            # Handle Scene objects
            if isinstance(loaded_data, trimesh.Scene):
                mesh = loaded_data.dump(concatenate=True)
            else:
                mesh = loaded_data

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
                # Point cloud has no faces, calculate via Convex Hull
                hull = mesh.convex_hull
                surface_area_m2 = hull.area * (scale_to_m ** 2)
                volume_m3 = hull.volume * (scale_to_m ** 3)
                used_convex_hull = True
            else:
                # Standard Mesh
                surface_area_m2 = mesh.area * (scale_to_m ** 2)
                is_watertight = getattr(mesh, 'is_watertight', False)

                if is_watertight:
                    volume_m3 = mesh.volume * (scale_to_m ** 3)
                else:
                    # Fallback for non-watertight mesh: Calculate volume using Convex Hull
                    try:
                        hull = mesh.convex_hull
                        volume_m3 = hull.volume * (scale_to_m ** 3)
                        used_convex_hull = True
                    except Exception:
                        volume_m3 = 0.0

            surface_area_cm2 = surface_area_m2 * 10_000.0
            volume_cm3 = volume_m3 * 1_000_000.0

        st.success("✅ File processed successfully!")
        st.divider()

        # Display Dimensions
        st.subheader("📐 Model Dimensions")
        col1, col2, col3 = st.columns(3)
        col1.metric("Width (X)", f"{width_x_m:.4f} m", f"{width_x_mm:.2f} mm")
        col2.metric("Length (Y)", f"{length_y_m:.4f} m", f"{length_y_mm:.2f} mm")
        col3.metric("Height (Z)", f"{height_z_m:.4f} m", f"{height_z_mm:.2f} mm")

        # Display Surface Area & Volume
        st.subheader("📊 Surface Area & Volume")
        res_a, res_b = st.columns(2)
        res_a.metric("Total Surface Area", f"{surface_area_m2:.6f} sq.m.", f"{surface_area_cm2:,.2f} cm²")
        
        if is_watertight:
            res_b.metric("Volume (Exact)", f"{volume_m3:.6f} m³", f"{volume_cm3:,.2f} cm³")
        elif used_convex_hull and volume_m3 > 0:
            res_b.metric("Volume (Convex Hull)", f"{volume_m3:.6f} m³", f"{volume_cm3:,.2f} cm³")
            st.info("💡 **Note:** Model is non-watertight or Point Cloud. Volume calculated using Convex Hull approximation.")
        else:
            res_b.info("Model mesh is non-watertight and volume couldn't be calculated.")

    except Exception as e:
        st.error(f"An error occurred while processing the file: {str(e)}")
    
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
