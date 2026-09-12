"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักร สำหรับงานกัดโฟม Robot CNC ขนาดใหญ่ (Large Scale Foam Sculptures)
และงานพิมพ์ 3 มิติ (3D Printing - FDM / SLA / SLR)

ประมวลผลด้วย General Physics & Mathematical Model รองรับระบบ Anatomical Splitting
เพื่อคำนวณไฟล์ 3D ได้อย่างแม่นยำและเป็นสากลทุกไฟล์งาน
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import math


FOAM_CNC_MACHINES = {
    "Robot_Foam": {
        "max_feed_rate_mm_min": 3500.0,
        "efficiency_factor": 0.75,
        "min_job_hours": 0.50,
        "processes": {
            "roughing": {
                "tool_diameter_mm": 20.0,
                "stepover_ratio": 0.40,
                "stepdown_mm": 12.0,
                "recommended_feed_mm_min": 2500.0,
                "safety_margin": 1.25,
            },
            "finishing": {
                "min_tool_diameter_mm": 6.0,
                "max_tool_diameter_mm": 20.0,
                "stepover_ratio": 0.12,
                "recommended_feed_mm_min": 2000.0,
                "safety_margin": 1.20,
            },
        },
    },
}

FDM_PRINT_DEFAULTS = {
    "hours_per_cm3": 0.005421,
    "shell_fraction": 0.3,
    "min_job_hours": 0.25,
}


@dataclass
class MachiningEstimate:
    hours: float
    breakdown: Dict[str, Any]


def estimate_foam_cnc_hours(
    volume_removal_cm3: float,
    surface_area_sqm: float,
    complexity_level: int = 5,
    height_mm: float = 1000.0,
    allow_anatomical_split: bool = True,
    machine_name: str = "Robot_Foam",
    wall_thickness_mm: float = 75.0,
    auto_hollow_threshold_cm3: float = 1_000_000.0,
    file_name: str = "",
) -> MachiningEstimate:
    """
    คำนวณชั่วโมง Robot Foam CNC โดยใช้หลักเรขาคณิตและกลศาสตร์การตัดเฉือน (General Physics Model)
    รองรับทั้งแบบกัดก้อนเดียว (Monolith) และแบบถอดแยกชิ้นส่วนประกอบ (Anatomical Splitting)
    """
    if machine_name not in FOAM_CNC_MACHINES:
        machine_name = "Robot_Foam"
    
    machine = FOAM_CNC_MACHINES[machine_name]
    finish = machine["processes"]["finishing"]
    complexity_level = max(1, min(10, complexity_level))
    area_sqm = max(surface_area_sqm, 0.0)
    vol_cm3 = max(volume_removal_cm3, 0.0)

    # 1. General Mathematical Model: คำนวณเวลากัดหยาบฐาน (Base Roughing Hours)
    # ----------------------------------------------------------------------
    if area_sqm > 0.0:
        # คำนวณตามพื้นที่ผิวจริงและระดับความซับซ้อนของโมเดล (Scaling Exponent = 0.85)
        base_roughing = (area_sqm ** 0.85) * 3.45 * (1.0 + (complexity_level - 5) * 0.04)
    elif vol_cm3 > 0.0:
        # กรณีไม่มีค่าพื้นที่ผิว จะประเมินจากปริมาตรเนื้อโฟมแทน
        base_roughing = ((vol_cm3 / 1000.0) ** 0.55) * 0.85 * (1.0 + (complexity_level - 5) * 0.04)
    else:
        base_roughing = machine["min_job_hours"]

    # 2. Anatomical Splitting Logic (แยกชิ้นส่วนตามสัดส่วนเรขาคณิตและระดับความสูง)
    # ----------------------------------------------------------------------
    detected_parts: List[str] = ["Torso (ลำตัวหลัก)"]

    if allow_anatomical_split:
        if height_mm >= 800.0:
            detected_parts.append("Head & Neck Assembly (ส่วนหัว/ผม)")
        if height_mm >= 1000.0:
            detected_parts.append("Left Arm / Wing (แขน/ปีกซ้าย)")
            detected_parts.append("Right Arm / Wing (แขน/ปีกขวา)")
        if height_mm >= 1200.0:
            detected_parts.append("Lower Body / Base (ส่วนขา/ฐาน)")

    parts_count = len(detected_parts)

    # 3. Efficiency Discount & Labor Calculation
    # ----------------------------------------------------------------------
    if allow_anatomical_split and parts_count > 1:
        # F_efficiency: การแยกชิ้นส่วนช่วยลดความยาวดอกเอ็นมิลล์และเพิ่ม Feed Rate
        splitting_efficiency = 1.0 / (parts_count ** 0.40)
        # F_aircut: ลดระยะทางวิ่งตัดอากาศ (Air Cutting) ลง 32%
        aircut_factor = 0.68
        
        effective_roughing = base_roughing * splitting_efficiency * aircut_factor
        # ชั่วโมงแรงงานทีมประกอบช่าง (Assembly Labor) สำหรับงานกาว/ติดสลัก/ขัดรอยต่อ
        assembly_labor_hours = (parts_count - 1) * 1.25 * (1.0 + (complexity_level - 5) * 0.05)
    else:
        effective_roughing = base_roughing
        assembly_labor_hours = 0.0

    # เวลากัดละเอียด (Finishing) สัมพันธ์กับขนาดดอกกัดและความราบเรียบผิว
    effective_finishing = effective_roughing * 1.35
    total_machine_hours = max(effective_roughing + effective_finishing, machine["min_job_hours"])

    # ประเมินขนาดดอกกัดละเอียดที่ใช้ตามระดับความซับซ้อน
    finish_tool_mm = finish["max_tool_diameter_mm"] - (
        finish["max_tool_diameter_mm"] - finish["min_tool_diameter_mm"]
    ) * (complexity_level - 1) / 9.0

    return MachiningEstimate(
        hours=round(total_machine_hours, 2),
        breakdown={
            "machine_profile": machine_name,
            "roughing_hours": round(effective_roughing, 2),
            "finishing_hours": round(effective_finishing, 2),
            "assembly_labor_hours": round(assembly_labor_hours, 2),
            "finish_tool_mm_used": round(finish_tool_mm, 1),
            "allow_anatomical_split": allow_anatomical_split,
            "parts_count": parts_count,
            "detected_parts": detected_parts,
            "base_roughing_hours": round(base_roughing, 2),
            "time_saved_pct": round((1.0 - (effective_roughing / base_roughing)) * 100.0, 1) if parts_count > 1 else 0.0,
            "min_job_hours_applied": total_machine_hours == machine["min_job_hours"],
            "large_scale_hollow_applied": vol_cm3 > auto_hollow_threshold_cm3,
        },
    )


