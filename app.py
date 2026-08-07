import streamlit as st
import trimesh

st.set_page_config(
    page_title="3D Model Analyzer", page_icon="📦", layout="centered"
)

# โหลด CDN สคริปต์ของ Lucide Icons และตั้งค่าสไตล์ UI
st.markdown(
    """
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        .icon-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .icon-subtitle {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 20px;
            font-weight: 600;
            margin-top: 15px;
            margin-bottom: 10px;
        }
        .metric-card {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 14px 18px;
            margin-bottom: 10px;
        }
        .metric-label {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
            color: #6c757d;
        }
        .metric-val {
            font-size: 22px;
            font-weight: bold;
            color: #212529;
            margin-top: 4px;
        }
        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 15px;
            font-weight: 500;
            margin-top: 10px;
        }
        .status-solid {
            background-color: #e7f5ff;
            color: #1864ab;
            border: 1px solid #a5d8ff;
        }
        .status-leak {
            background-color: #fff9db;
            color: #f59f00;
            border: 1px solid #ffe066;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# ส่วนหัวข้อเว็บ
st.markdown(
    """
    <div class="icon-title">
        <i data-lucide="box"></i> 3D Model Analyzer
    </div>
""",
    unsafe_allow_html=True,
)

st.write(
    "อัปโหลดไฟล์ 3D (.stl, .obj) เพื่อคำนวณพื้นที่ผิว ปริมาตร และขนาดชิ้นงาน"
)

uploaded_file = st.file_uploader(
    "ลากไฟล์มาวางที่นี่ หรือกด Browse files", type=["stl", "obj"]
)

if uploaded_file is not None:
  with st.spinner("Processing 3D file..."):
    try:
      mesh = trimesh.load(
          uploaded_file, file_type=uploaded_file.name.split(".")[-1]
      )
      if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump(concatenate=True)

      surface_area_sqm = mesh.area / 1_000_000.0
      volume_cu_cm = mesh.volume / 1_000.0 if mesh.is_watertight else 0.0
      width, depth, height = mesh.extents

      st.success("Processing Completed Successfully!")

      col1, col2 = st.columns(2)

      with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label"><i data-lucide="blocks"></i> พื้นที่ผิว (Surface Area)</div>
                <div class="metric-val">{surface_area_sqm:.4f} sq.m.</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

      with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label"><i data-lucide="boxes"></i> ปริมาตร (Volume)</div>
                <div class="metric-val">{volume_cu_cm:.2f} cu.cm.</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

      st.markdown("---")

      st.markdown(
          """
            <div class="icon-subtitle">
                <i data-lucide="ruler"></i> ขนาดชิ้นงาน (Bounding Box)
            </div>
        """,
          unsafe_allow_html=True,
      )

      st.write(
          f"**กว้าง x ยาว x สูง:** {width:.1f} x {depth:.1f} x {height:.1f} มม."
      )

      # แสดงสถานะความสมบูรณ์ของ Mesh
      if mesh.is_watertight:
        st.markdown(
            """
            <div class="status-badge status-solid">
                <i data-lucide="square-mouse-pointer"></i> สถานะ: ชิ้นงานสมบูรณ์ (Solid Closed Mesh)
            </div>
        """,
            unsafe_allow_html=True,
        )
      else:
        st.markdown(
            """
            <div class="status-badge status-leak">
                <i data-lucide="square-dashed-mouse-pointer"></i> สถานะ: ชิ้นงานมีรูรั่วหรือไม่ใช่ Solid Mesh
            </div>
        """,
            unsafe_allow_html=True,
        )

    except Exception as e:
      st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")

# สคริปต์แปลง tag <i data-lucide="..."></i> ให้เป็น SVG Icons บนหน้าเว็บ
st.markdown("<script>lucide.createIcons();</script>", unsafe_allow_html=True)
