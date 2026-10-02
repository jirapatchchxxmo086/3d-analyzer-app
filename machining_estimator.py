"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรสำหรับ Robot CNC (กัดโฟม) และ 3D Print FDM
พร้อมฟังก์ชันแนะนำจำนวนก้อนโฟมสำหรับผลิต (estimate_foam_blocks_needed)

หมายเหตุการแก้ไข (สำคัญ):
- estimate_foam_blocks_needed() ผ่านการปรับมาแล้วหลายรอบ (หารปริมาตร -> container-fit หมุน
  อิสระ -> ตัดชั้น+คูณหน้าตัด -> ตัดชั้นอย่างเดียว) ทุกรอบก่อนหน้าใช้ได้กับโมเดลขนาดเล็ก-กลาง
  (สูงไม่เกิน ~2 เมตร) แต่พังหนักกับโมเดลใหญ่ (คลาดเคลื่อนหลักร้อย% เทียบกับใบประเมินจริง)
  เวอร์ชันนี้ (ล่าสุด) เปลี่ยนมาใช้ "พื้นที่ผิว" (surface_area_sqm) แทน bounding box ทั้งหมด
  โดยตรงจากการเทียบข้อมูลใบประเมินจริง 8 ตัวอย่าง (Apple Jack ~0.9m, Twilight Sparkle ~0.9m,
  Boo1.95m/2.6m, Mike3m/4m, Sully6m/8m — ครอบคลุมพื้นที่ผิว 1.6-168 ตร.ม.):

      Foam Qty = FOAM_QTY_K × (พื้นที่ผิว ตร.ม.) ^ FOAM_QTY_EXPONENT

  fit ด้วย log-log regression ได้ K=0.2469, exponent=1.1285, R²=0.988 (error -31% ถึง +23%
  ต่อจุด) — รอบแรก fit จากแค่ 6 จุด (5.1-168 ตร.ม.) เคยประเมินเกินจริงหนักสำหรับโมเดลเล็ก
  (+31% ถึง +47% เทียบกับ Apple Jack/Twilight Sparkle ที่เพิ่งได้ข้อมูลมา) เพราะเป็นการ
  extrapolate นอกช่วงข้อมูลที่เคยมี — เพิ่ม 2 จุดเล็กเข้าไปแล้วช่วยแก้จุดนี้ได้มาก

  เหตุผลที่พื้นที่ผิวสัมพันธ์กับปริมาณโฟมมากกว่าปริมาตร/bounding box: จากใบประเมินจริง
  โมเดลขนาดใหญ่ (เช่น Sully) มีรายการ "เหล็กกล่อง"/"เหล็กแผ่น" เป็นวัตถุดิบหลักร่วมด้วย —
  แปลว่าใช้ "โครงเหล็กเป็นแกน แล้วหุ้มผิวด้วยโฟม" ไม่ใช่ก้อนโฟมตันเต็มทั้งก้อน ปริมาณโฟม
  จึงแปรผันตามพื้นที่ผิวที่ต้องหุ้ม ไม่ใช่ปริมาตรหรือหน้าตัดของ bounding box

  หมายเหตุ: ความคลาดเคลื่อนที่เหลือ (-31% ถึง +23%) มาจากความไม่สม่ำเสมอในข้อมูลจริงเอง
  (ทิศทาง error ไม่สอดคล้องกันแม้สเกลจากตัวละครเดียวกัน — ดูบทสนทนาการวิเคราะห์ Boo2.6m ที่
  ให้ผลสวนทางกับ Mike/Sully) น่าจะเกิดจากปัจจัยที่ไม่มีในข้อมูลเรขาคณิต (เช่น การใช้เศษวัสดุ
  เก่า, ดุลยพินิจผู้ประเมิน) มากกว่าที่จะแก้ด้วยสูตรที่ซับซ้อนขึ้น — ต้องการข้อมูลเพิ่มอีกมาก
  (15+ จุด) ถึงจะลองใส่ตัวแปรที่ 2 ได้อย่างมั่นใจโดยไม่เสี่ยง overfitting

  ผลคือ estimate_foam_blocks_needed() ไม่รับ width_mm/length_mm/height_mm/max_segment_mm
  อีกต่อไป — รับแค่ surface_area_sqm อย่างเดียว ส่วน max_segment_mm (สไลเดอร์ Foam Slicing
  Visualizer) ยังมีผลแค่กับภาพจำลองการตัดชั้น ไม่มีผลกับตัวเลขนี้แล้ว
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
# FIX: สูตรเดิม (FOAM_INTERCEPT_HR + FOAM_SLOPE_HR_PER_SQM*sqm) ใต้จริงเสมอ 16-48% เทียบกับ
# ใบประเมินจริง 6 ตัวอย่าง เปลี่ยนมาใช้ power-law fit จากพื้นที่ผิวแทน (เทียบกับ "Total Time"
# = Program+Machine hours ในใบประเมินจริง ซึ่งเป็นตัวเลขที่ Total Machine Cost คำนวณจริง ไม่
# รวม Setup): FOAM_HOURS_K * sqm^FOAM_HOURS_EXPONENT ให้ error สม่ำเสมอ 2-18% ทุกขนาด (จากเดิม
# ที่เคยคลาดเคลื่อนสูงสุดถึง 48% โดยเฉพาะโมเดลขนาดเล็ก)
#
# หมายเหตุสำคัญ: ใบประเมินจริงทั้ง 6 ตัวอย่างเป็น Complexity Level 5 ทั้งหมด ดังนั้นค่า K/
# exponent ด้านล่างคือค่าที่ "level 5" พอดี — COMPLEXITY_FACTOR_AT_LEVEL[5] ถูก normalize ให้
# เท่ากับ 1.0 (ไม่ขยับตัวเลขที่ fit มา) ส่วน level อื่นจะลดสัดส่วนลงตามเดิม (สัมพัทธ์กัน)
FOAM_HOURS_K = 4.6475
FOAM_HOURS_EXPONENT = 0.9092

