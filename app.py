"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรสำหรับ Robot CNC (กัดโฟม) และ 3D Print FDM
ปรับปรุงโครงสร้าง: Machine Time ในใบประเมิน = เวลา กัดหยาบ (Roughing) เท่านั้น
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import math


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

    # 1. คำนวณชั่วโมงกัดหยาบ (Roughing Hours) ให้ตรงกับ Machine Time ในใบประเมินจริง
    # อัตรากัดหยาบเฉลี่ยอยู่ที่ 3.6 - 3.9 ชม./ตร.ม. สำหรับงานตัวการ์ตูนโฟม
    rough_rate = 3.50 + (complexity_level * 0.12)
    roughing_hrs = round(area_sqm * rough_rate, 2)

    # 2. คำนวณชั่วโมงเก็บงานละเอียด (Finishing Hours) เพิ่มเติม
    # งานซับซ้อนมาก (Complexity 4-5) จะต้องใช้เวลาเก็บละเอียดประมาณ 40-50% ของเวลากัดหยาบ
    finish_ratio = 0.30 + (complexity_level * 0.05)
    finishing_hrs = round(roughing_hrs * finish_ratio, 2)

    # รวมเวลาเดินเครื่องทั้งหมด (Machine Hours)
    total_machine_hours = roughing_hrs + finishing_hrs

    # 3. Program & Setup Time
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
            "roughing_hours": roughing_hrs,         # เวลากัดหยาบตรงกับใบประเมิน
            "finishing_hours": finishing_hrs,       # เวลาเก็บงานที่คำนวณเผื่อไว้
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
