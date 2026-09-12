"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรสำหรับ Robot CNC (กัดโฟม) และ 3D Print FDM
ปรับจูนด้วย Dynamic Rate Calibration จากใบประเมินจริง 100%
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
    complexity_level: int = 5,
    height_mm: float = 1000.0,
    allow_anatomical_split: bool = True,
    machine_name: str = "Robot_Foam",
) -> MachiningEstimate:
    """
    คำนวณชั่วโมง Robot Foam CNC 
    - ปรับ Dynamic Rate ตามขนาดพื้นที่ผิวและความซับซ้อนของงาน
    """
    area_sqm = max(surface_area_sqm, 0.0)
    
    # กรณีไม่มีค่าพื้นที่ผิว ให้ประมาณการจากปริมาตร
    if area_sqm == 0.0 and volume_removal_cm3 > 0.0:
        area_sqm = ((volume_removal_cm3 / 1_000_000.0) ** (2.0 / 3.0)) * 6.0

    # 1. Dynamic Machine Rate (ชม./ตร.ม.) ตามขนาดพื้นที่ผิวและความซับซ้อน
    if area_sqm <= 2.0:
        base_rate = 3.50 + (complexity_level - 5) * 0.20
    elif area_sqm <= 5.0:
        base_rate = 3.10 + (complexity_level - 5) * 0.15
    else:
        base_rate = 3.00 + (complexity_level - 5) * 0.10

    base_machine_hours = area_sqm * base_rate

    # 2. Program & Setup Time
    program_hours = 0.2
    setup_hours = 0.5 if area_sqm <= 3.0 else max(0.5, area_sqm * 0.2)

    # 3. Anatomical Splitting Adjustment (กรณีงานชิ้นใหญ่แยกส่วนประกอบ)
    detected_parts = ["Torso (ลำตัวหลัก)"]
    if allow_anatomical_split:
        if height_mm >= 800.0:
            detected_parts.append("Head Assembly")
        if height_mm >= 1000.0:
            detected_parts.append("Arms / Wings")
        if height_mm >= 1200.0:
            detected_parts.append("Lower Body / Base")

    parts_count = len(detected_parts)
    
    if allow_anatomical_split and parts_count > 1 and area_sqm > 3.0:
        split_benefit = max(0.60, 1.0 - (parts_count * 0.08))
        effective_machine_hours = base_machine_hours * split_benefit
        assembly_labor_hours = (parts_count - 1) * 1.2
    else:
        effective_machine_hours = base_machine_hours
        assembly_labor_hours = 0.0

    total_time = effective_machine_hours + program_hours + setup_hours

    return MachiningEstimate(
        hours=round(total_time, 2),
        breakdown={
            "machine_type": "Robot CNC (Foam)",
            "surface_area_sqm": round(area_sqm, 2),
            "machine_hours": round(effective_machine_hours, 2),
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "assembly_labor_hours": round(assembly_labor_hours, 2),
            "effective_rate_hr_sqm": round(base_rate, 2),
            "parts_count": parts_count,
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
    คำนวณชั่วโมง 3D Print FDM อ้างอิงตาม Estimate Sheet
    - Fixed Setup Time = 8 hrs, Fixed Program Time = 4 hrs
    - Machine Rate = 260 - 420 ชม./ตร.ม.
    """
    area_sqm = max(surface_area_sqm, 0.0)

    # กรณีไม่มีค่าพื้นที่ผิว ให้ประมาณการจากปริมาตร
    if area_sqm == 0.0 and volume_cm3 > 0.0:
        approx_radius_cm = ((3.0 * volume_cm3) / (4.0 * math.pi)) ** (1.0 / 3.0)
        approx_area_cm2 = 4.0 * math.pi * (approx_radius_cm ** 2) * 1.3
        area_sqm = approx_area_cm2 / 10000.0

    # 1. Fixed Overhead Times
    program_hours = 4.0
    setup_hours = 8.0

    # 2. Machine Print Rate คำนวณตามขนาดพื้นที่ผิวและความซับซ้อน
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
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "effective_rate_hr_sqm": round(rate_per_sqm, 1),
            "hourly_rate_baht": 50,
        },
    )
