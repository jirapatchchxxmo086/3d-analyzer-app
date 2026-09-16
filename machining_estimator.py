"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรสำหรับ Robot CNC (กัดโฟม) และ 3D Print FDM

เวอร์ชันนี้เปลี่ยน estimate_foam_cnc_hours จากสูตร curve-fit (calibrate จากแค่
2 จุดข้อมูล) มาเป็นสูตรฟิสิกส์การตัดเฉือนจริง (feed rate × tool diameter ×
stepover × stepdown) โดยใช้พารามิเตอร์จากตาราง "Machine Information" ของ
Robot (Foam) ที่ผู้ใช้ให้มา (ดู MACHINE_PARAMS ด้านล่าง)

ทุกค่าคงที่ที่ยังไม่มีข้อมูลจริงรองรับ (เช่น setup_hours, FDM print speed)
จะมีคอมเมนต์ "ASSUMPTION — ต้องยืนยัน" กำกับไว้ ให้ถือว่าเป็นค่าประมาณเริ่มต้น
ที่ควรเทียบกับงานจริงก่อนใช้ตัดสินใจราคาจริง
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import math


@dataclass
class MachiningEstimate:
    hours: float
    breakdown: Dict[str, Any]


# ==========================================================================
# ตารางพารามิเตอร์เครื่องจักร — คัดลอกจากสเปกที่ผู้ใช้ให้มา (ก.ย. 2026)
# เก็บไว้ทั้งหมดแม้ตอนนี้จะมีแค่ Robot_Foam ที่ถูกใช้จริงใน estimator ด้านล่าง
# เผื่อขยายไปเครื่องอื่น (CNC Router, Hotwire, lasers, Water Jet) ในอนาคต —
# เครื่องพวกนี้ใน app.py ตอนนี้ยังใช้ "1 ชั่วโมง" เป็นค่าเริ่มต้นเดาๆ อยู่
# ==========================================================================
MACHINE_PARAMS = {
    "Robot_Foam": {
        "feed_rate_mm_per_min": 5000,
        "tool_diameter_mm_range": (6, 20),
        "stepover_pct_range": (0.30, 0.75),   # fraction ของ tool diameter
        "stepdown_mm_range": (10, 50),
        "working_area_mm": (2000, 1200, 1000),
        "material": "Foam",
    },
    "Robot_Wood": {
        "feed_rate_mm_per_min": 800,
        "tool_diameter_mm_range": (3, 20),
        "working_area_mm": (2000, 1200, 1000),
        "material": "Wood",
    },
    "CNC_Router_ATC": {
        "feed_rate_mm_per_min_range": (1500, 6000),   # material-specific: 2000-4000
        "tool_diameter_mm_range": (1.5, 20),
        "stepover_pct_range": (0.20, 0.50),
        "stepdown_pct_range": (0.20, 0.50),           # % ของ tool diameter (ไม่ใช่ mm)
        "working_area_mm": (1250, 2450, 150),
        "material": "HMR",
    },
    "Hotwire": {
        "feed_rate_mm_per_min": 200,
        "working_area_mm": (2000, 1200, 1000),
        "material": "Foam",
    },
    "Fiber_laser_N2": {"feed_rate_mm_per_min": 4800, "material": "Metal sheet (0.8-6mm)"},
    "CO2_laser": {"feed_rate_mm_per_min": 1000, "material": "Acrylic"},
    "Water_Jet": {"feed_rate_mm_per_min": 600, "material": "Mirror / Cement board"},
    # 3D print FDM/SLA: ตารางที่ให้มายังไม่มี "Feed Rate / print speed" ของเครื่องพิมพ์
    # (มีแค่ 1.75mm ซึ่งคือเส้นผ่านศูนย์กลาง "เส้นฟิลาเมนต์" ไม่ใช่หัวฉีด/nozzle)
    # ต้องขอ print speed (mm/s), nozzle diameter, layer height เพิ่มถึงจะทำสูตร
    # ฟิสิกส์แบบเดียวกับ Robot Foam ได้ครบ — ดู docstring ของ estimate_3d_print_hours
    "3D_Print_FDM": {"filament_diameter_mm": 1.75, "material": ("PETG", "PLA")},
    "3D_Print_SLA": {"material": "Resin Standard / Clear"},
}


