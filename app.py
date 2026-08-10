class ManufacturingCostCalculator:
    def __init__(self):
        # 1. ฐานข้อมูลวัสดุ
        self.materials = {
            "aluminum_6061": {
                "name": "อลูมิเนียม 6061",
                "density_g_cm3": 2.70,
                "price_per_kg": 180.0,
                "waste_factor": 1.10  # เผื่อเศษเสีย 10%
            },
            "stainless_304": {
                "name": "สแตนเลส 304",
                "density_g_cm3": 8.00,
                "price_per_kg": 220.0,
                "waste_factor": 1.08
            },
            "mild_steel": {
                "name": "เหล็กแผ่น SS400",
                "density_g_cm3": 7.85,
                "price_per_kg": 42.0,
                "waste_factor": 1.12
            }
        }

        # 2. ฐานข้อมูลเครื่องจักร (Machine & Rate DB)
        self.machines = {
            "cnc_milling_3axis": {
                "name": "CNC Milling 3-Axis",
                "machine_rate_per_hr": 450.0,  # ค่าชั่วโมงเครื่องจักร (บาท/ชม.)
                "labor_rate_per_hr": 200.0,    # ค่าแรงพนักงานคุมเครื่อง (บาท/ชม.)
                "default_setup_hr": 1.0        # เวลาเซ็ตเครื่องมาตรฐาน (ชม.)
            },
            "cnc_lathe": {
                "name": "CNC Lathe (เครื่องกลึง)",
                "machine_rate_per_hr": 350.0,
                "labor_rate_per_hr": 180.0,
                "default_setup_hr": 0.5
            },
            "laser_cutting": {
                "name": "Laser Cutting Machine",
                "machine_rate_per_hr": 800.0,
                "labor_rate_per_hr": 200.0,
                "default_setup_hr": 0.25
            }
        }

    def calculate_total_cost(
        self,
        material_key: str,
        surface_area_cm2: float,
        thickness_mm: float,
        machine_key: str,
        cycle_time_mins: float,
        batch_size: int = 1,
        setup_time_hrs: float = None,
        tooling_cost_per_part: float = 0.0,
        overhead_percent: float = 15.0
    ) -> dict:
        """
        คำนวณต้นทุนรวม (วัสดุ + ค่าแปรรูป + โอกับ)
        """
        # --- PART 1: คำนวณต้นทุนวัสดุ (Material Cost) ---
        if material_key not in self.materials:
            raise ValueError(f"ไม่พบวัสดุ: {material_key}")
        mat = self.materials[material_key]

        thickness_cm = thickness_mm / 10.0
        volume_cm3 = surface_area_cm2 * thickness_cm
        net_weight_kg = (volume_cm3 * mat["density_g_cm3"]) / 1000.0
        gross_weight_kg = net_weight_kg * mat["waste_factor"]
        material_cost_per_part = gross_weight_kg * mat["price_per_kg"]

        # --- PART 2: คำนวณค่าแปรรูป (Machining & Processing Cost) ---
        if machine_key not in self.machines:
            raise ValueError(f"ไม่พบเครื่องจักร: {machine_key}")
        mc = self.machines[machine_key]

        # รวมอัตราค่าบริการต่อชั่วโมง (Machine + Labor)
        total_hourly_rate = mc["machine_rate_per_hr"] + mc["labor_rate_per_hr"]

        # เวลา Setup ต่อชิ้น (หารกระจายตามขนาด Batch)
        actual_setup_hrs = setup_time_hrs if setup_time_hrs is not None else mc["default_setup_hr"]
        setup_time_per_part_hrs = actual_setup_hrs / batch_size
        setup_cost_per_part = setup_time_per_part_hrs * total_hourly_rate

        # เวลาการตัด/แปรรูปต่อชิ้น (Cycle Time)
        cycle_time_hrs = cycle_time_mins / 60.0
        run_cost_per_part = cycle_time_hrs * total_hourly_rate

        # ค่าแปรรูปพื้นฐานต่อชิ้น
        machining_cost_per_part = setup_cost_per_part + run_cost_per_part + tooling_cost_per_part

        # --- PART 3: สรุปต้นทุนรวมและ Overhead ---
        direct_cost = material_cost_per_part + machining_cost_per_part
        overhead_cost = direct_cost * (overhead_percent / 100.0)
        total_unit_cost = direct_cost + overhead_cost
        total_batch_cost = total_unit_cost * batch_size

        return {
            "summary": {
                "material_name": mat["name"],
                "machine_name": mc["name"],
                "batch_size": batch_size,
                "total_unit_cost": round(total_unit_cost, 2),
                "total_batch_cost": round(total_batch_cost, 2)
            },
            "breakdown_per_part": {
                "material_cost": round(material_cost_per_part, 2),
                "setup_cost": round(setup_cost_per_part, 2),
                "machining_run_cost": round(run_cost_per_part, 2),
                "tooling_cost": round(tooling_cost_per_part, 2),
                "overhead_cost": round(overhead_cost, 2)
            },
            "technical_details": {
                "gross_weight_kg": round(gross_weight_kg, 4),
                "cycle_time_mins": cycle_time_mins,
                "setup_hrs_total": actual_setup_hrs,
                "hourly_rate_combined": total_hourly_rate
            }
        }


