import streamlit as st
import trimesh
import os
import tempfile
import pandas as pd

# ==========================================
# ⚙️ 1. ตั้งค่าหน้าเว็บ Streamlit
# ==========================================
st.set_page_config(
    page_title="3D Cost Estimation & Quotation Tool",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 3D Cost Estimation & Quotation System")
st.caption("ระบบวิเคราะห์ไฟล์ 3D คำนวณพื้นที่ผิว ชั่วโมง Robot และประเมินราคาต้นทุนอัตโนมัติ")

# ==========================================
# 📊 2. Master Data & Logic การคำนวณ
# ==========================================
# ตัวคูณชั่วโมง Robot ต่อ ตร.ม. ตาม Level (1-10)
LEVEL_FACTORS = {
    1: 1.0, 2: 1.5, 3: 2.5, 4: 3.5, 5: 5.0,
    6: 6.5, 7: 8.0, 8: 10.0, 9: 12.0, 10: 15.0
}

# ราคา Hard Coat ต่อ ตร.ม.
HARDCOAT_RATES = {
    "ไม่มี (None)": 0,
    "Polyurea": 1350,
    "Mold Fiber": 1520,
    "Fiberglass (Work)": 1090,
    "Epoxy": 600
}

# ราคาทำสี (Color Type) ต่อ ตร.ม.
COLOR_RATES = {
    "ไม่มี (None)": 0,
    "Normal": 1440,
    "Chromium": 4800,
    "The Code": 1800,
    "Gold leaves": 168,
    "Sticker": 1200
}

# ==========================================
# 🛑 3. ระบบเซฟตี้ ป้องกันไฟล์ใหญ่เกินไป
# ==========================================
MAX_FILE_SIZE_MB = 80

# ==========================================
# 📂 4. ส่วนอัปโหลดและประมวลผลไฟล์ 3D
# ==========================================
st.subheader("1. อัปโหลดไฟล์โมเดล 3D")
uploaded_file = st.file_uploader("รองรับไฟล์ .STL, .OBJ, .PLY, .3MF", type=["stl", "obj", "ply", "3mf"])

# กำหนดค่าเริ่มต้นสำหรับพื้นที่ผิวและขนาด
surface_area_sqm = 0.0
dimensions_str = "0 x 0 x 0"

if uploaded_file is not None:
    # Check File Size
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        st.error(f"⛔ ไฟล์มีขนาดใหญ่เกินไป ({file_size_mb:.1f} MB)! จำกัดไม่เกิน {MAX_FILE_SIZE_MB} MB")
        st.stop()

    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        with st.spinner("กำลังอ่านและคำนวณโครงสร้างโมเดล 3D..."):
            mesh = trimesh.load(tmp_path)
            
            # คำนวณขนาดและพื้นที่ผิว
            if hasattr(mesh, 'area'):
                # แปลง mm² เป็น m² (1 m² = 1,000,000 mm²)
                surface_area_sqm = mesh.area / 1_000_000.0
                
            # ขนาดกว้าง x ยาว x สูง (mm)
            extents = mesh.extents
            dimensions_str = f"{extents[0]:.0f}*{extents[1]:.0f}*{extents[2]:.0f}"

            st.success(f"✅ อ่านไฟล์สำเร็จ: **{uploaded_file.name}**")
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("ขนาดชิ้นงาน (กxยxส mm)", dimensions_str)
            col_m2.metric("พื้นที่ผิวรวม (sq.m.)", f"{surface_area_sqm:.3f} ตร.ม.")
            col_m3.metric("จำนวน Triangles/Faces", f"{len(mesh.faces):,} Faces")

    except Exception as e:
        st.error(f" เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
        st.stop()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

st.divider()

# ==========================================
# 🧮 5. ฟอร์มป้อนข้อมูลการประเมินราคา
# ==========================================
st.subheader("2. ตั้งค่าเงื่อนไขการประเมินราคา (Quotation Inputs)")

col_input1, col_input2 = st.columns(2)

with col_input1:
    st.markdown("##### 📌 ข้อมูลงานและระดับความซับซ้อน")
    project_name = st.text_input("ชื่อชิ้นงาน / ลูกค้า", value="Model Project 1")
    complexity_level = st.slider("ระดับความซับซ้อน (Level 1-10)", min_value=1, max_value=10, value=5)
    
    manual_area = st.number_input("พื้นที่ทำสี/เคลือบผิว (sq.m.) [ปรับแก้ได้]", min_value=0.0, value=float(surface_area_sqm), step=0.1)

with col_input2:
    st.markdown("##### 🪵 วัสดุพิเศษเพิ่มเติม")
    use_plywood = st.checkbox("เพิ่ม ไม้อัดยางมารีน 20mm")
    plywood_qty = 0
    plywood_price_per_unit = 4000
    if use_plywood:
        plywood_qty = st.number_input("จำนวนแผ่นไม้อัด", min_value=1, value=1)
        # เงื่อนไขราคาสั่งซื้อขั้นต่ำ 100 แผ่น
        if plywood_qty >= 100:
            plywood_price_per_unit = 3500
            st.caption("🎉 ได้รับราคาสั่งซื้อขั้นต่ำ (≥ 100 แผ่น): 3,500 บาท/แผ่น")
        else:
            plywood_price_per_unit = 4000
            st.caption("ราคาปกติ (< 100 แผ่น): 4,000 บาท/แผ่น")

st.markdown("##### ⚙️ เลือกกระบวนการเครื่องจักร (Operations & Machines)")
col_op1, col_op2, col_op3, col_op4 = st.columns(4)

with col_op1:
    st.markdown("**1. Robot Milling**")
    use_robot = st.checkbox("ใช้งาน Robot", value=True)
    robot_rate = st.number_input("ค่าเครื่อง Robot (Baht/Hr)", value=300)
    robot_prog_time = st.number_input("Program time (Hr)", value=0.5, key="r_prog")
    robot_setup_time = st.number_input("Setup time (Hr)", value=0.5, key="r_setup")
    # คำนวณ Machine time จากพื้นที่ผิว * Factor
    factor = LEVEL_FACTORS.get(complexity_level, 5.0)
    calc_robot_mch_time = manual_area * factor
    robot_mch_time = st.number_input("Machine time (Hr)", value=float(calc_robot_mch_time), key="r_mch")
    robot_mat_cost = st.number_input("ค่าวัสดุ Robot (Baht)", value=2850)

with col_op2:
    st.markdown("**2. 3D Print FDM**")
    use_fdm = st.checkbox("ใช้งาน 3D Print", value=False)
    fdm_rate = st.number_input("ค่าเครื่อง 3D Print (Baht/Hr)", value=50)
    fdm_prog_time = st.number_input("Program time (Hr)", value=0.5, key="f_prog")
    fdm_setup_time = st.number_input("Setup time (Hr)", value=0.5, key="f_setup")
    fdm_mch_time = st.number_input("Machine time (Hr)", value=17.0, key="f_mch")
    fdm_mat_cost = st.number_input("ค่าวัสดุ 3D Print (Baht)", value=480)

with col_op3:
    st.markdown("**3. Structure / Assembly**")
    use_structure = st.checkbox("งานโครงสร้าง", value=False)
    structure_mat_cost = st.number_input("ค่าวัสดุโครงสร้าง (Baht)", value=720)

with col_op4:
    st.markdown("**4. Fiber Laser N2**")
    use_laser = st.checkbox("ใช้งาน Fiber Laser", value=False)
    laser_rate = st.number_input("ค่าเครื่อง Laser (Baht/Hr)", value=2400)
    laser_prog_time = st.number_input("Program time (Hr)", value=0.5, key="l_prog")
    laser_setup_time = st.number_input("Setup time (Hr)", value=0.5, key="l_setup")
    laser_mch_time = st.number_input("Machine time (Hr)", value=0.5, key="l_mch")
    laser_mat_cost = st.number_input("ค่าวัสดุ Laser (Baht)", value=648)

st.markdown("##### 🎨 งานเคลือบผิวและทำสี (Hard Coat & Finishing)")
col_coat1, col_coat2 = st.columns(2)
with col_coat1:
    selected_hardcoat = st.selectbox("ประเภท Hard Coat", list(HARDCOAT_RATES.keys()))
with col_coat2:
    selected_color = st.selectbox("ประเภทการทำสี (Color Type)", list(COLOR_RATES.keys()))

st.divider()

# ==========================================
# 📈 6. ประมวลผลตารางใบประเมินราคา (Summary)
# ==========================================
st.subheader("📋 สรุปใบประเมินราคา (Cost Estimation Summary)")

# คำนวณ Operation Robot
robot_total_time = (robot_prog_time + robot_setup_time + robot_mch_time) if use_robot else 0
robot_total_mch_cost = robot_total_time * robot_rate if use_robot else 0
robot_mat = robot_mat_cost if use_robot else 0

# คำนวณ Operation FDM
fdm_total_time = (fdm_prog_time + fdm_setup_time + fdm_mch_time) if use_fdm else 0
fdm_total_mch_cost = fdm_total_time * fdm_rate if use_fdm else 0
fdm_mat = fdm_mat_cost if use_fdm else 0

# คำนวณ Structure
struct_mat = structure_mat_cost if use_structure else 0

# คำนวณ Laser
laser_total_time = (laser_prog_time + laser_setup_time + laser_mch_time) if use_laser else 0
laser_total_mch_cost = laser_total_time * laser_rate if use_laser else 0
laser_mat = laser_mat_cost if use_laser else 0

# ค่าไม้อัดยางมารีน
plywood_total_cost = plywood_qty * plywood_price_per_unit if use_plywood else 0

# คำนวณราคารวมขั้นต้น
total_machine_cost = robot_total_mch_cost + fdm_total_mch_cost + laser_total_mch_cost
total_material_cost = robot_mat + fdm_mat + struct_mat + laser_mat + plywood_total_cost
prototype_cost = total_machine_cost + total_material_cost

# คำนวณ Hard Coat & Color
hardcoat_unit_cost = HARDCOAT_RATES[selected_hardcoat]
hardcoat_total_cost = manual_area * hardcoat_unit_cost

color_unit_cost = COLOR_RATES[selected_color]
color_total_cost = manual_area * color_unit_cost

grand_total_cost = prototype_cost + hardcoat_total_cost + color_total_cost

# แสดงผลแบบ Card Summary
col_res1, col_res2, col_res3, col_res4 = st.columns(4)
col_res1.metric("ชั่วโมง Robot รวม", f"{robot_total_time:.1f} ชม.")
col_res2.metric("รวมค่าเครื่องจักร (Machine)", f"฿{total_machine_cost:,.2f}")
col_res3.metric("รวมค่าวัสดุ (Material)", f"฿{total_material_cost:,.2f}")
col_res4.metric("💰 ราคาสรุปสุทธิ (Grand Total)", f"฿{grand_total_cost:,.2f}", delta_color="normal")

# ตารางเปรียบเทียบรายละเอียด
summary_data = {
    "รายการ (Process)": ["1. Robot", "2. 3D Print FDM", "3. Structure", "4. Fiber Laser N2", "5. ไม้อัดยางมารีน 20mm"],
    "เวลาทำงานรวม (Hr)": [f"{robot_total_time:.1f}", f"{fdm_total_time:.1f}", "-", f"{laser_total_time:.1f}", "-"],
    "ค่าเครื่องจักร (Baht)": [f"฿{robot_total_mch_cost:,.2f}", f"฿{fdm_total_mch_cost:,.2f}", "฿0.00", f"฿{laser_total_mch_cost:,.2f}", "฿0.00"],
    "ค่าวัสดุ (Baht)": [f"฿{robot_mat:,.2f}", f"฿{fdm_mat:,.2f}", f"฿{struct_mat:,.2f}", f"฿{laser_mat:,.2f}", f"฿{plywood_total_cost:,.2f}"]
}

df_summary = pd.DataFrame(summary_data)
st.table(df_summary)

st.markdown(f"""
> **รายละเอียดเพิ่มเติมเกี่ยวกับงานผิว/สี:**
> * **Hard Coat ({selected_hardcoat}):** {manual_area:.2f} ตร.ม. × ฿{hardcoat_unit_cost:,} = **฿{hardcoat_total_cost:,.2f}**
> * **Color ({selected_color}):** {manual_area:.2f} ตร.ม. × ฿{color_unit_cost:,} = **฿{color_total_cost:,.2f}**
""")
