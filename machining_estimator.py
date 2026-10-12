"""machining_estimator.py

========================
โมดูลประเมินชั่วโมงเครื่องจักรสำหรับ Robot CNC (กัดโฟม) และ 3D Print FDM (PETG)
พร้อมระบบ Dynamic Flow-Rate Model และการคำนวณม้วนพลาสติก
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, Optional


@dataclass
class MachiningEstimate:
  hours: float
  breakdown: Dict[str, Any]


# ==========================================================================
# ตารางพารามิเตอร์และค่าคงที่
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
FOAM_HOURS_K = 4.6475
FOAM_HOURS_EXPONENT = 0.9092
FOAM_QTY_K = 0.2469
FOAM_QTY_EXPONENT = 1.1285
DEFAULT_FOAM_MAX_SEGMENT_MM = 1000.0

# --- 3D Print FDM (PETG) Parameters ---
FDM_PROGRAM_HOURS = 2.0
FDM_SETUP_HOURS = 4.0
FDM_GRAMS_PER_ROLL = 1000.0
FDM_WEIGHT_K = 8535.7
FDM_WEIGHT_EXPONENT = 1.289
FDM_BASELINE_INFILL_PCT = 15.0
FDM_CALIBRATED_SQM_RANGE = (0.4, 1.4)
FDM_PETG_BAHT_PER_ROLL = 960.0


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
  """ประเมินชั่วโมงกัด Robot CNC (โฟม) เท่านั้น"""
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


def estimate_foam_blocks_needed(
    surface_area_sqm: float,
) -> Dict[str, Any]:
  """คำนวณปริมาณวัตถุดิบโฟมที่ต้องใช้ จากพื้นที่ผิวของโมเดล (ตร.ม.)"""
  surface_area_sqm = max(surface_area_sqm, 0.0)

  if surface_area_sqm <= 0:
    blocks_needed = 0.0
  else:
    blocks_needed = round(
        FOAM_QTY_K * (surface_area_sqm**FOAM_QTY_EXPONENT), 1
    )

  return {
      "surface_area_sqm": round(surface_area_sqm, 3),
      "blocks_needed": blocks_needed,
      "formula_k": FOAM_QTY_K,
      "formula_exponent": FOAM_QTY_EXPONENT,
      "note": (
          "Surface-area power-law estimate, calibrated against real estimate"
          " sheets"
      ),
  }


def estimate_3d_print_hours(
    volume_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    infill_pct: float = 15.0,
    layer_height_mm: float = 0.28,
    complexity_level: int = 4,
    technology: str = "FDM",
    material: str = "PETG",
    waste_margin_pct: float = 8.0,
) -> MachiningEstimate:
  """ประเมินงาน 3D Print FDM (PETG) ปรับปรุงความแม่นยำของเวลาพิมพ์และสเปกม้วน PETG"""
  volume_cm3 = max(volume_cm3, 0.0)
  area_sqm = max(surface_area_sqm, 0.0)

  if area_sqm == 0.0 and volume_cm3 > 0.0:
    approx_radius_cm = ((3.0 * volume_cm3) / (4.0 * math.pi)) ** (1.0 / 3.0)
    area_sqm = (4.0 * math.pi * (approx_radius_cm**2)) / 10000.0

  # 1. คำนวณน้ำหนักพลาสติก
  infill_effective = max(float(infill_pct), 5.0)
  infill_factor = infill_effective / FDM_BASELINE_INFILL_PCT

  base_weight_g = (
      FDM_WEIGHT_K * (area_sqm**FDM_WEIGHT_EXPONENT) * infill_factor
      if area_sqm > 0
      else 0.0
  )
  gross_weight_g = base_weight_g * (1.0 + (waste_margin_pct / 100.0))

  # 2. Dynamic Flow-Rate Speed (g/hr)
  weight_kg = gross_weight_g / 1000.0
  area_to_weight_ratio = (area_sqm / weight_kg) if weight_kg > 0 else 1.0

  if area_to_weight_ratio > 2.0:
    base_grams_per_hour = 16.0
  elif area_to_weight_ratio < 1.0:
    base_grams_per_hour = 30.0
  else:
    base_grams_per_hour = 30.0 - (area_to_weight_ratio - 1.0) * 14.0

  # 3. Layer Height Factor
  layer_factor = 0.28 / max(layer_height_mm, 0.1)

  # 4. คำนวณชั่วโมงพิมพ์จริง
  effective_grams_per_hour = base_grams_per_hour / layer_factor
  machine_hours = (
      gross_weight_g / effective_grams_per_hour if gross_weight_g > 0 else 0.0
  )

  hours_min = round(machine_hours * 0.85, 1)
  hours_max = round(machine_hours * 1.15, 1)

  program_hours = FDM_PROGRAM_HOURS if gross_weight_g > 0 else 0.0
  setup_hours = FDM_SETUP_HOURS if gross_weight_g > 0 else 0.0
  billed_hours = machine_hours + program_hours

  # 5. สรุปม้วน PETG
  rolls_exact = round(gross_weight_g / FDM_GRAMS_PER_ROLL, 2)
  rolls_to_buy = math.ceil(gross_weight_g / FDM_GRAMS_PER_ROLL)

  density = MATERIAL_DENSITY_G_PER_CM3.get(
      material, MATERIAL_DENSITY_G_PER_CM3["PETG"]
  )
  plastic_volume_cm3 = gross_weight_g / density if density > 0 else 0.0

  lo, hi = FDM_CALIBRATED_SQM_RANGE
  outside_range = area_sqm > 0 and not (lo <= area_sqm <= hi)

  return MachiningEstimate(
      hours=round(billed_hours, 2),
      breakdown={
          "machine_type": "3D Print FDM",
          "surface_area_sqm": round(area_sqm, 4),
          "infill_pct": infill_pct,
          "layer_height_mm": layer_height_mm,
          "material": material,
          "density_g_per_cm3": density,
          "net_weight_g": round(base_weight_g, 1),
          "estimated_weight_g": round(gross_weight_g, 1),
          "petg_rolls_exact": rolls_exact,
          "petg_rolls_allocated": rolls_to_buy,
          "petg_cost_baht": round(rolls_exact * FDM_PETG_BAHT_PER_ROLL, 0),
          "effective_volume_cm3": round(plastic_volume_cm3, 2),
          "effective_grams_per_hour": round(effective_grams_per_hour, 1),
          "machine_hours": round(machine_hours, 2),
          "machine_hours_range": (hours_min, hours_max),
          "program_hours": round(program_hours, 2),
          "setup_hours": round(setup_hours, 2),
          "billed_total_hours_excl_setup": round(billed_hours, 2),
          "hourly_rate_baht": 50,
          "outside_calibrated_range": outside_range,
          "calibrated_sqm_range": FDM_CALIBRATED_SQM_RANGE,
          "calibration_note": (
              "FDM dynamic flow-rate model based on surface-to-weight ratio and"
              " layer height"
          ),
      },
  )