# --- 3D Print FDM (PETG) — calibrate จากใบประเมินจริง 7 ใบงานพิมพ์ล้วน (ไม่ผสมโฟม) ---
# พบว่า (1) ชั่วโมงพิมพ์ = น้ำหนักเส้น(g) / 25 พอดี ทุกใบที่มีน้ำหนักระบุ (สูตรเดิม 45 g/hr
# เร็วเกินจริง ทำให้ชั่วโมงต่ำกว่าจริง ~44%) (2) Program=4hr, Setup=8hr คงที่ทุกงาน ไม่ขึ้นกับ
# ขนาด และ Setup ไม่ถูกคิดเงิน (ค่าเครื่องจริง = Program+Machine เท่านั้น) (3) PETG 1 ม้วน≈1kg
# (967-1046 g/ม้วน) (4) น้ำหนัก ≈ K x sqm^exp (fit 7 จุด, mean|err|=14%, leave-one-out=20%)
# ข้อจำกัด: 7 จุดนี้พื้นที่ผิวแค่ 0.4-1.4 ตร.ม. เป็นงาน "พิมพ์ทั้งชิ้น" เท่านั้น (ไม่รวม kornkan
# ที่เป็นงานผสมโฟม+พิมพ์บางส่วน ปริมาณ PETG ไม่สัมพันธ์กับพื้นที่ผิวทั้งตัว)
FDM_GRAMS_PER_HOUR = 25.0
FDM_PROGRAM_HOURS = 4.0
FDM_SETUP_HOURS = 8.0            # แสดงในรายละเอียดเท่านั้น ใบจริงไม่คิดเงิน Setup
FDM_GRAMS_PER_ROLL = 1000.0
FDM_WEIGHT_K = 8535.7            # กรัม ที่พื้นที่ผิว 1 ตร.ม.
FDM_WEIGHT_EXPONENT = 1.289
FDM_BASELINE_INFILL_PCT = 15.0   # สมมติฐาน: ยังไม่ทราบ infill จริงที่ทีมตั้งตอนสไลซ์
FDM_CALIBRATED_SQM_RANGE = (0.4, 1.4)
FDM_PETG_BAHT_PER_ROLL = 960.0

