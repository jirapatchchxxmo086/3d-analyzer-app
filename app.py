import streamlit as st
import trimesh
import tempfile
import os

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="3D Model Analyzer", page_icon="📦", layout="centered")

st.title("📦 ระบบวิเคราะห์ขนาดและพื้นที่ผิวจากไฟล์ 3D")
st.write("อัปโหลดไฟล์โมเดล 3D เพื่อประมวลผลหาขนาดมิติ (กว้าง x ยาว x สูง) และพื้นที่ผิวชิ้นงานอัตโนมัติ")

st.divider()

# ตัวรับอัปโหลดไฟล์ 3D
uploaded_file = st.file_uploader(
    "เลือกไฟล์ 3D ที่ต้องการวิเคราะห์", 
    type=["stl", "obj", "ply", "off", "3mf"]
)

if uploaded_file is not None:
    # แยกนามสกุลไฟล์
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    
    # บันทึกลง Temporary File ชั่วคราวเพื่อให้ trimesh โหลดได้สมบูรณ์
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        with st.spinner("กำลังประมวลผลไฟล์ 3D..."):
            # โหลดไฟล์ 3D ผ่าน Trimesh
            mesh = trimesh.load(tmp_path)
            
            # กรณีไฟล์เป็น Scene ให้รวมวัตถุทั้งหมดเข้าด้วยกัน
            if isinstance(mesh, trimesh.Scene):
                mesh = mesh.dump(concatenate=True)

            # 1. คำนวณขนาดกว้าง x ยาว x สูง (Extents / Bounding Box)
            extents = mesh.extents  # ค่ามิติตามแกน [X, Y, Z]
            width_x = extents[0]
            length_y = extents[1]
            height_z = extents[2]

            # 2. คำนวณพื้นที่ผิว (Surface Area)
            surface_area_mm2 = mesh.area
            surface_area_cm2 = surface_area_mm2 / 100.0  # แปลง mm² เป็น cm²

        st.success("✅ ประมวลผลไฟล์สำเร็จ!")
        st.divider()

        # แสดงผลขนาด กว้าง x ยาว x สูง
        st.subheader("📐 ขนาดมิติชิ้นงาน (Dimensions)")
        col1, col2, col3 = st.columns(3)
        col1.metric("ความกว้าง (X)", f"{width_x:.2f} mm", f"{width_x/10.0:.2f} cm")
        col2.metric("ความยาว (Y)", f"{length_y:.2f} mm", f"{length_y/10.0:.2f} cm")
        col3.metric("ความสูง (Z)", f"{height_z:.2f} mm", f"{height_z/10.0:.2f} cm")

        # แสดงผลพื้นที่ผิวและปริมาตร
        st.subheader("📊 พื้นที่ผิวและปริมาตร (Surface Area & Volume)")
        res_a, res_b = st.columns(2)
        res_a.metric("พื้นที่ผิวรวม (Surface Area)", f"{surface_area_cm2:,.2f} cm²", f"{surface_area_mm2:,.2f} mm²")
        
        if mesh.is_watertight:
            volume_cm3 = mesh.volume / 1000.0  # แปลง mm³ เป็น cm³
            res_b.metric("ปริมาตรชิ้นงาน (Volume)", f"{volume_cm3:,.2f} cm³")
        else:
            res_b.info("โมเดลไม่ปิดสนิท (Non-watertight)\nจึงประเมินได้เฉพาะพื้นที่ผิว")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {str(e)}")
    
    finally:
        # ลบไฟล์ชั่วคราวออกจากระบบ
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
