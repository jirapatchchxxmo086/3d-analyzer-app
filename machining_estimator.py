"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักร สำหรับงานทั่วไปและงานโครงสร้างขนาดใหญ่ (Large Scale Foam Sculptures)
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

FOAM_CNC_MACHINES = {
    "Robot_Foam": {
        "max_feed_rate_mm_min": 3500.0,
        "efficiency_factor": 0.75,  # เผื่อเวลาชะลอตามมุมและการยก Toolpath
        "min_job_hours": 0.50,
        "processes": {
            "roughing": {
                "tool_diameter_mm": 20.0,
                "stepover_ratio": 0.40,
                "stepdown_mm": 12.0,     # ปรับลดจาก 25mm ให้สมจริงกับระยะกินโฟมจริง
                "recommended_feed_mm_min": 2500.0, # Feed rate กัดหยาบที่ปลอดภัย
                "safety_margin": 1.25,   # เผื่อเวลา Retract / Clearance
            },
            "finishing": {
                "min_tool_diameter_mm": 6.0,
                "max_tool_diameter_mm": 20.0,
                "stepover_ratio": 0.12,  # Stepover ถี่ขึ้นเพื่อเก็บผิวเนียน
                "recommended_feed_mm_min": 2000.0, # Feed rate เก็บรายละเอียด
                "safety_margin": 1.20,
            },
        },
    },
}

FDM_PRINT_DEFAULTS = {
    "hours_per_cm3": 0.016615,
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
    complexity_level: int,
    machine_name: str = "Robot_Foam",
    wall_thickness_mm: float = 75.0,
    auto_hollow_threshold_cm3: float = 1_000_000.0,
) -> MachiningEstimate:
    if machine_name not in FOAM_CNC_MACHINES:
        machine_name = "Robot_Foam"
    
    machine = FOAM_CNC_MACHINES[machine_name]
    rough = machine["processes"]["roughing"]
    finish = machine["processes"]["finishing"]
    complexity_level = max(1, min(10, complexity_level))

    actual_roughing_vol_cm3 = volume_removal_cm3
    is_large_scale_hollow = False

    if volume_removal_cm3 > auto_hollow_threshold_cm3 and surface_area_sqm > 0:
        is_large_scale_hollow = True
        shell_thickness_m = wall_thickness_mm / 1000.0
        estimated_shell_volume_cm3 = (surface_area_sqm * shell_thickness_m) * 1_000_000.0
        actual_roughing_vol_cm3 = estimated_shell_volume_cm3 * 0.30

    volume_removal_mm3 = max(actual_roughing_vol_cm3, 0) * 1000.0
    surface_area_mm2 = max(surface_area_sqm, 0) * 1_000_000.0

    # --- คำนวณ Roughing ---
    complexity_rough_factor = 1.0 + (complexity_level - 1) * 0.08
    stepover_rough_mm = rough["tool_diameter_mm"] * rough["stepover_ratio"]
    stepdown_mm = rough["stepdown_mm"]
    
    roughing_path_mm = (
        (volume_removal_mm3 / (stepover_rough_mm * stepdown_mm)) * complexity_rough_factor
        if stepover_rough_mm > 0 and stepdown_mm > 0 else 0.0
    )
    rough_feed = min(rough["recommended_feed_mm_min"], machine["max_feed_rate_mm_min"]) * machine["efficiency_factor"]
    roughing_time_min = (roughing_path_mm / rough_feed * rough["safety_margin"]) if rough_feed > 0 else 0.0

    # --- คำนวณ Finishing ---
    finish_tool_mm = finish["max_tool_diameter_mm"] - (
        finish["max_tool_diameter_mm"] - finish["min_tool_diameter_mm"]
    ) * (complexity_level - 1) / 9.0
    
    complexity_finish_factor = 1.0 + (complexity_level - 1) * 0.12
    stepover_finish_mm = finish_tool_mm * finish["stepover_ratio"]
    finishing_path_mm = (surface_area_mm2 / stepover_finish_mm * complexity_finish_factor) if stepover_finish_mm > 0 else 0.0
    finish_feed = min(finish["recommended_feed_mm_min"], machine["max_feed_rate_mm_min"]) * machine["efficiency_factor"]
    finishing_time_min = (finishing_path_mm / finish_feed * finish["safety_margin"]) if finish_feed > 0 else 0.0

    total_hours = (roughing_time_min + finishing_time_min) / 60.0
    total_hours = max(total_hours, machine["min_job_hours"])

    return MachiningEstimate(
        hours=round(total_hours, 2),
        breakdown={
            "machine_profile": machine_name,
            "roughing_hours": round(roughing_time_min / 60.0, 2),
            "finishing_hours": round(finishing_time_min / 60.0, 2),
            "finish_tool_mm_used": round(finish_tool_mm, 1),
            "min_job_hours_applied": total_hours == machine["min_job_hours"],
            "large_scale_hollow_applied": is_large_scale_hollow,
        },
    )

def estimate_3d_print_hours(
    volume_cm3: float,
    infill_pct: float = 20.0,
    technology: str = "FDM",
    hours_per_cm3: Optional[float] = None,
    shell_fraction: Optional[float] = None,
) -> MachiningEstimate:
    p = FDM_PRINT_DEFAULTS
    
    if technology == "SLA":
        base_rate = 0.10
    elif technology == "SLR":
        base_rate = 0.12
    else:
        base_rate = hours_per_cm3 or p["hours_per_cm3"]

    shell_frac = shell_fraction if shell_fraction is not None else p["shell_fraction"]
    infill_fraction = max(0.0, min(100.0, infill_pct)) / 100.0
    
    effective_volume_cm3 = max(volume_cm3, 0) * (shell_frac + (1.0 - shell_frac) * infill_fraction)
    total_hours = max(effective_volume_cm3 * base_rate, p["min_job_hours"])

    return MachiningEstimate(
        hours=round(total_hours, 2),
        breakdown={
            "technology": technology,
            "effective_volume_cm3": round(effective_volume_cm3, 2),
            "rate_used_hours_per_cm3": base_rate,
            "hours_per_cm3": base_rate,  # รองรับ app.py เดิมเพื่อป้องกัน KeyError
        },
    )
