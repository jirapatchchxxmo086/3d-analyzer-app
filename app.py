import streamlit as st

# Config หน้าจอ
st.set_page_config(page_title="3D Analyzer & Cost Estimator", layout="wide")

# ==========================================
# 1. Session State Initialization
# ==========================================
if 'lang' not in st.session_state:
    st.session_state.lang = 'TH'

if 'added_materials' not in st.session_state:
    st.session_state.added_materials = []

# ==========================================
# 2. ระบบจัดการภาษา (Language Selector)
# ==========================================
col_title, col_lang = st.columns([8, 2])

with col_lang:
    selected_lang = st.radio(
        "🌐 Language / ภาษา",
        options=["TH", "EN"],
        horizontal=True,
        index=0 if st.session_state.lang == 'TH' else 1
    )
    st.session_state.lang = selected_lang

TRANS = {
    "TH": {
        "main_title": "📐 ระบบประเมินราคาชิ้นงาน 3D & ต้นทุนการผลิต (3D Cost Estimator)",
        "dim_section": "📏 1. มิติชิ้นงาน ปริมาตร และพื้นที่ผิว (Dimensions & Surface Area)",
        "length": "ความยาว (Length) - mm",
        "width": "ความกว้าง (Width) - mm",
        "height": "ความสูง (Height) - mm",
        "surface_area": "พื้นที่ผิวรวม (Surface Area) - ตร.ม.",
        "volume": "ปริมาตร (Volume) - cm³",
        "labor_section": "⏱️ 2. ชั่วโมงการทำงาน & ค่าแรง (Labor & Machine Hours)",
        "labor_hrs": "ชั่วโมงทำงานช่าง (Labor Hours)",
        "labor_rate": "ค่าแรงช่าง (บาท/ชม.)",
        "machine_hrs": "ชั่วโมงเครื่องจักร (Machine Hours)",
        "machine_rate": "ค่าบริการเครื่องจักร (บาท/ชม.)",
        "mat_section": "📦 3. ระบบเลือกรายการวัสดุสำหรับผลิตชิ้นงาน (Material Master Selection)",
        "add_expander": "➕ คลิกเพื่อเลือกและเพิ่มรายการวัสดุลงในชิ้นงาน",
        "cat_label": "เลือกหมวดหมู่วัสดุ",
        "mat_label": "เลือกรายการวัสดุ",
        "qty_label": "จำนวน / หน่วย",
        "add_btn": "➕ เพิ่มวัสดุ",
        "table_title": "📋 รายการวัสดุที่เลือกในชิ้นงาน",
        "del_btn": "ลบ",
        "finish_section": "🎨 4. งานเคลือบผิวแข็ง & งานทำสี (Finishing & Painting)",
        "hardcoat_label": "ประเภท Hardcoat / เคลือบผิว",
        "paint_label": "ประเภทการทำสี / ปิดผิว",
        "no_select": "None / ไม่มี",
        "summary_section": "📊 5. สรุปการประเมินราคาและต้นทุนรวม (Cost & Price Summary)",
        "total_mat_price": "ราคากลางวัสดุรวม",
        "total_labor_price": "ค่าแรง & ค่าเครื่องรวม",
        "total_finish_price": "ค่างานทำสี/เคลือบผิวรวม",
        "grand_total_price": "💰 ราคาขายรวมทั้งสิ้น (Grand Total Price)",
        "grand_total_cost": "📉 ต้นทุนรวมประมาณการ (Estimated Total Cost)",
        "profit": "📈 กำไรขั้นต้นประมาณการ (Estimated Profit)",
        "price": "ราคาขาย",
        "cost": "ต้นทุน",
        "baht": "฿"
    },
    "EN": {
        "main_title": "📐 3D Cost Estimator & Material Master System",
        "dim_section": "📏 1. Dimensions, Volume & Surface Area",
        "length": "Length (mm)",
        "width": "Width (mm)",
        "height": "Height (mm)",
        "surface_area": "Total Surface Area (sq.m.)",
        "volume": "Total Volume (cm³)",
        "labor_section": "⏱️ 2. Labor & Machine Hours",
        "labor_hrs": "Labor Hours (hrs)",
        "labor_rate": "Labor Rate (฿/hr)",
        "machine_hrs": "Machine Hours (hrs)",
        "machine_rate": "Machine Rate (฿/hr)",
        "mat_section": "📦 3. Material Master Selection",
        "add_expander": "➕ Click to select and add materials",
        "cat_label": "Select Category",
        "mat_label": "Select Material Item",
        "qty_label": "Quantity / Unit",
        "add_btn": "➕ Add Material",
        "table_title": "📋 Selected Materials List",
        "del_btn": "Delete",
        "finish_section": "🎨 4. Finishing & Painting",
        "hardcoat_label": "Hardcoat / Coating Type",
        "paint_label": "Painting / Surface Finish Type",
        "no_select": "None",
        "summary_section": "📊 5. Cost & Price Summary",
        "total_mat_price": "Total Material Price",
        "total_labor_price": "Total Labor & Machine Price",
        "total_finish_price": "Total Finishing Price",
        "grand_total_price": "💰 Grand Total Price",
        "grand_total_cost": "📉 Estimated Total Cost",
        "profit": "📈 Estimated Profit",
        "price": "Price",
        "cost": "Cost",
        "baht": "฿"
    }
}

