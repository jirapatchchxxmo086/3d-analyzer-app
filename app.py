import streamlit as st
import trimesh
import tempfile
import os

# 1. Page Configuration
st.set_page_config(
    page_title="3D Model Analyzer Pro",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Sidebar Controls: Customization Options
with st.sidebar:
    st.header("🎨 ปรับแต่งหน้าตาเว็บ (UI)")
    
    # Font Selection
    selected_font = st.selectbox(
        "เลือกฟอนต์ (Font):",
        ["Kanit", "Prompt", "Sarabun", "Inter", "Poppins"]
    )
    
    # Theme Selection
    theme_color = st.selectbox(
        "เลือกธีมสี (Color Theme):",
        ["Ocean Blue", "Sunset Purple", "Emerald Green", "Dark Mode"]
    )
    
    st.divider()
    st.header("⚙️ ตั้งค่าหน่วยวัด (Unit)")
    unit = st.selectbox(
        "หน่วยวัดของไฟล์:",
        ["มิลลิเมตร (mm)", "เซนติเมตร (cm)", "เมตร (m)", "นิ้ว (in)"]
    )
    unit_symbol = unit.split("(")[1].replace(")", "")
    
    st.divider()
    st.markdown("### 💡 ไฟล์ที่รองรับ")
    st.markdown("- `.stl` (Stereolithography)\n- `.obj` (Wavefront OBJ)\n- `.ply` (Polygon)\n- `.off` (Object Format)")

# 3. Dynamic CSS Setup based on user selection
THEMES = {
    "Ocean Blue": {"primary": "#2563EB", "secondary": "#3B82F6", "bg_grad": "linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%)", "card_border": "#BFDBFE"},
    "Sunset Purple": {"primary": "#7C3AED", "secondary": "#A855F7", "bg_grad": "linear-gradient(135deg, #5B21B6 0%, #7C3AED 100%)", "card_border": "#DDD6FE"},
    "Emerald Green": {"primary": "#059669", "secondary": "#10B981", "bg_grad": "linear-gradient(135deg, #065F46 0%, #10B981 100%)", "card_border": "#A7F3D0"},
    "Dark Mode": {"primary": "#F3F4F6", "secondary": "#6B7280", "bg_grad": "linear-gradient(135deg, #111827 0%, #1F2937 100%)", "card_border": "#374151"}
}

current_theme = THEMES[theme_color]

st.markdown(f"""
<style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600&family=Prompt:wght@300;400;600&family=Sarabun:wght@300;400;600&family=Inter:wght@300;400;600&family=Poppins:wght@300;400;600&display=swap');

    html, body, [class*="css"] {{
        font-family: '{selected_font}', sans-serif !important;
    }}

    /* Header Banner Styling */
    .header-banner {{
        background: {current_theme['bg_grad']};
        padding: 35px 20px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15);
    }}
    
    .header-banner h1 {{
        color: white !important;
        font-weight: 600;
        margin-bottom: 8px;
        font-size: 2.6rem;
    }}

    .header-banner p {{
        font-size: 1.15rem;
        opacity: 0.9;
        margin: 0;
    }}

    /* Modern Glassmorphism Cards */
    .metric-card {{
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        border: 1px solid {current_theme['card_border']};
        border-radius: 16px;
        padding: 22px 18px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    
    .metric-card:hover {{
        transform: translateY(-6px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
        border-color: {current_theme['primary']};
    }}

    .metric-value {{
        font-size: 1.85rem;
        font-weight: 600;
        color: {current_theme['primary']};
        margin-top: 8px;
    }}

    .metric-label {{
        font-size: 0.92rem;
        color: #4B5563;
        font-weight: 500;
    }}

    /* Status Badges */
    .badge-valid {{
        background-color: #DEF7EC;
        color: #03543F;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }}

    .badge-invalid {{
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }}
</style>
""", unsafe_allow_html=True)

# 4. Main Header Banner
st.markdown("""
    <div class="header-banner">
        <h1>🧊 3D Model Analyzer Pro</h1>
        <p>วิเคราะห์มิติ พื้นที่ผิว ปริมาตร และคำนวณราคาพิมพ์ 3D อัตโนมัติ</p>
    </div>
""", unsafe_allow_html=True)

# 5. File Upload Area
uploaded_file = st.file_uploader(
    "📤 ลากไฟล์ 3D มาวางที่นี่ หรือคลิกเพื่อเลือกไฟล์",
    type=["stl", "obj", "off", "ply"]
)

# 6. Model Processing & Tab Layout
if uploaded_file is not None:
    file_extension = f".{uploaded_file.name.split('.')[-1]}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_filepath = tmp_file.name

    try:
        mesh = trimesh.load(tmp_filepath)
        
        # Trigger Celebration Effect
        st.balloons()
        st.success(f"✅ โหลดและประมวลผลไฟล์สำเร็จ: **{uploaded_file.name}**")
        
        # Calculations
        surface_area = mesh.area
        is_watertight = mesh.is_watertight
        volume = mesh.volume if is_watertight else 0
        bounds = mesh.extents  # Size [X, Y, Z]

        # Use Tabs for Better Organization
        tab1, tab2, tab3 = st.tabs(["📊 ภาพรวมผลการคำนวณ", "📐 มิติและโครงสร้าง Mesh", "💰 ประเมินราคาพิมพ์ 3D"])

        # TAB 1: Main Metrics
        with tab1:
            st.write("")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">พื้นที่ผิวทั้งหมด (Surface Area)</div>
                        <div class="metric-value">{surface_area:,.2f} {unit_symbol}²</div>
                    </div>
                """, unsafe_allow_html=True)
                
            with col2:
                vol_display = f"{volume:,.2f} {unit_symbol}³" if is_watertight else "N/A (โมเดลมีช่องเปิด)"
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">ปริมาตรชิ้นงาน (Volume)</div>
                        <div class="metric-value">{vol_display}</div>
                    </div>
                """, unsafe_allow_html=True)

            with col3:
                status_html = '<span class="badge-valid">✓ ปิดสนิท (Watertight)</span>' if is_watertight else '<span class="badge-invalid">✕ มีช่องเปิด (Non-watertight)</span>'
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">สถานะของโมเดล (Mesh Status)</div>
                        <div style="margin-top: 10px;">{status_html}</div>
                    </div>
                """, unsafe_allow_html=True)

        # TAB 2: Dimensions & Mesh Details
        with tab2:
            st.write("")
            st.markdown("### 📐 ขนาดขอบเขตชิ้นงาน (Bounding Box Dimensions)")
            dim1, dim2, dim3 = st.columns(3)
            
            with dim1:
                st.metric("แกน X (ความกว้าง)", f"{bounds[0]:,.2f} {unit_symbol}")
            with dim2:
                st.metric("แกน Y (ความยาว)", f"{bounds[1]:,.2f} {unit_symbol}")
            with dim3:
                st.metric("แกน Z (ความสูง)", f"{bounds[2]:,.2f} {unit_symbol}")

            st.divider()
            st.markdown("### 🔍 โครงสร้างจุดและพื้นผิว (Topology Summary)")
            detail1, detail2 = st.columns(2)
            with detail1:
                st.info(f"• **จำนวนจุดยอด (Vertices):** {len(mesh.vertices):,} จุด")
            with detail2:
                st.info(f"• **จำนวนพื้นผิวสามเหลี่ยม (Faces):** {len(mesh.faces):,} หน้า")

        # TAB 3: 3D Printing Cost Estimator (Extra Feature)
        with tab3:
            st.write("")
            st.markdown("### 💡 ประมาณการน้ำหนักและค่าพิมพ์ 3D (3D Print Estimator)")
            
            if not is_watertight:
                st.warning("⚠️ โมเดลมีช่องเปิด (Non-watertight) ปริมาตรอาจไม่แม่นยำ 100%")

            est_col1, est_col2 = st.columns(2)
            
            with est_col1:
                material = st.selectbox("ชนิดเส้นพลาสติก (Filament):", ["PLA (1.24 g/cm³)", "ABS (1.04 g/cm³)", "PETG (1.27 g/cm³)"])
                densities = {"PLA (1.24 g/cm³)": 1.24, "ABS (1.04 g/cm³)": 1.04, "PETG (1.27 g/cm³)": 1.27}
                density = densities[material]
                
                infill = st.slider("เปอร์เซ็นต์ความหนาแน่นไส้ใน (Infill %):", 10, 100, 20, step=5)
                cost_per_gram = st.number_input("ราคาพิมพ์ต่อกรัม (บาท/กรัม):", value=2.5, step=0.5)

            with est_col2:
                # Calculate estimated mass in cm³ (Assuming standard units convert to cm³)
                # Convert volume to cm³ if units differ
                vol_cm3 = volume
                if "mm" in unit:
                    vol_cm3 = volume / 1000.0
                elif "m" in unit and "mm" not in unit:
                    vol_cm3 = volume * 1000000.0

                estimated_infill_vol = vol_cm3 * (infill / 100.0)
                estimated_weight_g = estimated_infill_vol * density
                estimated_cost_thb = estimated_weight_g * cost_per_gram

                st.markdown(f"""
                    <div style="background:#F3F4F6; padding:20px; border-radius:14px; border:1px solid #E5E7EB; margin-top:10px;">
                        <h4 style="margin:0; color:#374151;">📊 ผลการประเมินราคา</h4>
                        <p style="margin-top:10px; font-size:1.1rem;">• น้ำหนักโดยประมาณ: <b style="color:#2563EB;">{estimated_weight_g:,.2f} กรัม</b></p>
                        <p style="font-size:1.1rem;">• ราคาค่าพิมพ์ประมาณ: <b style="color:#059669;">{estimated_cost_thb:,.2f} บาท</b></p>
                    </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
    finally:
        if os.path.exists(tmp_filepath):
            os.remove(tmp_filepath)
else:
    st.info("👋 กรุณาอัปโหลดไฟล์ 3D ด้านบนเพื่อเริ่มต้นการวิเคราะห์")
```

---