# --- Foam Block defaults ---
# จำนวนก้อนโฟมคำนวณจากพื้นที่ผิว (ตร.ม.) — ค่า K/exponent fit จากใบประเมินจริง 8 ตัวอย่าง
# (ดูหมายเหตุด้านบน) — R²=0.988
FOAM_QTY_K = 0.2469
FOAM_QTY_EXPONENT = 1.1285

# max_segment_mm ยังใช้เป็นค่า default ของสไลเดอร์ "ขนาดบล็อกโฟมสูงสุดต่อชิ้น" ใน Foam
# Slicing Visualizer สำหรับภาพจำลองการตัดชั้นเท่านั้น ไม่มีผลกับ Foam Qty อีกต่อไป
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
    """
    ประเมินชั่วโมงกัด Robot CNC (โฟม) เท่านั้น — ไม่คำนวณจำนวนก้อนโฟมในฟังก์ชันนี้
    (ใช้ estimate_foam_blocks_needed() แยกต่างหากสำหรับจำนวนก้อน)

    machine_hours_total (= roughing_hours + finishing_hours) คือค่าที่ fit ตรงกับ "Total
    Time" (Program+Machine) ในใบประเมินจริงแล้ว — program_hours ด้านล่างจึงเป็นแค่ตัวเลข
    อ้างอิงในรายละเอียด (breakdown) ไม่ได้บวกซ้ำเข้าไปใน machine_hours_total หรือ .hours
    อีกต่อไป (เดิมเคยบวกซ้ำ ซึ่งจะทำให้ชั่วโมงรวมสูงเกินจริงเทียบกับสูตรใหม่นี้)
    """
    area_sqm = max(surface_area_sqm, 0.0)

    # ปรับตัวคูณความซับซ้อนให้อยู่ในช่วงสมเหตุสมผล (level 1-5) — normalize ให้ level 5 = 1.0
    # (เพราะสูตร power-law ด้านล่าง fit มาจากข้อมูลจริงที่เป็น level 5 ทั้งหมด) ระดับอื่นๆ
    # ลดสัดส่วนลงตามความสัมพัทธ์เดิม (1.0 + 0.12*(level-3)) หารด้วยค่าที่ level 5 (=1.24)
    raw_complexity_factor = 1.0 + 0.12 * (clamp(complexity_level, 1, 5) - 3)
    complexity_factor = raw_complexity_factor / 1.24

    machine_hours_total = FOAM_HOURS_K * (area_sqm ** FOAM_HOURS_EXPONENT) * complexity_factor if area_sqm > 0 else 0.0

    finishing_fraction = 0.35
    finishing_hours = machine_hours_total * finishing_fraction
    roughing_hours = machine_hours_total - finishing_hours

    finish_tool_mm = 6.0 if complexity_level >= 4 else 10.0

    # program_hours/setup_hours เก็บไว้ในรายละเอียดเฉยๆ (ไม่ถูกใช้ในหน้าเว็บตอนนี้ มีแค่
    # roughing_hours/finishing_hours เท่านั้นที่ถูกดึงไปใช้จริง) ไม่บวกเข้า machine_hours_total
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
            "billed_total_hours_excl_setup": round(roughing_hours + finishing_hours + program_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "hourly_rate_baht": 300,
            "calibration_note": "Robot Foam baseline model",
        },
    )