t = TRANS[st.session_state.lang]

with col_title:
    st.title(t["main_title"])

st.markdown("---")

# ==========================================
# 3. ฐานข้อมูลวัสดุสมบูรณ์ (Complete Database)
# ==========================================
MATERIAL_MASTER_DB = {
    "หมวด Foam": {
        "Foam 0.8 lb.": {"price": 2300, "cost": 2300},
        "Foam 1.0 lb.": {"price": 2850, "cost": 2850},
        "Foam 1.25 lb.": {"price": 3550, "cost": 3550},
        "Foam 1.5 lb.": {"price": 4100, "cost": 4100},
        "Foam 2.0 lb.": {"price": 6000, "cost": 6000},
        "Foam eva 50 มม.": {"price": 2520, "cost": 2100},
        "EVA แผ่น 30 มม.": {"price": 1440, "cost": 1200},
        "EVA แผ่นหนา 7mm": {"price": 13200, "cost": 11000},
    },
    "หมวด 3D Print / Resin": {
        "PLA Gray": {"price": 600, "cost": 500},
        "Resin Gray": {"price": 1200, "cost": 1000},
        "Resin ( 1000 / 1 sq.m. )": {"price": 1200, "cost": 1000},
        "เรซินใสหล่อพิเศษ 1kg": {"price": 350, "cost": 290},
        "เรซินใสหล่อพิเศษ 5kg": {"price": 960, "cost": 800},
        "Crystal resin": {"price": 1700, "cost": 1415},
    },
    "หมวด อะคริลิค (Acrylic)": {
        "อะคริลิคใส 1.5 3*6 ฟุต": {"price": 576, "cost": 480},
        "อะคริลิคใส 3 มม.": {"price": 2160, "cost": 1800},
        "Acrylic ใส 5 มม.": {"price": 3000, "cost": 2500},
        "Acrylic ใส 10 มม.": {"price": 5760, "cost": 4800},
        "Acrylic 2 mm.": {"price": 1440, "cost": 1200},
        "อะคริลิคขาว 5 มม.": {"price": 3000, "cost": 2500},
        "Acrylic 10 mm.": {"price": 5760, "cost": 4800},
        "Acrylic mirror 2 mm.": {"price": 2400, "cost": 2000},
        "อะคริลิค 25 มม.": {"price": 8640, "cost": 7200},
        "อะคริลิคแท่งใส 10 มม. 1.2 ม.": {"price": 456, "cost": 380},
        "แผ่นอะคริลิค 1 มม.": {"price": 450, "cost": 450},
        "แผ่นอะคริลิค 1.5 มม.": {"price": 750, "cost": 750},
        "แผ่นอะคริลิค 3 มม.": {"price": 1350, "cost": 1350},
        "แผ่นอะคริลิค 4 มม.": {"price": 2220, "cost": 1850},
        "แผ่นอะครีลิค 6 มม.": {"price": 6240, "cost": 5200},
        "แผ่นอะคลิลิกใส 5mm": {"price": 5000, "cost": 4160},
        "อะคริลิค 12 มม.": {"price": 5712, "cost": 4760},
    },
    "หมวด ไม้ / MDF / HMR / พลาสวูด": {
        "MDF 6 mm.": {"price": 300, "cost": 250},
        "MDF 10 mm.": {"price": 360, "cost": 300},
        "MDF 12 mm.": {"price": 420, "cost": 350},
        "MDF 15 mm.": {"price": 540, "cost": 450},
        "MDF 18 mm.": {"price": 660, "cost": 550},
        "MDF 25 mm.": {"price": 900, "cost": 750},
        "HMR 4 mm.": {"price": 255, "cost": 255},
        "HMR 6 mm.": {"price": 350, "cost": 350},
        "HMR 9 mm.": {"price": 475, "cost": 475},
        "Hmr 12 mm.": {"price": 635, "cost": 635},
        "Hmr 15 mm.": {"price": 780, "cost": 780},
        "Hmr 18 mm.": {"price": 910, "cost": 910},
        "HMR 25 mm.": {"price": 1150, "cost": 1150},
        "HMR Laminate 15 mm.": {"price": 2160, "cost": 1800},
        "HMR Laminate 18 mm.": {"price": 2400, "cost": 2000},
        "ไม้อัด 3 มม.": {"price": 180, "cost": 150},
        "ไม้อัด 6 มม.": {"price": 360, "cost": 300},
        "ไม้อัด 12 มม": {"price": 456, "cost": 380},
        "ไม้อัด 20 มม.": {"price": 1200, "cost": 1000},
        "ไม้อัดดัดโค้ง 6 มม.": {"price": 1080, "cost": 900},
        "ไม้อัดดัดโค้ง 10 มม.": {"price": 1308, "cost": 1090},
        "ไม้อัดยางมารีน 20mm": {"price": 4000, "cost": 3330},
        "ไม้จอยส์ ( 10 เส้น )": {"price": 320, "cost": 320},
        "ไม้โครง": {"price": 120, "cost": 100},
        "ไม้โอ๊ค veneer": {"price": 4000, "cost": 5600},
        "Plastwood 3 mm.": {"price": 420, "cost": 350},
        "Plastwood 4 mm.": {"price": 480, "cost": 400},
        "Plastwood 6 mm.": {"price": 660, "cost": 550},
        "Plastwood 10 mm.": {"price": 1440, "cost": 1200},
        "Plastwood 15 mm.": {"price": 1800, "cost": 1500},
        "Plastwood 20 mm.": {"price": 2400, "cost": 2000},
        "Plastwood 25 mm.": {"price": 3000, "cost": 2500},
    },
    "หมวด เหล็ก / สแตนเลส / โลหะ": {
        "เหล็กแผ่น 1 มม.": {"price": 850, "cost": 850},
        "เหล็กแผ่น 1.2 มม.": {"price": 1200, "cost": 1000},
        "เหล็กแผ่น 1.5 มม.": {"price": 1440, "cost": 1200},
        "เหล็กแผ่น 1.5 มม. 5*8": {"price": 2880, "cost": 2400},
        "เหล็กแผ่น 2 มม.": {"price": 1050, "cost": 1050},
        "เหล็กแผ่น 2.5 มม.": {"price": 2160, "cost": 1800},
        "เหล็กแผ่น 3 มม.": {"price": 2520, "cost": 2100},
        "เหล็กแผ่น 4 มม.": {"price": 3240, "cost": 2700},
        "เหล็กแผ่น 6 มม.": {"price": 3750, "cost": 3750},
        "เหล็กแผ่น 8 มม.": {"price": 6240, "cost": 5200},
        "เหล็กแผ่น 10 มม.": {"price": 5795, "cost": 5795},
        "เหล็กแผ่น 12 มม.": {"price": 6950, "cost": 6950},
        "เหล็กเส้น 4 มม. 1300": {"price": 100, "cost": 100},
        "เหล็กเส้น 10มม. 10ม.": {"price": 240, "cost": 200},
        "เหล็กกล่อง 1.25\" ( 32 มม.)": {"price": 600, "cost": 500},
        "เหล็กกล่อง 2*3 นิ้ว": {"price": 1200, "cost": 1000},
        "เหล็กท่อกลม 2 นิ้ว": {"price": 600, "cost": 500},
        "เหล็กท่อกลม 8 มม.": {"price": 120, "cost": 100},
        "เหล็กท่อกลม 6 นิ้ว": {"price": 1800, "cost": 1800},
        "เหล็กท่อกลม 20mm": {"price": 480, "cost": 400},
        "ท่อเหล็ก 1 นิ้ว": {"price": 216, "cost": 180},
        "ท่อเหล็ก 90 มม.": {"price": 5400, "cost": 4500},
        "ท่อเหล็ก 100 มม.": {"price": 6240, "cost": 5200},
        "เหล็กกลม 25mm ดัดโค้ง 2ชิ้น 1 ชุด": {"price": 4500, "cost": 3750},
        "เหล็กกลม 25mm ดัดโค้ง 2ชิ้น 10 ชุด": {"price": 4300, "cost": 3580},
        "เหล็กกลม 25mm ดัดโค้ง 2ชิ้น 20 ชุด": {"price": 4000, "cost": 3330},
        "Stainless แท่ง 10 มม. 1 ม.": {"price": 180, "cost": 150},
        "เพลาสแตนเลส 1/4 นิ้ว ( 6.35 มม. )": {"price": 270, "cost": 225},
        "เพลาสแตนเลส 3/16 นิ้ว ( 4.762 มม. )": {"price": 156, "cost": 130},
        "ท่อStainless 0.5 นิ้ว": {"price": 1800, "cost": 1500},
        "ท่อStainless 1 นิ้ว": {"price": 3000, "cost": 2500},
        "ท่อStainless 1.5 นิ้ว": {"price": 4200, "cost": 3500},
        "ท่อStainless 2 นิ้ว": {"price": 5400, "cost": 4500},
    },
    "หมวด แผ่นพลาสติก / พีวีซี / กระดาษ": {
        "แผ่น PVC": {"price": 70, "cost": 70},
        "แผ่น PVC ใส 5 มม.": {"price": 4200, "cost": 3500},
        "แผ่น PET 0.5 มม.": {"price": 65, "cost": 65},
        "แผ่น PET 1 มม.": {"price": 105, "cost": 105},
        "แผ่น PP": {"price": 100, "cost": 100},
        "แผ่นกระดาษ": {"price": 70, "cost": 70},
    },
    "หมวด สี / สารเคมี / งานปิดผิว": {
        "สีทากระดานดำ": {"price": 250, "cost": 200},
        "สีทองกลิตเตอร์ 1 ลิตร": {"price": 1440, "cost": 1200},
        "ตัวเคลือบ 2K 168 -3ลิตร": {"price": 3360, "cost": 2800},
        "Epoxy + PU Coating กันสนิม": {"price": 500, "cost": 415},
        "Walltex TOA 1 ถัง": {"price": 2148, "cost": 1790},
        "Texture ( 26A )": {"price": 340, "cost": 280},
        "ลามิเนตลายหินอ่อน": {"price": 1500, "cost": 1250},
        "Interior film ลายหินอ่อน 1*1 m.": {"price": 480, "cost": 400},
        "แผ่นปิดทอง ( 1 ตร.ม. )": {"price": 168, "cost": 140},
    },
    "หมวด ระบบไฟ / อุปกรณ์ไฟฟ้า": {
        "Strip light ( 1 m. )": {"price": 132, "cost": 110},
        "Strip light 4500k ( 1m. )": {"price": 600, "cost": 500},
        "Strip light 3000k ( 1m.)": {"price": 420, "cost": 350},
        "ไฟ COB 4000K ( 1 m )": {"price": 360, "cost": 300},
        "หม้อแปลง strip light": {"price": 1500, "cost": 1500},
        "Neon flex 12V ( 1 m.)": {"price": 180, "cost": 150},
        "Track light 4000K": {"price": 1800, "cost": 1500},
        "หลอดไฟกลม E27 Warm": {"price": 180, "cost": 150},
        "Light box 1 set": {"price": 5500, "cost": 4580},
        "Light box 10 set": {"price": 4500, "cost": 3750},
        "Light box 20 set": {"price": 4000, "cost": 3330},
    },
    "หมวด ฟิตติ้ง / อุปกรณ์ตกแต่ง / อื่นๆ": {
        "กระจก ( 5000 / 1 sq.m. )": {"price": 6000, "cost": 5000},
        "ท่อ PVC 25mm. 2.9 m.": {"price": 84, "cost": 70},
        "ท่อ pvc 1นิ้ว": {"price": 180, "cost": 150},
        "ข้อต่อเกรียวใน 1.5 นิ้ว": {"price": 120, "cost": 100},
        "เกรียวนอก 36 มม. 1ม.": {"price": 1200, "cost": 1000},
        "เชือกฟาง": {"price": 240, "cost": 200},
        "ชุดเข็มนาฬิกา": {"price": 300, "cost": 250},
        "แม่เหล็ก": {"price": 90, "cost": 75},
        "แม่เหล็ก ( 5*15*150 )": {"price": 300, "cost": 250},
        "ผ้าม่าน ( 1 ตร.ม. )": {"price": 1800, "cost": 1500},
        "สลิง 6 มม. ( 1 เมตร )": {"price": 120, "cost": 100},
        "หญ้าเทียม 50 sq.m.": {"price": 9600, "cost": 8000},
        "หญ้าเทียม 1 sq.m.": {"price": 192, "cost": 160},
        "Mechanic small": {"price": 36000, "cost": 30000},
        "Mechanic Large": {"price": 120000, "cost": 100000},
        "บานพับ": {"price": 360, "cost": 300},
        "บานพับแสตนเลส": {"price": 200, "cost": 165},
        "ผ้า canvas 1 เมตร": {"price": 216, "cost": 180},
        "ผ้า 210T": {"price": 120, "cost": 100},
        "ล้อ": {"price": 240, "cost": 200},
        "Cement board 12 มม.": {"price": 720, "cost": 600},
        "ยางกันลื่น 3มม. (1.2*1ม.)": {"price": 720, "cost": 600},
        "ทุ่งดอกหญ้า 1 ตร.ม.": {"price": 120, "cost": 100},
        "มือจับฝัง": {"price": 200, "cost": 165},
        "ลวดดัดโครง 4mm": {"price": 240, "cost": 200},
    }
}

