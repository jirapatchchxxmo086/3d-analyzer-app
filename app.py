import streamlit as st
import trimesh
import tempfile
import os

# Page configuration
st.set_page_config(page_title="3D Model Analyzer", page_icon="📦", layout="centered")

st.title("📦 3D Model Dimension & Surface Area Analyzer")
st.write("Upload a 3D model file to automatically extract bounding box dimensions (Width x Length x Height), surface area in sq.m., and volume.")

st.divider()

# File uploader component
uploaded_file = st.file_uploader(
    "Select a 3D model file", 
    type=["stl", "obj", "ply", "off", "3mf"]
)

if uploaded_file is not None:
    # Get file extension
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    
    # Save to a temporary file for Trimesh processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        with st.spinner("Processing 3D model file..."):
            # Load 3D model using Trimesh (Default coordinate units for 3D meshes are mm)
            mesh = trimesh.load(tmp_path)
            
            # If the model is a Scene, concatenate all geometries into a single mesh
            if isinstance(mesh, trimesh.Scene):
                mesh = mesh.dump(concatenate=True)

            # 1. Calculate Bounding Box Dimensions (X, Y, Z in mm and m)
            extents = mesh.extents  # Extents array [X, Y, Z]
            width_x = extents[0]
            length_y = extents[1]
            height_z = extents[2]

            # 2. Calculate Surface Area (Convert mm² to sq.m.)
            surface_area_mm2 = mesh.area
            surface_area_m2 = surface_area_mm2 / 1_000_000.0  # 1 sq.m. = 1,000,000 mm²
            surface_area_cm2 = surface_area_mm2 / 100.0

        st.success("✅ File processed successfully!")
        st.divider()

        # Display Dimensions
        st.subheader("📐 Model Dimensions")
        col1, col2, col3 = st.columns(3)
        col1.metric("Width (X)", f"{width_x/1000.0:.4f} m", f"{width_x:.2f} mm")
        col2.metric("Length (Y)", f"{length_y/1000.0:.4f} m", f"{length_y:.2f} mm")
        col3.metric("Height (Z)", f"{height_z/1000.0:.4f} m", f"{height_z:.2f} mm")

        # Display Surface Area & Volume
        st.subheader("📊 Surface Area & Volume")
        res_a, res_b = st.columns(2)
        res_a.metric("Total Surface Area", f"{surface_area_m2:.6f} sq.m.", f"{surface_area_cm2:,.2f} cm²")
        
        if mesh.is_watertight:
            volume_cm3 = mesh.volume / 1000.0
            volume_m3 = mesh.volume / 1_000_000_000.0  # 1 m³ = 1,000,000,000 mm³
            res_b.metric("Volume", f"{volume_m3:.6f} m³", f"{volume_cm3:,.2f} cm³")
        else:
            res_b.info("Model mesh is non-watertight.\nVolume calculation unavailable.")

    except Exception as e:
        st.error(f"An error occurred while processing the file: {str(e)}")
    
    finally:
        # Cleanup temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
