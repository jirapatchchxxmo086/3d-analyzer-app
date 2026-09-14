import streamlit as st
import math
from dataclasses import dataclass
from typing import Dict, Any, Optional

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION (ต้องอยู่บรรทัดแรกสุดเสมอ)
# ---------------------------------------------------------
st.set_page_config(
    page_title="3D & CNC Machining Estimator",
    page_icon="⚙️",
    layout="wide"
)

# ---------------------------------------------------------
# 2. CORE ESTIMATION LOGIC
# ---------------------------------------------------------
@dataclass
class MachiningEstimate:
    hours: float
    breakdown: Dict[str, Any]


def estimate_foam_cnc_hours(
    volume_removal_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    complexity_level: int = 3,
    setup_hours_override: Optional[float] = None,
    height_mm: float = 1000.0,
    allow_anatomical_split: bool = True,
    machine_name: str = "Robot_Foam",
) -> MachiningEstimate:
    """
    คำนวณชั่วโมง Robot Foam CNC 
    - Machine Time ในใบประเมิน = เวลา กัดหยาบ (Roughing)
    - เวลา กัดรายละเอียด (Finishing) คิดเพิ่มตาม Complexity
    """
    area_sqm = max(surface_area_sqm, 0.0)
    
    if area_sqm == 0.0 and volume_removal_cm3 > 0.0:
        area_sqm = ((volume_removal_cm3 / 1_000_000.0) ** (2.0 / 3.0)) * 6.0

    rough_rate = 3.50 + (complexity_level * 0.12)
    roughing_hrs = round(area_sqm * rough_rate, 2)

    finish_ratio = 0.30 + (complexity_level * 0.05)
    finishing_hrs = round(roughing_hrs * finish_ratio, 2)

    total_machine_hours = roughing_hrs + finishing_hrs

    program_hours = 0.2
    if setup_hours_override is not None:
        setup_hours = setup_hours_override
    else:
        setup_hours = 1.0 if area_sqm <= 2.0 else 0.5

    total_time = total_machine_hours + program_hours + setup_hours
    finish_tool_mm = 6.0 if complexity_level >= 4 else 10.0

    return MachiningEstimate(
        hours=round(total_time, 2),
        breakdown={
            "machine_type": "Robot CNC (Foam)",
            "surface_area_sqm": round(area_sqm, 2),
            "machine_hours": round(total_machine_hours, 2),
            "roughing_hours": roughing_hrs,
            "finishing_hours": finishing_hrs,
            "finish_tool_mm_used": finish_tool_mm,
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "effective_rate_hr_sqm": round(rough_rate, 2),
            "hourly_rate_baht": 300,
        },
    )


def estimate_3d_print_hours(
    volume_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    infill_pct: float = 15.0,
    complexity_level: int = 4,
    technology: str = "FDM",
) -> MachiningEstimate:
    """
    คำนวณชั่วโมง 3D Print FDM
    """
    area_sqm = max(surface_area_sqm, 0.0)

    if area_sqm == 0.0 and volume_cm3 > 0.0:
        approx_radius_cm = ((3.0 * volume_cm3) / (4.0 * math.pi)) ** (1.0 / 3.0)
        approx_area_cm2 = 4.0 * math.pi * (approx_radius_cm ** 2) * 1.3
        area_sqm = approx_area_cm2 / 10000.0

    program_hours = 4.0
    setup_hours = 8.0

    if area_sqm <= 0.5:
        rate_per_sqm = 260.0
    elif area_sqm <= 1.2:
        rate_per_sqm = 320.0 + (complexity_level * 15.0)
    else:
        rate_per_sqm = 380.0 + (complexity_level * 8.0)

    machine_hours = area_sqm * rate_per_sqm
    total_time = machine_hours + program_hours + setup_hours

    return MachiningEstimate(
        hours=round(total_time, 2),
        breakdown={
            "machine_type": "3D Print FDM",
            "surface_area_sqm": round(area_sqm, 2),
            "machine_hours": round(machine_hours, 2),
            "roughing_hours": 0.0,
            "finishing_hours": round(machine_hours, 2),
            "finish_tool_mm_used": 0.4,
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "effective_rate_hr_sqm": round(rate_per_sqm, 1),
            "hourly_rate_baht": 50,
        },
    )


# ---------------------------------------------------------
# 3. STREAMLIT USER INTERFACE ( UI เต็มรูปแบบ )
# ---------------------------------------------------------
st.title("⚙️ ระบบประเมินเวลาและต้นทุน CNC / 3D Print")
st.caption("Robot CNC (กัดโฟม) & 3D Printing (FDM)")

# Sidebar Settings
st.sidebar.header("📌 ตั้งค่าการประเมิน")
process_type = st.sidebar.radio(
    "เลือกประเภทกระบวนการ:",
    ["Robot CNC (กัดโฟม)", "3D Printing (FDM)"]
)

st.sidebar.markdown("---")
complexity = st.sidebar.slider("ระดับความซับซ้อนของชิ้นงาน (Complexity):", 1, 5, 3)