# ==========================================
# 4. ส่วนที่ 1: วิเคราะห์พื้นที่ผิวและมิติชิ้นงาน (Dimensions & Surface Area)
# ==========================================
st.subheader(t["dim_section"])

dim_col1, dim_col2, dim_col3, dim_col4, dim_col5 = st.columns(5)

with dim_col1:
    length = st.number_input(t["length"], min_value=0.0, value=2610.56, step=10.0)
with dim_col2:
    width = st.number_input(t["width"], min_value=0.0, value=1700.0, step=10.0)
with dim_col3:
    height = st.number_input(t["height"], min_value=0.0, value=500.0, step=10.0)

# คำนวณพื้นที่ผิวอัตโนมัติ (ตร.ม.)
auto_surface_area = round(2 * ((length * width) + (length * height) + (width * height)) / 1_000_000, 2)
auto_volume = round((length * width * height) / 1000, 2)

with dim_col4:
    surface_area = st.number_input(t["surface_area"], min_value=0.0, value=auto_surface_area, step=0.1)
with dim_col5:
    volume = st.number_input(t["volume"], min_value=0.0, value=auto_volume, step=10.0)

st.markdown("---")

# ==========================================
# 5. ส่วนที่ 2: ชั่วโมงการทำงานและค่าบริการ (Labor & Machine Hours)
# ==========================================
st.subheader(t["labor_section"])

