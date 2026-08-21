import streamlit as st
import trimesh
import numpy as np
import tempfile
import os
import base64
import pandas as pd
from string import Template
import streamlit.components.v1 as components

# ==========================================
# ⚙️ 1. Page Configuration
# ==========================================
st.set_page_config(page_title="3D Model Analyzer & Cost Estimator", page_icon="📦", layout="wide")

# ==========================================
# 🎨 1b. Custom Theme — Studio / Art Workshop, warm
# ==========================================
# Base colors (primary/background/text) come from .streamlit/config.toml.
# This block layers deeper styling on top: cards, metrics, buttons, headers,
# tables, and expanders — matching the warm coral/amber studio look.
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans Thai', 'IBM Plex Sans', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Fraunces', serif !important;
        color: #3A2E26 !important;
        font-weight: 600 !important;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: #F3E7D8;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        border: 1px solid #E8D5BE;
        overflow: visible;
    }
    div[data-testid="stMetricLabel"] {
        color: #8A6F5C !important;
    }
    div[data-testid="stMetricValue"] {
        color: #3A2E26 !important;
        font-family: 'IBM Plex Sans Thai', sans-serif;
        overflow: visible !important;
        text-overflow: unset !important;
        font-size: 1.15rem !important;
    }
    div[data-testid="stMetricDelta"] {
        overflow: visible !important;
    }

    /* Buttons */
    .stButton > button {
        background-color: #C65D3B;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        transition: filter 0.15s ease;
    }
    .stButton > button:hover {
        filter: brightness(1.08);
        color: #FFFFFF;
    }

    /* Expanders */
    div[data-testid="stExpander"] {
        border: 1px solid #E8D5BE;
        border-radius: 12px;
        background: #FBF6F0;
    }

    /* Dataframes / tables */
    div[data-testid="stDataFrame"] {
        border: 1px solid #E8D5BE;
        border-radius: 8px;
        overflow: hidden;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #F3E7D8;
        border-right: 1px solid #E8D5BE;
    }

    /* Sidebar nav pills (built from st.sidebar.radio) */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
        flex-direction: column;
        gap: 4px;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
        padding: 10px 12px;
        border-radius: 8px;
        width: 100%;
        margin: 0;
        display: flex;
        align-items: center;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:last-child {
        margin-left: 0 !important;
        padding-left: 0 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label [data-baseweb="radio"],
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label [data-baseweb="radio"] > div,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label svg {
        display: none !important;  /* hide the default radio dot, whichever DOM shape Streamlit renders */
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
        background: #EADFCC;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
        background: #C65D3B;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) p {
        color: #FFFFFF !important;
        font-weight: 500;
    }

    /* Success / info / warning boxes keep readable warm-tinted borders */
    div[data-testid="stAlert"] {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🌐 2. Language Translations Dictionary
# ==========================================
TEXTS = {
    "TH": {
        "sidebar_menu": "📌 เมนูหลัก",
        "page_1_name": "📦 แบบจำลอง 3 มิติและพื้นผิว",
        "page_2_name": "💰 ประเมินราคา",
        "lang_select": "🌐 เลือกภาษา / Language",
        # Page 1
        "p1_title": "📦 3D Model Dimension & Surface Area Analyzer",
        "p1_sub": "อัปโหลดไฟล์โมเดล 3D เพื่อวิเคราะห์ขนาด Bounding Box, พื้นที่ผิว, ปริมาตร และความซับซ้อนของพื้นผิวอัตโนมัติ",
        "welcome_title": "สวัสดีค่ะ",
        "welcome_sub": "มาเริ่มสร้างสรรค์งานชิ้นต่อไปกันเถอะ",
        "file_processed_badge": "ประมวลผลไฟล์สำเร็จ",
        "file_processed_sub": "ข้อมูลพร้อมสำหรับประเมินราคา",
        "unit_setting": "⚙️ ตั้งค่าหน่วย",
        "unit_select": "เลือกหน่วยของไฟล์โมเดล 3D",
        "unit_help": "ไฟล์ 3D (OBJ, STL, PLY) เก็บเพียงตัวเลขไม่มีหน่วย กำหนดหน่วยให้ตรงกับตอนสร้างโมเดล",
        "unit_m": "เมตร (m)",
        "unit_dm": "เดซิเมตร / 10 ซม. (dm)",
        "unit_cm": "เซนติเมตร (cm)",
        "unit_mm": "มิลลิเมตร (mm)",
        "size_panel_title": "📏 ปรับขนาดโมเดล",
        "size_panel_sub": "ค่าเริ่มต้นดึงจากไฟล์ 3D — แก้ไขได้",
        "lock_ratio": "ล็อกสัดส่วน 1:1",
        "size_w": "กว้าง (mm)",
        "size_l": "ยาว (mm)",
        "size_h": "สูง (mm)",
        "size_reset_btn": "↺ รีเซ็ตเป็นขนาดไฟล์ต้นฉบับ",
        "size_recalc_note": "💡 พื้นที่ผิว/ปริมาตรคำนวณใหม่อัตโนมัติตามขนาดที่ปรับ",
        "file_uploader": "เลือกไฟล์โมเดล 3D",
        "success_msg": "✅ ประมวลผลไฟล์สำเร็จ! ส่งข้อมูลไปยังหน้า 2 เรียบร้อย",
        "viewer_title": "🖥️ ตัวอย่างโมเดล 3D Interactive",
        "viewer_help": "หมุน: คลิกซ้าย | ขยาย: สกรอลล์ | ย้าย: คลิกขวา",
        "dim_title": "📐 ขนาดโมเดล (Dimensions)",
        "dim_w": "ความกว้าง (X)",
        "dim_l": "ความยาว (Y)",
        "dim_h": "ความสูง (Z)",
        "small_dim_warn": "⚠️ **ข้อสังเกต:** โมเดลมีขนาดเล็กกว่า 10 ซม. ({:.1f} cm) โปรดตรวจสอบข้อจำกัดของเครื่องจักร",
        "area_vol_title": "📊 พื้นที่ผิว & ปริมาตร",
        "surf_area": "พื้นที่ผิวรวม",
        "vol_exact": "ปริมาตร (Exact)",
        "vol_hull": "ปริมาตร (Convex Hull)",
        "vol_note": "💡 **หมายเหตุ:** โมเดลไม่เป็น Watertight หรือเป็น Point Cloud ปริมาตรคำนวณโดยใช้ Convex Hull",
        "vol_err": "โมเดลไม่สมบูรณ์ ไม่สามารถคำนวณปริมาตรได้",
        "complexity_title": "🔍 ระดับความซับซ้อนของพื้นผิว",
        "surface_metrics": "รายละเอียดตัวชี้วัดพื้นผิว (Surface Metrics)",
        "area_ratio": "อัตราส่วนพื้นที่ผิวส่วนเกิน:",
        "normal_dev": "ความเบี่ยงเบนแนวฉากผิวเฉลี่ย:",
        "face_density": "ความหนาแน่นโพลีกอน:",
        "complexity_err": "⚠️ ไม่สามารถวิเคราะห์ระดับความซับซ้อนของพื้นผิวได้\n\nสาเหตุ: {}",
        # Page 2
        "p2_title": "💰 การคำนวณต้นทุน & ประมาณการราคา",
        "p2_sub": "ระบบดึงข้อมูลพื้นที่ผิวจากหน้าแรกมาประมวลผลร่วมกับสูตรคำนวณ Robot และ Material Master Data",
        "model_info": "📌 **ข้อมูลโมเดลปัจจุบันจากหน้าแรก:** ไฟล์ `{}` | ขนาด `{}` mm | พื้นที่ผิว `{:.3f}` ตร.ม.",
        "project_name": "ชื่อชิ้นงาน / ลูกค้า",
        "complexity_level": "ระดับความซับซ้อน (Level 1-10)",
        "calc_area": "พื้นที่ทำสี/เคลือบผิว รวมทั้งล็อต (sq.m.)",
        "production_qty": "จำนวนที่ผลิต (Qty)",
        "per_piece_area_note": "พื้นที่ผิวต่อชิ้นจากไฟล์ 3D: {:.4f} ตร.ม. × {} ชิ้น = {:.4f} ตร.ม.",
        "op_title": "⚙️ เลือกกระบวนการเครื่องจักร (Operations)",
        "mch_rate": "ค่าเครื่อง (฿/Hr)",
        "op_select_machine": "เลือกประเภทเครื่องจักร",
        "op_rate": "ค่าเครื่อง",
        "op_qty_hr": "จำนวนชั่วโมง (Hr)",
        "op_qty_unit": "จำนวนชิ้น (Unit)",
        "op_add_btn": "➕ เพิ่มกระบวนการ",
        "op_expander": "➕ คลิกเพื่อเลือกและเพิ่มกระบวนการเครื่องจักรลงในชิ้นงาน",
        "op_selected_list": "📋 รายการกระบวนการเครื่องจักรที่เลือกในชิ้นงานนี้",
        "op_clear_btn": "🗑️ ล้างรายการกระบวนการทั้งหมด",
        "op_col_machine": "เครื่องจักร",
        "op_col_unit": "หน่วยคิดราคา",
        "op_col_rate": "อัตรา (฿)",
        "op_col_qty": "จำนวน",
        "op_col_total": "รวม (฿)",
        "use_mat": "📦 ระบบเลือกรายการวัสดุสำหรับผลิตชิ้นงาน (Material Master Selection)",
        "mat_expander": "➕ คลิกเพื่อเลือกและเพิ่มรายการวัสดุลงในชิ้นงาน",
        "select_cat": "เลือกหมวดหมู่วัสดุ",
        "select_item": "เลือกรายการวัสดุ",
        "mat_qty": "จำนวน / หน่วย",
        "add_mat_btn": "➕ เพิ่มวัสดุ",
        "selected_mat_list": "📋 รายการวัสดุที่เลือกในชิ้นงานนี้",
        "clear_mat_btn": "🗑️ ล้างรายการวัสดุทั้งหมด",
        "finishing_title": "🎨 งานเคลือบผิวแข็ง & งานทำสี (Finishing & Painting)",
        "finish_select": "เลือกประเภทงานเคลือบผิว/ทำสี",
        "finish_rate": "อัตรา (฿/ตร.ม.)",
        "finish_area": "พื้นที่ใช้งานนี้ (ตร.ม.)",
        "finish_add_btn": "➕ เพิ่มงานเคลือบผิว",
        "finish_expander": "➕ คลิกเพื่อเลือกและเพิ่มงานเคลือบผิว/ทำสีลงในชิ้นงาน (เพิ่มได้หลายชนิด)",
        "finish_selected_list": "📋 รายการงานเคลือบผิวที่เลือกในชิ้นงานนี้",
        "finish_clear_btn": "🗑️ ล้างรายการงานเคลือบผิวทั้งหมด",
        "finish_col_type": "ประเภท",
        "finish_col_rate": "อัตรา (฿/ตร.ม.)",
        "finish_col_area": "พื้นที่ (ตร.ม.)",
        "finish_col_total": "รวม (฿)",
        "mold_title": "🗿 งานทำโมล (Mold Making)",
        "mold_select": "ประเภทโมล",
        "mold_qty": "จำนวนโมล (ชุด)",
        "mold_rate_label": "อัตรา: ฿{:,.2f}/ตร.ม. × {} โมล × {:.4f} ตร.ม./ชิ้น = ฿{:,.2f}",
        "mold_cost": "ค่าทำโมล",
        "summary_title": "📊 สรุปประมาณการราคาผลิต (Costing & Price Summary)",
        "mch_cost": "ค่าประมวลผลเครื่องจักร",
        "mat_cost": "ค่าวัสดุและอุปกรณ์",
        "paint_cost": "ค่าเคลือบผิว & ทำสี",
        "grand_total": "🏷️ ราคารวมประมาณการ (Grand Total)",
    },
    "EN": {
        "sidebar_menu": "📌 Main Menu",
        "page_1_name": "📦 3D Model & Surface",
        "page_2_name": "💰 Cost Estimator",
        "lang_select": "🌐 Select Language / เลือกภาษา",
        # Page 1
        "p1_title": "📦 3D Model Dimension & Surface Area Analyzer",
        "p1_sub": "Upload a 3D model file to automatically extract bounding box dimensions, surface area, volume, and surface detail complexity.",
        "welcome_title": "Welcome back",
        "welcome_sub": "Let's bring your ideas to life.",
        "file_processed_badge": "File processed successfully",
        "file_processed_sub": "Data ready for cost estimation",
        "unit_setting": "⚙️ Unit Settings",
        "unit_select": "Select Model File Unit",
        "unit_help": "3D formats (OBJ, STL, PLY) store raw numbers without units. Select the unit used when creating the model.",
        "unit_m": "Meters (m)",
        "unit_dm": "Decimeters / 10 cm (dm)",
        "unit_cm": "Centimeters (cm)",
        "unit_mm": "Millimeters (mm)",
        "size_panel_title": "📏 Adjust model size",
        "size_panel_sub": "Defaults from the 3D file — editable",
        "lock_ratio": "Lock ratio 1:1",
        "size_w": "Width (mm)",
        "size_l": "Length (mm)",
        "size_h": "Height (mm)",
        "size_reset_btn": "↺ Reset to original file size",
        "size_recalc_note": "💡 Surface area/volume recalculate automatically with the adjusted size",
        "file_uploader": "Select a 3D model file",
        "success_msg": "✅ File processed successfully! Data passed to Page 2.",
        "viewer_title": "🖥️ 3D Model Interactive Viewer",
        "viewer_help": "Rotate: Left Click | Zoom: Scroll | Pan: Right Click",
        "dim_title": "📐 Model Dimensions",
        "dim_w": "Width (X)",
        "dim_l": "Length (Y)",
        "dim_h": "Height (Z)",
        "small_dim_warn": "⚠️ **Notice:** Model has dimensions smaller than 10 cm ({:.1f} cm). Please verify factory manufacturing limits.",
        "area_vol_title": "📊 Surface Area & Volume",
        "surf_area": "Total Surface Area",
        "vol_exact": "Volume (Exact)",
        "vol_hull": "Volume (Convex Hull)",
        "vol_note": "💡 **Note:** Model is non-watertight or Point Cloud. Volume calculated using Convex Hull approximation.",
        "vol_err": "Model mesh is non-watertight and volume couldn't be calculated.",
        "complexity_title": "🔍 Surface Detail Complexity",
        "surface_metrics": "Surface Metrics Details",
        "area_ratio": "Surface Area Excess Ratio:",
        "normal_dev": "Average Surface Normal Deviation:",
        "face_density": "Surface Polygon Density:",
        "complexity_err": "⚠️ Unable to analyze surface detail complexity.\n\nReason: {}",
        # Page 2
        "p2_title": "💰 Costing & Cost Estimate",
        "p2_sub": "Retrieves surface area from Page 1 and processes with Robot and Material Master Data formulas.",
        "model_info": "📌 **Current Model Data from Page 1:** File `{}` | Dimensions `{}` mm | Surface Area `{:.3f}` sq.m.",
        "project_name": "Project Name / Customer",
        "complexity_level": "Complexity Level (Level 1-10)",
        "calc_area": "Painting / Coating Area, whole batch (sq.m.)",
        "production_qty": "Production Quantity (Qty)",
        "per_piece_area_note": "Per-piece surface area from 3D file: {:.4f} sq.m. × {} pcs = {:.4f} sq.m.",
        "op_title": "⚙️ Select Machine Operations",
        "mch_rate": "Machine Rate (฿/Hr)",
        "op_select_machine": "Select Machine Type",
        "op_rate": "Rate",
        "op_qty_hr": "Hours (Hr)",
        "op_qty_unit": "Quantity (Unit)",
        "op_add_btn": "➕ Add Operation",
        "op_expander": "➕ Click to select and add machine operations to the project",
        "op_selected_list": "📋 Selected Machine Operations",
        "op_clear_btn": "🗑️ Clear All Operations",
        "op_col_machine": "Machine",
        "op_col_unit": "Billing Unit",
        "op_col_rate": "Rate (฿)",
        "op_col_qty": "Qty",
        "op_col_total": "Total (฿)",
        "use_mat": "📦 Material Master Selection",
        "mat_expander": "➕ Click to select and add materials to the project",
        "select_cat": "Select Category",
        "select_item": "Select Material Item",
        "mat_qty": "Quantity / Unit",
        "add_mat_btn": "➕ Add Material",
        "selected_mat_list": "📋 Selected Material List",
        "clear_mat_btn": "🗑️ Clear All Materials",
        "finishing_title": "🎨 Surface Finishing & Painting",
        "finish_select": "Select Finish / Coating Type",
        "finish_rate": "Rate (฿/sq.m.)",
        "finish_area": "Area for this line (sq.m.)",
        "finish_add_btn": "➕ Add Finish",
        "finish_expander": "➕ Click to select and add finish/coating types to the project (add as many as needed)",
        "finish_selected_list": "📋 Selected Finishing Items",
        "finish_clear_btn": "🗑️ Clear All Finishing Items",
        "finish_col_type": "Type",
        "finish_col_rate": "Rate (฿/sq.m.)",
        "finish_col_area": "Area (sq.m.)",
        "finish_col_total": "Total (฿)",
        "mold_title": "🗿 Mold Making",
        "mold_select": "Mold Type",
        "mold_qty": "Number of Molds",
        "mold_rate_label": "Rate: ฿{:,.2f}/sq.m. × {} molds × {:.4f} sq.m./pc = ฿{:,.2f}",
        "mold_cost": "Mold Cost",
        "summary_title": "📊 Costing & Price Summary",
        "mch_cost": "Machine Processing Cost",
        "mat_cost": "Material & Equipment Cost",
        "paint_cost": "Coating & Painting Cost",
        "grand_total": "🏷️ Grand Total Estimated Price",
    }
}

# ==========================================
# 🔄 3. Session State Initialization
# ==========================================
if "language" not in st.session_state:
    st.session_state["language"] = "TH"
if "surface_area_sqm" not in st.session_state:
    st.session_state["surface_area_sqm"] = 0.0
if "dimensions_str" not in st.session_state:
    st.session_state["dimensions_str"] = "0 * 0 * 0"
if "width_x_mm" not in st.session_state:
    st.session_state["width_x_mm"] = 0.0
if "length_y_mm" not in st.session_state:
    st.session_state["length_y_mm"] = 0.0
if "height_z_mm" not in st.session_state:
    st.session_state["height_z_mm"] = 0.0
if "file_name" not in st.session_state:
    st.session_state["file_name"] = "ยังไม่ได้เลือกไฟล์"
if "selected_materials" not in st.session_state:
    st.session_state["selected_materials"] = []
if "selected_operations" not in st.session_state:
    st.session_state["selected_operations"] = []
if "selected_finishes" not in st.session_state:
    st.session_state["selected_finishes"] = []

# ==========================================
# 🧭 4. Sidebar Navigation & Language Selector
# ==========================================
# --- Sidebar brand header (logo + app name), like the top-left brand mark ---
st.sidebar.markdown("""
<div style="display:flex; align-items:center; gap:10px; padding:4px 0 18px;">
    <div style="width:38px; height:38px; border-radius:10px; background:#F3E7D8;
                display:flex; align-items:center; justify-content:center; font-size:20px;">🧊</div>
    <div>
        <p style="margin:0; font-weight:600; font-size:16px; color:#3A2E26; line-height:1.2;">3D Analyzer</p>
        <p style="margin:0; font-size:12px; color:#8A6F5C; line-height:1.2;">Cost Estimator</p>
    </div>
</div>
""", unsafe_allow_html=True)

lang = st.sidebar.selectbox(
    TEXTS[st.session_state["language"]]["lang_select"],
    options=["TH", "EN"],
    index=0 if st.session_state["language"] == "TH" else 1
)
st.session_state["language"] = lang
t = TEXTS[lang]  # Short access for current language dict

nav_options = [t["page_1_name"], t["page_2_name"]]
if "nav_page_choice" not in st.session_state or st.session_state["nav_page_choice"] not in nav_options:
    st.session_state["nav_page_choice"] = nav_options[0]

page = st.sidebar.radio("", nav_options, key="nav_page_choice")

st.sidebar.divider()

# ==========================================
# 📦 หน้า 1: วิเคราะห์โมเดล 3D
# ==========================================
if page == t["page_1_name"]:
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:1.2rem;">
        <span style="font-size:26px;">👋</span>
        <div>
            <p style="margin:0; font-weight:600; font-size:19px; color:#3A2E26;">{t['welcome_title']}</p>
            <p style="margin:0; font-size:13px; color:#8A6F5C;">{t['welcome_sub']}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.header(t["unit_setting"])
    unit_input = st.sidebar.selectbox(
        t["unit_select"],
        options=[t["unit_m"], t["unit_dm"], t["unit_cm"], t["unit_mm"]],
        index=0,
        help=t["unit_help"]
    )

    if unit_input == t["unit_m"]:
        scale_to_m = 1.0
    elif unit_input == t["unit_dm"]:
        scale_to_m = 0.1
    elif unit_input == t["unit_cm"]:
        scale_to_m = 0.01
    else:
        scale_to_m = 0.001

    def process_and_clean_mesh(loaded_data):
        if isinstance(loaded_data, trimesh.Scene):
            geometries = []
            for node_name in loaded_data.graph.nodes_geometry:
                transform, geometry_name = loaded_data.graph[node_name]
                geom = loaded_data.geometry[geometry_name].copy()
                geom.apply_transform(transform)
                geometries.append(geom)

            if geometries:
                mesh = trimesh.util.concatenate(geometries)
            else:
                mesh = trimesh.Trimesh()
        else:
            mesh = loaded_data

        if isinstance(mesh, trimesh.Trimesh):
            try:
                mesh.update_faces(mesh.unique_faces())
            except Exception:
                pass
            try:
                mesh.remove_degenerate_faces()
            except Exception:
                pass
            try:
                mesh.remove_infinite_values()
            except Exception:
                pass

        return mesh

    def analyze_surface_complexity(mesh, scale_to_m, is_point_cloud):
        if is_point_cloud or not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
            return {"score": None, "level": None, "error": "Point Cloud (No faces)"}

        if len(mesh.faces) == 0:
            return {"score": None, "level": None, "error": "No faces in mesh"}

        area_raw = mesh.area
        if area_raw <= 0:
            return {"score": None, "level": None, "error": "Surface area is 0"}

        area_m2 = area_raw * (scale_to_m ** 2)

        area_ratio = None
        area_error = None
        try:
            hull = mesh.convex_hull
            hull_area = hull.area
            if hull_area > 0:
                area_ratio = float(area_raw / hull_area)
            else:
                area_error = "Convex Hull area is 0"
        except Exception as e:
            area_error = str(e)

        surface_roughness = None
        roughness_error = None
        try:
            face_adjacency = mesh.face_adjacency
            if len(face_adjacency) > 0:
                normals = mesh.face_normals
                n0 = normals[face_adjacency[:, 0]]
                n1 = normals[face_adjacency[:, 1]]
                dot_products = np.clip(np.sum(n0 * n1, axis=1), -1.0, 1.0)
                angles_rad = np.arccos(dot_products)
                surface_roughness = float(np.mean(angles_rad))
            else:
                surface_roughness = 0.0
        except Exception as e:
            roughness_error = str(e)

        face_density_per_m2 = float(len(mesh.faces) / area_m2) if area_m2 > 0 else 0.0

        score_components = []
        if area_ratio is not None:
            s_area = float(np.clip(1 - np.exp(-1.2 * max(area_ratio - 1.0, 0.0)), 0.0, 1.0)) * 100
            score_components.append(s_area)

        if surface_roughness is not None:
            s_rough = float(np.clip(1 - np.exp(-2.5 * surface_roughness), 0.0, 1.0)) * 100
            score_components.append(s_rough)

        if not score_components:
            return {"score": None, "level": None, "error": f"{area_error} | {roughness_error}"}

        detail_score = round(sum(score_components) / len(score_components), 1)

        if detail_score < 20:
            level = "Simple Surface" if lang == "EN" else "ผิวเรียบง่าย"
        elif detail_score < 45:
            level = "Moderate Surface" if lang == "EN" else "ผิวมีรายละเอียดปานกลาง"
        elif detail_score < 70:
            level = "Detailed Surface" if lang == "EN" else "ผิวมีรายละเอียดสูง"
        else:
            level = "Highly Complex Surface" if lang == "EN" else "ผิวมีความซับซ้อนสูงมาก"

        return {
            "score": detail_score,
            "level": level,
            "area_ratio": round(area_ratio, 3) if area_ratio is not None else None,
            "surface_roughness_deg": round(np.degrees(surface_roughness), 2) if surface_roughness is not None else None,
            "face_density": round(face_density_per_m2, 1),
            "total_faces": len(mesh.faces),
            "area_error": area_error,
            "roughness_error": roughness_error
        }

    HTML_TEMPLATE = Template("""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js"></script>
        <style>
            body { margin: 0; overflow: hidden; background-color: #1a1a1a; }
            #viewer-container { width: 100%; height: 500px; position: relative; }
            #loading {
                position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
                color: #ffffff; font-family: sans-serif; font-size: 14px; pointer-events: none;
            }
            #viewer-toolbar {
                position: absolute; bottom: 14px; left: 50%; transform: translateX(-50%);
                display: flex; gap: 8px; z-index: 10;
            }
            #viewer-toolbar button {
                width: 36px; height: 36px; border-radius: 8px; border: none;
                background: rgba(255,255,255,0.92); color: #3A2E26;
                font-size: 16px; cursor: pointer; display: flex;
                align-items: center; justify-content: center;
            }
            #viewer-toolbar button:hover { background: #ffffff; }
        </style>
    </head>
    <body>
        <div id="viewer-container">
            <div id="loading">Loading 3D Model...</div>
            <div id="viewer-toolbar">
                <button id="btn-reset" title="Reset view">&#8635;</button>
                <button id="btn-zoom-in" title="Zoom in">+</button>
                <button id="btn-zoom-out" title="Zoom out">&minus;</button>
            </div>
        </div>
        <script>
            const container = document.getElementById('viewer-container');
            const loading = document.getElementById('loading');
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0x1a1a1a);

            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 500, 0.1, 1000);
            const renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(container.clientWidth, 500);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            const controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;

            const ambientLight = new THREE.AmbientLight(0x777777);
            scene.add(ambientLight);

            const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
            dirLight1.position.set(1, 1, 1).normalize();
            scene.add(dirLight1);

            const dirLight2 = new THREE.DirectionalLight(0x555555, 0.5);
            dirLight2.position.set(-1, -1, -1).normalize();
            scene.add(dirLight2);

            function base64ToArrayBuffer(base64) {
                var binary_string = window.atob(base64);
                var len = binary_string.length;
                var bytes = new Uint8Array(len);
                for (var i = 0; i < len; i++) {
                    bytes[i] = binary_string.charCodeAt(i);
                }
                return bytes.buffer;
            }

            let initialCameraPos = null;

            try {
                const loader = new THREE.STLLoader();
                const arrayBuffer = base64ToArrayBuffer("$b64_stl");
                const geometry = loader.parse(arrayBuffer);

                geometry.center();
                geometry.computeVertexNormals();

                const material = new THREE.MeshStandardMaterial({
                    color: 0x2196F3,
                    roughness: 0.3,
                    metalness: 0.2
                });
                const mesh = new THREE.Mesh(geometry, material);
                scene.add(mesh);

                geometry.computeBoundingSphere();
                const radius = geometry.boundingSphere.radius;
                camera.position.set(radius * 2.2, radius * 2.2, radius * 2.2);
                camera.lookAt(0, 0, 0);
                controls.update();
                initialCameraPos = camera.position.clone();

                loading.style.display = 'none';
            } catch (err) {
                loading.innerText = 'Failed to load 3D preview';
                console.error(err);
            }

            document.getElementById('btn-zoom-in').addEventListener('click', function () {
                camera.position.multiplyScalar(0.8);
                controls.update();
            });
            document.getElementById('btn-zoom-out').addEventListener('click', function () {
                camera.position.multiplyScalar(1.25);
                controls.update();
            });
            document.getElementById('btn-reset').addEventListener('click', function () {
                if (initialCameraPos) {
                    camera.position.copy(initialCameraPos);
                    controls.target.set(0, 0, 0);
                    controls.update();
                }
            });

            function animate() {
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }
            animate();
        </script>
    </body>
    </html>
    """)


    def render_3d_viewer(mesh_obj):
        try:
            if isinstance(mesh_obj, trimesh.PointCloud) or len(mesh_obj.vertices) == 0:
                return None
            stl_bytes = mesh_obj.export(file_type='stl')
            b64_stl = base64.b64encode(stl_bytes).decode('utf-8')
            return HTML_TEMPLATE.substitute(b64_stl=b64_stl)
        except Exception:
            return None

    uploaded_file = st.file_uploader(
        t["file_uploader"],
        type=["stl", "obj", "ply", "off", "3mf"]
    )

    if uploaded_file is not None:
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            with st.spinner("Processing 3D model file..."):
                loaded_data = trimesh.load(tmp_path)
                mesh = process_and_clean_mesh(loaded_data)

                is_point_cloud = isinstance(mesh, trimesh.PointCloud)

                # --- Convert the raw mesh to real millimetres once, using the
                # file-unit interpretation above. This becomes the "base" shape
                # that the size-editor panel scales from. ---
                mesh_mm = mesh.copy()
                mesh_mm.apply_scale(scale_to_m * 1000.0)
                base_extents = mesh_mm.extents
                base_w_mm, base_l_mm, base_h_mm = float(base_extents[0]), float(base_extents[1]), float(base_extents[2])

                file_identity = f"{uploaded_file.name}_{uploaded_file.size}"
                if st.session_state.get("size_panel_file_id") != file_identity:
                    st.session_state["size_panel_file_id"] = file_identity
                    st.session_state["dim_w_mm"] = round(base_w_mm, 3)
                    st.session_state["dim_l_mm"] = round(base_l_mm, 3)
                    st.session_state["dim_h_mm"] = round(base_h_mm, 3)
                if "lock_ratio_toggle" not in st.session_state:
                    st.session_state["lock_ratio_toggle"] = True

                def _sync_from_width():
                    if st.session_state.get("lock_ratio_toggle", True) and base_w_mm > 0:
                        k = st.session_state["dim_w_mm"] / base_w_mm
                        st.session_state["dim_l_mm"] = round(base_l_mm * k, 3)
                        st.session_state["dim_h_mm"] = round(base_h_mm * k, 3)

                def _sync_from_length():
                    if st.session_state.get("lock_ratio_toggle", True) and base_l_mm > 0:
                        k = st.session_state["dim_l_mm"] / base_l_mm
                        st.session_state["dim_w_mm"] = round(base_w_mm * k, 3)
                        st.session_state["dim_h_mm"] = round(base_h_mm * k, 3)

                def _sync_from_height():
                    if st.session_state.get("lock_ratio_toggle", True) and base_h_mm > 0:
                        k = st.session_state["dim_h_mm"] / base_h_mm
                        st.session_state["dim_w_mm"] = round(base_w_mm * k, 3)
                        st.session_state["dim_l_mm"] = round(base_l_mm * k, 3)

                st.sidebar.markdown("---")
                st.sidebar.subheader(t["size_panel_title"])
                st.sidebar.caption(t["size_panel_sub"])
                st.sidebar.toggle(t["lock_ratio"], key="lock_ratio_toggle")
                st.sidebar.number_input(t["size_w"], min_value=0.001, key="dim_w_mm", step=1.0, on_change=_sync_from_width)
                st.sidebar.number_input(t["size_l"], min_value=0.001, key="dim_l_mm", step=1.0, on_change=_sync_from_length)
                st.sidebar.number_input(t["size_h"], min_value=0.001, key="dim_h_mm", step=1.0, on_change=_sync_from_height)
                if st.sidebar.button(t["size_reset_btn"], use_container_width=True):
                    st.session_state["dim_w_mm"] = round(base_w_mm, 3)
                    st.session_state["dim_l_mm"] = round(base_l_mm, 3)
                    st.session_state["dim_h_mm"] = round(base_h_mm, 3)
                    st.rerun()
                st.sidebar.caption(t["size_recalc_note"])

                # --- Apply the (possibly non-uniform) scale the user dialed in,
                # then recompute area/volume from the ACTUAL transformed mesh —
                # exact either way, uniform or not. ---
                kx = st.session_state["dim_w_mm"] / base_w_mm if base_w_mm > 0 else 1.0
                ky = st.session_state["dim_l_mm"] / base_l_mm if base_l_mm > 0 else 1.0
                kz = st.session_state["dim_h_mm"] / base_h_mm if base_h_mm > 0 else 1.0

                final_mesh = mesh_mm.copy()
                scale_matrix = np.eye(4)
                scale_matrix[0, 0] = kx
                scale_matrix[1, 1] = ky
                scale_matrix[2, 2] = kz
                final_mesh.apply_transform(scale_matrix)

                width_x_mm = st.session_state["dim_w_mm"]
                length_y_mm = st.session_state["dim_l_mm"]
                height_z_mm = st.session_state["dim_h_mm"]
                width_x_m = width_x_mm / 1000.0
                length_y_m = length_y_mm / 1000.0
                height_z_m = height_z_mm / 1000.0
                width_x_cm = width_x_mm / 10.0
                length_y_cm = length_y_mm / 10.0
                height_z_cm = height_z_mm / 10.0

                surface_area_m2 = 0.0
                volume_m3 = 0.0
                is_watertight = False
                used_convex_hull = False

                if is_point_cloud:
                    hull = final_mesh.convex_hull
                    surface_area_m2 = hull.area / 1_000_000.0
                    volume_m3 = hull.volume / 1_000_000_000.0
                    used_convex_hull = True
                else:
                    surface_area_m2 = final_mesh.area / 1_000_000.0
                    is_watertight = getattr(final_mesh, 'is_watertight', False)

                    if is_watertight:
                        volume_m3 = final_mesh.volume / 1_000_000_000.0
                    else:
                        try:
                            hull = final_mesh.convex_hull
                            volume_m3 = hull.volume / 1_000_000_000.0
                            used_convex_hull = True
                        except Exception:
                            volume_m3 = 0.0

                surface_area_cm2 = surface_area_m2 * 10_000.0
                volume_cm3 = volume_m3 * 1_000_000.0

                # final_mesh is already in real millimetres, so scale_to_m=0.001 here
                complexity = analyze_surface_complexity(final_mesh, 0.001, is_point_cloud)

                st.session_state["surface_area_sqm"] = surface_area_m2
                st.session_state["dimensions_str"] = f"{width_x_mm:.0f}*{length_y_mm:.0f}*{height_z_mm:.0f}"
                st.session_state["width_x_mm"] = width_x_mm
                st.session_state["length_y_mm"] = length_y_mm
                st.session_state["height_z_mm"] = height_z_mm
                st.session_state["file_name"] = uploaded_file.name

            file_size_kb = uploaded_file.size / 1024

            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E8D5BE; border-radius:12px;
                        padding:14px 18px; display:flex; align-items:center; justify-content:space-between;
                        margin-bottom:1.2rem;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="width:38px; height:38px; border-radius:8px; background:#F3E7D8;
                                display:flex; align-items:center; justify-content:center; font-size:18px;">📄</div>
                    <div>
                        <p style="margin:0; font-weight:500; font-size:14px; color:#3A2E26;">{uploaded_file.name}</p>
                        <p style="margin:0; font-size:12px; color:#8A6F5C;">{file_size_kb:.1f} KB</p>
                    </div>
                </div>
                <div style="background:#E7F1E4; border-radius:8px; padding:8px 14px; display:flex; align-items:center; gap:8px;">
                    <span style="color:#2E7D32; font-size:16px;">✓</span>
                    <div>
                        <p style="margin:0; font-weight:500; font-size:13px; color:#2E7D32;">{t['file_processed_badge']}</p>
                        <p style="margin:0; font-size:11px; color:#4E7A50;">{t['file_processed_sub']}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_viewer, col_metrics = st.columns([1.2, 1])

            with col_viewer:
                st.subheader(t["viewer_title"])
                st.caption(t["viewer_help"])
                html_viewer = render_3d_viewer(final_mesh)
                if html_viewer:
                    components.html(html_viewer, height=510)
                else:
                    st.info("No 3D Viewer preview available.")

            with col_metrics:
                st.subheader(t["dim_title"])
                dim_col1, dim_col2, dim_col3 = st.columns(3)
                dim_col1.metric(t["dim_w"], f"{width_x_mm:,.1f} mm", f"↑ {width_x_m:,.3f} m")
                dim_col2.metric(t["dim_l"], f"{length_y_mm:,.1f} mm", f"↑ {length_y_m:,.3f} m")
                dim_col3.metric(t["dim_h"], f"{height_z_mm:,.1f} mm", f"↑ {height_z_m:,.3f} m")

                min_dimension_mm = min(width_x_mm, length_y_mm, height_z_mm)
                if min_dimension_mm < 100.0:
                    st.warning(t["small_dim_warn"].format(min_dimension_mm / 10.0))

                st.markdown("---")

                st.subheader(t["area_vol_title"])
                res_a, res_b = st.columns(2)
                res_a.metric(t["surf_area"], f"{surface_area_m2:,.4f} sq.m", f"{surface_area_cm2:,.1f} sq.cm")

                if is_watertight:
                    res_b.metric(t["vol_exact"], f"{volume_m3:,.4f} cu.m", f"{volume_cm3:,.1f} cu.cm")
                elif used_convex_hull and volume_m3 > 0:
                    res_b.metric(t["vol_hull"], f"{volume_m3:,.4f} cu.m", f"{volume_cm3:,.1f} cu.cm")
                    st.info(t["vol_note"])
                else:
                    res_b.info(t["vol_err"])

                st.markdown("---")
                st.subheader(t["complexity_title"])
                if complexity and complexity.get("score") is not None:
                    st.metric(t["complexity_title"], complexity["level"], f"{complexity['score']}%")
                    st.progress(complexity["score"] / 100)

                    with st.expander(t["surface_metrics"]):
                        if complexity['area_ratio'] is not None:
                            st.write(f"- **{t['area_ratio']}** `{complexity['area_ratio']}`")
                        if complexity['surface_roughness_deg'] is not None:
                            st.write(f"- **{t['normal_dev']}** `{complexity['surface_roughness_deg']}°`")
                        st.write(f"- **{t['face_density']}** `{complexity['face_density']:,.0f}` Faces/sq.m")
                else:
                    error_msg = complexity.get("error") if complexity else "Unknown"
                    st.warning(t["complexity_err"].format(error_msg))

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

# ==========================================
# 💰 หน้าที่ 2: คำนวณราคา & ใบประเมิน
# ==========================================
elif page == t["page_2_name"]:
    st.title(t["p2_title"])
    st.caption(t["p2_sub"])

    st.info(t["model_info"].format(
        st.session_state['file_name'], 
        st.session_state['dimensions_str'], 
        st.session_state['surface_area_sqm']
    ))

    # 🗂️ Material Master Data Database
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
        "PETG": {"price": 960, "cost": 800},
        "เรซินใสหล่อพิเศษ 230kg": {"price": 34800, "cost": 29000},
        "เจลโค้ดเชื่อมเรซิ่น 25 kg": {"price": 4500, "cost": 3750},
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
        "อะคริลิคใส 8 มม.": {"price": 4200, "cost": 3500},
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
        "Plastwood 8 mm.": {"price": 960, "cost": 800},
        "ไม้อัดแท้ 270*270*1000": {"price": 0, "cost": 0},
        "ไม้อัดกันน้ำ 20mm": {"price": 1500, "cost": 1200},
        "Veneer 1 ตร.ม.": {"price": 1248, "cost": 1040},
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
        "เหล็กเส้นกลม 15มม. 10ม.": {"price": 540, "cost": 450},
        "ท่อ Stainless 5 mm.": {"price": 72, "cost": 60},
        "เหล็กกล่อง 4*4 นิ้ว": {"price": 2040, "cost": 1700},
        "ตะแกรง Wiremesh 2*50 m. (0.2*0.2 m.)": {"price": 3000, "cost": 2500},
        "Stainless 2 mm.": {"price": 5400, "cost": 4500},
        "Stainless 0.7 mm.": {"price": 2520, "cost": 2100},
        "Stainless HL 1.2 mm.": {"price": 3000, "cost": 2500},
        "Stainless mirror 2 mm.": {"price": 4560, "cost": 3800},
        "เหล็กกล่อง 1*1": {"price": 240, "cost": 200},
        "เหล็กกล่อง 1*2 นิ้ว": {"price": 720, "cost": 600},
        "เหล็กกล่อง 1.5*1.5": {"price": 840, "cost": 700},
        "เหล็กกล่อง 2*2": {"price": 1080, "cost": 900},
        "เหล็กกล่อง 2*4": {"price": 780, "cost": 650},
        "เหล็กกล่อง 2.5*2.5": {"price": 1560, "cost": 1300},
        "สแตนเลสแท่ง 10 มม.": {"price": 360, "cost": 300},
        "เหล็กกัลวาไนซ์": {"price": 1000, "cost": 800},
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
        "Texture ( 26A )": {"price": 340, "cost": 272},
        "พิมพ์ UV (ละเอียด/เงา/ด้าน) 1 ตร.ม.": {"price": 2160, "cost": 1800},
    },
    "หมวด ระบบไฟ / อุปกรณ์ไฟฟ้า": {
        "Strip light ( 1 m. )": {"price": 132, "cost": 110},
        "Strip light 4500k ( 1m. )": {"price": 600, "cost": 500},
        "Strip light 3000k ( 1m.)": {"price": 420, "cost": 350},
        "ไฟ COB 4000K ( 1 m )": {"price": 360, "cost": 300},
        "หม้อแปลง strip light": {"price": 1500, "cost": 1500},
        "Neon flex 12V ( 1 m.)": {"price": 180, "cost": 150},
        "Track light 4000K": {"price": 1800, "cost": 1500},
        "โคมไฟกลม Ø 500": {"price": 2400, "cost": 2000},
        "ไฟ LED เส้น": {"price": 360, "cost": 300},
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
        "บานพับแสตนเลส": {"price": 200, "cost": 160},
        "มือจับฝัง": {"price": 200, "cost": 160},
        "กระจกใส 2 มม. 0.6*1.2 ม.": {"price": 1800, "cost": 1500},
        "กระจกเงา 5mm": {"price": 4500, "cost": 3600},
        "เชือกใย 20 มม. (200 ม.)": {"price": 6600, "cost": 5500},
        "เชือก 16 มม. (200 ม.)": {"price": 3720, "cost": 3100},
        "สลิง 2.5 มม. ( 1 เมตร )": {"price": 24, "cost": 20},
        "ผ้าสักหลาด 1 ตร.ม.": {"price": 180, "cost": 150},
        "มอสเทียม 1 ตร.ม.": {"price": 180, "cost": 150},
        "ท่อเหล็ก OD 1.5 นิ้ว": {"price": 420, "cost": 350},
        "ผ้าปริ้นสี": {"price": 1000, "cost": 800},
        "ผ้าอัดกาว": {"price": 500, "cost": 400},
        "ก้านพลาสติก 22มม. 1 ม.": {"price": 300, "cost": 250},
        "ท่ออลูมิเนียม 1 นิ้ว": {"price": 1680, "cost": 1400},
        "ผ้าหน่วงกันไฟ 1 ตร.ม.": {"price": 960, "cost": 800},
        "ปี๊ปทินเนอร์ 9.5 กิโล": {"price": 1260, "cost": 1050},
        "แว่นหมวกันน็อค ชิลด์ดำ": {"price": 600, "cost": 500},
        "พวงมาลัยสำเร็จรูป": {"price": 96, "cost": 80},
        "สกรูหกเหลี่ยม 3m": {"price": 360, "cost": 300},
        "ผ้า plush (1/sqm.)": {"price": 0, "cost": 0},
    }
}

    LEVEL_FACTORS = {1: 1.0, 2: 1.5, 3: 2.5, 4: 3.5, 5: 5.0, 6: 6.5, 7: 8.0, 8: 10.0, 9: 12.0, 10: 15.0}

    # ==========================================
    # 🎨 Hard Coat Master Pricing (จากใบประเมินราคาโรงงานจริง)
    # ==========================================
    # ทุกอัตราเป็น ฿/ตร.ม. เว้นแต่จะระบุไว้เป็นอย่างอื่น

    # 1) กระบวนการเคลือบผิว (Coating Process) — คิดตามพื้นที่ทำสี/เคลือบผิวทั้งล็อต
    COAT_PROCESS_RATES = {
        "Epoxy": 600,
        "Polyurea": 1350,
    }

    # 2) งานทำโมล (Mold) — คิดตามพื้นที่ผิวต่อชิ้น × จำนวนโมล (ไม่ใช่จำนวนชิ้นที่ผลิต)
    MOLD_RATES = {
        "None / ไม่มี": 0,
        "Mold (1 time)": 605,
        "Mold fiber": 1520,
        "Mold silicone": 4310,
    }

    # 3) งาน Work (แรงงานขึ้นรูป/ประกอบ Fiberglass) — ส่วนใหญ่คิดตามพื้นที่, มี 1 รายการที่เหมาราคาเป็นก้อน
    WORK_RATES = {
        "Work (฿/ตร.ม.)": {"rate": 1090, "billing": "sq.m."},
        "หล่อตัน ธรรมดา (เหมาราคา)": {"rate": 280000, "billing": "lump"},
    }

    # 4) งานสี / Surface Finish — ราคาลูกค้า (price) รวมมาร์จิ้น ~20% เหนือต้นทุนภายใน (cost)
    COLOR_FINISH_DB = {
        "Normal":         {"price": 1440, "cost": 1200},
        "Sticker remove": {"price": 780,  "cost": 650},
        "Gold leaves":    {"price": 168,  "cost": 140},
        "Clear":          {"price": 600,  "cost": 500},
        "The Code":       {"price": 1800, "cost": 1500},
        "Chromium":       {"price": 4800, "cost": 4000},
        "Stainless":      {"price": 1440, "cost": 1200},
        "Sticker":        {"price": 1200, "cost": 1000},
    }

    # 5) ข้อมูลอ้างอิง — อัตราแรงงานรายวัน และจำนวนชั่วโมงแนะนำตามระดับความซับซ้อน (Level)
    #    ยังไม่ผูกเข้ากับราคารวมอัตโนมัติ ใช้เป็นตัวช่วยประกอบการตัดสินใจตั้งชั่วโมง/เรทงาน Work ด้านบน
    LABOR_RATES = {"Engineer": 1000, "Worker": 500, "Designer": 2000}
    HARD_COAT_HOURS = {1: 2, 2: 3, 3: 4, 4: 6, 5: 8, 6: 12, 7: 15, 8: 20}
    SANDING_HOURS   = {1: 3, 2: 4, 3: 5, 4: 4, 5: 6, 6: 8, 7: 12, 8: 15}
    PAINTING_HOURS  = {1: 4, 2: 5, 3: 6, 4: 8, 5: 15, 6: 20, 7: 30, 8: 40}

    # 🏭 Machine Master Data — billing unit per machine type (from factory Excel IFS formula).
    # Everything is Baht/Hr. except 3D Print SLA, which bills per finished unit (Baht/Unit).
    # Add/remove machine types here — the Operations UI below reads this list automatically.
    MACHINE_TYPES = {
        "Robot": "Baht/Hr.",
        "CNC Router": "Baht/Hr.",
        "Hotwire": "Baht/Hr.",
        "Robot / Router": "Baht/Hr.",
        "Robot / Hotwire": "Baht/Hr.",
        "CNC Router / Hotwire": "Baht/Hr.",
        "Water Jet": "Baht/Hr.",
        "Co2 laser": "Baht/Hr.",
        "Fiber laser N2": "Baht/Hr.",
        "Fiber laser O2": "Baht/Hr.",
        "3D Print FDM": "Baht/Hr.",
        "3D Print SLA": "Baht/Unit",
        "Structure": "Baht/Hr.",
    }
    # Default machine rates (฿) — placeholders until real factory rates are entered; editable per-operation in the UI.
    MACHINE_DEFAULT_RATES = {
        "Robot": 300, "CNC Router": 300, "Hotwire": 200, "Robot / Router": 300,
        "Robot / Hotwire": 300, "CNC Router / Hotwire": 300, "Water Jet": 800,
        "Co2 laser": 600, "Fiber laser N2": 2400, "Fiber laser O2": 2400,
        "3D Print FDM": 50, "3D Print SLA": 150, "Structure": 250,
    }

    # 1. ข้อมูลทั่วไป
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        project_name = st.text_input(t["project_name"], value=st.session_state["file_name"])
        complexity_level = st.slider(t["complexity_level"], min_value=1, max_value=10, value=5)
        production_qty = st.number_input(t["production_qty"], min_value=1, value=1, step=1)

    per_piece_area = float(st.session_state["surface_area_sqm"])
    suggested_batch_area = round(per_piece_area * production_qty, 4)

    with col_in2:
        calc_area = st.number_input(
            t["calc_area"],
            min_value=0.0,
            value=suggested_batch_area,
            step=0.1
        )
        st.caption(t["per_piece_area_note"].format(per_piece_area, production_qty, suggested_batch_area))

    st.markdown(f"##### {t['op_title']}")

    with st.expander(t["op_expander"], expanded=True):
        o_col1, o_col2, o_col3, o_col4 = st.columns([2, 1.3, 1.3, 1])

        with o_col1:
            selected_machine = st.selectbox(t["op_select_machine"], list(MACHINE_TYPES.keys()))

        op_unit = MACHINE_TYPES[selected_machine]  # "Baht/Hr." or "Baht/Unit"
        default_rate = MACHINE_DEFAULT_RATES.get(selected_machine, 0)

        with o_col2:
            # key includes the machine name so switching machines gives a fresh widget
            # (a fixed key would make Streamlit keep the old rate on rerun and ignore value=).
            op_rate = st.number_input(
                f"{t['op_rate']} ({op_unit})",
                min_value=0.0, value=float(default_rate), step=10.0,
                key=f"op_rate_{selected_machine}"
            )

        with o_col3:
            if op_unit == "Baht/Hr.":
                # Handy default for Robot: suggest hours from area × complexity level factor,
                # same estimate the original single-machine version used.
                if selected_machine == "Robot":
                    suggested_qty = round(calc_area * LEVEL_FACTORS.get(complexity_level, 5.0), 2)
                else:
                    suggested_qty = 1.0
                op_qty = st.number_input(
                    t["op_qty_hr"], min_value=0.0, value=float(suggested_qty), step=0.5,
                    key=f"op_qty_{selected_machine}"
                )
            else:  # Baht/Unit (e.g. 3D Print SLA)
                op_qty = st.number_input(
                    t["op_qty_unit"], min_value=0.0, value=1.0, step=1.0,
                    key=f"op_qty_{selected_machine}"
                )

        with o_col4:
            st.write(" ")
            st.write(" ")
            if st.button(t["op_add_btn"], use_container_width=True, key="add_op_btn"):
                new_op = {
                    "machine": selected_machine,
                    "unit": op_unit,
                    "rate": op_rate,
                    "qty": op_qty,
                    "total": op_rate * op_qty,
                }
                st.session_state["selected_operations"].append(new_op)
                st.toast(f"Added {selected_machine} x {op_qty} {op_unit}")

    if st.session_state["selected_operations"]:
        st.markdown(f"###### {t['op_selected_list']}")
        ops_df = pd.DataFrame(st.session_state["selected_operations"])
        display_ops_df = ops_df[["machine", "unit", "rate", "qty", "total"]].copy()
        display_ops_df.columns = [
            t["op_col_machine"], t["op_col_unit"], t["op_col_rate"], t["op_col_qty"], t["op_col_total"]
        ]
        st.dataframe(display_ops_df, use_container_width=True)

        col_clear_op, col_stat_op = st.columns([1, 3])
        with col_clear_op:
            if st.button(t["op_clear_btn"]):
                st.session_state["selected_operations"] = []
                st.rerun()

    # ==========================================
    # 📦 ระบบเลือกวัสดุจาก Master Data
    # ==========================================
    st.markdown("---")
    st.markdown(f"##### {t['use_mat']}")

    with st.expander(t["mat_expander"], expanded=True):
        m_col1, m_col2, m_col3, m_col4 = st.columns([1.5, 2, 1, 1])

        with m_col1:
            selected_cat = st.selectbox(t["select_cat"], list(MATERIAL_MASTER_DB.keys()))

        with m_col2:
            materials_in_cat = list(MATERIAL_MASTER_DB[selected_cat].keys())
            selected_mat_item = st.selectbox(t["select_item"], materials_in_cat)

        unit_price = MATERIAL_MASTER_DB[selected_cat][selected_mat_item]["price"]
        unit_cost = MATERIAL_MASTER_DB[selected_cat][selected_mat_item]["cost"]

        with m_col3:
            mat_qty = st.number_input(t["mat_qty"], min_value=1.0, value=1.0, step=1.0)
            st.caption(f"Price: ฿{unit_price:,.2f} | Cost: ฿{unit_cost:,.2f}")

        with m_col4:
            st.write(" ")
            st.write(" ")
            if st.button(t["add_mat_btn"], use_container_width=True):
                new_item = {
                    "cat": selected_cat,
                    "name": selected_mat_item,
                    "qty": mat_qty,
                    "unit_price": unit_price,
                    "unit_cost": unit_cost,
                    "total_price": unit_price * mat_qty,
                    "total_cost": unit_cost * mat_qty
                }
                st.session_state["selected_materials"].append(new_item)
                st.toast(f"Added {selected_mat_item} x {mat_qty}")

    if st.session_state["selected_materials"]:
        st.markdown(f"###### {t['selected_mat_list']}")
        mat_df = pd.DataFrame(st.session_state["selected_materials"])

        display_df = mat_df[["cat", "name", "qty", "unit_price", "total_price"]].copy()
        display_df.columns = ["Category / หมวดหมู่", "Material / ชื่อวัสดุ", "Qty / จำนวน", "Unit Price / ราคา", "Total / ราคารวม"]
        st.dataframe(display_df, use_container_width=True)

        col_clear, col_stat = st.columns([1, 3])
        with col_clear:
            if st.button(t["clear_mat_btn"]):
                st.session_state["selected_materials"] = []
                st.rerun()

    # ==========================================
    # 🎨 Hard Coat: งานเคลือบผิว / โมล / Work / งานสี
    # (จัดกลุ่มตามตาราง "Hard Coat" ในใบประเมินราคาจริง)
    # ==========================================
    st.markdown("---")
    st.markdown(f"##### {t['finishing_title']}")

    HARDCOAT_CATEGORIES = {
        "TH": ["🧪 กระบวนการเคลือบผิว (Coating)", "🗿 งานทำโมล (Mold)", "🛠️ งาน Work (แรงงานขึ้นรูป)", "🎨 งานสี (Color / Surface Finish)"],
        "EN": ["🧪 Coating Process", "🗿 Mold", "🛠️ Work (Labor)", "🎨 Color / Surface Finish"],
    }[lang]

    with st.expander(t["finish_expander"], expanded=True):
        hc_cat = st.radio("—", HARDCOAT_CATEGORIES, horizontal=True, key="hc_cat", label_visibility="collapsed")

        # ---- 1) Coating Process ----
        if hc_cat == HARDCOAT_CATEGORIES[0]:
            c1, c2, c3, c4 = st.columns([2, 1.3, 1.3, 1])
            with c1:
                hc_item = st.selectbox(t["finish_select"], list(COAT_PROCESS_RATES.keys()), key="hc_item_coat")
            with c2:
                hc_rate = st.number_input(
                    t["finish_rate"], min_value=0.0,
                    value=float(COAT_PROCESS_RATES[hc_item]), step=10.0, key=f"hc_rate_coat_{hc_item}"
                )
            with c3:
                hc_area = st.number_input(
                    t["finish_area"], min_value=0.0, value=float(calc_area), step=0.1, key="hc_area_coat"
                )
            with c4:
                st.write(" "); st.write(" ")
                if st.button(t["finish_add_btn"], use_container_width=True, key="add_hc_coat"):
                    st.session_state["selected_finishes"].append({
                        "type": f"Coating - {hc_item}", "rate": hc_rate, "cost_rate": None,
                        "area": hc_area, "total": hc_rate * hc_area, "total_cost": None,
                    })
                    st.toast(f"Added {hc_item}")

        # ---- 2) Mold ----
        elif hc_cat == HARDCOAT_CATEGORIES[1]:
            c1, c2 = st.columns(2)
            with c1:
                hc_item = st.selectbox(t["mold_select"], list(MOLD_RATES.keys()), key="hc_item_mold")
            hc_rate = MOLD_RATES[hc_item]
            with c2:
                hc_qty = st.number_input(t["mold_qty"], min_value=0, value=0, step=1, key="hc_qty_mold")
            hc_total = hc_rate * hc_qty * per_piece_area
            st.caption(t["mold_rate_label"].format(hc_rate, hc_qty, per_piece_area, hc_total))
            if st.button(t["finish_add_btn"], key="add_hc_mold"):
                st.session_state["selected_finishes"].append({
                    "type": f"Mold - {hc_item}", "rate": hc_rate, "cost_rate": None,
                    "area": round(hc_qty * per_piece_area, 4), "total": hc_total, "total_cost": None,
                })
                st.toast(f"Added {hc_item}")

        # ---- 3) Work (labor) ----
        elif hc_cat == HARDCOAT_CATEGORIES[2]:
            c1, c2, c3, c4 = st.columns([2, 1.3, 1.3, 1])
            with c1:
                hc_item = st.selectbox("Work", list(WORK_RATES.keys()), key="hc_item_work", label_visibility="collapsed")
            hc_info = WORK_RATES[hc_item]
            with c2:
                hc_rate = st.number_input(
                    f"{t['finish_rate'] if hc_info['billing']=='sq.m.' else ('อัตรา (฿/งาน)' if lang=='TH' else 'Rate (฿/job)')}",
                    min_value=0.0, value=float(hc_info["rate"]), step=10.0, key=f"hc_rate_work_{hc_item}"
                )
            with c3:
                if hc_info["billing"] == "sq.m.":
                    hc_qty = st.number_input(t["finish_area"], min_value=0.0, value=float(calc_area), step=0.1, key=f"hc_qty_work_{hc_item}")
                else:
                    hc_qty = st.number_input(
                        "จำนวนงาน (ชุด)" if lang == "TH" else "Number of jobs",
                        min_value=0.0, value=1.0, step=1.0, key=f"hc_qty_work_{hc_item}"
                    )
            with c4:
                st.write(" "); st.write(" ")
                if st.button(t["finish_add_btn"], use_container_width=True, key="add_hc_work"):
                    st.session_state["selected_finishes"].append({
                        "type": f"Work - {hc_item}", "rate": hc_rate, "cost_rate": None,
                        "area": hc_qty, "total": hc_rate * hc_qty, "total_cost": None,
                    })
                    st.toast(f"Added {hc_item}")

            with st.popover("💡 " + ("ตัวช่วยประเมินชั่วโมงแรงงาน" if lang == "TH" else "Labor hour helper")):
                st.caption(
                    ("ชั่วโมงแนะนำตาม Level ปัจจุบัน (" if lang == "TH" else "Suggested hours for current Level (")
                    + f"{complexity_level}):"
                )
                st.write(
                    f"- Hard Coat: `{HARD_COAT_HOURS.get(complexity_level, '-')}` Hr. | "
                    f"Sanding: `{SANDING_HOURS.get(complexity_level, '-')}` Hr. | "
                    f"Painting: `{PAINTING_HOURS.get(complexity_level, '-')}` Hr."
                )
                st.write(
                    ("อัตราแรงงาน/วัน: " if lang == "TH" else "Daily labor rate: ")
                    + " | ".join([f"{k} ฿{v:,.0f}" for k, v in LABOR_RATES.items()])
                )

        # ---- 4) Color / Surface Finish ----
        else:
            c1, c2, c3, c4 = st.columns([2, 1.6, 1.3, 1])
            with c1:
                hc_item = st.selectbox(t["finish_select"], list(COLOR_FINISH_DB.keys()), key="hc_item_color")
            hc_info = COLOR_FINISH_DB[hc_item]
            with c2:
                hc_rate = st.number_input(
                    f"{t['finish_rate']} (cost ฿{hc_info['cost']:,} +20%)",
                    min_value=0.0, value=float(hc_info["price"]), step=10.0, key=f"hc_rate_color_{hc_item}"
                )
            with c3:
                hc_area = st.number_input(
                    t["finish_area"], min_value=0.0, value=float(calc_area), step=0.1, key="hc_area_color"
                )
            with c4:
                st.write(" "); st.write(" ")
                if st.button(t["finish_add_btn"], use_container_width=True, key="add_hc_color"):
                    st.session_state["selected_finishes"].append({
                        "type": f"Color - {hc_item}", "rate": hc_rate, "cost_rate": hc_info["cost"],
                        "area": hc_area, "total": hc_rate * hc_area, "total_cost": hc_info["cost"] * hc_area,
                    })
                    st.toast(f"Added {hc_item}")

    if st.session_state["selected_finishes"]:
        st.markdown(f"###### {t['finish_selected_list']}")
        finish_df = pd.DataFrame(st.session_state["selected_finishes"])
        display_finish_df = finish_df[["type", "rate", "area", "total"]].copy()
        display_finish_df["total_cost"] = finish_df["total_cost"]
        display_finish_df.columns = [
            t["finish_col_type"], t["finish_col_rate"], t["finish_col_area"], t["finish_col_total"],
            "Total Cost (internal)" if lang == "EN" else "ต้นทุนภายใน (฿)",
        ]
        st.dataframe(display_finish_df, use_container_width=True)

        finishing_margin = sum(
            (item["total"] - item["total_cost"])
            for item in st.session_state["selected_finishes"]
            if item.get("total_cost") is not None
        )
        if finishing_margin:
            st.caption(
                ("มาร์จิ้นจากงานสี (เทียบต้นทุนภายใน): " if lang == "TH" else "Margin on color/finish items (vs internal cost): ")
                + f"฿{finishing_margin:,.2f}"
            )

        col_clear_f, col_stat_f = st.columns([1, 3])
        with col_clear_f:
            if st.button(t["finish_clear_btn"]):
                st.session_state["selected_finishes"] = []
                st.rerun()

    # ==========================================
    # 🧮 การคำนวณสรุปราคาและต้นทุนรวม
    # ==========================================
    st.markdown("---")
    st.subheader(t["summary_title"])

    machine_total = sum(op["total"] for op in st.session_state["selected_operations"])

    material_total_price = sum(item["total_price"] for item in st.session_state["selected_materials"])
    finishing_total = sum(f["total"] for f in st.session_state["selected_finishes"])

    subtotal = machine_total + material_total_price + finishing_total

    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric(t["mch_cost"], f"฿{machine_total:,.2f}")
    col_res2.metric(t["mat_cost"], f"฿{material_total_price:,.2f}")
    col_res3.metric(t["paint_cost"], f"฿{finishing_total:,.2f}")

    st.markdown(f"### {t['grand_total']}")
    st.title(f"฿ {subtotal:,.2f} THB")
