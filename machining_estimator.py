"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรอัตโนมัติ + ระบบแยกชิ้นกัดสำหรับงานขนาดใหญ่ (> 1 เมตร)
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

FOAM_CNC_MACHINES = {
    "Robot_Foam": {
        "max_feed_rate_mm_min": 5000.0,
        "efficiency_factor": 0.85,
        "min_job_hours": 0.25,
        "processes": {
            "roughing": {
                "tool_diameter_mm": 20.0,
                "stepover_ratio": 0.50,
                "stepdown_mm": 25.0,
                "recommended_feed_mm_min": 5000.0,
                "safety_margin": 1.15,
            },
            "finishing": {
                "min_tool_diameter_mm": 6.0,
                "max_tool_diameter_mm": 20.0,
                "stepover_ratio": 0.15,
                "recommended_feed_mm_min": 5000.0,
                "safety_margin": 1.10,
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
) -> MachiningEstimate:
    """ประเมินชั่วโมง Foam CNC"""
    if machine_name not in FOAM_CNC_MACHINES:
        machine_name = "Robot_Foam"
    
    machine = FOAM_CNC_MACHINES[machine_name]
    rough = machine["processes"]["roughing"]
    finish = machine["processes"]["finishing"]
    complexity_level = max(1, min(10, complexity_level))

    volume_removal_mm3 = max(volume_removal_cm3, 0) * 1000.0
    surface_area_mm2 = max(surface_area_sqm, 0) * 1_000_000.0

    # Roughing Time
    stepover_rough_mm = rough["tool_diameter_mm"] * rough["stepover_ratio"]
    stepdown_mm = rough["stepdown_mm"]
    roughing_path_mm = (
        volume_removal_mm3 / (stepover_rough_mm * stepdown_mm)
        if stepover_rough_mm > 0 and stepdown_mm > 0 else 0.0
    )
    rough_feed = min(rough["recommended_feed_mm_min"], machine["max_feed_rate_mm_min"]) * machine["efficiency_factor"]
    roughing_time_min = (roughing_path_mm / rough_feed * rough["safety_margin"]) if rough_feed > 0 else 0.0

    # Finishing Time
    finish_tool_mm = finish["max_tool_diameter_mm"] - (
        finish["max_tool_diameter_mm"] - finish["min_tool_diameter_mm"]
    ) * (complexity_level - 1) / 9.0
    stepover_finish_mm = finish_tool_mm * finish["stepover_ratio"]
    finishing_path_mm = surface_area_mm2 / stepover_finish_mm if stepover_finish_mm > 0 else 0.0
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
        },
    )

def estimate_3d_print_hours(
    volume_cm3: float,
    infill_pct: float = 20,
    hours_per_cm3: Optional[float] = None,
    shell_fraction: Optional[float] = None,
) -> MachiningEstimate:
    """ประเมินชั่วโมง 3D Print FDM"""
    p = FDM_PRINT_DEFAULTS
    hours_per_cm3 = hours_per_cm3 or p["hours_per_cm3"]
    shell_fraction = shell_fraction if shell_fraction is not None else p["shell_fraction"]

    infill_fraction = max(0.0, min(100.0, infill_pct)) / 100.0
    effective_volume_cm3 = max(volume_cm3, 0) * (shell_fraction + (1 - shell_fraction) * infill_fraction)

    total_hours = max(effective_volume_cm3 * hours_per_cm3, p["min_job_hours"])

    return MachiningEstimate(
        hours=round(total_hours, 2),
        breakdown={
            "effective_volume_cm3": round(effective_volume_cm3, 2),
            "hours_per_cm3": hours_per_cm3,
        },
    )

# ==========================================
# 🌟 ระบบคำนวณการตัดแบ่งชิ้นงานเกิน 1 เมตร
# ==========================================

def calculate_split_milling_plan(
    part_volume_cm3: float,
    bounding_box_dims_mm: tuple,  # (X_mm, Y_mm, Z_mm)
    surface_area_sqm: float,
    complexity_level: int,
    max_segment_size_mm: float = 1000.0,  # เกณฑ์ตัดแบ่งหากเกิน 1 เมตร (1,000 mm)
    split_type: str = "planar",            # 'planar' (ตัดตามระนาบ) หรือ 'joint' (ตัดตามข้อต่อ/สัดส่วน)
    machine_name: str = "Robot_Foam",
) -> Dict[str, Any]:
    """
    คำนวณการกัดแบบแยกชิ้นส่วนเมื่อขนาดชิ้นงานเกิน 1 เมตร เพื่อลดปริมาตรสกัดโฟมทิ้ง
    """
    x_mm, y_mm, z_mm = bounding_box_dims_mm
    
    # จำนวนชิ้นที่ต้องตัดแบ่งในแต่ละแกน (X, Y, Z)
    splits_x = max(1, int(-(-x_mm // max_segment_size_mm)))
    splits_y = max(1, int(-(-y_mm // max_segment_size_mm)))
    splits_z = max(1, int(-(-z_mm // max_segment_size_mm)))
    
    total_segments = splits_x * splits_y * splits_z
    
    # ปริมาตร Bounding Box รวมแบบชิ้นเดียว
    single_bbox_vol_cm3 = (x_mm * y_mm * z_mm) / 1000.0
    single_volume_removal_cm3 = max(0.0, single_bbox_vol_cm3 - part_volume_cm3)
    
    # คำนวณแบบกัดชิ้นเดียว (Unsplit)
    unsplit_est = estimate_foam_cnc_hours(
        volume_removal_cm3=single_volume_removal_cm3,
        surface_area_sqm=surface_area_sqm,
        complexity_level=complexity_level,
        machine_name=machine_name
    )
    
    if total_segments > 1:
        # กำหนด Efficiency Factor ของการแนบเนื้อโฟมตามประเภทการตัด
        # Joint-based (ตัดตามข้อต่อ/แขนขา): กล่องโฟมจะกระชับแนบชิ้นงานได้มากกว่า Planar (ตัดตามแกนตรง)
        efficiency_factor = 0.15 if split_type == "joint" else 0.25 
        
        # ปริมาตรโฟมส่วนเกินที่ต้องกัดออกจริงเมื่อหั่นแยกชิ้นแล้ว
        split_volume_removal_cm3 = single_volume_removal_cm3 * efficiency_factor
        
        split_est = estimate_foam_cnc_hours(
            volume_removal_cm3=split_volume_removal_cm3,
            surface_area_sqm=surface_area_sqm,  # พื้นที่ผิวรวมของโมเดลเท่าเดิม
            complexity_level=complexity_level,
            machine_name=machine_name
        )
        
        # เพิ่มเวลาประกอบ/ทากาว t-overhead ต่องาน (0.3 ชม. ต่อชิ้นย่อย)
        assembly_overhead = (total_segments - 1) * 0.3
        total_split_hours = round(split_est.hours + assembly_overhead, 2)
        foam_savings_pct = round((1 - (split_volume_removal_cm3 / (single_volume_removal_cm3 or 1))) * 100, 1)
    else:
        split_est = unsplit_est
        total_split_hours = unsplit_est.hours
        split_volume_removal_cm3 = single_volume_removal_cm3
        foam_savings_pct = 0.0

    return {
        "is_split_required": total_segments > 1,
        "total_segments": total_segments,
        "split_grid": f"{splits_x} x {splits_y} x {splits_z} ชิ้น",
        "split_type": "ตัดตามข้อต่อ/สัดส่วน (Joint-based)" if split_type == "joint" else "ตัดตามระนาบ (Planar)",
        "unsplit_roughing_hours": unsplit_est.breakdown["roughing_hours"],
        "optimized_roughing_hours": split_est.breakdown["roughing_hours"],
        "optimized_total_hours": total_split_hours,
        "foam_waste_reduction_pct": foam_savings_pct,
        "summary": {
            "single_piece_hours": unsplit_est.hours,
            "smart_split_hours": total_split_hours,
            "time_saved_hours": round(max(0.0, unsplit_est.hours - total_split_hours), 2)
        }
    }
