"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรสำหรับ Robot CNC (กัดโฟม) และ 3D Print FDM
"""

from dataclasses import dataclass
from typing import Dict, Any
import math


@dataclass
class MachiningEstimate:
    hours: float
    breakdown: Dict[str, Any]


def estimate_foam_cnc_hours(
    volume_removal_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    complexity_level: int = 3,
    setup_hours_override: float = None,
    height_mm: float = 1000.0,
    allow_anatomical_split: bool = True,
    machine_name: str = "Robot_Foam",
) -> MachiningEstimate:
    area_sqm = max(surface_area_sqm, 0.0)
    
    if area_sqm == 0.0 and volume_removal_cm3 > 0.0:
        area_sqm = ((volume_removal_cm3 / 1_000_000.0) ** (2.0 / 3.0)) * 6.0

    # Base Rate
    base_rate = 3.10 + (complexity_level * 0.15)
    base_machine_hours = area_sqm * base_rate

    # Program & Setup Time
    program_hours = 0.2
    setup_hours = setup_hours_override if setup_hours_override is not None else (1.0 if area_sqm < 2.0 else 0.5)

    effective_machine_hours = base_machine_hours
    total_time = effective_machine_hours + program_hours + setup_hours

    # แยกสัดส่วน Roughing / Finishing จาก Machine Hours เพื่อรองรับ app.py
    roughing_hrs = round(effective_machine_hours * 0.4, 2)
    finishing_hrs = round(effective_machine_hours * 0.6, 2)

    return MachiningEstimate(
        hours=round(total_time, 2),
        breakdown={
            "machine_type": "Robot CNC (Foam)",
            "surface_area_sqm": round(area_sqm, 2),
            "machine_hours": round(effective_machine_hours, 2),
            "roughing_hours": roughing_hrs,      # <-- เพิ่ม Key นี้
            "finishing_hours": finishing_hrs,    # <-- เพิ่ม Key นี้
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "effective_rate_hr_sqm": round(base_rate, 2),
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
            "roughing_hours": 0.0,                             # <-- เพิ่ม Key นี้ (3D Print ไม่มี Roughing)
            "finishing_hours": round(machine_hours, 2),        # <-- เพิ่ม Key นี้
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "effective_rate_hr_sqm": round(rate_per_sqm, 1),
            "hourly_rate_baht": 50,
        },
    )
