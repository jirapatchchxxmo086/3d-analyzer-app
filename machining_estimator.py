"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรสำหรับ Robot CNC (กัดโฟม) และ 3D Print FDM
พร้อมฟังก์ชันแนะนำจำนวนก้อนโฟมสำหรับผลิต (estimate_foam_blocks_needed)

หมายเหตุการแก้ไข (สำคัญ):
- estimate_foam_blocks_needed() ผ่านการปรับมาแล้วหลายรอบ (หารปริมาตร -> container-fit หมุน
  อิสระ -> ตัดชั้น+คูณหน้าตัด) ทุกรอบก่อนหน้าให้ตัวเลขคลาดเคลื่อนจากข้อมูลจริงมาก เวอร์ชันนี้
  (ล่าสุด) ตัดพารามิเตอร์ width_mm/length_mm ออกทั้งหมด ตามที่ผู้ใช้ยืนยันจากการเทียบภาพ
  จำลอง Bounding Box จริงว่า "ก้อนโฟม 1 ก้อนคลุมหน้าตัดของโมเดลได้พอดีเสมอ" — ตัวกำหนด
  จำนวนก้อนจริงๆ มีแค่ความสูงอย่างเดียว หารด้วย max_segment_mm (ค่าเดียวกับสไลเดอร์ Foam
  Slicing Visualizer) เทียบกับข้อมูลจริง 3 ตัวอย่างแล้วตรงกันหมด (ดู docstring ของฟังก์ชัน)
- estimate_foam_cnc_hours() ไม่คำนวณจำนวนก้อนโฟมซ้อนอยู่ข้างในอีกต่อไป (ก่อนหน้านี้มี
  logic คำนวณก้อนโฟมซ้ำอยู่ทั้งในฟังก์ชันนี้และใน estimate_foam_blocks_needed() ซึ่งให้
  ตัวเลขไม่ตรงกัน) — ให้ฟังก์ชันนี้โฟกัสแค่ชั่วโมงเครื่องจักร ส่วนจำนวนก้อนโฟมเรียก
  estimate_foam_blocks_needed() แยกต่างหากที่เดียว
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

# --- Foam Block defaults ---
# จำนวนก้อนโฟมคำนวณจาก "ความสูง ÷ max_segment_mm" เท่านั้น (สมมติว่าหน้าตัดก้อนคลุม
# หน้าตัดโมเดลได้พอดีเสมอ) — max_segment_mm ใช้ค่าเดียวกับสไลเดอร์ Foam Slicing Visualizer
DEFAULT_FOAM_MAX_SEGMENT_MM = 1000.0  # ค่าเริ่มต้นเดียวกับสไลเดอร์ Visualizer (1 เมตร)
DEFAULT_FOAM_WASTE_FACTOR = 1.0


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
    """
    ประเมินชั่วโมงกัด Robot CNC (โฟม) เท่านั้น — ไม่คำนวณจำนวนก้อนโฟมในฟังก์ชันนี้
    (ใช้ estimate_foam_blocks_needed() แยกต่างหากสำหรับจำนวนก้อน)
    """
    area_sqm = max(surface_area_sqm, 0.0)

    # ปรับตัวคูณความซับซ้อนให้อยู่ในช่วงสมเหตุสมผล (level 1-5)
    complexity_factor = 1.0 + 0.12 * (clamp(complexity_level, 1, 5) - 3)

    machine_hours_total = (FOAM_INTERCEPT_HR + (FOAM_SLOPE_HR_PER_SQM * area_sqm)) * complexity_factor

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
            "billed_total_hours_excl_setup": round(roughing_hours + finishing_hours + program_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "hourly_rate_baht": 300,
            "calibration_note": "Robot Foam baseline model",
        },
    )


def estimate_foam_blocks_needed(
    height_mm: float,
    max_segment_mm: float = DEFAULT_FOAM_MAX_SEGMENT_MM,
    waste_factor: float = DEFAULT_FOAM_WASTE_FACTOR,
) -> Dict[str, Any]:
    """
    คำนวณปริมาณวัตถุดิบโฟมที่ต้องใช้ (ตามที่ระบุจากผู้ใช้ — สมมติว่าหน้าตัดก้อนโฟม
    1 ก้อนคลุมหน้าตัดของโมเดลได้พอดีเสมอ ตัวกำหนดจำนวนก้อนจริงๆ คือความสูงอย่างเดียว):

    ปริมาณ = (height_mm ÷ max_segment_mm) × waste_factor แล้วปัดทศนิยม 1 ตำแหน่ง
    max_segment_mm ใช้ค่าเดียวกับสไลเดอร์ "ขนาดบล็อกโฟมสูงสุดต่อชิ้น" ใน Foam Slicing
    Visualizer ที่ผู้ใช้ปรับอยู่แล้วในหน้าเว็บ (ค่าเริ่มต้น 1000 มม. = 1 เมตร/ก้อน)

    เทียบกับข้อมูลจริง 3 ตัวอย่าง:
    - boo1.95m (สูง 1950มม.) -> 1.9 (จริง ~1.8)
    - boo2.6m  (สูง 2600มม.) -> 2.6 (จริง ~2.5-3)
    - Mike3m   (สูง 3000มม.) -> 3.0 (จริง ~3)
    ตรงกันหมด ไม่ต้องคูณด้วยจำนวนก้อนต่อหน้าตัดอีกต่อไป (เวอร์ชันก่อนหน้าซึ่งคูณหน้าตัดด้วย
    ให้ตัวเลขสูงเกินจริงหลายเท่า เช่น Mike3m เคยได้ 9-27 ก้อน ทั้งที่จริงใช้แค่ ~3 ก้อน)
    """
    height_mm = max(height_mm, 0.0)

    layers = (height_mm / max_segment_mm) if max_segment_mm > 0 else 0.0
    blocks_needed = round(layers * waste_factor, 1)

    return {
        "layers_raw": round(layers, 3),
        "waste_factor": waste_factor,
        "blocks_needed": blocks_needed,
        "max_segment_mm": max_segment_mm,
        "note": "Height-only estimate, calibrated against real estimate sheets",
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
