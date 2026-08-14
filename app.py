import streamlit as st
import trimesh
import os
import tempfile
import pandas as pd

# ==========================================
# ⚙️ 1. ตั้งค่าหน้าเว็บ
# ==========================================
st.set_page_config(
    page_title="3D Model Analyzer & Cost Estimator",
    page_icon="🤖",
    layout="wide"
)

# ==========================================
# 🔄 2. สปินและจัดเก็บ Session State (ส่งข้ามหน้า)
# ==========================================
if "surface_area_sqm" not in st.session_state:
    st.session_state["surface_area_sqm"] = 0.0
if "dimensions_str" not in st.session_state:
    st.session_state["dimensions_str"] = "0 * 0 * 0"
if "mesh_faces" not in st.session_state:
    st.session_state["mesh_faces"] = 0
if "file_name" not in st.session_state:
    st.session_state["file_name"] = "ยังไม่ได้เลือกไฟล์"

# ==========================================
# 🧭 3. เมนูนำทาง (Sidebar Navigation)
# ==========================================
st.sidebar.title("📌 เมนูหลัก")
page = st.sidebar.radio(
    "เลือกหน้าต่างทำงาน:",
    ["📦 หน้า 1: อัปโหลด & ประเมินพื้นที่ 3D", "💰 หน้าที่ 2: คำนวณราคา & ใบประเมิน"]
)

st.sidebar.divider()
st.sidebar.markdown(f"""
**สรุปข้อมูลโมเดลปัจจุบัน:**
* **ไฟล์:** `{st.session_state['file_name']}`
* **ขนาด:** `{st.session_state['dimensions_str']}` mm
* **พื้นที่ผิว:** `{st.session_state['surface_area_sqm']:.3f}` sq.m.
""")

# ==========================================
# 🛑 ค่าคงที่ Safety Constraint
# ==========================================
MAX_FILE_SIZE_MB = 80

