"""
machining_estimator.py
========================
โมดูลประเมินชั่วโมงเครื่องจักรอัตโนมัติ จากพารามิเตอร์เครื่องจริง + ข้อมูลเรขาคณิตของโมเดล 3D
แทนที่การรอทีมงานกรอกชั่วโมงเอง (ยังคงแก้มือทับได้เสมอ ไม่บังคับ)

เวอร์ชัน 2 — รองรับหลายโปรไฟล์เครื่องจักร (ขยายเพิ่มเครื่องใหม่ได้ในอนาคตโดยไม่ต้องแก้ฟังก์ชัน)
ใช้สูตรเชิงวิศวกรรม CAM/Slicer จริง:
  - Roughing: คำนวณจาก "ปริมาตรที่ต้องกัดออกจริง" (ไม่ใช่ทั้งบล็อกสี่เหลี่ยม)
  - Finishing: คำนวณจาก "พื้นที่ผิวจริงของโมเดล" (ไม่ใช่ราสเตอร์ทั้งหน้าตัดซ้ำทุกชั้นแบบ Roughing)

⚠️ นี่คือค่าประมาณ ไม่ใช่ตัวเลขแม่นยำ 100% ต้อง calibrate เทียบกับงานจริงก่อนเชื่อถือเต็มที่
"""

from dataclasses import dataclass


# ==========================================
# โปรไฟล์เครื่องจักร Foam CNC
# เพิ่มเครื่องใหม่ได้โดยเพิ่ม key ใหม่ในนี้ ไม่ต้องแก้ฟังก์ชันคำนวณเลย
# ==========================================

FOAM_CNC_MACHINES = {
    # โปรไฟล์นี้ใช้ค่าจากตาราง Machine Information จริงที่ทีมส่งมา (เครื่อง "Robot (Foam)")
    "Robot_Foam": {
        "max_feed_rate_mm_min": 5000.0,   # จากตาราง (Feed Rate)
        "efficiency_factor": 0.85,        # ⚠️ ค่าอ้างอิงทั่วไป ควร calibrate เทียบงานจริง
        "min_job_hours": 0.25,            # เวลาขั้นต่ำต่องาน (ติดตั้งชิ้นงาน/probe) กันชิ้นเล็กออกมาใกล้ 0 ชม.
        "processes": {
            "roughing": {
                "tool_diameter_mm": 20.0,     # ใช้ดอกใหญ่สุดในช่วง 6-20mm เพื่อกัดเร็ว
                "stepover_ratio": 0.50,       # กึ่งกลางช่วง 30-75% ที่ให้มา — ⚠️ ควรยืนยันค่าจริง
                "stepdown_mm": 25.0,          # กึ่งกลางช่วง 10-50mm ที่ให้มา — ⚠️ ควรยืนยันค่าจริง
                "recommended_feed_mm_min": 5000.0,
                "safety_margin": 1.15,
            },
            "finishing": {
                "min_tool_diameter_mm": 6.0,  # complexity สูงสุด (10) -> ดอกเล็กสุด ละเอียดสุด
                "max_tool_diameter_mm": 20.0, # complexity ต่ำสุด (1) -> ดอกใหญ่สุด เร็วสุด
                "stepover_ratio": 0.15,       # ค่าทั่วไปสำหรับงาน finishing (ละเอียดกว่า roughing)
                "recommended_feed_mm_min": 5000.0,
                "safety_margin": 1.10,
            },
        },
    },
    # ตัวอย่างโปรไฟล์เพิ่มเติม (เก็บไว้เผื่ออนาคตมีเครื่องรุ่นอื่น หรือปรับใช้ได้ทันที)
    "Foam_CNC_HighSpeed": {
        "max_feed_rate_mm_min": 10000.0,
        "efficiency_factor": 0.90,
        "min_job_hours": 0.2,
        "processes": {
            "roughing": {
                "tool_diameter_mm": 20.0, "stepover_ratio": 0.50, "stepdown_mm": 15.0,
                "recommended_feed_mm_min": 8000.0, "safety_margin": 1.10,
            },
            "finishing": {
                "min_tool_diameter_mm": 6.0, "max_tool_diameter_mm": 20.0, "stepover_ratio": 0.08,
                "recommended_feed_mm_min": 6000.0, "safety_margin": 1.05,
            },
        },
    },
}

# ⚠️ ค่าเหล่านี้ปรับจากการเทียบกับงานจริง 1 ชิ้น (17 Aug 2026, Color Culture — โมเดลขนาดใกล้เคียง)
# ยังเป็นการ calibrate จากจุดอ้างอิงเดียว ควรเก็บงานจริงเพิ่มมาเทียบอีกเพื่อความมั่นใจ
FDM_PRINT_DEFAULTS = {
    "print_speed_mm_min": 3000,
    "layer_height_mm": 0.6,        # ปรับจาก 0.2 -> 0.6 (เครื่องพิมพ์ใหญ่ใช้ layer หนากว่าเครื่องตั้งโต๊ะ)
    "line_width_mm": 0.7,          # ปรับจาก 0.4 -> 0.7 (หัวฉีดใหญ่กว่ามาตรฐาน 0.4mm)
    "shell_fraction": 0.3,
    "overhead_factor": 1.25,
    "min_job_hours": 0.25,
}


@dataclass
class MachiningEstimate:
    hours: float
    breakdown: dict  # รายละเอียดแต่ละส่วน เพื่อ debug/ตรวจสอบว่าคำนวณสมเหตุสมผลไหม


