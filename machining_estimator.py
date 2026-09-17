"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรและคำนวณจำนวนก้อนโฟม
ด้วยวิธี 3D Bounding Box Grid Fitting
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import math
import itertools


@dataclass
class MachiningEstimate:
    hours: float
    breakdown: Dict[str, Any]


# ==========================================================================
# ค่าคงที่และพารามิเตอร์เริ่มต้น
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

MATERIAL_DENSITY_G_PER_CM3 = {"PETG": 1.27, "PLA": 1.24}

# --- Robot Foam Parameters ---
FOAM_INTERCEPT_HR = 1.0
FOAM_SLOPE_HR_PER_SQM = 2.20
FOAM_MRR_CM3_PER_HR = 15000.0  # อัตราการกัดเนื้อโฟมออก (cm³/hr)

# --- 3D Print FDM Parameters ---
WALL_THICKNESS_MM = 1.2

# --- Foam Block Defaults (mm) ---
DEFAULT_FOAM_BLOCK_W_MM = 600.0
DEFAULT_FOAM_BLOCK_L_MM = 1220.0
DEFAULT_FOAM_BLOCK_H_MM = 2440.0
DEFAULT_FOAM_WASTE_FACTOR = 1.15


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def estimate_foam_cnc_hours(
    volume_removal_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    complexity_level: int = 3,
    setup_hours_override: Optional[float] = None,
    width_mm: float = 0.0,
    length_mm: float = 0.0,
    height_mm: float = 1000.0,
    allow_anatomical_split: bool = True,
    machine_name: str = "Robot_Foam",
) -> MachiningEstimate:
    """
    ประเมินชั่วโมงกัด Robot CNC โดยพิจารณาจาก:
    1. ปริมาตรเนื้อโฟมที่ต้องกัดออก (Material Removal Rate)
    2. พื้นที่ผิวงาน (Surface Finishing Time)
    3. ความสูง/ขนาด Bounding Box (Z-Travel Penalty)
    4. ระดับความซับซ้อน (Complexity Factor)
    """
    area_sqm = max(surface_area_sqm, 0.0)
    vol_removal = max(volume_removal_cm3, 0.0)
    max_dim_mm = max(width_mm, length_mm, height_mm, 0.0)

    # 1. คำนวณเวลากัดหยาบจากปริมาตรเนื้อวัสดุที่ต้องกัดออกจริง
    roughing_hours = vol_removal / FOAM_MRR_CM3_PER_HR if vol_removal > 0 else 0.5

    # 2. คำนวณเวลากัดละเอียดจากพื้นที่ผิว
    complexity_factor = 1.0 + 0.12 * (clamp(complexity_level, 1, 5) - 3)
    finishing_hours = (FOAM_INTERCEPT_HR + (FOAM_SLOPE_HR_PER_SQM * area_sqm)) * 0.45 * complexity_factor

    # 3. Z-Travel Factor (ชิ้นงานสูงเกิน 1 เมตร หัวกัดต้องยกและเคลื่อนที่ระยะไกลขึ้น)
    z_penalty = 1.0 + max(0.0, (max_dim_mm - 1000.0) / 2000.0)
    machine_hours_total = (roughing_hours + finishing_hours) * z_penalty

    finish_tool_mm = 6.0 if complexity_level >= 4 else 10.0

    program_hours = max(0.2, round(0.15 * area_sqm, 2))
    if setup_hours_override is not None:
        setup_hours = max(0.0, setup_hours_override)
    else:
        setup_hours = max(0.8, round(0.5 * area_sqm, 2))

    total_hours = round(machine_hours_total + program_hours + setup_hours, 2)

    return MachiningEstimate(
        hours=total_hours,
        breakdown={
            "machine_type": "Robot CNC (Foam)",
            "surface_area_sqm": round(area_sqm, 4),
            "volume_removal_cm3": round(vol_removal, 2),
            "machine_hours_total": round(machine_hours_total, 2),
            "roughing_hours": round(roughing_hours * z_penalty, 2),
            "finishing_hours": round(finishing_hours * z_penalty, 2),
            "finish_tool_mm_used": finish_tool_mm,
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "billed_total_hours_excl_setup": round(machine_hours_total + program_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "hourly_rate_baht": 300,
            "calibration_note": "3D Bounding Box & Removal Rate calibrated",
        },
    )


def estimate_foam_blocks_needed(
    width_mm: float,
    length_mm: float,
    height_mm: float,
    block_w_mm: float = DEFAULT_FOAM_BLOCK_W_MM,
    block_l_mm: float = DEFAULT_FOAM_BLOCK_L_MM,
    block_h_mm: float = DEFAULT_FOAM_BLOCK_H_MM,
    waste_factor: float = DEFAULT_FOAM_WASTE_FACTOR,
) -> Dict[str, Any]:
    """
    คำนวณจำนวนก้อนโฟมด้วยวิธี 3D Bounding Box Grid Fitting:
    - คำนวณจำนวนก้อนโฟมเต็มก้อนที่ต้องต่อกันตามแกน X, Y, Z
    - ลองหมุนทิศทาง Bounding Box ทั้ง 6 แบบเพื่อหาจำนวนก้อนโฟมน้อยที่สุด
    """
    piece_dims = (max(width_mm, 0.0), max(length_mm, 0.0), max(height_mm, 0.0))
    block_dims = (block_w_mm, block_l_mm, block_h_mm)

    if any(p <= 0 for p in piece_dims) or any(b <= 0 for b in block_dims):
        return {
            "blocks_needed_raw": 0,
            "waste_factor": waste_factor,
            "blocks_needed": 0.0,
            "units_per_axis": (0, 0, 0),
            "block_dims_mm": block_dims,
            "note": "Invalid dimensions",
        }

    best_units_product = None
    best_units_per_axis = (0, 0, 0)
    best_orientation = (0.0, 0.0, 0.0)

    # ทดลองหมุนทิศทางโมเดลเทียบกับขนาดก้อนโฟมมาตรฐาน
    for perm in itertools.permutations(piece_dims):
        units_x = math.ceil(perm[0] / block_dims[0])
        units_y = math.ceil(perm[1] / block_dims[1])
        units_z = math.ceil(perm[2] / block_dims[2])

        units_product = units_x * units_y * units_z

        if best_units_product is None or units_product < best_units_product:
            best_units_product = units_product
            best_units_per_axis = (units_x, units_y, units_z)
            best_orientation = perm

    blocks_needed_raw = best_units_product if best_units_product is not None else 0
    blocks_needed = round(blocks_needed_raw * waste_factor, 1)

    return {
        "blocks_needed_raw": blocks_needed_raw,
        "waste_factor": waste_factor,
        "blocks_needed": blocks_needed,
        "units_per_axis": best_units_per_axis,
        "fitted_dimensions_mm": best_orientation,
        "block_dims_mm": block_dims,
        "note": "3D Bounding Box Grid Fitting (Oriented Minimum Block Count)",
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
