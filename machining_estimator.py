"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรอัตโนมัติ + ระบบวิเคราะห์การตัดแบ่งชิ้นส่วนเสมือน (Virtual Splitting)
เพื่อรองรับโจทย์ Tool Reach Limit และการคำนวณเปรียบเทียบการประหยัดเวลา/เนื้อโฟม
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
    """ฟังก์ชันคำนวณชั่วโมงกัดพื้นฐาน (คง Logic เดิมของคุณไว้ 100%)"""
    if machine_name not in FOAM_CNC_MACHINES:
        raise ValueError(f"ไม่พบโปรไฟล์เครื่องจักร: {machine_name}")
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

# =========================================================================
# 🌟 ฟังก์ชันใหม่ที่เพิ่มเข้ามา: วิเคราะห์เงื่อนไข Tool Reach & คำนวณแผนแยกชิ้นส่วน
# =========================================================================

def analyze_smart_splitting(
    part_volume_cm3: float,
    bounding_box_dims_mm: tuple,  # (Width_X, Length_Y, Height_Z)
    surface_area_sqm: float,
    complexity_level: int,
    tool_reach_limit_mm: float = 200.0,
    reach_safety_factor: float = 1.2,
    machine_name: str = "Robot_Foam",
) -> Dict[str, Any]:
    """
    วิเคราะห์ว่าชิ้นงานควรตัดแบ่งหรือไม่ พร้อมเปรียบเทียบผลลัพธ์ระหว่าง ชิ้นเดียว vs แยกชิ้น
    """
    x_mm, y_mm, z_mm = bounding_box_dims_mm
    max_part_depth_mm = max(x_mm, y_mm, z_mm)
    
    # คำนวณ Bounding Box Volume และ Volume ที่ต้องกัดออกกรณีชิ้นเดียว
    bbox_volume_cm3 = (x_mm * y_mm * z_mm) / 1000.0
    unsplit_volume_removal_cm3 = max(0.0, bbox_volume_cm3 - part_volume_cm3)
    
    # 1. คำนวณแบบกัดชิ้นเดียว (Original Unsplit)
    unsplit_est = estimate_foam_cnc_hours(
        volume_removal_cm3=unsplit_volume_removal_cm3,
        surface_area_sqm=surface_area_sqm,
        complexity_level=complexity_level,
        machine_name=machine_name
    )
    
    # 2. เช็กเงื่อนไข Maximum Tool Reach Exceeded Factor
    max_allowed_reach_mm = tool_reach_limit_mm * reach_safety_factor
    is_tool_exceeded = max_part_depth_mm > max_allowed_reach_mm
    
    # 3. จำลองการแบ่งชิ้นส่วนเสมือน (Virtual Splitting)
    # หาจำนวนการตัดแบ่งที่จำเป็นเพื่อให้ความลึกแต่ละชิ้นไม่เกิน Tool Reach
    num_splits = max(2, int(-(-max_part_depth_mm // max_allowed_reach_mm))) if is_tool_exceeded else 1
    
    if num_splits > 1:
        # เมื่อตัดแบ่งชิ้นงาน กล่อง Bounding Box ย่อยจะกระชับเข้าหาเนื้อชิ้นงานมากขึ้น
        # ประเมินว่า Bounding Box รวมย่อยจะลดปริมาตรส่วนเกินลงได้ประมาณ 40-60%
        split_bbox_efficiency = 0.50  # Factor ประมาณการโฟมส่วนเกินที่ประหยัดได้จากการจัดวางใหม่
        split_volume_removal_cm3 = unsplit_volume_removal_cm3 * split_bbox_efficiency
        
        split_est = estimate_foam_cnc_hours(
            volume_removal_cm3=split_volume_removal_cm3,
            surface_area_sqm=surface_area_sqm, # พื้นที่ผิวรวมเท่าเดิม
            complexity_level=complexity_level,
            machine_name=machine_name
        )
        
        # เพิ่ม Setup / Assembly Time Overhead ต่องานทากาวประกอบกลับ (เช่น 0.5 ชม. ต่อจุดตัด)
        assembly_overhead_hours = (num_splits - 1) * 0.5
        total_split_hours = round(split_est.hours + assembly_overhead_hours, 2)
        foam_savings_pct = round((1 - (split_volume_removal_cm3 / unsplit_volume_removal_cm3)) * 100, 1)
    else:
        split_est = unsplit_est
        total_split_hours = unsplit_est.hours
        foam_savings_pct = 0.0

    return {
        "tool_reach_exceeded": is_tool_exceeded,
        "recommended_splits": num_splits,
        "max_depth_mm": max_part_depth_mm,
        "threshold_limit_mm": max_allowed_reach_mm,
        "unsplit_plan": {
            "milling_hours": unsplit_est.hours,
            "foam_waste_volume_cm3": round(unsplit_volume_removal_cm3, 2),
            "status": "RISK: Tool Reach Exceeded" if is_tool_exceeded else "SAFE"
        },
        "optimized_split_plan": {
            "milling_hours": total_split_hours,
            "foam_waste_volume_cm3": round(split_volume_removal_cm3, 2) if num_splits > 1 else round(unsplit_volume_removal_cm3, 2),
            "time_saved_hours": round(max(0.0, unsplit_est.hours - total_split_hours), 2),
            "foam_savings_pct": foam_savings_pct,
            "status": "SAFE"
        }
    }
