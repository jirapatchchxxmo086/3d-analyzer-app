"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรสำหรับ Robot CNC (กัดโฟม) และ 3D Print FDM

เวอร์ชันนี้ calibrate จากใบประเมินราคาจริง 5 ใบที่ผู้ใช้ให้มา (ส.ค. 2026) แทน
การเดาจากตารางพารามิเตอร์เครื่องจักรเพียงอย่างเดียว:

- Robot Foam: ชั่วโมงคำนวณจาก "พื้นที่ผิว" โดยตรง (ตามที่ผู้ใช้ยืนยัน) —
  fit เชิงเส้นกับข้อมูลจริง 3 ใบ (Level 5 ทั้งหมด) ได้ hours = 1.54 + 3.06×area_sqm
  คลาดเคลื่อน <1% ทุกใบ
- 3D Print FDM: ชั่วโมงคำนวณจาก "น้ำหนักเส้นพลาสติกที่ใช้จริง" (ตามที่ผู้ใช้ยืนยันว่า
  วัดกันที่ปริมาตร/น้ำหนักเพราะความเร็ว-อุณหภูมิเครื่อง fix อยู่แล้ว) — คำนวณจาก
  2 ใบจริงได้อัตราคงที่ 25 กรัม/ชั่วโมงเป๊ะทั้ง 2 ใบ (11,600g→464hr, 12,400g→496hr)

ทุกค่าที่ยัง "ASSUMPTION" (ยังไม่มีข้อมูลจริงรองรับพอ) มีคอมเมนต์กำกับไว้ชัดเจน —
ที่สำคัญสุดคือ: มีข้อมูล Level 5 อย่างเดียว จึงยังไม่รู้แน่ชัดว่าสูตรพื้นที่ผิว→
ชั่วโมงของ Robot Foam เปลี่ยนไปแค่ไหนที่ level อื่น (ใช้สมมติฐานเดิมจากสูตร
เวอร์ชันก่อนหน้าไปพลางๆ ว่า slope เปลี่ยน ±0.15 ชม./ตร.ม. ต่อ 1 level)
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import math


@dataclass
class MachiningEstimate:
    hours: float
    breakdown: Dict[str, Any]


# ==========================================================================
# ตารางพารามิเตอร์เครื่องจักรดิบ (จากสเปกที่ผู้ใช้ให้มา) — เก็บไว้เป็นข้อมูลอ้างอิง/
# เผื่อขยายไปเครื่องอื่นในอนาคต (CNC Router, Hotwire, lasers, Water Jet ยังไม่มี
# estimate_* ของตัวเอง) ไม่ได้ใช้ขับสูตรชั่วโมงโดยตรงอีกต่อไป เพราะข้อมูลใบประเมิน
# จริงแม่นกว่าสูตรฟิสิกส์ที่เดาจากพารามิเตอร์เพียงอย่างเดียว
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

# น้ำหนักวัสดุต่อปริมาตร (g/cm3) — ใช้แปลง effective_volume_cm3 -> น้ำหนักที่คาดว่า
# จะใช้จริง (กรัม) ก่อนจะแปลงเป็นชั่วโมงด้วยอัตรา 25 g/hr ที่ calibrate ไว้แล้ว
# ASSUMPTION: เป็นค่ามาตรฐานทั่วไปของวัสดุ ไม่ใช่ค่าที่วัดจากม้วนเส้นจริงของคุณ
MATERIAL_DENSITY_G_PER_CM3 = {"PETG": 1.27, "PLA": 1.24}

# --- Robot Foam: calibrated จากใบประเมินจริง 3 ใบ (ทั้งหมด Level 5) ----------
FOAM_CALIBRATION_LEVEL = 5
FOAM_INTERCEPT_HR = 1.54          # least-squares fit จากข้อมูลจริง, คลาดเคลื่อน <1%
FOAM_SLOPE_HR_PER_SQM = 3.06      # ที่ Level 5
# ASSUMPTION: ยังไม่มีข้อมูลจริงที่ level อื่น ใช้อัตราเปลี่ยนแปลงเดิมจากสูตร
# เวอร์ชันก่อนหน้า (ยังไม่ validate) — ถ้ามีใบประเมินที่ level อื่นส่งมาเพิ่มได้
# จะ fit slope(level) ให้แม่นแทนค่าคงที่นี้
FOAM_SLOPE_CHANGE_PER_LEVEL = 0.15