def estimate_foam_cnc_hours(
    volume_removal_cm3: float,
    surface_area_sqm: float,
    complexity_level: int,
    machine_name: str = "Robot_Foam",
) -> MachiningEstimate:
    """
    ประเมินชั่วโมง Foam CNC จาก 2 รอบ: Roughing (กัดหยาบเอาเนื้อออก) + Finishing (กัดตามผิว)
    ใช้โปรไฟล์เครื่องจักรจาก FOAM_CNC_MACHINES (เพิ่ม/แก้เครื่องได้ที่ด้านบนไฟล์นี้)

    volume_removal_cm3 : ปริมาตรที่ต้องกัดออก (Bounding Box volume - ปริมาตรชิ้นงานจริง) หน่วย cm3
    surface_area_sqm   : พื้นที่ผิวจริงของโมเดล (จาก mesh) หน่วย ตร.ม.
    complexity_level   : 1-10 ยิ่งสูง ยิ่งต้องใช้ดอกเล็กกัดละเอียด (finishing ช้าลง)
    """
    if machine_name not in FOAM_CNC_MACHINES:
        raise ValueError(f"ไม่พบโปรไฟล์เครื่องจักร: {machine_name}")
    machine = FOAM_CNC_MACHINES[machine_name]
    rough = machine["processes"]["roughing"]
    finish = machine["processes"]["finishing"]
    complexity_level = max(1, min(10, complexity_level))

    volume_removal_mm3 = max(volume_removal_cm3, 0) * 1000.0
    surface_area_mm2 = max(surface_area_sqm, 0) * 1_000_000.0

    # --- Roughing: ปริมาตรที่ต้องกัดออกจริง หารด้วยหน้าตัดที่กัดได้ต่อครั้ง (stepover x stepdown) ---
    stepover_rough_mm = rough["tool_diameter_mm"] * rough["stepover_ratio"]
    stepdown_mm = rough["stepdown_mm"]
    roughing_path_mm = (
        volume_removal_mm3 / (stepover_rough_mm * stepdown_mm)
        if stepover_rough_mm > 0 and stepdown_mm > 0 else 0.0
    )
    rough_feed = min(rough["recommended_feed_mm_min"], machine["max_feed_rate_mm_min"]) * machine["efficiency_factor"]
    roughing_time_min = (roughing_path_mm / rough_feed * rough["safety_margin"]) if rough_feed > 0 else 0.0

    # --- Finishing: พื้นที่ผิวจริง หารด้วย stepover (ดอกเล็กลงตาม complexity) ---
    finish_tool_mm = finish["max_tool_diameter_mm"] - (
        finish["max_tool_diameter_mm"] - finish["min_tool_diameter_mm"]
    ) * (complexity_level - 1) / 9.0
    stepover_finish_mm = finish_tool_mm * finish["stepover_ratio"]
    finishing_path_mm = surface_area_mm2 / stepover_finish_mm if stepover_finish_mm > 0 else 0.0
    finish_feed = min(finish["recommended_feed_mm_min"], machine["max_feed_rate_mm_min"]) * machine["efficiency_factor"]
    finishing_time_min = (finishing_path_mm / finish_feed * finish["safety_margin"]) if finish_feed > 0 else 0.0

    total_hours = (roughing_time_min + finishing_time_min) / 60.0
    total_hours = max(total_hours, machine["min_job_hours"])  # กันชิ้นเล็กออกมาเป็น 0 ชม.

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
    print_speed_mm_min: float = None,
    layer_height_mm: float = None,
    line_width_mm: float = None,
    shell_fraction: float = None,
    overhead_factor: float = None,
) -> MachiningEstimate:
    """
    ประเมินชั่วโมง 3D Print FDM จากปริมาตรชิ้นงานและค่าพารามิเตอร์การพิมพ์

    volume_cm3 : ปริมาตรชิ้นงานจริง (ไม่ใช่ bounding box) หน่วย cm3
    infill_pct : เปอร์เซ็นต์ infill ที่จะใช้พิมพ์ (0-100)
    """
    p = FDM_PRINT_DEFAULTS
    print_speed_mm_min = print_speed_mm_min or p["print_speed_mm_min"]
    layer_height_mm = layer_height_mm or p["layer_height_mm"]
    line_width_mm = line_width_mm or p["line_width_mm"]
    shell_fraction = shell_fraction if shell_fraction is not None else p["shell_fraction"]
    overhead_factor = overhead_factor or p["overhead_factor"]

    volume_mm3 = max(volume_cm3, 0) * 1000.0
    infill_fraction = max(0.0, min(100.0, infill_pct)) / 100.0

    effective_volume_mm3 = volume_mm3 * (shell_fraction + (1 - shell_fraction) * infill_fraction)
    cross_section_mm2 = layer_height_mm * line_width_mm
    extrusion_length_mm = effective_volume_mm3 / cross_section_mm2 if cross_section_mm2 > 0 else 0.0

    time_min = (extrusion_length_mm / print_speed_mm_min if print_speed_mm_min > 0 else 0.0) * overhead_factor
    total_hours = max(time_min / 60.0, p["min_job_hours"])

    return MachiningEstimate(
        hours=round(total_hours, 2),
        breakdown={
            "effective_volume_cm3": round(effective_volume_mm3 / 1000.0, 2),
            "extrusion_length_m": round(extrusion_length_mm / 1000.0, 1),
            "overhead_factor": overhead_factor,
        },
    )
