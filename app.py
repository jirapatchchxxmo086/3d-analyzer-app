import streamlit as st

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="โปรแกรมประเมินต้นทุนการผลิต", page_icon="⚙️", layout="wide")

# ฐานข้อมูลวัสดุ
MATERIALS = {
    "aluminum_6061": {"name": "อลูมิเนียม 6061", "density": 2.70, "price_per_kg": 180.0, "waste": 1.10},
    "stainless_304": {"name": "สแตนเลส 304", "density": 8.00, "price_per_kg": 220.0, "waste": 1.08},
    "mild_steel": {"name": "เหล็กแผ่น SS400", "density": 7.85, "price_per_kg": 42.0, "waste": 1.12},
    "pla_plastic": {"name": "พลาสติก PLA (3D Print)", "density": 1.24, "price_per_kg": 650.0, "waste": 1.05},
    "acrylic": {"name": "อะคริลิก (Acrylic)", "density": 1.18, "price_per_kg": 150.0, "waste": 1.10}
}

# ฐานข้อมูลเครื่องจักร
MACHINES = {
    "cnc_milling_3axis": {"name": "CNC Milling 3-Axis", "machine_rate": 450.0, "labor_rate": 200.0, "default_setup": 1.0},
    "cnc_lathe": {"name": "CNC Lathe (เครื่องกลึง)", "machine_rate": 350.0, "labor_rate": 180.0, "default_setup": 0.5},
    "laser_cutting": {"name": "Laser Cutting Machine", "machine_rate": 800.0, "labor_rate": 200.0, "default_setup": 0.25}
}

st.title("⚙️ ระบบประเมินต้นทุนวัสดุและค่าแปรรูปการผลิต")
st.write("คำนวณต้นทุนวัสดุตามพื้นที่ผิว + ค่าแปรรูปเครื่องจักร + ค่า Setup และ Overhead")

st.divider()

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. ข้อมูลวัสดุและขนาดชิ้นงาน")
    mat_key = st.selectbox(
        "เลือกประเภทวัสดุ",
        options=list(MATERIALS.keys()),
        format_func=lambda x: MATERIALS[x]["name"]
    )
    surface_area = st.number_input("พื้นที่ผิวชิ้นงาน (cm²)", min_value=1.0, value=320.0, step=10.0)
    thickness = st.number_input("ความหนาชิ้นงาน (mm)", min_value=0.1, value=12.0, step=0.5)

    st.subheader("2. ข้อมูลกระบวนการผลิต (Machining)")
    mc_key = st.selectbox(
        "เลือกเครื่องจักรที่ใช้",
        options=list(MACHINES.keys()),
        format_func=lambda x: MACHINES[x]["name"]
    )
    cycle_time = st.number_input("เวลาตัด/แปรรูปต่อชิ้น (นาที)", min_value=0.1, value=18.0, step=1.0)
    batch_size = st.number_input("จำนวนผลิตใน Batch นี้ (ชิ้น)", min_value=1, value=20, step=1)

with col2:
    st.subheader("3. ต้นทุนเพิ่มเติมและโอกับ")
    setup_time = st.number_input("เวลา Setup เครื่องทั้งหมด (ชั่วโมง)", min_value=0.0, value=MACHINES[mc_key]["default_setup"], step=0.25)
    tooling_cost = st.number_input("ค่าเสื่อม Tooling / ดอกกัด (บาท/ชิ้น)", min_value=0.0, value=25.0, step=5.0)
    overhead_pct = st.number_input("ค่าโอกับ/บริหารจัดการ Overhead (%)", min_value=0.0, value=12.0, step=1.0)

    st.write("")
    calculate_btn = st.button("🚀 คำนวณต้นทุนการผลิต", type="primary", use_container_width=True)

# คำนวณผลลัพธ์
if calculate_btn:
    mat = MATERIALS[mat_key]
    mc = MACHINES[mc_key]

    # 1. วัสดุ
    volume_cm3 = surface_area * (thickness / 10.0)
    net_weight_kg = (volume_cm3 * mat["density"]) / 1000.0
    gross_weight_kg = net_weight_kg * mat["waste"]
    mat_cost = gross_weight_kg * mat["price_per_kg"]

    # 2. แปรรูป
    total_hourly_rate = mc["machine_rate"] + mc["labor_rate"]
    setup_cost_per_part = (setup_time / batch_size) * total_hourly_rate
    run_cost_per_part = (cycle_time / 60.0) * total_hourly_rate
    machining_cost = setup_cost_per_part + run_cost_per_part + tooling_cost

    # 3. สรุป
    direct_cost = mat_cost + machining_cost
    overhead_cost = direct_cost * (overhead_pct / 100.0)
    unit_cost = direct_cost + overhead_cost
    batch_cost = unit_cost * batch_size

    st.divider()
    st.subheader("📊 ผลการประเมินต้นทุน")

    res_col1, res_col2 = st.columns(2)
    res_col1.metric("ต้นทุนรวมต่อชิ้น (Total Unit Cost)", f"{unit_cost:,.2f} บาท")
    res_col2.metric(f"ต้นทุนรวมทั้ง Batch ({batch_size} ชิ้น)", f"{batch_cost:,.2f} บาท")

    st.markdown("### รายละเอียดสัดส่วนต้นทุนต่อชิ้น (Cost Breakdown)")
    st.table([
        {"รายการ": "1. ค่าวัสดุ (Material Cost)", "จำนวนเงิน (บาท)": f"{mat_cost:,.2f}"},
        {"รายการ": "2. ค่า Setup เครื่อง (เฉลี่ยต่อชิ้น)", "จำนวนเงิน (บาท)": f"{setup_cost_per_part:,.2f}"},
        {"รายการ": "3. ค่าแปรรูปจริง (Machining Run Cost)", "จำนวนเงิน (บาท)": f"{run_cost_per_part:,.2f}"},
        {"รายการ": "4. ค่า Tooling / มีดตัด", "จำนวนเงิน (บาท)": f"{tooling_cost:,.2f}"},
        {"รายการ": f"5. ค่าโอกับ (Overhead {overhead_pct}%)", "จำนวนเงิน (บาท)": f"{overhead_cost:,.2f}"},
    ])