def estimate_foam_blocks_needed(
    surface_area_sqm: float,
) -> Dict[str, Any]:
    """
    คำนวณปริมาณวัตถุดิบโฟมที่ต้องใช้ จากพื้นที่ผิวของโมเดล (ตร.ม.) — fit จากใบประเมิน
    จริง 8 ตัวอย่าง (Apple Jack ~0.9m, Twilight Sparkle ~0.9m, Boo1.95m/2.6m, Mike3m/4m,
    Sully6m/8m) ครอบคลุมตั้งแต่โมเดลเล็กไปจนถึงใหญ่มาก (พื้นที่ผิว 1.6-168 ตร.ม.):

        Foam Qty = FOAM_QTY_K × (surface_area_sqm) ^ FOAM_QTY_EXPONENT

    เทียบกับข้อมูลจริง (R²=0.988, error -31% ถึง +23% ต่อจุด):
    - apple_jack        (1.6 ตร.ม.)  -> 0.42  (จริง 0.4)
    - twilight_sparkle  (2.2 ตร.ม.)  -> 0.60  (จริง 0.5)
    - boo1.95m          (5.1 ตร.ม.)  -> 1.55  (จริง 1.8)
    - boo2.6m           (9.1 ตร.ม.)  -> 2.98  (จริง 2.5)
    - mike3m            (17.5 ตร.ม.) -> 6.24  (จริง 9.0)
    - mike4m            (30.5 ตร.ม.) -> 11.68 (จริง 14.0)
    - sully6m           (94.5 ตร.ม.) -> 41.85 (จริง 34.0)
    - sully8m           (168 ตร.ม.)  -> 80.10 (จริง 74.0)

    แม่นยำกว่าทุกสูตรก่อนหน้ามาก (bounding-box/container-fit เคยคลาดเคลื่อนหลักร้อย-พัน%
    สำหรับโมเดลใหญ่ — ดูหมายเหตุด้านบนของไฟล์) ความคลาดเคลื่อนที่เหลืออยู่ (~20-30%) เกิด
    จากความไม่สม่ำเสมอในข้อมูลจริงเอง ไม่ใช่ที่รูปแบบสูตร — ต้องการข้อมูลอ้างอิงเพิ่มอีกมาก
    ก่อนจะลองปรับให้แม่นยำขึ้นไปกว่านี้ได้อย่างมั่นใจ
    """
    surface_area_sqm = max(surface_area_sqm, 0.0)

    if surface_area_sqm <= 0:
        blocks_needed = 0.0
    else:
        blocks_needed = round(FOAM_QTY_K * (surface_area_sqm ** FOAM_QTY_EXPONENT), 1)

    return {
        "surface_area_sqm": round(surface_area_sqm, 3),
        "blocks_needed": blocks_needed,
        "formula_k": FOAM_QTY_K,
        "formula_exponent": FOAM_QTY_EXPONENT,
        "note": "Surface-area power-law estimate, calibrated against 6 real estimate sheets (R2=0.98)",
    }