# ==========================================
# ตัวอย่างการใช้งาน
# ==========================================
if __name__ == "__main__":
    calc = ManufacturingCostCalculator()

    # ตั้งค่าพารามิเตอร์การผลิต
    JOB_PARAMS = {
        "material_key": "aluminum_6061",   # วัสดุ: อลูมิเนียม 6061
        "surface_area_cm2": 320.0,          # พื้นที่ผิว 320 cm²
        "thickness_mm": 12.0,               # ความหนา 12 mm
        "machine_key": "cnc_milling_3axis", # เครื่องจักร: CNC Milling
        "cycle_time_mins": 18.0,            # เวลาแปรรูปจริงต่อชิ้น 18 นาที
        "batch_size": 20,                   # จำนวนผลิต 20 ชิ้น
        "setup_time_hrs": 1.5,              # เวลาเซ็ตเครื่อง 1.5 ชั่วโมง
        "tooling_cost_per_part": 25.0,      # ค่าสึกหรอดอกกัด/Tooling 25 บาท/ชิ้น
        "overhead_percent": 12.0            # โอกับ/บริหารจัดการ 12%
    }

    res = calc.calculate_total_cost(**JOB_PARAMS)

    # แสดงผลรายงาน
    print("==================================================")
    print("      รายงานสรุปการประเมินต้นทุนการผลิต (Manufacturing Cost)")
    print("==================================================")
    print(f"• วัสดุที่ใช้        : {res['summary']['material_name']}")
    print(f"• เครื่องจักร      : {res['summary']['machine_name']}")
    print(f"• ขนาด Batch การผลิต : {res['summary']['batch_size']} ชิ้น")
    print("--------------------------------------------------")
    print("สัดส่วนต้นทุนต่อชิ้น (Cost Breakdown per Unit):")
    print(f"  1. ค่าวัสดุ (Material Cost)     : {res['breakdown_per_part']['material_cost']:>8.2f} บาท")
    print(f"  2. ค่า Setup เครื่อง (หาร Batch)  : {res['breakdown_per_part']['setup_cost']:>8.2f} บาท")
    print(f"  3. ค่าแปรรูปจริง (Run Cost)     : {res['breakdown_per_part']['machining_run_cost']:>8.2f} บาท")
    print(f"  4. ค่า Tooling / เครื่องมือตัด  : {res['breakdown_per_part']['tooling_cost']:>8.2f} บาท")
    print(f"  5. ค่าโอกับ (Overhead {JOB_PARAMS['overhead_percent']}%)   : {res['breakdown_per_part']['overhead_cost']:>8.2f} บาท")
    print("--------------------------------------------------")
    print(f"★ ต้นทุนรวมต่อชิ้น (Total Unit Cost)  : {res['summary']['total_unit_cost']:>8.2f} บาท")
    print(f"★ ต้นทุนรวมทั้ง Batch ({JOB_PARAMS['batch_size']} ชิ้น)       : {res['summary']['total_batch_cost']:>8.2f} บาท")
    print("==================================================")