lab_col1, lab_col2, lab_col3, lab_col4 = st.columns(4)

with lab_col1:
    labor_hrs = st.number_input(t["labor_hrs"], min_value=0.0, value=12.0, step=0.5)
with lab_col2:
    labor_rate = st.number_input(t["labor_rate"], min_value=0.0, value=250.0, step=10.0)
with lab_col3:
    machine_hrs = st.number_input(t["machine_hrs"], min_value=0.0, value=8.0, step=0.5)
with lab_col4:
    machine_rate = st.number_input(t["machine_rate"], min_value=0.0, value=150.0, step=10.0)

total_labor_cost = (labor_hrs * labor_rate) + (machine_hrs * machine_rate)
total_labor_price = total_labor_cost * 1.2  # กำหนด Margin ค่าแรงเพิ่มเติม 20%

st.caption(f"💡 {t['total_labor_price']}: {t['baht']}{total_labor_price:,.2f} | {t['cost']}: {t['baht']}{total_labor_cost:,.2f}")

st.markdown("---")

# ==========================================
# 6. ส่วนที่ 3: เลือกรายการวัสดุ (Material Selection & Dynamic Table)
# ==========================================
st.subheader(t["mat_section"])

with st.expander(t["add_expander"], expanded=True):
    col1, col2, col3, col4 = st.columns([2.5, 2.5, 1.5, 1])
    
    categories = list(MATERIAL_MASTER_DB.keys())
    selected_cat = col1.selectbox(t["cat_label"], options=categories)
    
    items = list(MATERIAL_MASTER_DB[selected_cat].keys())
    selected_item = col2.selectbox(t["mat_label"], options=items)
    
    qty = col3.number_input(t["qty_label"], min_value=0.01, value=1.00, step=0.50)
    
    col4.markdown("<br>", unsafe_allow_html=True)
    if col4.button(t["add_btn"], type="primary"):
        item_data = MATERIAL_MASTER_DB[selected_cat][selected_item]
        st.session_state.added_materials.append({
            "category": selected_cat,
            "name": selected_item,
            "qty": qty,
            "unit_price": item_data["price"],
            "unit_cost": item_data["cost"],
            "total_price": item_data["price"] * qty,
            "total_cost": item_data["cost"] * qty
        })
        st.rerun()

    item_info = MATERIAL_MASTER_DB[selected_cat][selected_item]
    st.caption(f"{t['price']}: {t['baht']}{item_info['price']:,.2f} | {t['cost']}: {t['baht']}{item_info['cost']:,.2f}")

