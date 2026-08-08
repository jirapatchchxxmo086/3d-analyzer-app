import streamlit as st
import trimesh

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="3D Model Analyzer Pro", page_icon="📦", layout="centered"
)

# 2. ปรับแต่ง Font ผ่าน Sidebar
st.sidebar.header("⚙️ ตั้งค่ารูปแบบหน้าเว็บ")

font_choice = st.sidebar.selectbox(
    "เลือกฟอนต์ (Font)",
    options=["Kanit", "Prompt", "Sarabun", "Inter", "Poppins"],
    index=0,
)

# 3. โหลด Font Awesome Icons, Google Fonts และสั่งการ CSS
st.markdown(
    f"""
    <!-- โหลด Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- โหลด Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Kanit:wght@300;400;600&family=Poppins:wght@400;600&family=Prompt:wght@300;400;600&family=Sarabun:wght@300;400;600&display=swap" rel="stylesheet">
    
    <style>
        html, body, [class*="css"] {{
            font-family: '{font_choice}', sans-serif;
        }}
        .icon-title {{
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 30px;
            font-weight: 700;
            color: #2563eb;
            margin-bottom: 5px;
        }}
        .icon-subtitle {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 20px;
            font-weight: 600;
            color: #334155;
            margin-top: 15px;
            margin-bottom: 10px;
        }}
        .metric-card {{
            background-color: #f0f6ff;
            border: 1px solid #bfdbfe;
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }}
        .metric-label {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            color: #64748b;
        }}
        .metric-val {{
            font-size: 24px;
            font-weight: 700;
            color: #0f172a;
            margin-top: 6px;
        }}
        .status-badge {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px 18px;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            margin-top: 15px;
        }}
        .status-solid {{
            background-color: #dcfce7;
            color: #166534;
            border: 1px solid #86efac;
        }}
        .status-leak {{
            background-color: #fef9c3;
            color: #854d0e;
            border: 1px solid #fde047;
        }}
    </style>
""",
    unsafe_allow_html=True,
)

# 4. ส่วนหัวข้อหลัก
st.markdown(
    """
    <div class="icon-title">
        <i class="fa-solid fa-cube"></i> 3D Model Analyzer Pro
    </div>
""",
    unsafe_allow_html=True,
)

st.write(
    "อัปโหลดไฟล์ 3D (.stl, .obj) เพื่อวิเคราะห์พื้นที่ผิว ปริมาตร ขนาดโครงสร้าง"
    " และประมาณการต้นทุนการพิมพ์ 3D"
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
            volume_cu_cm = (
                mesh.volume / 1_000.0 if mesh.is_watertight else 0.0
            )
            width, depth, height = mesh.extents

            st.success("Processing Completed Successfully!")

            # เอฟเฟกต์ดาวพาสเทลลอยละมุน ✨
            st.markdown(
                """
                <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
                <script>
                    confetti({
                        particleCount: 35,
                        spread: 60,
                        origin: { y: 0.6 },
                        colors: ['#ffb7b2', '#ffdac1', '#e2f0cb', '#b5edd4', '#c7ceea'],
                        gravity: 0.5,
                        ticks: 250,
                        scalar: 0.9
                    });
                </script>
            """,
                unsafe_allow_html=True,
            )

            # ระบบ Tab
            tab1, tab2, tab3 = st.tabs([
                "📊 ภาพรวม (Summary)",
                "📏 ขนาดชิ้นงาน (Dimensions)",
                "💰 ประมาณการราคาพิมพ์ (3D Cost)",
            ])

            with tab1:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <div class="metric-label"><i class="fa-solid fa-layer-group"></i> พื้นที่ผิว (Surface Area)</div>
                            <div class="metric-val">{surface_area_sqm:.4f} sq.m.</div>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.markdown(
                        f"""
                        <div class="metric-card">
                            <div class="metric-label"><i class="fa-solid fa-cubes"></i> ปริมาตร (Volume)</div>
                            <div class="metric-val">{volume_cu_cm:.2f} cu.cm.</div>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )

                if mesh.is_watertight:
                    st.markdown(
                        """
                        <div class="status-badge status-solid">
                            <i class="fa-solid fa-circle-check"></i> สถานะ: ชิ้นงานสมบูรณ์ (Solid Closed Mesh)
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        """
                        <div class="status-badge status-leak">
                            <i class="fa-solid fa-triangle-exclamation"></i> สถานะ: ชิ้นงานมีรูรั่วหรือไม่ใช่ Solid Mesh
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )

            with tab2:
                st.markdown(
                    """
                    <div class="icon-subtitle">
                        <i class="fa-solid fa-ruler-combined"></i> Bounding Box Dimensions
                    </div>
                """,
                    unsafe_allow_html=True,
                )

                col_w, col_d, col_h = st.columns(3)
                col_w.metric("ความกว้าง (Width)", f"{width:.1f} mm")
                col_d.metric("ความยาว (Depth)", f"{depth:.1f} mm")
                col_h.metric("ความสูง (Height)", f"{height:.1f} mm")

                with st.expander(
                    "🔍 รายละเอียดทางเทคนิคเพิ่มเติม (Advanced Specs)"
                ):
                    st.write(f"**จำนวน Vertices:** {len(mesh.vertices):,}")
                    st.write(f"**จำนวน Faces:** {len(mesh.faces):,}")

            with tab3:
                st.markdown(
                    """
                    <div class="icon-subtitle">
                        <i class="fa-solid fa-calculator"></i> 3D Printing Cost Estimator
                    </div>
                """,
                    unsafe_allow_html=True,
                )

                material = st.selectbox(
                    "เลือกประเภทเส้นพลาสติก", ["PLA", "ABS", "PETG"]
                )
                density_map = {"PLA": 1.24, "ABS": 1.04, "PETG": 1.27}
                infill = st.slider("เปอร์เซ็นต์ Infill (%)", 10, 100, 20)
                price_per_gram = st.number_input(
                    "ราคาเส้นพลาสติก (บาท/กรัม)", value=0.8
                )

                # คำนวณน้ำหนักและราคาประมาณการ
                estimated_weight = (
                    volume_cu_cm * density_map[material] * (infill / 100)
                )
                estimated_cost = estimated_weight * price_per_gram

                c1, c2 = st.columns(2)
                c1.metric(
                    "น้ำหนักประมาณการ (Weight)", f"{estimated_weight:.1f} grams"
                )
                c2.metric("ค่าวัสดุประมาณการ (Cost)", f"฿{estimated_cost:.2f}")

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
