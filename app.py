import streamlit as st
import trimesh

st.set_page_config(
    page_title="3D Model Analyzer", page_icon="📦", layout="centered"
)
st.title("📦 3D Model Analyzer")
st.write(
    "อัปโหลดไฟล์ 3D (.stl, .obj) เพื่อคำนวณพื้นที่ผิว ปริมาตร และขนาดชิ้นงาน"
)

uploaded_file = st.file_uploader(
    "ลากไฟล์มาวางที่นี่ หรือกด Browse files", type=["stl", "obj"]
)

if uploaded_file is not None:
  with st.spinner("กำลังประมวลผลไฟล์ 3D..."):
    try:
      mesh = trimesh.load(
          uploaded_file, file_type=uploaded_file.name.split(".")[-1]
      )
      if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)

      surface_area_sqm = mesh.area / 1_000_000.0
      volume_cu_cm = mesh.volume / 1_000.0 if mesh.is_watertight else 0.0
      width, depth, height = mesh.extents

      st.success("ประมวลผลสำเร็จ!")
      col1, col2 = st.columns(2)
      col1.metric("📐 พื้นที่ผิว (Surface Area)", f"{surface_area_sqm:.4f} sq.m.")
      col2.metric("📦 ปริมาตร (Volume)", f"{volume_cu_cm:.2f} cu.cm.")

      st.markdown("---")
      st.subheader("📏 ขนาดชิ้นงาน (Bounding Box)")
      st.write(
          f"**กว้าง x ยาว x สูง:** {width:.1f} x {depth:.1f} x {height:.1f} มม."
      )

      if mesh.is_watertight:
        st.info("🔒 ชิ้นงานสมบูรณ์ (Solid Closed Mesh)")
      else:
        st.warning("⚠️ ชิ้นงานมีรูรั่วหรือไม่ใช่ Solid Mesh")
    except Exception as e:
      st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