# แสดงตารางรายการวัสดุที่เลือก
if st.session_state.added_materials:
    st.write(f"### {t['table_title']}")
    
    total_mat_price = 0.0
    total_mat_cost = 0.0

    for idx, mat in enumerate(st.session_state.added_materials):
        c1, c2, c3, c4, c5, c6 = st.columns([3, 1.5, 2, 2, 2, 1])
        c1.write(f"**{mat['name']}** ({mat['category']})")
        c2.write(f"x {mat['qty']}")
        c3.write(f"{t['price']}: {t['baht']}{mat['total_price']:,.2f}")
        c4.write(f"{t['cost']}: {t['baht']}{mat['total_cost']:,.2f}")
        
        total_mat_price += mat['total_price']
        total_mat_cost += mat['total_cost']
        
        if c6.button(t["del_btn"], key=f"del_{idx}"):
            st.session_state.added_materials.pop(idx)
            st.rerun()
else:
    total_mat_price = 0.0
    total_mat_cost = 0.0

st.markdown("---")

# ==========================================
# 7. ส่วนที่ 4: งานเคลือบผิวแข็ง & งานทำสี (Finishing & Painting)
# ==========================================
st.subheader(t["finish_section"])

f_col1, f_col2 = st.columns(2)

# อัตราค่าบริการตามประเภทงานต่อ ตร.ม.
FINISH_RATES = {
    t["no_select"]: {"price": 0, "cost": 0},
    "Hardcoat Polyurea": {"price": 1200, "cost": 900},
    "Epoxy Resin": {"price": 800, "cost": 600},
    "2K Spray Painting": {"price": 1500, "cost": 1100},
    "PU Film Coating": {"price": 900, "cost": 700}
}