def _lerp(level: int, hi_at_level1: float, lo_at_level10: float,
          level_min: int = 1, level_max: int = 10) -> float:
    """
    เส้นตรงจาก hi_at_level1 (complexity ต่ำสุด) ไปหา lo_at_level10 (complexity สูงสุด)
    ใช้กับ stepover/stepdown ที่ควรเล็กลง (ละเอียดขึ้น) เมื่องานซับซ้อนขึ้น
    """
    level = max(level_min, min(level_max, level))
    t = (level - level_min) / (level_max - level_min)
    return hi_at_level1 - t * (hi_at_level1 - lo_at_level10)


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
    คำนวณชั่วโมง Robot Foam CNC จากพารามิเตอร์การตัดเฉือนจริงของแถว
    "Robot (Foam)" ในตาราง Machine Information — แทนสูตร curve-fit เดิมที่
    calibrate จากแค่ 2 จุดข้อมูล และไม่เคยใช้ volume_removal_cm3 เลย

    Roughing (กัดหยาบ) — volumetric material-removal-rate model:
        removal_rate_mm3_per_min = tool_diameter_mm × stepover_pct × stepdown_mm × feed_rate
        roughing_minutes = (volume_removal_cm3 × 1000) / removal_rate_mm3_per_min
                            + overhead ต่อ Z-level (retract/reposition)

    Finishing (กัดละเอียด) — surface raster model (ตอนนี้ใช้พื้นที่ผิวจริง
    และ "ระยะห่างเส้น" ที่แคบลงตาม complexity แทนค่าคงที่ ~0.7 ชม. แบบเดิม):
        line_spacing_mm = finish_tool_mm × finishing_stepover_pct
        finishing_minutes = (surface_area_mm2 / line_spacing_mm) / feed_rate

    ASSUMPTION — ต้องยืนยันก่อนใช้ตัดสินใจราคาจริง:
      - Tool diameter กัดหยาบ = ใช้ทูลใหญ่สุด (20mm) เสมอ (roughing เน้นความเร็ว)
      - เส้นโค้ง stepover/stepdown ตาม complexity: ตั้งเป็นเชิงเส้นจากปลายค่าสูงสุด
        ไปต่ำสุดของ range ที่ให้มา (งานซับซ้อนมาก = สเต็ปเล็กลง = กัดนานขึ้นแต่
        ปลอดภัยกว่าไม่กินเข้าเนื้อโมเดล)
      - setup_hours: ยังไม่มีข้อมูลจริง ใช้สูตรประมาณจากสัดส่วนความสูงชิ้นงาน
        เทียบพื้นที่ทำงานเครื่อง (0.5 ชม. ชิ้นเล็ก ถึง ~1.5 ชม. ชิ้นเกือบเต็มโต๊ะ)
      - program_hours: ประมาณว่างานซับซ้อนขึ้นใช้เวลาโปรแกรม/ตั้งค่า CAM นานขึ้น
      - overhead ต่อ Z-level: 0.5 นาที/level (retract + reposition)
      ถ้ามีชั่วโมงงานจริง (พื้นที่/ปริมาตร/complexity → ชั่วโมงที่ใช้จริง อย่างน้อย
      2-3 ชิ้นที่เคยผลิต) ส่งมาได้ จะ calibrate ตัวเลขเหล่านี้ให้แม่นกว่าการเดา
    """
    params = MACHINE_PARAMS["Robot_Foam"]
    feed_rate = params["feed_rate_mm_per_min"]
    _tool_d_min, tool_d_max = params["tool_diameter_mm_range"]
    stepover_min, stepover_max = params["stepover_pct_range"]
    stepdown_min, stepdown_max = params["stepdown_mm_range"]

    area_sqm = max(surface_area_sqm, 0.0)
    volume_removal_cm3 = max(volume_removal_cm3, 0.0)

    # FIX: เดิมมีแค่ fallback ทางเดียว (เดา area จาก volume) ถ้า volume มีแต่ area
    # ไม่มีก็ยัง error ได้ เพิ่ม fallback ย้อนกลับให้สมมาตรกัน
    if area_sqm == 0.0 and volume_removal_cm3 > 0.0:
        area_sqm = ((volume_removal_cm3 / 1_000_000.0) ** (2.0 / 3.0)) * 6.0
    if volume_removal_cm3 == 0.0 and area_sqm > 0.0:
        # ASSUMPTION: ไม่มีข้อมูลปริมาตรที่ต้องกัดออกจริง ประมาณจากความหนาเฉลี่ย
        # ของเนื้อโฟมส่วนเกินรอบโมเดล 50mm (กันหารด้วยศูนย์ ไม่ใช่ค่าที่แม่น)
        assumed_avg_removal_depth_mm = 50.0
        volume_removal_cm3 = (area_sqm * 10_000.0) * (assumed_avg_removal_depth_mm / 10.0)

    # --- Roughing: volumetric removal-rate model --------------------------
    roughing_tool_mm = tool_d_max
    roughing_stepover_pct = _lerp(complexity_level, stepover_max, stepover_min)
    roughing_stepdown_mm = _lerp(complexity_level, stepdown_max, stepdown_min)

    removal_rate_mm3_per_min = (
        roughing_tool_mm * roughing_stepover_pct * roughing_stepdown_mm * feed_rate
    )
    volume_removal_mm3 = volume_removal_cm3 * 1000.0
    roughing_minutes = (
        volume_removal_mm3 / removal_rate_mm3_per_min if removal_rate_mm3_per_min > 0 else 0.0
    )

    # FIX: height_mm รับเข้ามาแต่ไม่เคยถูกใช้เลยในเวอร์ชันก่อนหน้า — ใช้คำนวณ
    # จำนวน Z-level ของการกัดหยาบ + overhead retract/reposition ต่อชั้น
    z_levels = max(1, math.ceil(height_mm / roughing_stepdown_mm))
    overhead_min_per_level = 0.5  # ASSUMPTION
    roughing_minutes += z_levels * overhead_min_per_level

    # --- Finishing: surface raster model -----------------------------------
    finish_tool_mm = 6.0 if complexity_level >= 4 else 10.0
    # ASSUMPTION: finishing ใช้สเต็ปโอเวอร์ละเอียดกว่า roughing เสมอ (เพดาน 60%
    # แทน 75%) และยังลดลงตาม complexity เหมือนกัน — ทำให้ finishing ยาวขึ้นจริง
    # ตาม level แทนที่จะคงที่ ~0.7 ชม. แบบเดิม
    finishing_stepover_pct = _lerp(complexity_level, 0.60, stepover_min)
    line_spacing_mm = finish_tool_mm * finishing_stepover_pct
    surface_area_mm2 = area_sqm * 1_000_000.0
    finishing_path_len_mm = (
        surface_area_mm2 / line_spacing_mm if line_spacing_mm > 0 else 0.0
    )
    finishing_minutes = finishing_path_len_mm / feed_rate if feed_rate > 0 else 0.0

    roughing_hours = roughing_minutes / 60.0
    finishing_hours = finishing_minutes / 60.0

    # --- Setup & program time ----------------------------------------------
    if setup_hours_override is not None:
        setup_hours = setup_hours_override
    else:
        # FIX: เดิมเป็น `0.5 if area_sqm < 2.0 else 0.5` — สองฝั่งค่าเท่ากัน จึง
        # ไม่มีผลอะไรเลย (no-op). ตอนนี้ scale ตามสัดส่วนความสูงชิ้นงานเทียบมิติ
        # ที่ใหญ่สุดของพื้นที่ทำงานเครื่อง — ASSUMPTION ต้องยืนยันกับงานจริง
        max_working_dim_mm = max(params["working_area_mm"])
        size_ratio = min(height_mm / max_working_dim_mm, 1.0)
        setup_hours = 0.5 + size_ratio * 1.0   # 0.5 ชม. (ชิ้นเล็ก) ถึง 1.5 ชม. (เกือบเต็มโต๊ะ)

    # ASSUMPTION: งานซับซ้อนขึ้นใช้เวลาโปรแกรม/CAM setup นานขึ้น (เดิมคงที่ 0.2 ชม.)
    program_hours = 0.15 + complexity_level * 0.05

    total_time = roughing_hours + finishing_hours + program_hours + setup_hours

    return MachiningEstimate(
        hours=round(total_time, 2),
        breakdown={
            "machine_type": "Robot CNC (Foam)",
            "surface_area_sqm": round(area_sqm, 4),
            "volume_removal_cm3": round(volume_removal_cm3, 2),
            "roughing_hours": round(roughing_hours, 2),
            "finishing_hours": round(finishing_hours, 2),
            "roughing_tool_mm_used": roughing_tool_mm,
            "roughing_stepover_pct": round(roughing_stepover_pct, 3),
            "roughing_stepdown_mm": round(roughing_stepdown_mm, 2),
            "z_levels": z_levels,
            "finish_tool_mm_used": finish_tool_mm,
            "finishing_stepover_pct": round(finishing_stepover_pct, 3),
            "feed_rate_mm_per_min": feed_rate,
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "hourly_rate_baht": 300,
        },
    )


def estimate_3d_print_hours(
    volume_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    infill_pct: float = 15.0,
    complexity_level: int = 4,
    technology: str = "FDM",
) -> MachiningEstimate:
    """
    คำนวณชั่วโมง 3D Print FDM

    🔴 FIX (bug ร้ายแรงที่สุดที่เจอ): เวอร์ชันก่อนหน้านี้ breakdown dict ไม่มีคีย์
    'effective_volume_cm3' และ 'hours_per_cm3' เลย แต่ app.py เรียกใช้ 2 คีย์นี้
    ตรงๆ ตอนแสดงผล (`print_result.breakdown['effective_volume_cm3']` และ
    `['hours_per_cm3']`) — แปลว่าเดิมทุกครั้งที่เลือกเครื่อง "3D Print FDM" ใน
    หน้าประเมินราคา จะเกิด **KeyError และหน้าเว็บพังทันที** เพิ่ม 2 คีย์นี้แล้ว

    ⚠️ ตาราง Machine Information ที่ให้มายังไม่มี Feed Rate / print speed ของ
    เครื่อง 3D print FDM/SLA (มีแค่ 1.75mm ซึ่งคือเส้นผ่านศูนย์กลาง "เส้นฟิลาเมนต์"
    ไม่ใช่หัวฉีด) จึงยังทำสูตรฟิสิกส์แบบเดียวกับ Robot Foam ไม่ได้ครบ 100% — สูตร
    ด้านล่างนี้ปรับปรุง 2 อย่างจากของเดิมโดยไม่ต้องรอข้อมูลเพิ่ม:
      1) ทำให้ infill_pct มีผลจริง (เดิมรับพารามิเตอร์มาแต่ไม่ใช้เลย) —ผนัง
         ภายนอก (shell) พิมพ์ 100% เสมอ ส่วนแกนในคูณด้วย infill_pct
      2) ตัด "หน้าผาราคา" ออก (เดิมพื้นที่ 0.50 → 0.51 ตร.ม. ราคาขึ้นเกือบเท่าตัว)
         เปลี่ยนเป็นสูตรต่อเนื่องแทน

    ASSUMPTION — ต้องยืนยันก่อนใช้ตัดสินใจราคาจริง (ตัวเลขคาดเดาจากค่ามาตรฐาน
    ทั่วไปของเครื่อง FDM ไม่ใช่ค่าที่วัดจากเครื่องจริงของคุณ):
      - ความหนาผนัง (shell) สมมติ 1.2mm (≈ 3 เส้น nozzle 0.4mm)
      - อัตราการอัดวัสดุพื้นฐาน 8 mm³/s ที่ complexity level 1 ลดลง 5%/level
        (งานละเอียด = travel/retract เยอะ = extrude เฉลี่ยช้าลง)
      ถ้ามี print speed (mm/s), nozzle diameter, layer height จากสเปกเครื่องจริง
      หรือมีงานพิมพ์จริงที่รู้ทั้งปริมาตรและเวลาที่ใช้จริง (อย่างน้อย 2-3 ชิ้น)
      ส่งมาได้ จะ calibrate ตัวเลขพวกนี้ให้แม่นแทนค่าประมาณข้างต้น
    """
    volume_cm3 = max(volume_cm3, 0.0)
    area_sqm = max(surface_area_sqm, 0.0)

    if area_sqm == 0.0 and volume_cm3 > 0.0:
        approx_radius_cm = ((3.0 * volume_cm3) / (4.0 * math.pi)) ** (1.0 / 3.0)
        approx_area_cm2 = 4.0 * math.pi * (approx_radius_cm ** 2) * 1.3
        area_sqm = approx_area_cm2 / 10000.0

    WALL_THICKNESS_MM = 1.2  # ASSUMPTION
    shell_volume_cm3 = min(area_sqm * 10_000.0 * (WALL_THICKNESS_MM / 10.0), volume_cm3)
    core_volume_cm3 = max(volume_cm3 - shell_volume_cm3, 0.0)
    infill_fraction = max(0.0, min(infill_pct, 100.0)) / 100.0
    effective_volume_cm3 = shell_volume_cm3 + core_volume_cm3 * infill_fraction

    BASE_FLOW_CM3_PER_HR = 8.0 * 3600.0 / 1000.0  # 8 mm3/s -> 28.8 cm3/hr  ASSUMPTION
    complexity_factor = max(0.5, 1.0 - 0.05 * (max(1, min(complexity_level, 10)) - 1))
    effective_flow_cm3_per_hr = BASE_FLOW_CM3_PER_HR * complexity_factor
    hours_per_cm3 = 1.0 / effective_flow_cm3_per_hr if effective_flow_cm3_per_hr > 0 else 0.0

    machine_hours = effective_volume_cm3 * hours_per_cm3
    program_hours = 4.0
    setup_hours = 8.0
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
            "effective_volume_cm3": round(effective_volume_cm3, 2),
            "hours_per_cm3": hours_per_cm3,
            "machine_hours": round(machine_hours, 2),
            "roughing_hours": 0.0,
            "finishing_hours": round(machine_hours, 2),
            "finish_tool_mm_used": 0.4,
            "program_hours": round(program_hours, 2),
            "setup_hours": round(setup_hours, 2),
            "parts_count": 1,
            "assembly_labor_hours": 0.0,
            "hourly_rate_baht": 50,
        },
    )