def estimate_3d_print_hours(
    volume_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    infill_pct: float = 15.0,
    complexity_level: int = 4,
    technology: str = "FDM",
    material: str = "PETG",
) -> MachiningEstimate:
    """
    ประเมินงาน 3D Print FDM (PETG) จากพื้นที่ผิว — calibrate จากใบประเมินจริง 7 ใบ
    (ดูหมายเหตุที่ค่าคงที่ FDM_* ด้านบนไฟล์)

        น้ำหนัก(g)  = FDM_WEIGHT_K x sqm^FDM_WEIGHT_EXPONENT x (infill / infill ฐาน)
        Machine(hr) = น้ำหนัก / 25 g/hr
        Program(hr) = 4 คงที่        Setup(hr) = 8 คงที่ (ไม่คิดเงิน)
        hours       = Program + Machine (ตรงกับ "Total Time" ที่ใบจริงใช้คิดค่าเครื่อง)
        PETG(ม้วน)  = น้ำหนัก / 1000

    ข้อจำกัดที่ยังไม่ได้ปิด:
    - volume_cm3 ไม่ถูกใช้คำนวณอีกต่อไป (ใบประเมินจริงไม่มีปริมาตรให้เทียบ) เก็บพารามิเตอร์ไว้
      เผื่อโค้ดเดิมที่เรียกใช้อยู่ ไม่ได้มีผลต่อผลลัพธ์
    - การปรับตาม infill เป็นสัดส่วนตรงจากค่าฐานสมมติ 15% ยังไม่มีข้อมูลจริงยืนยัน
    - complexity_level ยังไม่มีผล (ข้อมูล level 4/5 ที่มียังแยกผลกระทบไม่ออก)
    - พื้นที่ผิวนอกช่วง 0.4-1.4 ตร.ม. คือการเดานอกช่วงข้อมูลจริง (ดู outside_calibrated_range)
    """
    volume_cm3 = max(volume_cm3, 0.0)
    area_sqm = max(surface_area_sqm, 0.0)

    if area_sqm == 0.0 and volume_cm3 > 0.0:
        approx_radius_cm = ((3.0 * volume_cm3) / (4.0 * math.pi)) ** (1.0 / 3.0)
        area_sqm = (4.0 * math.pi * (approx_radius_cm ** 2)) / 10000.0

    # ผนังยังต้องพิมพ์เสมอแม้ infill ต่ำมาก จึงไม่ปล่อยให้ตัวคูณเหลือ 0
    infill_effective = max(float(infill_pct), 5.0)
    infill_factor = infill_effective / FDM_BASELINE_INFILL_PCT

    weight_g = FDM_WEIGHT_K * (area_sqm ** FDM_WEIGHT_EXPONENT) * infill_factor if area_sqm > 0 else 0.0

    machine_hours = weight_g / FDM_GRAMS_PER_HOUR
    program_hours = FDM_PROGRAM_HOURS if weight_g > 0 else 0.0
    setup_hours = FDM_SETUP_HOURS if weight_g > 0 else 0.0
    billed_hours = machine_hours + program_hours  # Setup ไม่คิดเงินตามใบประเมินจริง

    petg_rolls = weight_g / FDM_GRAMS_PER_ROLL
    density = MATERIAL_DENSITY_G_PER_CM3.get(material, MATERIAL_DENSITY_G_PER_CM3["PETG"])
    plastic_volume_cm3 = weight_g / density if density > 0 else 0.0

    lo, hi = FDM_CALIBRATED_SQM_RANGE
    outside_range = area_sqm > 0 and not (lo <= area_sqm <= hi)

    return MachiningEstimate(
        hours=round(billed_hours, 2),
        breakdown={
            "machine_type": "3D Print FDM",
            "surface_area_sqm": round(area_sqm, 4),
            "infill_pct": infill_pct,
            "material": material,
            "density_g_per_cm3": density,
            "estimated_weight_g": round(weight_g, 1),
            "petg_rolls": round(petg_rolls, 1),
            "petg_cost_baht": round(petg_rolls * FDM_PETG_BAHT_PER_ROLL, 0),
            "effective_volume_cm3": round(plastic_volume_cm3, 2),
            "hours_per_cm3": round(machine_hours / plastic_volume_cm3, 6) if plastic_volume_cm3 > 0 else 0.0,
            "machine_hours": round(machine_hours, 2),
            "roughing_hours": 0.0,
            "finishing_hours": round(machine_hours, 2),
            "finish_tool_mm_used": 0.4,
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "billed_total_hours_excl_setup": round(billed_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "hourly_rate_baht": 50,
            "outside_calibrated_range": outside_range,
            "calibrated_sqm_range": FDM_CALIBRATED_SQM_RANGE,
            "calibration_note": "FDM calibrated from 7 real quotes (0.4-1.4 sqm, full prints only)",
        },
    )