with f_col1:
    hardcoat = st.selectbox(t["hardcoat_label"], options=[t["no_select"], "Hardcoat Polyurea", "Epoxy Resin"])
    hc_rate = FINISH_RATES.get(hardcoat, {"price": 0, "cost": 0})
    hc_price = hc_rate["price"] * surface_area
    hc_cost = hc_rate["cost"] * surface_area
    st.caption(f"อัตราค่าบริการ: {t['baht']}{hc_rate['price']:,.2f} / ตร.ม. | ราคารวม: {t['baht']}{hc_price:,.2f}")

with f_col2:
    painting = st.selectbox(t["paint_label"], options=[t["no_select"], "2K Spray Painting", "PU Film Coating"])
    pt_rate = FINISH_RATES.get(painting, {"price": 0, "cost": 0})
    pt_price = pt_rate["price"] * surface_area
    pt_cost = pt_rate["cost"] * surface_area
    st.caption(f"อัตราค่าบริการ: {t['baht']}{pt_rate['price']:,.2f} / ตร.ม. | ราคารวม: {t['baht']}{pt_price:,.2f}")

total_finish_price = hc_price + pt_price
total_finish_cost = hc_cost + pt_cost

st.markdown("---")

# ==========================================
# 8. ส่วนที่ 5: สรุปผลการคำนวณทั้งหมด (Cost & Price Summary Dashboard)
# ==========================================
st.subheader(t["summary_section"])

grand_total_price = total_mat_price + total_labor_price + total_finish_price
grand_total_cost = total_mat_cost + total_labor_cost + total_finish_cost
profit = grand_total_price - grand_total_cost
margin_percent = (profit / grand_total_price * 100) if grand_total_price > 0 else 0.0

sum_col1, sum_col2, sum_col3 = st.columns(3)

sum_col1.metric(t["grand_total_price"], f"{t['baht']}{grand_total_price:,.2f}")
sum_col2.metric(t["grand_total_cost"], f"{t['baht']}{grand_total_cost:,.2f}")
sum_col3.metric(t["profit"], f"{t['baht']}{profit:,.2f}", delta=f"{margin_percent:.1f}% Margin")

st.info(f"💡 **สรุปสัดส่วนราคา:** รายการวัสดุ: {t['baht']}{total_mat_price:,.2f} | ค่าแรง & เครื่องจักร: {t['baht']}{total_labor_price:,.2f} | งานเคลือบ & ทำสี: {t['baht']}{total_finish_price:,.2f}")