# Main Input Section
st.subheader("📐 ข้อมูลขนาดและพื้นที่ผิวชิ้นงาน")

input_mode = st.radio(
    "วิธีการระบุขนาดชิ้นงาน:",
    ["ระบุขนาดกว้าง x ยาว x สูง (ระบบประเมินพื้นที่ให้อัตโนมัติ)", "ระบุพื้นที่ผิวและปริมาตรโดยตรง"],
    horizontal=True
)

surface_area_sqm = 0.0
volume_cm3 = 0.0
height_mm = 1000.0

if input_mode == "ระบุขนาดกว้าง x ยาว x สูง (ระบบประเมินพื้นที่ให้อัตโนมัติ)":
    c1, c2, c3 = st.columns(3)
    with c1:
        width_mm = st.number_input("ความกว้าง Width (mm):", min_value=1.0, value=500.0, step=50.0)
    with c2:
        length_mm = st.number_input("ความยาว Length (mm):", min_value=1.0, value=500.0, step=50.0)
    with c3:
        height_mm = st.number_input("ความสูง Height (mm):", min_value=1.0, value=1000.0, step=50.0)

    # แปลงหน่วยเป็นเมตรและเซนติเมตร
    w_m, l_m, h_m = width_mm / 1000.0, length_mm / 1000.0, height_mm / 1000.0
    
    # ประเมินพื้นที่ผิวทรงกล่อง (Bounding Box Surface Area)
    bounding_box_area = 2 * (w_m * l_m + w_m * h_m + l_m * h_m)
    
    # ปรับลดตัวคูณตามทรงรูปทรงจริง (Organic Shape Factor ~0.7-0.85)
    shape_factor = st.slider("ตัวคูณรูปทรง (Shape Factor):", 0.5, 1.0, 0.75, 0.05, 
                             help="0.6 = ทรงอินทรีย์/การ์ตูนโค้งมน, 1.0 = ทรงกล่องสี่เหลี่ยมเป๊ะ")
    
    surface_area_sqm = bounding_box_area * shape_factor
    volume_cm3 = (width_mm / 10.0) * (length_mm / 10.0) * (height_mm / 10.0) * shape_factor

    st.info(f"💡 **ประมาณการณ์จากขนาด:** พื้นที่ผิว ≈ **{surface_area_sqm:.2f} ตร.ม.** | ปริมาตร ≈ **{volume_cm3:,.0f} cm³**")

else:
    col1, col2 = st.columns(2)
    with col1:
        surface_area_sqm = st.number_input("พื้นที่ผิวชิ้นงาน (ตร.ม. / sqm):", min_value=0.0, value=1.5, step=0.1)
    with col2:
        volume_cm3 = st.number_input("ปริมาตรชิ้นงาน (ลบ.ซม. / cm³):", min_value=0.0, value=50000.0, step=1000.0)

st.markdown("---")

# คำนวณเมื่อกดปุ่ม
if st.button("🚀 คำนวณเวลาประเมิน", type="primary", use_container_width=True):
    try:
        if process_type == "Robot CNC (กัดโฟม)":
            result = estimate_foam_cnc_hours(
                volume_removal_cm3=volume_cm3,
                surface_area_sqm=surface_area_sqm,
                complexity_level=complexity,
                height_mm=height_mm
            )
        else:
            result = estimate_3d_print_hours(
                volume_cm3=volume_cm3,
                surface_area_sqm=surface_area_sqm,
                complexity_level=complexity
            )

        bd = result.breakdown
        total_cost = result.hours * bd["hourly_rate_baht"]

        # Display Summary Cards
        m1, m2, m3 = st.columns(3)
        m1.metric("เวลารวมทั้งหมด", f"{result.hours} ชม.")
        m2.metric("เวลาเดินเครื่อง (Machine)", f"{bd['machine_hours']} ชม.")
        m3.metric("ประมาณการค่าบริการ", f"{total_cost:,.2f} บาท")

        # Display Breakdown Details
        st.subheader("📋 รายละเอียดการประเมิน (Breakdown)")
        
        b1, b2 = st.columns(2)
        with b1:
            st.write(f"• **กระบวนการ:** {bd['machine_type']}")
            st.write(f"• **พื้นที่ผิวที่ใช้คำนวณ:** {bd['surface_area_sqm']} ตร.ม.")
            st.write(f"• **เวลากัดหยาบ (Roughing):** {bd['roughing_hours']} ชม.")
            st.write(f"• **เวลาเก็บรายละเอียด (Finishing):** {bd['finishing_hours']} ชม.")
            
        with b2:
            st.write(f"• **เวลาเขียนโปรแกรม (CAM):** {bd['program_hours']} ชม.")
            st.write(f"• **เวลา Setup เครื่อง:** {bd['setup_hours']} ชม.")
            st.write(f"• **ขนาดดอกกัด/หัวฉีด:** {bd['finish_tool_mm_used']} mm")
            st.write(f"• **อัตราค่าบริการ:** {bd['hourly_rate_baht']} บาท/ชม.")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการคำนวณ: {e}")
