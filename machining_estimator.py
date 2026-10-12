# --- 3D Print FDM (PETG) Parameters — ปรับปรุงเพื่อความแม่นยำของเวลาพิมพ์ ---
FDM_PROGRAM_HOURS = 2.0  # ปรับลดจาก 4.0 hr ให้สอดคล้องกับงานเตรียมไฟล์จริง
FDM_SETUP_HOURS = 4.0  # ปรับลดจาก 8.0 hr ให้สมเหตุสมผล
FDM_GRAMS_PER_ROLL = 1000.0
FDM_WEIGHT_K = 8535.7
FDM_WEIGHT_EXPONENT = 1.289
FDM_BASELINE_INFILL_PCT = 15.0
FDM_CALIBRATED_SQM_RANGE = (0.4, 1.4)
FDM_PETG_BAHT_PER_ROLL = 960.0


def estimate_3d_print_hours(
    volume_cm3: float = 0.0,
    surface_area_sqm: float = 0.0,
    infill_pct: float = 15.0,
    layer_height_mm: float = 0.28,  # ค่าเริ่มต้นความหนาชั้นพิมพ์ (0.2, 0.28, 0.32)
    complexity_level: int = 4,
    technology: str = "FDM",
    material: str = "PETG",
    waste_margin_pct: float = 8.0,  # เผื่อ Support & Loss 8%
) -> MachiningEstimate:
  """ประเมินงาน 3D Print FDM (PETG) ปรับปรุงความแม่นยำของเวลาพิมพ์ (Machine Hours)

  ตามสัดส่วนพื้นที่ผิว/น้ำหนัก และ Layer Height
  """
  volume_cm3 = max(volume_cm3, 0.0)
  area_sqm = max(surface_area_sqm, 0.0)

  if area_sqm == 0.0 and volume_cm3 > 0.0:
    approx_radius_cm = ((3.0 * volume_cm3) / (4.0 * math.pi)) ** (1.0 / 3.0)
    area_sqm = (4.0 * math.pi * (approx_radius_cm**2)) / 10000.0

  # 1. คำนวณน้ำหนักพลาสติก (Net & Gross Weight)
  infill_effective = max(float(infill_pct), 5.0)
  infill_factor = infill_effective / FDM_BASELINE_INFILL_PCT

  base_weight_g = (
      FDM_WEIGHT_K * (area_sqm**FDM_WEIGHT_EXPONENT) * infill_factor
      if area_sqm > 0
      else 0.0
  )
  gross_weight_g = base_weight_g * (1.0 + (waste_margin_pct / 100.0))

  # 2. คำนวณอัตราการฉีดเนื้อพลาสติกแบบแปรผัน (Dynamic Extrusion Speed g/hr)
  # สัดส่วนพื้นที่ผิวต่อน้ำหนัก (sq.m / kg)
  weight_kg = gross_weight_g / 1000.0
  area_to_weight_ratio = (
      (area_sqm / weight_kg) if weight_kg > 0 else 1.0
  )  # ปกติอยู่ช่วง 0.8 - 3.5

  # งานผิวเยอะ/รายละเอียดสูง (Ratio สูง) = พิมพ์ช้า (~16 g/hr)
  # งานก้อนตัน/Infill เยอะ (Ratio ต่ำ) = พิมพ์เร็ว (~32 g/hr)
  if area_to_weight_ratio > 2.0:
    base_grams_per_hour = 16.0  # งานผิวเยอะ / มี Retraction เยอะ
  elif area_to_weight_ratio < 1.0:
    base_grams_per_hour = 30.0  # งานก้อนเนื้อตัน เดินเร็ว
  else:
    # Interpolate ระหว่าง 16 - 30 g/hr
    base_grams_per_hour = 30.0 - (area_to_weight_ratio - 1.0) * 14.0

  # 3. ตัวคูณ Layer Height (อ้างอิงฐานที่ 0.28 mm)
  # พิมพ์ละเอียดขึ้น (เช่น 0.2 mm) ใช้เวลานานขึ้น (+35%)
  layer_factor = 0.28 / max(layer_height_mm, 0.1)

  # 4. คำนวณชั่วโมงพิมพ์จริง (Machine Hours)
  effective_grams_per_hour = base_grams_per_hour / layer_factor
  machine_hours = (
      gross_weight_g / effective_grams_per_hour if gross_weight_g > 0 else 0.0
  )

  # ช่วงเวลาประมาณการหน้างาน (Min - Max Hours: ±15%)
  hours_min = round(machine_hours * 0.85, 1)
  hours_max = round(machine_hours * 1.15, 1)

  # 5. Program & Setup Hours
  program_hours = FDM_PROGRAM_HOURS if gross_weight_g > 0 else 0.0
  setup_hours = FDM_SETUP_HOURS if gross_weight_g > 0 else 0.0
  billed_hours = machine_hours + program_hours

  # 6. ม้วน PETG
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
          # --- ข้อมูลน้ำหนักและม้วนพลาสติก ---
          "net_weight_g": round(base_weight_g, 1),
          "estimated_weight_g": round(gross_weight_g, 1),
          "petg_rolls_exact": rolls_exact,
          "petg_rolls_allocated": rolls_to_buy,
          "petg_cost_baht": round(rolls_exact * FDM_PETG_BAHT_PER_ROLL, 0),
          "effective_volume_cm3": round(plastic_volume_cm3, 2),
          # --- ชั่วโมงการทำงานและช่วงประเมิน ---
          "effective_grams_per_hour": round(effective_grams_per_hour, 1),
          "machine_hours": round(machine_hours, 2),
          "machine_hours_range": (hours_min, hours_max),  # (ชั่วโมง Min, Max)
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
