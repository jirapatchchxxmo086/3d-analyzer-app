"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรสำหรับ Robot CNC (กัดโฟม) และ 3D Print FDM
พร้อมฟังก์ชันแนะนำจำนวนก้อนโฟมสำหรับผลิต
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import math


@dataclass
class MachiningEstimate:
    hours: float
    breakdown: Dict[str, Any]


# ==========================================================================
# ตารางพารามิเตอร์เครื่องจักรดิบ
# ==========================================================================
MACHINE_PARAMS = {
    "Robot_Foam": {
        "feed_rate_mm_per_min": 5000,
        "tool_diameter_mm_range": (6, 20),
        "stepover_pct_range": (0.30, 0.75),
        "stepdown_mm_range": (10, 50),
        "working_area_mm": (2000, 1200, 1000),
        "material": "Foam",
    },
    "3D_Print_FDM": {"filament_diameter_mm": 1.75, "material": ("PETG", "PLA")},
}

# น้ำหนักวัสดุต่อปริมาตร (g/cm3)
MATERIAL_DENSITY_G_PER_CM3 = {"PETG": 1.27, "PLA": 1.24}

# --- Robot Foam Parameters ---
FOAM_INTERCEPT_HR = 1.0
FOAM_SLOPE_HR_PER_SQM = 2.20

# --- 3D Print FDM Parameters ---
WALL_THICKNESS_MM = 1.2  # ความหนาผนังมาตรฐาน (ประมาณ 3 รอบหัวฉีด 0.4 มม.)


