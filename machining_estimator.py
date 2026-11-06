"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรสำหรับ Robot CNC (กัดโฟม) และ 3D Print FDM (PETG)
ผสานระบบคำนวณก้อนโฟม v2 และระบบคำนวณ FDM PETG ละเอียด (Wall layers, Shell fraction, 1.2kg rolls)
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, Optional


@dataclass
class MachiningEstimate:
    hours: float
    breakdown: Dict[str, Any]


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
FOAM_HOURS_K = 4.6475
FOAM_HOURS_EXPONENT = 0.9092
DEFAULT_FOAM_MAX_SEGMENT_MM = 1000.0


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


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

    raw_complexity_factor = 1.0 + 0.12 * (clamp(complexity_level, 1, 5) - 3)
    complexity_factor = raw_complexity_factor / 1.24

    machine_hours_total = (
        FOAM_HOURS_K * (area_sqm**FOAM_HOURS_EXPONENT) * complexity_factor
        if area_sqm > 0
        else 0.0
    )

    finishing_fraction = 0.35
    finishing_hours = machine_hours_total * finishing_fraction
    roughing_hours = machine_hours_total - finishing_hours

    finish_tool_mm = 6.0 if complexity_level >= 4 else 10.0

    program_hours = max(0.2, round(0.15 * area_sqm, 2))
    if setup_hours_override is not None:
        setup_hours = max(0.0, setup_hours_override)
    else:
        setup_hours = max(0.8, round(0.5 * area_sqm, 2))

    return MachiningEstimate(
        hours=round(roughing_hours + finishing_hours, 2),
        breakdown={
            "machine_type": "Robot CNC (Foam)",
            "surface_area_sqm": round(area_sqm, 4),
            "machine_hours_total": round(machine_hours_total, 2),
            "roughing_hours": round(roughing_hours, 2),
            "finishing_hours": round(finishing_hours, 2),
            "finish_tool_mm_used": finish_tool_mm,
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "billed_total_hours_excl_setup": round(
                roughing_hours + finishing_hours + program_hours, 2
            ),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "hourly_rate_baht": 300,
            "calibration_note": "Robot Foam baseline model",
        },
    )


def estimate_foam_blocks_v2(
    surface_area_sqm: float, z_height_mm: float = 0.0
) -> float:
    """สูตรคำนวณจำนวนก้อนโฟมกลาง (Dynamic Calibration v2)"""
    surface_area_sqm = max(float(surface_area_sqm), 0.0)

    if surface_area_sqm <= 0:
        return 0.0

    if surface_area_sqm < 10.0:
        blocks_needed = surface_area_sqm * 0.30
    elif surface_area_sqm < 32.0 and z_height_mm <= 4000.0:
        blocks_needed = (surface_area_sqm**0.95) * 0.38
    else:
        blocks_needed = (surface_area_sqm**0.85) * 0.90

    return round(blocks_needed, 1)


def estimate_foam_blocks_needed(
    surface_area_sqm: float, z_height_mm: float = 0.0
) -> Dict[str, Any]:
    """คำนวณจำนวนก้อนโฟม (เชื่อมโยงเข้ากับสูตรกลาง v2)"""
    surface_area_sqm = max(float(surface_area_sqm), 0.0)
    blocks_needed = estimate_foam_blocks_v2(
        surface_area_sqm=surface_area_sqm, z_height_mm=z_height_mm
    )
    return {
        "surface_area_sqm": round(surface_area_sqm, 3),
        "blocks_needed": blocks_needed,
        "formula_type": "Dynamic Calibrated Model v2",
        "note": "Multi-tier dynamic calibrated foam estimate",
    }


# ==========================================================================
# --- 3D Print FDM (PETG) Parameters & Advanced Logic (ผสานจาก fdm_estimator.py) ---
# ==========================================================================
FDM_ROLL_WEIGHT_G = 1200.0
FDM_BASELINE_INFILL_PCT = 9.0
FDM_BASELINE_WALLS = 2
FDM_PETG_BAHT_PER_ROLL = 960.0

FDM_GRAMS_PER_HOUR = 25.0
FDM_WEIGHT_K = 8535.7
FDM_WEIGHT_EXPONENT = 1.289
FDM_CALIBRATED_SQM_RANGE = (0.35, 1.4)
FDM_PROGRAM_HOURS = 2.0
FDM_SETUP_HOURS = 4.0

FDM_SHELL_FRACTION = 0.30
FDM_WALL_LINE_MM = 0.45


def ceil_rolls(rolls_exact: float) -> int:
    """ปัดขึ้นเป็นม้วนเต็ม (กันเลขทศนิยมคลาดเคลื่อน เช่น 2.0000001)"""
    return int(math.ceil(round(float(rolls_exact), 6))) if rolls_exact > 0 else 0


