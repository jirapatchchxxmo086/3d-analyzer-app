"""
fdm_estimator.py
================
ประเมินงาน 3D Print FDM (PETG): ชั่วโมงพิมพ์ น้ำหนักเส้น และจำนวนม้วน

ข้อมูลจากหน้างาน (ยืนยันโดยทีม):
  - เส้น PETG 1 ม้วนหนัก 1.2 กก.
  - Infill มาตรฐาน 8-10%  (ใช้ 9% เป็นค่ากลาง)
  - ผนัง (wall layers) เริ่มต้น 2 ชั้น งานขอหนาพิเศษเพิ่มเป็น 3 ชั้น
  - จำนวนม้วนปัดขึ้นเป็นม้วนเต็มเสมอ (2.5 -> 3) เพราะม้วนที่แกะแล้วเสื่อมสภาพได้

ข้อมูลจากใบประเมินจริง 7 ใบ (งานพิมพ์ล้วน):
  - ชั่วโมงพิมพ์ = น้ำหนักเส้น (กรัม) / 25 พอดี
  - น้ำหนักเส้น ~ K x พื้นที่ผิว^p  (fit จาก 7 ใบ คลาดเฉลี่ย ~14%, ใบที่เพี้ยนสุดคือ montho +57%)

สิ่งที่ยังเป็นสมมติฐาน (ยังไม่มีข้อมูลจริงยืนยัน):
  - FDM_SHELL_FRACTION: สัดส่วนน้ำหนักที่ไม่ขึ้นกับ infill (ผนัง/ผิวบนล่าง)
  - FDM_WALL_LINE_MM: ความหนาของผนัง 1 ชั้น (ขึ้นกับขนาดหัวฉีด)
  - ค่าที่ fit มาผูกกับ infill 8-10% และผนัง 2 ชั้น ที่ทีมใช้เป็นมาตรฐาน

ไฟล์นี้ไม่พึ่ง machining_estimator.py (กัน import วน) ให้ machining_estimator.py ดึงฟังก์ชันจากที่นี่
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class MachiningEstimate:
    hours: float
    breakdown: Dict[str, Any]


# --- ข้อมูลจากทีม ---
FDM_ROLL_WEIGHT_G = 1200.0
FDM_BASELINE_INFILL_PCT = 9.0
FDM_BASELINE_WALLS = 2
FDM_PETG_BAHT_PER_ROLL = 960.0

# --- จากใบประเมินจริง ---
FDM_GRAMS_PER_HOUR = 25.0
FDM_WEIGHT_K = 8535.7            # กรัม ที่พื้นที่ผิว 1 ตร.ม. (ผนัง 2 ชั้น, infill ~9%)
FDM_WEIGHT_EXPONENT = 1.289
FDM_CALIBRATED_SQM_RANGE = (0.35, 1.4)
FDM_PROGRAM_HOURS = 2.0          # คงตามไฟล์เดิมของคุณ (ใบจริง 7 ใบเป็น Program 4 / Setup 8 ชม.)
FDM_SETUP_HOURS = 4.0

# --- สมมติฐาน (ดูหัวไฟล์) ---
FDM_SHELL_FRACTION = 0.30
FDM_WALL_LINE_MM = 0.45

MATERIAL_DENSITY_G_PER_CM3 = {"PETG": 1.27, "PLA": 1.24}


def ceil_rolls(rolls_exact: float) -> int:
    """ปัดขึ้นเป็นม้วนเต็ม (กันเลขทศนิยมคลาด เช่น 2.0000001 ไม่ให้กลายเป็น 3)"""
    return int(math.ceil(round(float(rolls_exact), 6))) if rolls_exact > 0 else 0


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
    layer_height_mm: float = 0.28,   # ยังไม่ใช้คำนวณ (ไม่มีข้อมูลจริงรองรับ) เก็บไว้ให้โค้ดเดิมเรียกได้
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
    billed_hours = machine_hours + program_hours          # Setup ไม่คิดเงินตามใบประเมินจริง

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


def estimate_petg_rolls_from_hours(
    machine_hours: float,
    waste_margin_pct: float = 0.0,
    grams_per_hour: float = FDM_GRAMS_PER_HOUR,
) -> Dict[str, Any]:
    """แปลงชั่วโมงพิมพ์ -> น้ำหนัก -> ม้วน (ปัดขึ้น) ใช้อัตรา 25 g/ชม. ชุดเดียวกับตัวประเมินหลัก"""
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