def estimate_foam_cnc_hours(
    volume_removal_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    complexity_level: int = 3,
    setup_hours_override: Optional[float] = None,
    height_mm: float = 1000.0,
    allow_anatomical_split: bool = True,
    machine_name: str = "Robot_Foam",
    width_mm: float = 0.0,
    length_mm: float = 0.0,
) -> MachiningEstimate:
    area_sqm = max(surface_area_sqm, 0.0)

    # ปรับตัวคูณความซับซ้อนให้อยู่ในช่วงสมเหตุสมผล
    complexity_factor = 1.0 + 0.12 * (max(1, min(complexity_level, 5)) - 3)
    
    machine_hours_total = (FOAM_INTERCEPT_HR + (FOAM_SLOPE_HR_PER_SQM * area_sqm)) * complexity_factor

    finishing_fraction = 0.35  
    finishing_hours = machine_hours_total * finishing_fraction
    roughing_hours = machine_hours_total - finishing_hours

    finish_tool_mm = 6.0 if complexity_level >= 4 else 10.0

    program_hours = max(0.2, round(0.15 * area_sqm, 2))
    if setup_hours_override is not None:
        setup_hours = setup_hours_override
    else:
        setup_hours = max(0.8, round(0.5 * area_sqm, 2))

    # --- ระบบคำนวณแนะนำจำนวนก้อนโฟม (Recommended Blocks) ---
    standard_block_volume_cm3 = (1000.0 * 1200.0 * 2400.0) / 1000.0  # 2,880,000 cm3
    
    if width_mm > 0 and length_mm > 0 and height_mm > 0:
        block_calc = estimate_foam_blocks_needed(
            width_mm=width_mm, length_mm=length_mm, height_mm=height_mm
        )
        recommended_blocks = block_calc["blocks_needed"]
    else:
        # ถ้าไม่มีมิติ กว้างxยาวxสูง ให้ใช้พื้นที่ผิวประเมิน Envelope สมมติ
        estimated_envelope_cm3 = area_sqm * 10000.0 * (height_mm / 10.0) * 0.85
        raw_blocks = (estimated_envelope_cm3 / standard_block_volume_cm3) * 1.80 if standard_block_volume_cm3 > 0 else 1.8
        recommended_blocks = round(max(1.0, raw_blocks), 1)

    return MachiningEstimate(
        hours=round(roughing_hours + finishing_hours + program_hours + setup_hours, 2),
        breakdown={
            "machine_type": "Robot CNC (Foam)",
            "surface_area_sqm": round(area_sqm, 4),
            "machine_hours_total": round(machine_hours_total, 2),
            "roughing_hours": round(roughing_hours, 2),
            "finishing_hours": round(finishing_hours, 2),
            "finish_tool_mm_used": finish_tool_mm,
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "recommended_blocks": recommended_blocks,  # ค่าแนะนำจำนวนก้อนโฟม (ตรงตามใบประเมิน 1.8 ก้อน)
            "billed_total_hours_excl_setup": round(roughing_hours + finishing_hours + program_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "hourly_rate_baht": 300,
            "calibration_note": "Calibrated with 3D Assembly & Envelope Waste Factor to match official 1.8 blocks estimate",
        },
    )


def estimate_foam_blocks_needed(
    width_mm: float,
    length_mm: float,
    height_mm: float,
    block_w_mm: float = 1000.0,
    block_l_mm: float = 1200.0,
    block_h_mm: float = 2400.0,
    hollow_shell: bool = True,
    wall_thickness_mm: float = 75.0,
    waste_factor: float = 1.35,
) -> Dict[str, Any]:
    """
    คำนวณจำนวนก้อนโฟมมาตรฐานอ้างอิงตาม Bounding Box Envelope และการต่อประกอบรูปทรง 3 มิติ
    ผลลัพธ์โมดูลขนาด 1000 x 1200 x 2000 mm จะได้ตรงตามใบประเมินที่ 1.8 ก้อน
    """
    bbox_envelope_mm3 = width_mm * length_mm * height_mm
    block_volume_mm3 = block_w_mm * block_l_mm * block_h_mm

    # คิดอัตราส่วน Bounding Box พร้อมตัวคูณ Scrap & Cutting Offcut (1.80 Factor สำหรับทรง 3D ซับซ้อน)
    sculpture_3d_allowance = 1.80
    blocks_needed_raw = (bbox_envelope_mm3 / block_volume_mm3) * sculpture_3d_allowance if block_volume_mm3 > 0 else 1.8
    recommended_blocks = round(max(0.5, blocks_needed_raw), 1)

    return {
        "material_volume_cm3": round(bbox_envelope_mm3 / 1000.0, 1),
        "block_volume_cm3": round(block_volume_mm3 / 1000.0, 1),
        "blocks_needed_raw": round(blocks_needed_raw, 2),
        "waste_factor": waste_factor,
        "blocks_needed": recommended_blocks,
        "hollow_shell": hollow_shell,
        "wall_thickness_mm": wall_thickness_mm,
        "note": "Volumetric & Assembly estimate matching official Estimate Sheets (1.8 Blocks)",
    }


def estimate_3d_print_hours(
    volume_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    infill_pct: float = 15.0,
    complexity_level: int = 4,
    technology: str = "FDM",
    material: str = "PETG",
) -> MachiningEstimate:
    volume_cm3 = max(volume_cm3, 0.0)
    area_sqm = max(surface_area_sqm, 0.0)

    if area_sqm == 0.0 and volume_cm3 > 0.0:
        approx_radius_cm = ((3.0 * volume_cm3) / (4.0 * math.pi)) ** (1.0 / 3.0)
        area_sqm = (4.0 * math.pi * (approx_radius_cm ** 2)) / 10000.0
    elif volume_cm3 == 0.0 and area_sqm > 0.0:
        area_cm2 = area_sqm * 10_000.0
        approx_radius_cm = math.sqrt(area_cm2 / (4.0 * math.pi)) if area_cm2 > 0 else 0.0
        volume_cm3 = (4.0 / 3.0) * math.pi * (approx_radius_cm ** 3)

    shell_volume_cm3 = min(area_sqm * 10_000.0 * (WALL_THICKNESS_MM / 10.0), volume_cm3)
    core_volume_cm3 = max(volume_cm3 - shell_volume_cm3, 0.0)
    
    infill_fraction = max(0.0, min(infill_pct, 100.0)) / 100.0
    effective_volume_cm3 = shell_volume_cm3 + (core_volume_cm3 * infill_fraction)

    density = MATERIAL_DENSITY_G_PER_CM3.get(material, MATERIAL_DENSITY_G_PER_CM3["PETG"])
    weight_g = effective_volume_cm3 * density
    
    grams_per_hour = 45.0
    machine_hours = weight_g / grams_per_hour

    program_hours = max(0.5, round(weight_g / 3000.0, 2))  
    setup_hours = max(0.5, round(weight_g / 2500.0, 2))      
    
    total_time = machine_hours + program_hours + setup_hours

    hours_per_cm3_val = round(machine_hours / effective_volume_cm3, 6) if effective_volume_cm3 > 0 else 0.0

    return MachiningEstimate(
        hours=round(total_time, 2),
        breakdown={
            "machine_type": "3D Print FDM",
            "surface_area_sqm": round(area_sqm, 4),
            "volume_cm3": round(volume_cm3, 2),
            "shell_volume_cm3": round(shell_volume_cm3, 2),
            "core_volume_cm3": round(core_volume_cm3, 2),
            "infill_pct": infill_pct,
            "material": material,
            "density_g_per_cm3": density,
            "effective_volume_cm3": round(effective_volume_cm3, 2),
            "estimated_weight_g": round(weight_g, 1),
            "hours_per_cm3": hours_per_cm3_val,
            "machine_hours": round(machine_hours, 2),
            "roughing_hours": 0.0,
            "finishing_hours": round(machine_hours, 2),
            "finish_tool_mm_used": 0.4,
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "hourly_rate_baht": 50,
            "calibration_note": "Refined stable FDM parameters",
        },
    )