def estimate_petg_rolls_from_hours(
    machine_hours: float,
    waste_margin_pct: float = 0.0,
    grams_per_hour: float = FDM_GRAMS_PER_HOUR,
) -> Dict[str, Any]:
    """แปลงชั่วโมงพิมพ์ -> น้ำหนัก -> ม้วน (ปัดขึ้น) ใช้อัตรา 25 g/ชม. และน้ำหนักม้วน 1,200 กรัม"""
    weight_g = max(float(machine_hours), 0.0) * grams_per_hour
    rolls_exact = weight_g * (1.0 + waste_margin_pct / 100.0) / FDM_ROLL_WEIGHT_G
    rolls_to_buy = ceil_rolls(rolls_exact)
    return {
        "machine_hours": round(float(machine_hours), 2),
        "gross_weight_g": round(weight_g, 1),
        "roll_weight_g": FDM_ROLL_WEIGHT_G,
        "rolls_exact": round(rolls_exact, 2),
        "rolls_to_buy": rolls_to_buy,
        "total_material_cost_baht": round(rolls_to_buy * FDM_PETG_BAHT_PER_ROLL, 0),
        "baht_per_roll": FDM_PETG_BAHT_PER_ROLL,
    }


def estimate_3d_print_hours(
    volume_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    infill_pct: float = FDM_BASELINE_INFILL_PCT,
    complexity_level: int = 4,
    technology: str = "FDM",
    material: str = "PETG",
    wall_layers: int = 2,
    weight_override_g: Optional[float] = None,
    waste_margin_pct: float = 0.0,
    layer_height_mm: float = 0.28,
) -> MachiningEstimate:
    """
    น้ำหนัก = (K x sqm^p) x ตัวคูณ infill + น้ำหนักผนังส่วนที่เพิ่ม/ลดจาก 2 ชั้น
    ชั่วโมงพิมพ์ = น้ำหนัก / 25 g/ชม.   |   ม้วน = น้ำหนัก / 1200 g ปัดขึ้น
    ถ้าใส่ weight_override_g (น้ำหนักจากสไลเซอร์) จะใช้ค่านั้นแทนสูตร ซึ่งแม่นที่สุด
    """
    area_sqm = max(float(surface_area_sqm), 0.0)
    if area_sqm == 0.0 and volume_cm3 > 0.0:
        r_cm = ((3.0 * float(volume_cm3)) / (4.0 * math.pi)) ** (1.0 / 3.0)
        area_sqm = (4.0 * math.pi * r_cm ** 2) / 10000.0

    density = MATERIAL_DENSITY_G_PER_CM3.get(material, MATERIAL_DENSITY_G_PER_CM3["PETG"])
    infill_eff = max(float(infill_pct), 5.0)
    walls = max(1, int(wall_layers))
    infill_factor = FDM_SHELL_FRACTION + (1.0 - FDM_SHELL_FRACTION) * infill_eff / FDM_BASELINE_INFILL_PCT
    wall_extra_g = (walls - FDM_BASELINE_WALLS) * area_sqm * 10000.0 * (FDM_WALL_LINE_MM / 10.0) * density

    if weight_override_g and weight_override_g > 0:
        weight_g, source = float(weight_override_g), "slicer"
    elif area_sqm > 0:
        weight_g = max(FDM_WEIGHT_K * area_sqm ** FDM_WEIGHT_EXPONENT * infill_factor + wall_extra_g, 0.0)
        source = "formula"
    else:
        weight_g, source = 0.0, "none"

    machine_hours = weight_g / FDM_GRAMS_PER_HOUR
    program_hours = FDM_PROGRAM_HOURS if weight_g > 0 else 0.0
    setup_hours = FDM_SETUP_HOURS if weight_g > 0 else 0.0
    billed_hours = machine_hours + program_hours

    rolls_exact = weight_g * (1.0 + waste_margin_pct / 100.0) / FDM_ROLL_WEIGHT_G
    rolls_to_buy = ceil_rolls(rolls_exact)
    lo, hi = FDM_CALIBRATED_SQM_RANGE

    return MachiningEstimate(
        hours=round(billed_hours, 2),
        breakdown={
            "machine_type": "3D Print FDM",
            "surface_area_sqm": round(area_sqm, 4),
            "infill_pct": infill_pct,
            "wall_layers": walls,
            "layer_height_mm": layer_height_mm,
            "material": material,
            "density_g_per_cm3": density,
            "weight_source": source,
            "net_weight_g": round(weight_g, 1),
            "estimated_weight_g": round(weight_g, 1),
            "petg_roll_weight_g": FDM_ROLL_WEIGHT_G,
            "petg_rolls": round(rolls_exact, 2),
            "petg_rolls_exact": round(rolls_exact, 2),
            "petg_rolls_allocated": rolls_to_buy,
            "petg_rolls_to_buy": rolls_to_buy,
            "petg_cost_baht": round(rolls_to_buy * FDM_PETG_BAHT_PER_ROLL, 0),
            "petg_cost_exact_baht": round(rolls_exact * FDM_PETG_BAHT_PER_ROLL, 0),
            "effective_volume_cm3": round(weight_g / density, 2) if density > 0 else 0.0,
            "effective_grams_per_hour": FDM_GRAMS_PER_HOUR,
            "machine_hours": round(machine_hours, 2),
            "machine_hours_range": (round(machine_hours * 0.8, 1), round(machine_hours * 1.2, 1)),
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "billed_total_hours_excl_setup": round(billed_hours, 2),
            "hourly_rate_baht": 50,
            "outside_calibrated_range": source == "formula" and not (lo <= area_sqm <= hi),
            "calibrated_sqm_range": FDM_CALIBRATED_SQM_RANGE,
            "calibration_note": "FDM: hours = weight/25 g/hr; weight from surface area (7 real quotes); rolls 1.2 kg rounded up",
        },
    )