# ==========================================
# 📦 หน้า 1: อัปโหลด & ประเมินพื้นที่ 3D
# ==========================================
if page == "📦 หน้า 1: อัปโหลด & ประเมินพื้นที่ 3D":
    st.title("📦 หน้า 1: วิเคราะห์โมเดล 3D & คำนวณพื้นที่ผิว")
    st.caption("อัปโหลดไฟล์ 3D เพื่อตรวจสอบขนาด โครงสร้างสามเหลี่ยม และคำนวณพื้นที่ผิวอัตโนมัติ")

    uploaded_file = st.file_uploader(
        "อัปโหลดไฟล์ 3D (.STL, .OBJ, .PLY, .3MF)", 
        type=["stl", "obj", "ply", "3mf"]
    )

    if uploaded_file is not None:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            st.error(f"⛔ ไฟล์มีขนาดใหญ่เกินไป ({file_size_mb:.1f} MB)! ระบบจำกัดไม่เกิน {MAX_FILE_SIZE_MB} MB เพื่อป้องกันระบบล่ม")
            st.stop()

        file_ext = os.path.splitext(uploaded_file.name)[1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            with st.spinner("กำลังประมวลผลโมเดล 3D..."):
                mesh = trimesh.load(tmp_path)

                # คำนวณค่าต่างๆ
                area_sqm = (mesh.area / 1_000_000.0) if hasattr(mesh, 'area') else 0.0
                extents = mesh.extents
                dim_str = f"{extents[0]:.0f}*{extents[1]:.0f}*{extents[2]:.0f}"
                faces_count = len(mesh.faces) if hasattr(mesh, 'faces') else 0

                # บันทึกเข้า Session State เพื่อนำไปใช้ต่อในหน้าที่ 2
                st.session_state["surface_area_sqm"] = area_sqm
                st.session_state["dimensions_str"] = dim_str
                st.session_state["mesh_faces"] = faces_count
                st.session_state["file_name"] = uploaded_file.name

                st.success("✅ ประมวลผลและบันทึกข้อมูลสำเร็จ!")

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
            st.stop()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # แสดงผลข้อมูลที่คำนวณได้
    st.subheader("📊 ผลการวิเคราะห์โมเดล 3D")
    col1, col2, col3 = st.columns(3)
    col1.metric("ขนาดชิ้นงาน (กxยxส mm)", st.session_state["dimensions_str"])
    col2.metric("พื้นที่ผิวรวม (sq.m.)", f"{st.session_state['surface_area_sqm']:.3f} ตร.ม.")
    col3.metric("จำนวน Triangles/Faces", f"{st.session_state['mesh_faces']:,} Faces")

    st.divider()
    if st.session_state["surface_area_sqm"] > 0:
        st.info("💡 ข้อมูลพื้นที่ผิวและขนาดชิ้นงานถูกบันทึกเรียบร้อยแล้ว กดเลือก **'หน้า 2: คำนวณราคา & ใบประเมิน'** ทางแถบเมนูด้านซ้ายเพื่อประเมินราคาต่อได้เลย")

# ==========================================
# 💰 หน้าที่ 2: คำนวณราคา & ใบประเมิน
# ==========================================
elif page == "💰 หน้าที่ 2: คำนวณราคา & ใบประเมิน":
    st.title("💰 หน้าที่ 2: คำนวณต้นทุนและออกใบประเมินราคา")
    st.caption("ระบบดึงข้อมูลพื้นที่ผิวจากหน้าแรกมาประมวลผลร่วมกับสูตรคำนวณ Robot และ Master Data")

    # Master Data Tables
    LEVEL_FACTORS = {1: 1.0, 2: 1.5, 3: 2.5, 4: 3.5, 5: 5.0, 6: 6.5, 7: 8.0, 8: 10.0, 9: 12.0, 10: 15.0}
    HARDCOAT_RATES = {"ไม่มี (None)": 0, "Polyurea": 1350, "Mold Fiber": 1520, "Fiberglass (Work)": 1090, "Epoxy": 600}
    COLOR_RATES = {"ไม่มี (None)": 0, "Normal": 1440, "Chromium": 4800, "The Code": 1800, "Gold leaves": 168, "Sticker": 1200}

    # Input Form
    col_in1, col_in2 = st.columns(2)

    with col_in1:
        st.markdown("##### 📌 ข้อมูลงาน & ระดับความซับซ้อน")
        project_name = st.text_input("ชื่อชิ้นงาน / ลูกค้า", value=st.session_state["file_name"])
        complexity_level = st.slider("ระดับความซับซ้อน (Level 1-10)", min_value=1, max_value=10, value=5)
        
        # ดึงพื้นที่ผิวอัตโนมัติ
        calc_area = st.number_input(
            "พื้นที่ทำสี/เคลือบผิว (sq.m.)", 
            min_value=0.0, 
            value=float(st.session_state["surface_area_sqm"]), 
            step=0.1
        )

    with col_in2:
        st.markdown("##### 🪵 วัสดุพิเศษ (ไม้อัดยางมารีน 20mm)")
        use_plywood = st.checkbox("เพิ่ม ไม้อัดยางมารีน 20mm")
        plywood_qty = 0
        plywood_price = 4000
        if use_plywood:
            plywood_qty = st.number_input("จำนวนแผ่นไม้อัด", min_value=1, value=1)
            # เงื่อนไขสั่งซื้อขั้นต่ำ 100 แผ่น
            if plywood_qty >= 100:
                plywood_price = 3500
                st.caption("🎉 ได้รับราคาสั่งซื้อขั้นต่ำ (≥ 100 แผ่น): 3,500 บาท/แผ่น")
            else:
                plywood_price = 4000
                st.caption("ราคาปกติ (< 100 แผ่น): 4,000 บาท/แผ่น")

    st.markdown("##### ⚙️ เลือกกระบวนการเครื่องจักร (Operations & Machines)")
    c_op1, c_op2, c_op3, c_op4 = st.columns(4)

    with c_op1:
        st.markdown("**1. Robot Milling**")
        use_robot = st.checkbox("ใช้งาน Robot", value=True)
        robot_rate = st.number_input("ค่าเครื่อง (฿/Hr)", value=300)
        robot_prog = st.number_input("Program (Hr)", value=0.5, key="r_p")
        robot_setup = st.number_input("Setup (Hr)", value=0.5, key="r_s")
        # สูตรคำนวณ Robot Machine Time จากพื้นที่ผิว * Level Factor
        auto_robot_mch = calc_area * LEVEL_FACTORS.get(complexity_level, 5.0)
        robot_mch = st.number_input("Machine (Hr)", value=float(auto_robot_mch), key="r_m")
        robot_mat = st.number_input("ค่าวัสดุ (฿)", value=2850)

    with c_op2:
        st.markdown("**2. 3D Print FDM**")
        use_fdm = st.checkbox("ใช้งาน 3D Print", value=False)
        fdm_rate = st.number_input("ค่าเครื่อง FDM (฿/Hr)", value=50)
        fdm_prog = st.number_input("Program (Hr)", value=0.5, key="f_p")
        fdm_setup = st.number_input("Setup (Hr)", value=0.5, key="f_s")
        fdm_mch = st.number_input("Machine (Hr)", value=17.0, key="f_m")
        fdm_mat = st.number_input("ค่าวัสดุ FDM (฿)", value=480)

    with c_op3:
        st.markdown("**3. Structure / Assembly**")
        use_struct = st.checkbox("งานโครงสร้าง", value=False)
        struct_mat = st.number_input("ค่าวัสดุโครงสร้าง (฿)", value=720)

    with c_op4:
        st.markdown("**4. Fiber Laser N2**")
        use_laser = st.checkbox("ใช้งาน Laser", value=False)
        laser_rate = st.number_input("ค่าเครื่อง Laser (฿/Hr)", value=2400)
        laser_prog = st.number_input("Program (Hr)", value=0.5, key="l_p")
        laser_setup = st.number_input("Setup (Hr)", value=0.5, key="l_s")
        laser_mch = st.number_input("Machine (Hr)", value=0.5, key="l_m")
        laser_mat = st.number_input("ค่าวัสดุ Laser (฿)", value=648)

    st.markdown("##### 🎨 งานเคลือบผิวและทำสี (Hard Coat & Finishing)")
    c_coat1, c_coat2 = st.columns(2)
    with c_coat1:
        sel_hardcoat = st.selectbox("ประเภท Hard Coat", list(HARDCOAT_RATES.keys()))
    with c_coat2:
        sel_color = st.selectbox("ประเภทการทำสี (Color Type)", list(COLOR_RATES.keys()))

    st.divider()

    # ==========================================
    # 🧮 คำนวณสรุปผลราคาสุทธิ
    # ==========================================
    # Robot
    r_time = (robot_prog + robot_setup + robot_mch) if use_robot else 0
    r_mch_cost = r_time * robot_rate if use_robot else 0
    r_mat_cost = robot_mat if use_robot else 0

    # FDM
    f_time = (fdm_prog + fdm_setup + fdm_mch) if use_fdm else 0
    f_mch_cost = f_time * fdm_rate if use_fdm else 0
    f_mat_cost = fdm_mat if use_fdm else 0

    # Structure
    s_mat_cost = struct_mat if use_struct else 0

    # Laser
    l_time = (laser_prog + laser_setup + laser_mch) if use_laser else 0
    l_mch_cost = l_time * laser_rate if use_laser else 0
    l_mat_cost = laser_mat if use_laser else 0

    # Plywood
    plywood_total = plywood_qty * plywood_price if use_plywood else 0

    # Totals
    total_mch_cost = r_mch_cost + f_mch_cost + l_mch_cost
    total_mat_cost = r_mat_cost + f_mat_cost + s_mat_cost + l_mat_cost + plywood_total
    prototype_cost = total_mch_cost + total_mat_cost

    hardcoat_cost = calc_area * HARDCOAT_RATES[sel_hardcoat]
    color_cost = calc_area * COLOR_RATES[sel_color]

    grand_total = prototype_cost + hardcoat_cost + color_cost

    # ==========================================
    # 📋 แสดงตารางใบประเมินราคา
    # ==========================================
    st.subheader(f"📋 สรุปใบประเมินราคา: {project_name}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ชั่วโมง Robot รวม", f"{r_time:.1f} ชม.")
    m2.metric("ค่าเครื่องจักรรวม", f"฿{total_mch_cost:,.2f}")
    m3.metric("ค่าวัสดุรวม", f"฿{total_mat_cost:,.2f}")
    m4.metric("💰 ราคาสรุปสุทธิ (Grand Total)", f"฿{grand_total:,.2f}")

    df_summary = pd.DataFrame({
        "กระบวนการ (Process)": ["1. Robot Milling", "2. 3D Print FDM", "3. Structure", "4. Fiber Laser N2", "5. ไม้อัดยางมารีน 20mm"],
        "เวลารวม (Hr)": [f"{r_time:.1f}", f"{f_time:.1f}", "-", f"{l_time:.1f}", "-"],
        "ค่าเครื่องจักร (Baht)": [f"฿{r_mch_cost:,.2f}", f"฿{f_mch_cost:,.2f}", "฿0.00", f"฿{l_mch_cost:,.2f}", "฿0.00"],
        "ค่าวัสดุ (Baht)": [f"฿{r_mat_cost:,.2f}", f"฿{f_mat_cost:,.2f}", f"฿{s_mat_cost:,.2f}", f"฿{l_mat_cost:,.2f}", f"฿{plywood_total:,.2f}"]
    })
    st.table(df_summary)

    st.markdown(f"""
    > **งานตกแต่งผิว & สี:**
    > * **Hard Coat ({sel_hardcoat}):** {calc_area:.2f} sq.m. × ฿{HARDCOAT_RATES[sel_hardcoat]:,} = **฿{hardcoat_cost:,.2f}**
    > * **Color ({sel_color}):** {calc_area:.2f} sq.m. × ฿{COLOR_RATES[sel_color]:,} = **฿{color_cost:,.2f}**
    """)
