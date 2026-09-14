import streamlit as st
import math
from dataclasses import dataclass
from typing import Dict, Any, Optional

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION (ต้องอยู่บรรทัดแรกสุดของ Streamlit)
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
# 3. STREAMLIT USER INTERFACE
# ---------------------------------------------------------
st.title("⚙️ ระบบประเมินเวลาและต้นทุน CNC / 3D Print")
st.caption("Robot CNC (กัดโฟม) & 3D Printing (FDM)")

# Sidebar Selection
st.sidebar.header("📌 ตั้งค่าการประเมิน")
process_type = st.sidebar.radio(
    "เลือกประเภทกระบวนการ:",
    ["Robot CNC (กัดโฟม)", "3D Printing (FDM)"]
)

st.sidebar.markdown("---")
complexity = st.sidebar.slider("ระดับความซับซ้อนของชิ้นงาน (Complexity):", 1, 5, 3)

# Main Form inputs
col1, col2 = st.columns(2)

with col1:
    surface_area = st.number_input("พื้นที่ผิวชิ้นงาน (ตร.ม. / sqm):", min_value=0.0, value=1.5, step=0.1)

with col2:
    volume = st.number_input("ปริมาตรชิ้นงาน (ลบ.ซม. / cm³):", min_value=0.0, value=50000.0, step=1000.0)

st.markdown("---")

# Calculate Button
if st.button("🚀 คำนวณเวลาประเมิน", type="primary", use_container_width=True):
    try:
        if process_type == "Robot CNC (กัดโฟม)":
            result = estimate_foam_cnc_hours(
                volume_removal_cm3=volume,
                surface_area_sqm=surface_area,
                complexity_level=complexity
            )
        else:
            result = estimate_3d_print_hours(
                volume_cm3=volume,
                surface_area_sqm=surface_area,
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
            st.write(f"• **พื้นที่ผิวที่คำนวณ:** {bd['surface_area_sqm']} ตร.ม.")
            st.write(f"• **เวลากัดหยาบ (Roughing):** {bd['roughing_hours']} ชม.")
            st.write(f"• **เวลาเก็บละเอียด (Finishing):** {bd['finishing_hours']} ชม.")
            
        with b2:
            st.write(f"• **เวลาเขียนโปรแกรม:** {bd['program_hours']} ชม.")
            st.write(f"• **เวลา Setup:** {bd['setup_hours']} ชม.")
            st.write(f"• **ขนาดดอกกัด/หัวฉีด:** {bd['finish_tool_mm_used']} mm")
            st.write(f"• **อัตราค่าบริการ:** {bd['hourly_rate_baht']} บาท/ชม.")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการคำนวณ: {e}")