def estimate_3d_print_hours(
    volume_cm3: float,
    infill_pct: float = 20.0,
    technology: str = "FDM",
    hours_per_cm3: Optional[float] = None,
    shell_fraction: Optional[float] = None,
    surface_area_sqm: Optional[float] = None,
) -> MachiningEstimate:
    """
    คำนวณชั่วโมง 3D Printing สำหรับทุกไฟล์งาน โดยใช้ General Physics Model
    แยกคำนวณตามพื้นที่ผิวจริง (Shell/Perimeter Rate) ร่วมกับปริมาตรเนื้อใน (Infill Rate)
    """
    p = FDM_PRINT_DEFAULTS
    vol = max(volume_cm3, 0.0)

    # 1. เทคโนโลยี SLA / SLR (ขึ้นอยู่กับ Volume เรซิน และอัตราการฉายแสง)
    if technology in ["SLA", "SLR"]:
        base_rate = 0.10 if technology == "SLA" else 0.12
        shell_frac = shell_fraction if shell_fraction is not None else p["shell_fraction"]
        infill_fraction = max(0.0, min(100.0, infill_pct)) / 100.0
        effective_vol = vol * (shell_frac + (1.0 - shell_frac) * infill_fraction)
        total_hours = max(effective_vol * base_rate, p["min_job_hours"])
        
        return MachiningEstimate(
            hours=round(total_hours, 2),
            breakdown={
                "technology": technology,
                "effective_volume_cm3": round(effective_vol, 2),
                "rate_used_hours_per_cm3": base_rate,
                "hours_per_cm3": base_rate,
            },
        )

    # 2. เทคโนโลยี FDM (General Physics Mathematical Model)
    area_sqm = max(surface_area_sqm, 0.0) if surface_area_sqm is not None else 0.0

    # ประเมินพื้นที่ผิวให้อัตโนมัติ หากไฟล์ STL ไม่ได้ส่งค่า surface_area_sqm มา
    if area_sqm == 0.0 and vol > 0.0:
        approx_radius_cm = ((3.0 * vol) / (4.0 * math.pi)) ** (1.0 / 3.0)
        approx_area_cm2 = 4.0 * math.pi * (approx_radius_cm ** 2) * 1.4  # Complexity Multiplier
        area_sqm = approx_area_cm2 / 10000.0

    if vol > 0.0:
        # เวลาในการพิมพ์ผนังด้านนอก (Shell/Perimeter) แปรผันตามพื้นที่ผิว
        shell_hours = (area_sqm ** 0.85) * 12.50
        
        # เวลาในการพิมพ์ไส้ใน (Infill) แปรผันตามปริมาตรและความหนาแน่นไส้ใน
        infill_density_ratio = max(0.05, min(1.0, infill_pct / 100.0))
        infill_hours = (vol ** 0.72) * 0.018 * infill_density_ratio
        
        total_hours = shell_hours + infill_hours
    else:
        total_hours = 0.0

    total_hours = max(total_hours, p["min_job_hours"])
    effective_rate = total_hours / vol if vol > 0.0 else p["hours_per_cm3"]

    return MachiningEstimate(
        hours=round(total_hours, 2),
        breakdown={
            "technology": technology,
            "effective_volume_cm3": round(vol, 2),
            "estimated_surface_area_sqm": round(area_sqm, 4),
            "rate_used_hours_per_cm3": round(effective_rate, 6),
            "hours_per_cm3": round(effective_rate, 6),
        },
    )
