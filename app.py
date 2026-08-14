import streamlit as st

# Config หน้าจอ Streamlit
st.set_page_config(page_title="3D Analyzer & Cost Estimator", layout="wide")

# ==========================================
# 1. ระบบจัดการภาษา (Language Selector)
# ==========================================
if 'lang' not in st.session_state:
    st.session_state.lang = 'TH'

col_lang1, col_lang2 = st.columns([8, 2])
with col_lang2:
    selected_lang = st.radio(
        "🌐 Language / ภาษา",
        options=["TH", "EN"],
        horizontal=True,
        index=0 if st.session_state.lang == 'TH' else 1
    )
    st.session_state.lang = selected_lang

# พจนานุกรมคำแปล UI
TRANS = {
    "TH": {
        "title": "📦 ระบบเลือกรายการวัสดุสำหรับผลิตชิ้นงาน (Material Master Selection)",
        "add_expander": "➕ คลิกเพื่อเลือกและเพิ่มรายการวัสดุลงในชิ้นงาน",
        "cat_label": "เลือกหมวดหมู่วัสดุ",
        "mat_label": "เลือกรายการวัสดุ",
        "qty_label": "จำนวน / หน่วย",
        "add_btn": "➕ เพิ่มวัสดุ",
        "price": "ราคาขาย",
        "cost": "ต้นทุน",
        "finish_title": "🎨 งานเคลือบผิวแข็ง & งานทำสี (Finishing & Painting)",
        "hardcoat_label": "ประเภท Hardcoat / เคลือบผิว",
        "paint_label": "ประเภทการทำสี / ปิดผิว",
        "no_hardcoat": "None / ไม่มี",
        "no_paint": "None / ไม่มี",
        "service_rate": "อัตราค่าบริการ",
        "total_price": "ราคารวม",
        "sqm": "ตร.ม.",
        "baht": "฿"
    },
    "EN": {
        "title": "📦 Material Master Selection",
        "add_expander": "➕ Click to select and add materials",
        "cat_label": "Select Category",
        "mat_label": "Select Material Item",
        "qty_label": "Quantity / Unit",
        "add_btn": "➕ Add Material",
        "price": "Price",
        "cost": "Cost",
        "finish_title": "🎨 Finishing & Painting",
        "hardcoat_label": "Hardcoat / Coating Type",
        "paint_label": "Painting / Surface Finish Type",
        "no_hardcoat": "None",
        "no_paint": "None",
        "service_rate": "Service Rate",
        "total_price": "Total Price",
        "sqm": "sq.m.",
        "baht": "฿"
    }
}

t = TRANS[st.session_state.lang]

# ==========================================
# 2. ฐานข้อมูลวัสดุสมบูรณ์ (Complete Database)
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
# 3. ส่วน UI: Material Master Selection
# ==========================================
st.subheader(t["title"])

with st.expander(t["add_expander"], expanded=True):
    col1, col2, col3, col4 = st.columns([2.5, 2.5, 1.5, 1])
    
    # 1. เลือกหมวดหมู่
    categories = list(MATERIAL_MASTER_DB.keys())
    selected_cat = col1.selectbox(t["cat_label"], options=categories)
    
    # 2. เลือกรายการวัสดุในหมวดหมู่นั้นๆ
    items = list(MATERIAL_MASTER_DB[selected_cat].keys())
    selected_item = col2.selectbox(t["mat_label"], options=items)
    
    # 3. เลือกจำนวน
    qty = col3.number_input(t["qty_label"], min_value=0.01, value=1.00, step=0.50)
    
    # 4. ปุ่มกดเพิ่มวัสดุ
    col4.markdown("<br>", unsafe_allow_html=True)
    add_btn = col4.button(t["add_btn"], type="primary")

    # แสดงราคา & ต้นทุน ตัวที่เลือก
    item_info = MATERIAL_MASTER_DB[selected_cat][selected_item]
    st.caption(f"{t['price']}: {t['baht']}{item_info['price']:,.2f} | {t['cost']}: {t['baht']}{item_info['cost']:,.2f}")

st.markdown("---")

# ==========================================
# 4. ส่วน UI: Finishing & Painting
# ==========================================
st.subheader(t["finish_title"])

f_col1, f_col2 = st.columns(2)

with f_col1:
    hardcoat = st.selectbox(t["hardcoat_label"], options=[t["no_hardcoat"], "Hardcoat Polyurea", "Epoxy Resin"])
    st.caption(f"{t['service_rate']}: {t['baht']}0.00 / {t['sqm']} | {t['total_price']}: {t['baht']}0.00")

with f_col2:
    painting = st.selectbox(t["paint_label"], options=[t["no_paint"], "2K Spray Painting", "PU Film Coating"])
    st.caption(f"{t['service_rate']}: {t['baht']}0.00 / {t['sqm']} | {t['total_price']}: {t['baht']}0.00")