# --- 3D Print FDM: calibrated จากใบประเมินจริง 2 ใบ (Level 4 ทั้งคู่) --------
# 11,600g -> 464hr และ 12,400g -> 496hr ให้อัตราคงที่ 25 g/hr เป๊ะทั้ง 2 ใบ
FDM_GRAMS_PER_HOUR = 25.0
# ASSUMPTION: ความหนาผนัง (shell) ที่ใช้แปลง mesh volume -> น้ำหนักที่คาดว่าจะพิมพ์จริง
# (shell พิมพ์ 100% เสมอ ส่วนแกนในคูณด้วย infill_pct) ยังไม่มีข้อมูลยืนยัน
WALL_THICKNESS_MM = 1.2  # ≈ 3 เส้น nozzle 0.4mm


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
    คำนวณชั่วโมง Robot Foam CNC จากพื้นที่ผิวโดยตรง (ตามที่ยืนยันว่าเป็นหลักการ
    จริงที่ใช้อยู่) — calibrate จากใบประเมินจริง 3 ใบ:

        machine_hours = FOAM_INTERCEPT_HR + slope(complexity_level) × surface_area_sqm

    ซึ่งคือผลรวมของ roughing + finishing (ในของจริงไม่ได้แยกเป็น 2 ค่า มีแค่
    "Machine time" รวมเดียว) — ฟังก์ชันนี้แบ่งให้เป็น roughing/finishing สำหรับ
    2 ช่องกรอกในหน้าเว็บ ด้วยสัดส่วนที่เพิ่มขึ้นตาม complexity (ยังเป็น
    ASSUMPTION เรื่องสัดส่วนการแบ่ง — "ผลรวม" เท่านั้นที่ calibrate จริง)

    หมายเหตุสำคัญจากข้อมูลจริง: "Total Time" ที่ใช้คิดราคาในใบประเมิน =
    Program time + Machine time เท่านั้น **ไม่รวม Setup time** — Setup ดูเหมือน
    ถูกคิดแยกต่างหาก (ยืนยันตรงกันทั้ง 3 ใบ) ฟังก์ชันนี้จึงคืน roughing_hours +
    finishing_hours (= machine_hours) และ program_hours แยกออกจาก setup_hours
    ให้ผู้เรียกตัดสินใจเองว่าจะรวม setup เข้าราคาหรือไม่

    volume_removal_cm3 ไม่ได้ใช้คำนวณชั่วโมงอีกต่อไป (ตามข้อมูลจริงที่ยืนยันว่า
    คิดจากพื้นที่ผิว ไม่ใช่ปริมาตร) — แต่ยังรับพารามิเตอร์นี้ไว้เผื่อใช้กับ
    estimate_foam_blocks_needed() เพื่อคำนวณจำนวนก้อนโฟมที่ต้องใช้แทน
    """
    area_sqm = max(surface_area_sqm, 0.0)

    slope = FOAM_SLOPE_HR_PER_SQM + FOAM_SLOPE_CHANGE_PER_LEVEL * (
        complexity_level - FOAM_CALIBRATION_LEVEL
    )
    slope = max(slope, 0.1)  # กันไม่ให้ slope ติดลบที่ level ต่ำมากๆ
    machine_hours_total = FOAM_INTERCEPT_HR + slope * area_sqm

    # ASSUMPTION: สัดส่วน roughing/finishing เท่านั้น (ไม่กระทบผลรวมที่ calibrate
    # แล้ว) — งานซับซ้อนขึ้น สัดส่วนเวลากัดละเอียดควรมากขึ้น
    finishing_fraction = max(0.10, min(0.10 + 0.03 * complexity_level, 0.60))
    finishing_hours = machine_hours_total * finishing_fraction
    roughing_hours = machine_hours_total - finishing_hours

    finish_tool_mm = 6.0 if complexity_level >= 4 else 10.0

    # ASSUMPTION: program/setup ยังไม่ได้ calibrate แม่นเท่า machine_hours (มีแค่
    # 3 จุดข้อมูลที่ต่างขนาดกันมาก) — ใช้สูตรคร่าวๆ ที่ fit จุดข้อมูลใหญ่พอดี และ
    # floor ตามจุดข้อมูลเล็กสองจุด (0.2hr program / 1.0hr setup)
    program_hours = max(0.2, 0.23 * area_sqm)
    if setup_hours_override is not None:
        setup_hours = setup_hours_override
    else:
        setup_hours = max(1.0, 0.92 * area_sqm)

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
            "calibration_note": "hours = 1.54 + 3.06*area_sqm @ Level 5, fit to 3 real jobs, <1% error",
        },
    )


def estimate_foam_blocks_needed(
    width_mm: float,
    length_mm: float,
    height_mm: float,
    block_w_mm: float = 600.0,
    block_l_mm: float = 1220.0,
    block_h_mm: float = 2440.0,
    hollow_shell: bool = True,
    wall_thickness_mm: float = 75.0,
    waste_factor: float = 1.15,
) -> Dict[str, Any]:
    """
    ประมาณ "จำนวนก้อนโฟม" ที่ต้องใช้ เพื่อ link กับจำนวนวัสดุในหัวข้อ Material ถัดไป

    ⚠️ ค่าเริ่มต้น block_w/l/h_mm (600×1220×2440mm) เป็นแค่ตัวเลขตัวอย่าง — ยังไม่ใช่
    ขนาดก้อนโฟมจริงที่คุณใช้สั่งซื้อ กรุณาส่งขนาดจริงมาให้ปรับ ไม่งั้นตัวเลขที่ได้
    จะผิดตามสัดส่วนของขนาดที่ใช้เดา

    วิธีคำนวณ (โมเดลง่ายที่สุด — ยังไม่ใช่ nesting/packing จริง):
      1. ถ้า hollow_shell=True (ตรงกับ "Hollow Shell" ใน Foam Slicing Visualizer
         ที่มีอยู่แล้วในหน้า 2): คำนวณปริมาตรเฉพาะเปลือกหนา wall_thickness_mm
         รอบนอกโมเดล (bbox ลบด้วย bbox ที่หดเข้าไป 2×wall_thickness_mm ทุกแกน)
         ถ้า False: ใช้ปริมาตร bbox เต็มก้อน
      2. หารด้วยปริมาตรก้อนโฟม 1 ก้อน แล้วคูณ waste_factor (เผื่อเศษ/ของเสียจากการ
         เข้าไม้ต่อก้อน) ปัดขึ้นเป็นจำนวนเต็ม

    ⚠️ นี่เป็นการประมาณจากปริมาตรอย่างเดียว ไม่ได้คำนวณการจัดวาง/ตัดแบ่งจริงแบบที่
    Foam Slicing Visualizer (grid_visualizer.py) ทำ ถ้าอยากให้ตัวเลขตรงกับที่ผัง
    การตัดแบ่งแสดงในหน้าเว็บเป๊ะๆ แนะนำส่ง grid_visualizer.py มาให้ดูด้วย จะได้ผูก
    จำนวนก้อนกับ logic การ slice เดียวกัน แทนที่จะมี 2 สูตรคนละที่ที่อาจให้ตัวเลข
    ไม่ตรงกัน
    """
    bbox_volume_mm3 = width_mm * length_mm * height_mm

    if hollow_shell:
        inner_w = max(width_mm - 2 * wall_thickness_mm, 0.0)
        inner_l = max(length_mm - 2 * wall_thickness_mm, 0.0)
        inner_h = max(height_mm - 2 * wall_thickness_mm, 0.0)
        inner_volume_mm3 = inner_w * inner_l * inner_h
        material_volume_mm3 = max(bbox_volume_mm3 - inner_volume_mm3, 0.0)
    else:
        material_volume_mm3 = bbox_volume_mm3

    block_volume_mm3 = block_w_mm * block_l_mm * block_h_mm
    blocks_needed_raw = material_volume_mm3 / block_volume_mm3 if block_volume_mm3 > 0 else 0.0
    blocks_needed = math.ceil(blocks_needed_raw * waste_factor)

    return {
        "material_volume_cm3": round(material_volume_mm3 / 1000.0, 1),
        "block_volume_cm3": round(block_volume_mm3 / 1000.0, 1),
        "blocks_needed_raw": round(blocks_needed_raw, 2),
        "waste_factor": waste_factor,
        "blocks_needed": blocks_needed,
        "hollow_shell": hollow_shell,
        "wall_thickness_mm": wall_thickness_mm,
        "note": "Volumetric estimate only — not a real nesting/packing calculation.",
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
    คำนวณชั่วโมง 3D Print FDM จาก "น้ำหนักเส้นพลาสติกที่คาดว่าจะใช้" (ตามที่ยืนยัน
    ว่าคิดจากปริมาตร/น้ำหนักเพราะความเร็ว-อุณหภูมิเครื่อง fix อยู่แล้ว):

        weight_g = effective_volume_cm3 × material_density_g_per_cm3
        machine_hours = weight_g / FDM_GRAMS_PER_HOUR   (= 25 g/hr, calibrate แม่น
                                                            จากใบประเมินจริง 2 ใบ)

    effective_volume_cm3 = shell (ผนังนอก พิมพ์ 100% เสมอ) + แกนใน×infill_pct —
    ใช้ mesh volume จริงจากไฟล์ 3D + สมมติความหนาผนัง WALL_THICKNESS_MM

    ✅ Grams -> ชั่วโมง (25 g/hr): calibrate จากข้อมูลจริง แม่นเป๊ะ 2/2 ใบ
    ⚠️ Geometry -> grams (ผ่าน infill + ความหนาผนัง + ความหนาแน่นวัสดุ): ยังเป็น
    ASSUMPTION เพราะใบประเมินจริงมีแค่ "น้ำหนักที่ใช้จริง" ไม่มี infill % หรือ
    ความหนาแน่นวัสดุกำกับไว้ — ถ้าเครื่อง slicer ของคุณมีค่าประมาณน้ำหนักให้อยู่แล้ว
    แนะนำใช้ค่านั้นตรงๆ แทนการคำนวณจาก mesh volume ในขั้นนี้ จะแม่นกว่า
    """
    volume_cm3 = max(volume_cm3, 0.0)
    area_sqm = max(surface_area_sqm, 0.0)

    if area_sqm == 0.0 and volume_cm3 > 0.0:
        approx_radius_cm = ((3.0 * volume_cm3) / (4.0 * math.pi)) ** (1.0 / 3.0)
        approx_area_cm2 = 4.0 * math.pi * (approx_radius_cm ** 2) * 1.3
        area_sqm = approx_area_cm2 / 10000.0
    elif volume_cm3 == 0.0 and area_sqm > 0.0:
        # ASSUMPTION: ไม่มีปริมาตรจริง (เช่น mesh คำนวณ volume ไม่สำเร็จ) ประมาณ
        # ย้อนกลับจากพื้นที่ผิว โดยสมมติทรงกลม (เหมือนทิศทางตรงข้ามของ fallback
        # ด้านบน) — คร่าวมาก แต่ดีกว่าปล่อยให้ทั้งสูตรกลายเป็น 0 เงียบๆ
        area_cm2 = area_sqm * 10_000.0
        approx_radius_cm = math.sqrt(area_cm2 / (4.0 * math.pi * 1.3)) if area_cm2 > 0 else 0.0
        volume_cm3 = (4.0 / 3.0) * math.pi * (approx_radius_cm ** 3)

    shell_volume_cm3 = min(area_sqm * 10_000.0 * (WALL_THICKNESS_MM / 10.0), volume_cm3)
    core_volume_cm3 = max(volume_cm3 - shell_volume_cm3, 0.0)
    infill_fraction = max(0.0, min(infill_pct, 100.0)) / 100.0
    effective_volume_cm3 = shell_volume_cm3 + core_volume_cm3 * infill_fraction

    density = MATERIAL_DENSITY_G_PER_CM3.get(material, MATERIAL_DENSITY_G_PER_CM3["PETG"])
    weight_g = effective_volume_cm3 * density
    machine_hours = weight_g / FDM_GRAMS_PER_HOUR

    program_hours = 4.0   # ตรงกับใบประเมินจริงทั้ง 2 ใบเป๊ะ (ไม่ต้องแก้)
    setup_hours = 8.0     # ตรงกับใบประเมินจริงทั้ง 2 ใบเป๊ะ (ไม่ต้องแก้)
    total_time = machine_hours + program_hours + setup_hours

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
            "hours_per_cm3": round(machine_hours / effective_volume_cm3, 5) if effective_volume_cm3 > 0 else 0.0,
            "machine_hours": round(machine_hours, 2),
            "roughing_hours": 0.0,
            "finishing_hours": round(machine_hours, 2),
            "finish_tool_mm_used": 0.4,
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "hourly_rate_baht": 50,
            "calibration_note": "hours = weight_g / 25, weight_g exact-matched 2 real jobs (464hr@11.6kg, 496hr@12.4kg)",
        },
    )
