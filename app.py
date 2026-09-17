import streamlit as st
import trimesh
import numpy as np
import tempfile
import os
import base64
import pandas as pd
from string import Template
import streamlit.components.v1 as components
import auth
from grid_visualizer import create_foam_grid_visualizer, get_submeshes

auth.require_login()

# ==========================================
# ⚙️ 1. Page Configuration
# ==========================================
st.set_page_config(page_title="3D Model Analyzer & Cost Estimator", page_icon="📦", layout="wide")

# ==========================================
# 🎨 1b. Custom Theme — Studio / Art Workshop, warm
# ==========================================
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

    /* Sidebar nav pills */
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
        display: none !important;
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
        "p1_title": "📦 3D Model Dimension & Surface Area Analyzer",
        "p1_sub": "อัปโหลดไฟล์โมเดล 3D เพื่อวิเคราะห์ขนาด Bounding Box, พื้นที่ผิว, ปริมาตร และความซับซ้อนของพื้นผิวอัตโนมัติ",
        "welcome_title": "สวัสดีค่ะ",
        "welcome_sub": "มาเริ่มสร้างสรรค์งานชิ้นต่อไปกันเถอะ",
        "file_processed_badge": "ประมวลผลไฟล์สำเร็จ",
        "file_processed_sub": "ข้อมูลพร้อมสำหรับประเมินราคา",
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
        "p1_title": "📦 3D Model Dimension & Surface Area Analyzer",
        "p1_sub": "Upload a 3D model file to automatically extract bounding box dimensions, surface area, volume, and surface detail complexity.",
        "welcome_title": "Welcome back",
        "welcome_sub": "Let's bring your ideas to life.",
        "file_processed_badge": "File processed successfully",
        "file_processed_sub": "Data ready for cost estimation",
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
if "volume_cm3" not in st.session_state:
    st.session_state["volume_cm3"] = 0.0
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
if "mesh" not in st.session_state:
    st.session_state["mesh"] = None
if "submesh_count" not in st.session_state:
    st.session_state["submesh_count"] = 1

# ==========================================
# 🛠️ Helper Functions & Constants
# ==========================================
SCALE_TO_M = 0.001

# STL/OBJ/PLY/OFF files carry no unit metadata — trimesh just returns whatever
# numbers are in the file. The app previously assumed every file was already
# in millimeters (see FIX NOTE below), which silently produces wrong areas/
# volumes/prices for files authored in cm, m, or inches. Let the user tell us.
UNIT_TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "inch": 25.4}

def process_and_clean_mesh(loaded_data):
    sub_count = 1
    if isinstance(loaded_data, trimesh.Scene):
        geometries = []
        for node_name in loaded_data.graph.nodes_geometry:
            transform, geometry_name = loaded_data.graph[node_name]
            geom = loaded_data.geometry[geometry_name].copy()
            geom.apply_transform(transform)
            geometries.append(geom)

        sub_count = len(geometries) if geometries else 1
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

    return mesh, sub_count

def analyze_surface_complexity(mesh, scale_to_m, is_point_cloud, current_lang="TH"):
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
        level = "Simple Surface" if current_lang == "EN" else "ผิวเรียบง่าย"
    elif detail_score < 45:
        level = "Moderate Surface" if current_lang == "EN" else "ผิวมีรายละเอียดปานกลาง"
    elif detail_score < 70:
        level = "Detailed Surface" if current_lang == "EN" else "ผิวมีรายละเอียดสูง"
    else:
        level = "Highly Complex Surface" if current_lang == "EN" else "ผิวมีความซับซ้อนสูงมาก"

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

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / 500, 0.1, 10000);
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

            // FIX: near/far and orbit zoom limits now scale with the model instead
            // of being fixed values, so large models don't get clipped by the far
            // plane and small models don't get near-clipped when zoomed in close.
            camera.near = Math.max(radius / 500, 0.01);
            camera.far = Math.max(radius * 20, 2000);
            camera.updateProjectionMatrix();
            controls.minDistance = camera.near * 4;
            controls.maxDistance = camera.far * 0.9;

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

# ==========================================
# 🧭 4. Sidebar Navigation & Language Selector
# ==========================================
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
t = TEXTS[lang]

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

    uploaded_file = st.file_uploader(
        t["file_uploader"],
        type=["stl", "obj", "ply", "off", "3mf"]
    )
    # Source file unit is fixed to mm (no dropdown) per request — all files in
    # this workflow are authored in mm.
    file_unit_to_mm = UNIT_TO_MM["mm"]

    if uploaded_file is not None:
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        try:
            with st.spinner("Processing 3D model file..."):
                loaded_data = trimesh.load(tmp_path)
                mesh, submesh_cnt = process_and_clean_mesh(loaded_data)
                st.session_state["submesh_count"] = submesh_cnt

                is_point_cloud = isinstance(mesh, trimesh.PointCloud)

                # FIX: previously `mesh_mm.apply_scale(SCALE_TO_M * 1000.0)` == apply_scale(1.0),
                # a no-op that silently assumed the source file was already in millimeters.
                # Now it uses the unit the user picked above.
                mesh_mm = mesh.copy()
                mesh_mm.apply_scale(file_unit_to_mm)
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
                st.sidebar.caption(
                    "🔓 ปิดสวิตช์นี้เพื่อปรับกว้าง/ยาว/สูงอิสระจากกัน — รูปทรงโมเดลจะยืด/บีบตามค่าที่ตั้ง"
                    if lang == "TH" else
                    "🔓 Turn this off to set width/length/height independently — the "
                    "model's shape will stretch/squash to match."
                )
                st.sidebar.number_input(t["size_w"], min_value=0.001, key="dim_w_mm", step=1.0, on_change=_sync_from_width)
                st.sidebar.number_input(t["size_l"], min_value=0.001, key="dim_l_mm", step=1.0, on_change=_sync_from_length)
                st.sidebar.number_input(t["size_h"], min_value=0.001, key="dim_h_mm", step=1.0, on_change=_sync_from_height)
                if st.sidebar.button(t["size_reset_btn"], use_container_width=True):
                    st.session_state["dim_w_mm"] = round(base_w_mm, 3)
                    st.session_state["dim_l_mm"] = round(base_l_mm, 3)
                    st.session_state["dim_h_mm"] = round(base_h_mm, 3)
                    st.rerun()
                st.sidebar.caption(t["size_recalc_note"])

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

                surface_area_m2 = 0.0
                volume_m3 = 0.0
                is_watertight = False
                used_convex_hull = False
                used_bbox_estimate = False

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

                    # FIX: previously, if the mesh wasn't watertight AND convex_hull()
                    # also failed/returned 0, volume_m3 stayed exactly 0 and that 0
                    # silently flowed into every downstream calculation (page 2's 3D
                    # print time estimate collapsed to program+setup only, with zero
                    # machine time, because effective_volume got capped at 0). Two
                    # more attempts before giving up:
                    if volume_m3 <= 0:
                        try:
                            repaired = final_mesh.copy()
                            trimesh.repair.fill_holes(repaired)
                            if getattr(repaired, 'is_watertight', False):
                                volume_m3 = repaired.volume / 1_000_000_000.0
                                is_watertight = True
                                used_convex_hull = False
                        except Exception:
                            pass
                    if volume_m3 <= 0:
                        try:
                            # ASSUMPTION: ไม่รู้ solidity จริงของโมเดล ใช้ 40% ของปริมาตร
                            # oriented bounding box เป็นค่ากลางๆ (ระหว่างโมเดลกลวงบางกับ
                            # โมเดลตัน) — ประมาณคร่าวมาก แจ้งเตือนผู้ใช้ชัดเจนในหน้าเว็บ
                            obb_volume_mm3 = final_mesh.bounding_box_oriented.volume
                            volume_m3 = (obb_volume_mm3 * 0.4) / 1_000_000_000.0
                            used_bbox_estimate = True
                        except Exception:
                            volume_m3 = 0.0

                surface_area_cm2 = surface_area_m2 * 10_000.0
                volume_cm3 = volume_m3 * 1_000_000.0

                complexity = analyze_surface_complexity(final_mesh, SCALE_TO_M, is_point_cloud, lang)

                st.session_state["mesh"] = final_mesh
                st.session_state["surface_area_sqm"] = surface_area_m2
                st.session_state["volume_cm3"] = volume_cm3
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
                elif used_bbox_estimate and volume_m3 > 0:
                    res_b.metric(
                        "ปริมาตร (ประมาณจาก Bounding Box)" if lang == "TH" else "Volume (Bounding Box estimate)",
                        f"{volume_m3:,.4f} cu.m", f"{volume_cm3:,.1f} cu.cm"
                    )
                    st.warning(
                        "⚠️ โมเดลนี้คำนวณปริมาตรแบบละเอียดไม่ได้ (ไม่ watertight และ "
                        "Convex Hull ก็ล้มเหลว) ตัวเลขนี้จึงเป็นการประมาณคร่าวๆ จาก "
                        "Bounding Box เท่านั้น (สมมติความตัน 40%) ไม่แม่นยำเท่าปริมาตรจริง "
                        "— ควรตรวจสอบไฟล์ 3D ต้นฉบับว่ามีรูรั่ว/geometry เสียหรือไม่"
                        if lang == "TH" else
                        "⚠️ Couldn't compute an exact volume for this mesh (not "
                        "watertight, and Convex Hull also failed). This is a rough "
                        "estimate from the bounding box only (assuming 40% solidity) — "
                        "check the source 3D file for holes/broken geometry."
                    )
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

    if st.session_state.get("surface_area_sqm", 0.0) <= 0:
        st.warning(
            "⚠️ ยังไม่มีข้อมูลโมเดลจากหน้าแรก กรุณาอัปโหลดไฟล์ 3D ที่หน้า "
            f"'{t['page_1_name']}' ก่อน ไม่เช่นนั้นราคาที่ประเมินจะอิงพื้นที่ผิว/ปริมาตร = 0"
            if lang == "TH" else
            "⚠️ No model data yet — please upload a 3D file on the "
            f"'{t['page_1_name']}' page first, otherwise the estimate below will be "
            "based on a surface area/volume of 0."
        )

    from data_loader import (
        load_material_master_db,
        load_rate_dict,
        load_mold_rates,
        load_work_rates,
        load_color_finish_db,
        load_labor_rates,
        load_complexity_hours,
        get_data_quality_warnings,
        SheetAPIError,
        COAT_PROCESS_SHEET_NAME,
    )
    from machining_estimator import (
        estimate_foam_cnc_hours,
        estimate_3d_print_hours,
        estimate_foam_blocks_needed,
        DEFAULT_FOAM_BLOCK_W_MM,
        DEFAULT_FOAM_BLOCK_L_MM,
        DEFAULT_FOAM_BLOCK_H_MM,
        DEFAULT_FOAM_WASTE_FACTOR,
    )

    # FIX: these were previously called with no caching, so every single widget
    # interaction on this page (a slider drag, a number_input change, etc.)
    # re-read the master-data source (Excel/Sheets) from scratch. That's the
    # most likely cause of the page feeling slow/laggy. st.cache_data keeps the
    # result in memory and only reloads if the underlying function's code/args
    # change or the TTL expires.
    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_material_master_db():
        return load_material_master_db()

    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_coat_process_rates():
        return load_rate_dict(COAT_PROCESS_SHEET_NAME, "process_name", "rate")

    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_mold_rates():
        return load_mold_rates()

    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_work_rates():
        return load_work_rates()

    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_color_finish_db():
        return load_color_finish_db()

    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_labor_rates():
        return load_labor_rates()

    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_complexity_hours():
        return load_complexity_hours()

    # FIX: previously an unhandled network/token error here would crash the whole
    # page with a raw traceback. Now it shows a message the user can act on, with
    # a button to retry (clears the 5-minute cache so the next click re-fetches).
    try:
        MATERIAL_MASTER_DB = _cached_material_master_db()
        COAT_PROCESS_RATES = _cached_coat_process_rates()
        MOLD_RATES = _cached_mold_rates()
        WORK_RATES = _cached_work_rates()
        COLOR_FINISH_DB = _cached_color_finish_db()
        LABOR_RATES = _cached_labor_rates()
        COMPLEXITY_HOURS_DB = _cached_complexity_hours()
    except SheetAPIError as e:
        st.error(f"❌ โหลดข้อมูลราคาจาก Google Sheet ไม่สำเร็จ: {e}")
        if st.button("🔄 ลองโหลดข้อมูลใหม่" if lang == "TH" else "🔄 Retry"):
            st.cache_data.clear()
            st.rerun()
        st.stop()

    # FIX: check_for_duplicate_items() existed in data_loader.py but was never
    # called, so duplicate rows in the Sheet silently overwrote each other with
    # no warning. Surface it here.
    dq_warnings = get_data_quality_warnings()
    if dq_warnings:
        with st.expander(
            f"⚠️ พบข้อมูลซ้ำในชีทราคา ({len(dq_warnings)} รายการ) — คลิกเพื่อดูรายละเอียด"
            if lang == "TH" else
            f"⚠️ Found {len(dq_warnings)} duplicate row(s) in the price sheet — click to view",
            expanded=False,
        ):
            for w in dq_warnings:
                st.write(f"- {w}")

    # FIX: previously hardcoded here (and the hour tables stopped at level 8 even
    # though the complexity slider goes to 10). Now sourced from the LaborRates /
    # ComplexityHours sheets via Code.gs, so editing the sheet is enough to
    # update these — no code deploy needed, and any level actually defined in
    # the sheet is honored (not capped at 8).
    HARD_COAT_HOURS = {lvl: v["hard_coat"] for lvl, v in COMPLEXITY_HOURS_DB.items()}
    SANDING_HOURS = {lvl: v["sanding"] for lvl, v in COMPLEXITY_HOURS_DB.items()}
    PAINTING_HOURS = {lvl: v["painting"] for lvl, v in COMPLEXITY_HOURS_DB.items()}

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

    MACHINE_DEFAULT_RATES = {
        "Robot": 300, "CNC Router": 300, "Hotwire": 200, "Robot / Router": 300,
        "Robot / Hotwire": 300, "CNC Router / Hotwire": 300, "Water Jet": 800,
        "Co2 laser": 600, "Fiber laser N2": 2400, "Fiber laser O2": 2400,
        "3D Print FDM": 50, "3D Print SLA": 150, "Structure": 250,
    }

    col_in1, col_in2 = st.columns(2)
    with col_in1:
        project_name = st.text_input(t["project_name"], value=st.session_state["file_name"])
        complexity_level = st.slider(t["complexity_level"], min_value=1, max_value=10, value=5)
        production_qty = st.number_input(t["production_qty"], min_value=1, value=1, step=1)

    per_piece_area = float(st.session_state["surface_area_sqm"])
    suggested_batch_area = round(per_piece_area * production_qty, 4)

    per_piece_volume_cm3 = float(st.session_state.get("volume_cm3", 0.0))
    bbox_w_mm = float(st.session_state.get("width_x_mm", 0.0))
    bbox_l_mm = float(st.session_state.get("length_y_mm", 0.0))
    bbox_h_mm = float(st.session_state.get("height_z_mm", 0.0))
    bbox_volume_cm3 = (bbox_w_mm * bbox_l_mm * bbox_h_mm) / 1000.0
    per_piece_removal_cm3 = max(bbox_volume_cm3 - per_piece_volume_cm3, 0.0)

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

        op_unit = MACHINE_TYPES[selected_machine]
        default_rate = MACHINE_DEFAULT_RATES.get(selected_machine, 0)

        with o_col2:
            op_rate = st.number_input(
                f"{t['op_rate']} ({op_unit})",
                min_value=0.0, value=float(default_rate), step=10.0,
                key=f"op_rate_{selected_machine}"
            )

        with o_col3:
            if op_unit == "Baht/Hr.":
                if selected_machine == "Robot":
                    machining_result = estimate_foam_cnc_hours(
                        volume_removal_cm3=per_piece_removal_cm3,
                        surface_area_sqm=per_piece_area,
                        complexity_level=complexity_level,
                    )
                    suggested_rough = machining_result.breakdown["roughing_hours"]
                    suggested_finish = machining_result.breakdown["finishing_hours"]
                    st.caption(
                        f"⚙️ ประมาณอัตโนมัติต่อ 1 ชิ้น "
                        f"(ดอก finishing {machining_result.breakdown['finish_tool_mm_used']} มม.)"
                    )
                    op_qty_rough = st.number_input(
                        "ชั่วโมงกัดหยาบ (Roughing)" if lang == "TH" else "Roughing hours",
                        min_value=0.0, value=float(suggested_rough), step=0.25,
                        key=f"op_qty_rough_{selected_machine}_{complexity_level}"
                    )
                    op_qty_finish = st.number_input(
                        "ชั่วโมงกัดละเอียด (Finishing)" if lang == "TH" else "Finishing hours",
                        min_value=0.0, value=float(suggested_finish), step=0.25,
                        key=f"op_qty_finish_{selected_machine}_{complexity_level}"
                    )
                    op_qty = None
                elif selected_machine == "3D Print FDM":
                    fdm_infill_pct = st.slider(
                        "Infill (%)" if lang != "TH" else "Infill (%)",
                        min_value=0, max_value=100, value=15, step=5,
                        key=f"fdm_infill_{selected_machine}",
                        help=(
                            "สัดส่วนเนื้อพลาสติกด้านในชิ้นงาน (ไม่รวมผนังนอก) — ยิ่งสูง "
                            "ยิ่งใช้เส้นพลาสติกมากขึ้นและใช้เวลาพิมพ์นานขึ้นตามสัดส่วน"
                            if lang == "TH" else
                            "Interior fill density (walls are always ~100%) — higher "
                            "infill uses proportionally more filament and print time."
                        ),
                    )
                    print_result = estimate_3d_print_hours(
                        volume_cm3=per_piece_volume_cm3,
                        surface_area_sqm=per_piece_area,
                        infill_pct=float(fdm_infill_pct),
                        complexity_level=complexity_level,
                    )
                    suggested_qty = print_result.hours
                    st.caption(
                        f"⚙️ ประมาณอัตโนมัติต่อ 1 ชิ้น น้ำหนักที่คาดว่าจะใช้ "
                        f"~{print_result.breakdown['estimated_weight_g']:.0f} g "
                        f"จากปริมาตรพิมพ์จริง {print_result.breakdown['effective_volume_cm3']} cm³ "
                        f"(อัตรา {print_result.breakdown['hours_per_cm3']:.5f} ชม./cm³)"
                    )
                    op_qty = st.number_input(
                        t["op_qty_hr"], min_value=0.0, value=float(suggested_qty), step=0.5,
                        key=f"op_qty_{selected_machine}"
                    )
                else:
                    suggested_qty = 1.0
                    op_qty = st.number_input(
                        t["op_qty_hr"], min_value=0.0, value=float(suggested_qty), step=0.5,
                        key=f"op_qty_{selected_machine}"
                    )
            else:
                op_qty = st.number_input(
                    t["op_qty_unit"], min_value=0.0, value=1.0, step=1.0,
                    key=f"op_qty_{selected_machine}"
                )

        with o_col4:
            st.write(" ")
            st.write(" ")
            if st.button(t["op_add_btn"], use_container_width=True, key="add_op_btn"):
                if selected_machine == "Robot" and op_unit == "Baht/Hr.":
                    rough_label = f"{selected_machine} (กัดหยาบ)" if lang == "TH" else f"{selected_machine} (Roughing)"
                    finish_label = f"{selected_machine} (กัดละเอียด)" if lang == "TH" else f"{selected_machine} (Finishing)"
                    new_ops = [
                        {
                            "machine": rough_label, "unit": op_unit, "rate": op_rate,
                            "qty": op_qty_rough, "total": op_rate * op_qty_rough,
                        },
                        {
                            "machine": finish_label, "unit": op_unit, "rate": op_rate,
                            "qty": op_qty_finish, "total": op_rate * op_qty_finish,
                        },
                    ]
                    st.session_state["selected_operations"].extend(new_ops)
                    st.toast(f"Added Robot Roughing {op_qty_rough} + Finishing {op_qty_finish} {op_unit}")
                else:
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

        # FIX: แสดงผลแบบทีละแถวด้วย st.columns แทน st.dataframe เพื่อใส่ปุ่มลบ (🗑️) ต่อแถวได้
        # เดิมมีแค่ "ล้างรายการทั้งหมด" ถ้าเลือกผิด 1 รายการต้องลบทิ้งทั้งหมดแล้วเลือกใหม่ทุกอัน
        op_header_cols = st.columns([2.2, 1.3, 1.1, 1.1, 1.2, 0.6])
        for col, label in zip(
            op_header_cols,
            [t["op_col_machine"], t["op_col_unit"], t["op_col_rate"], t["op_col_qty"], t["op_col_total"], ""]
        ):
            col.markdown(f"**{label}**")

        op_to_delete = None
        for i, op in enumerate(st.session_state["selected_operations"]):
            row_cols = st.columns([2.2, 1.3, 1.1, 1.1, 1.2, 0.6])
            row_cols[0].write(op["machine"])
            row_cols[1].write(op["unit"])
            row_cols[2].write(f"{op['rate']:,.2f}")
            row_cols[3].write(f"{op['qty']:,.2f}")
            row_cols[4].write(f"{op['total']:,.2f}")
            if row_cols[5].button("🗑️", key=f"del_op_{i}", help="ลบแถวนี้" if lang == "TH" else "Delete this row"):
                op_to_delete = i

        if op_to_delete is not None:
            st.session_state["selected_operations"].pop(op_to_delete)
            st.rerun()

        col_clear_op, col_stat_op = st.columns([1, 3])
        with col_clear_op:
            if st.button(t["op_clear_btn"]):
                st.session_state["selected_operations"] = []
                st.rerun()

    # ----------------------------------------------------------------------
    # 🧩 Plotly Foam Slicing Visualizer
    # ----------------------------------------------------------------------
    x_mm = st.session_state.get("width_x_mm", 0.0)
    y_mm = st.session_state.get("length_y_mm", 0.0)
    z_mm = st.session_state.get("height_z_mm", 0.0)
    current_mesh = st.session_state.get("mesh")
    submesh_count = st.session_state.get("submesh_count", 1)

    # ค่า wall_thickness เริ่มต้น (ใช้ร่วมกันทั้ง visualizer และ block estimator ด้านล่าง
    # แม้ผู้ใช้ยังไม่เปิด visualizer เพื่อไม่ให้ block estimator พังหา key ไม่เจอ)
    if "p2_wall_thick" not in st.session_state:
        st.session_state["p2_wall_thick"] = 75

    if x_mm > 0 and y_mm > 0 and z_mm > 0:
        st.markdown("---")
        with st.expander("🧩 ภาพจำลองผังการตัดแบ่งบล็อกโฟม (Foam Slicing Visualizer)", expanded=True):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                max_seg_m = st.slider("ขนาดบล็อกโฟมสูงสุดต่อชิ้น (เมตร)", 0.5, 2.0, 1.0, 0.1, key="p2_max_seg")
            with col_v2:
                wall_thick = st.slider("ความหนาเปลือกโฟม Hollow Shell (มม.)", 30, 150, 75, 5, key="p2_wall_thick")

            current_slice_mode = "modular" if submesh_count > 1 else "planar"

            fig_grid = create_foam_grid_visualizer(
                x_mm=x_mm,
                y_mm=y_mm,
                z_mm=z_mm,
                max_segment_mm=max_seg_m * 1000.0,
                wall_thickness_mm=wall_thick,
                mesh=current_mesh,
                slice_mode=current_slice_mode
            )
            st.plotly_chart(fig_grid, use_container_width=True, key="p2_foam_grid_chart")

        st.markdown("##### 💡 แนะนำกลยุทธ์การตัดแบ่งและกัดโฟม (Machining Optimization Strategy)")

        col_rec1, col_rec2 = st.columns([2, 1])

        aspect_ratio = max(x_mm, y_mm, z_mm) / (min(x_mm, y_mm, z_mm) + 1e-5)
        is_flat = (z_mm < x_mm * 0.5) or (z_mm < y_mm * 0.5)

        with col_rec1:
            if submesh_count > 1:
                st.success(f"🧩 **ตรวจพบโมเดลแยกชิ้นส่วนแล้ว ({submesh_count} ชิ้นส่วน)**")
                st.write("""
                * **กลยุทธ์:** นำแต่ละชิ้นส่วน (เช่น แขน, ขา, ลำตัว) เข้ากระบวนการจัดวางบนเตียงกัดแยกกัน
                * **ข้อดี:** ไม่ต้องผ่าไฟล์ใหม่ ประหยัดเนื้อโฟมได้สูงสุด และสามารถรันกัดพร้อมกันหลายเครื่องได้ทันที
                """)
            else:
                if is_flat:
                    st.info("🎯 **แนะนำ: ตัดแบ่ง 2 ซีกหน้า-หลัง (2-Plane Split / Half-Split)**")
                    st.write("""
                    * **วิธีจัดวาง:** ผ่าครึ่งโมเดลตามแนวราบ วางโฟมราบกับเตียงกัด (เหมาะกับงานนูนหรือครึ่งองค์)
                    * **ข้อดี:** ล็อกชิ้นงานง่าย กัดเรียบเนียน ประหยัดเวลา ไม่ต้องใช้เครื่องกัดหลายแกนซับซ้อน
                    """)
                elif aspect_ratio > 2.2:
                    st.warning("✂️ **แนะนำ: ถอดแยกชิ้นส่วนตามข้อต่อ (Modular Joint Split)**")
                    st.write("""
                    * **วิธีจัดวาง:** ใช้ Plane Slice แบ่งโฟมตามสัดส่วนองค์ประกอบ (เช่น หัว, ลำตัว, แขน, ขา)
                    * **ข้อดี:** ลดการกัด Air-Cutting สุญญากาศรอบตัวโมเดล ประหยัดโฟมก้อนใหญ่ และช่วยให้ดอกกัดเข้าถึงจุดลึกได้ง่ายขึ้น
                    """)
                else:
                    st.info("📐 **แนะนำ: ตัดแบ่งบล็อกสมมาตร 2–4 ส่วน (Grid / Layer Slicing)**")
                    st.write("""
                    * **วิธีจัดวาง:** หั่นโฟมเป็นแผ่น/บล็อกทรงสี่เหลี่ยม 2–4 ชิ้นเท่าๆ กัน
                    * **ข้อดี:** เข้ากับขนาดบล็อกโฟมมาตรฐาน สะดวกต่อการนำมาต่อกาวและขัดโป๊ว
                    """)

        with col_rec2:
            if submesh_count > 1:
                est_time_saved = 45
                est_material_saved = 35
            else:
                est_time_saved = 35 if is_flat else (40 if aspect_ratio > 2.2 else 20)
                est_material_saved = 30 if is_flat else (35 if aspect_ratio > 2.2 else 15)

            st.metric(label="⏱️ ประเมินเวลาที่ลดได้", value=f"~{est_time_saved}%")
            st.metric(label="📦 ประเมินการลดขยะโฟม", value=f"~{est_material_saved}%")

    # ==========================================
    # 📦 ประเมินจำนวนก้อนโฟมที่ต้องใช้ (Recommended Foam Blocks)
    # ==========================================
    # ใช้สูตร hollow-shell (bbox ลบส่วนกลวงตาม wall_thickness) หารด้วยปริมาตรก้อนมาตรฐาน
    # แล้วเผื่อ waste_factor — ใช้ wall_thickness เดียวกับ visualizer ด้านบน (ไม่ต้องตั้งซ้ำ)
    # ไม่มี UI ให้ตั้งค่าขนาดก้อน/waste factor แยก (ตามที่ขอ) — ใช้ค่า default คงที่
    # ภายใน แสดงผลแค่ตัวเลขแนะนำทศนิยม 1 ตำแหน่ง เหมือนตัวอย่าง "1.8 ก้อน"
    #
    # ถ้าโมเดลมีหลายชิ้นส่วน (submesh_count > 1) คำนวณแยกทีละชิ้นแล้วรวมยอด แทนที่จะใช้
    # bbox รวมทั้งโมเดล ซึ่งจะเผื่อพื้นที่ว่างระหว่างชิ้นส่วนเกินจริง — ถ้า get_submeshes()
    # ใช้งานไม่ได้ (เช่น trimesh/networkx เวอร์ชันไม่เข้ากัน) จะ fallback ไปใช้ bbox รวม
    # แทน ไม่ทำให้ทั้งหน้าพัง
    st.markdown("---")
    st.markdown("##### 📦 ประเมินจำนวนก้อนโฟมที่ต้องใช้ (Recommended Foam Blocks)")

    current_wall_thick = float(st.session_state.get("p2_wall_thick", 75))

    submeshes_for_blocks = []
    submesh_split_failed = False
    if submesh_count > 1 and current_mesh is not None:
        try:
            submeshes_for_blocks = get_submeshes(current_mesh)
        except Exception:
            # FIX: get_submeshes() (mesh.split() ผ่าน trimesh -> networkx) เคยพังทั้งหน้า
            # เพราะไม่มีการดักจับ error เลย ตอนนี้ถ้าแยกชิ้นส่วนไม่สำเร็จ จะ fallback ไปคำนวณ
            # จาก bounding box รวมทั้งโมเดลแทน แล้วแจ้งเตือนผู้ใช้เฉยๆ ไม่ทำให้แอป error
            submesh_split_failed = True

    total_blocks = 0.0
    per_piece_blocks = 0.0

    if submesh_count > 1 and len(submeshes_for_blocks) > 1:
        per_part_blocks = []
        for sm in submeshes_for_blocks:
            ext = sm.extents
            calc = estimate_foam_blocks_needed(
                width_mm=float(ext[0]), length_mm=float(ext[1]), height_mm=float(ext[2]),
                block_w_mm=DEFAULT_FOAM_BLOCK_W_MM, block_l_mm=DEFAULT_FOAM_BLOCK_L_MM,
                block_h_mm=DEFAULT_FOAM_BLOCK_H_MM,
                wall_thickness_mm=current_wall_thick, waste_factor=DEFAULT_FOAM_WASTE_FACTOR,
            )
            per_part_blocks.append(calc["blocks_needed"])
        per_piece_blocks = round(sum(per_part_blocks), 1)
        total_blocks = round(per_piece_blocks * production_qty, 1)
    elif x_mm > 0 and y_mm > 0 and z_mm > 0:
        calc = estimate_foam_blocks_needed(
            width_mm=x_mm, length_mm=y_mm, height_mm=z_mm,
            block_w_mm=DEFAULT_FOAM_BLOCK_W_MM, block_l_mm=DEFAULT_FOAM_BLOCK_L_MM,
            block_h_mm=DEFAULT_FOAM_BLOCK_H_MM,
            wall_thickness_mm=current_wall_thick, waste_factor=DEFAULT_FOAM_WASTE_FACTOR,
        )
        per_piece_blocks = calc["blocks_needed"]
        total_blocks = round(per_piece_blocks * production_qty, 1)

    if x_mm > 0 and y_mm > 0 and z_mm > 0:
        if submesh_split_failed:
            st.caption(
                "⚠️ แยกชิ้นส่วนโมเดลอัตโนมัติไม่สำเร็จ ตัวเลขด้านล่างคำนวณจาก Bounding Box "
                "รวมทั้งโมเดลแทน (อาจเผื่อเนื้อโฟมเกินจริงเล็กน้อยถ้าโมเดลมีหลายชิ้นแยกห่างกัน)"
                if lang == "TH" else
                "⚠️ Automatic part-splitting failed — the number below is calculated from the "
                "whole-model bounding box instead (may slightly overestimate for models with "
                "widely separated parts)."
            )
        # FIX: ข้อความเดิม "0.5 ก้อน (จำนวน 1 ชิ้น)" ทำให้สับสนว่า "ก้อน" กับ "ชิ้น" เป็น
        # หน่วยเดียวกันหรือเปล่า — ตอนนี้แยกความหมายชัดเจน: "ชิ้น" = จำนวนโปรดักต์ที่จะผลิต,
        # "ก้อน" = ปริมาณวัตถุดิบโฟมที่ต้องใช้ ถ้าผลิตมากกว่า 1 ชิ้น จะโชว์ทั้งยอดรวมและ
        # ค่าเฉลี่ยต่อชิ้นให้เห็นที่มาของตัวเลขด้วย
        if production_qty > 1:
            st.info(
                f"คำแนะนำ: ผลิตชิ้นงาน {production_qty} ชิ้น ต้องใช้โฟมรวมประมาณ "
                f"{total_blocks:.1f} ก้อน (เฉลี่ย {per_piece_blocks:.1f} ก้อนต่อชิ้น)"
                if lang == "TH" else
                f"Recommendation: producing {production_qty} pcs needs approximately "
                f"{total_blocks:.1f} block(s) of foam in total (avg. {per_piece_blocks:.1f} block(s) per piece)"
            )
        else:
            st.info(
                f"คำแนะนำ: ผลิตชิ้นงาน 1 ชิ้น ต้องใช้โฟมประมาณ {total_blocks:.1f} ก้อน"
                if lang == "TH" else
                f"Recommendation: producing 1 pc needs approximately {total_blocks:.1f} block(s) of foam"
            )
    else:
        st.info(
            "อัปโหลดไฟล์ 3D ที่หน้าแรกก่อน เพื่อคำนวณจำนวนก้อนโฟม"
            if lang == "TH" else
            "Upload a 3D file on Page 1 first to calculate the number of foam blocks needed."
        )

    # ==========================================
    # 📦 ระบบเลือกรายการวัสดุจาก Master Data
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

        # FIX: แสดงผลแบบทีละแถวเพื่อใส่ปุ่มลบ (🗑️) ต่อแถว — เลือกวัสดุผิด 1 ตัวลบเฉพาะแถวนั้นได้
        mat_header_cols = st.columns([1.6, 2.2, 1.0, 1.2, 1.2, 0.6])
        for col, label in zip(
            mat_header_cols,
            ["Category / หมวดหมู่", "Material / ชื่อวัสดุ", "Qty / จำนวน", "Unit Price / ราคา", "Total / ราคารวม", ""]
        ):
            col.markdown(f"**{label}**")

        mat_to_delete = None
        for i, item in enumerate(st.session_state["selected_materials"]):
            row_cols = st.columns([1.6, 2.2, 1.0, 1.2, 1.2, 0.6])
            row_cols[0].write(item["cat"])
            row_cols[1].write(item["name"])
            row_cols[2].write(f"{item['qty']:,.2f}")
            row_cols[3].write(f"{item['unit_price']:,.2f}")
            row_cols[4].write(f"{item['total_price']:,.2f}")
            if row_cols[5].button("🗑️", key=f"del_mat_{i}", help="ลบแถวนี้" if lang == "TH" else "Delete this row"):
                mat_to_delete = i

        if mat_to_delete is not None:
            st.session_state["selected_materials"].pop(mat_to_delete)
            st.rerun()

        col_clear, col_stat = st.columns([1, 3])
        with col_clear:
            if st.button(t["clear_mat_btn"]):
                st.session_state["selected_materials"] = []
                st.rerun()

    # ==========================================
    # 🎨 Hard Coat: งานเคลือบผิว / โมล / Work / งานสี
    # ==========================================
    st.markdown("---")
    st.markdown(f"##### {t['finishing_title']}")

    HARDCOAT_CATEGORIES = {
        "TH": ["🧪 กระบวนการเคลือบผิว (Coating)", "🗿 งานทำโมล (Mold)", "🛠️ งาน Work (แรงงานขึ้นรูป)", "🎨 งานสี (Color / Surface Finish)"],
        "EN": ["🧪 Coating Process", "🗿 Mold", "🛠️ Work (Labor)", "🎨 Color / Surface Finish"],
    }[lang]

    with st.expander(t["finish_expander"], expanded=True):
        hc_cat = st.radio("—", HARDCOAT_CATEGORIES, horizontal=True, key="hc_cat", label_visibility="collapsed")

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

        elif hc_cat == HARDCOAT_CATEGORIES[2]:
            c1, c2, c3, c4 = st.columns([2, 1.3, 1.3, 1])
            with c1:
                hc_item = st.selectbox("Work", list(WORK_RATES.keys()), key="hc_item_work", label_visibility="collapsed")
            hc_info = WORK_RATES[hc_item]
            with c2:
                hc_rate = st.number_input(
                    f"{t['finish_rate'] if hc_info['billing']=='sq.m.' else ('อัตรา (฿/งาน)' if lang=='TH' else 'Rate (฿/job)')}",
                    min_value=0.0, value=float(hc_info["rate"]), step=10.0, key=f"hc_rate_work_input_{hc_item}"
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
                if complexity_level not in COMPLEXITY_HOURS_DB:
                    st.warning(
                        f"⚠️ ไม่มีข้อมูลชั่วโมงสำหรับ Level {complexity_level} ในชีท "
                        "ComplexityHours — กรุณาเพิ่มแถวสำหรับ level นี้"
                        if lang == "TH" else
                        f"⚠️ No hour data for Level {complexity_level} in the "
                        "ComplexityHours sheet — please add a row for this level."
                    )
                st.caption(
                    ("ชั่วโมงแนะนำตาม Level ปัจจุบัน (" if lang == "TH" else "Suggested hours for current Level (")
                    + f"{complexity_level}):"
                )
                st.write(
                    f"- Hard Coat: `{HARD_COAT_HOURS.get(complexity_level, '-')}` Hr. | "
                    f"Sanding: `{SANDING_HOURS.get(complexity_level, '-')}` Hr. | "
                    f"Painting: `{PAINTING_HOURS.get(complexity_level, '-')}` Hr."
                )
                if LABOR_RATES:
                    st.write(
                        ("อัตราแรงงาน/วัน: " if lang == "TH" else "Daily labor rate: ")
                        + " | ".join([f"{k} ฿{v:,.0f}" for k, v in LABOR_RATES.items()])
                    )
                else:
                    st.caption(
                        "⚠️ ไม่มีข้อมูลใน LaborRates sheet" if lang == "TH"
                        else "⚠️ No data in LaborRates sheet"
                    )

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

        # FIX: แสดงผลแบบทีละแถวเพื่อใส่ปุ่มลบ (🗑️) ต่อแถว — เลือกงานเคลือบผิวผิด 1 รายการ
        # ลบเฉพาะแถวนั้นได้ ไม่ต้องกด "ล้างทั้งหมด" แล้วเลือกใหม่ทุกรายการ
        cost_col_label = "Total Cost (internal)" if lang == "EN" else "ต้นทุนภายใน (฿)"
        finish_header_cols = st.columns([2.4, 1.1, 1.1, 1.2, 1.3, 0.6])
        for col, label in zip(
            finish_header_cols,
            [t["finish_col_type"], t["finish_col_rate"], t["finish_col_area"], t["finish_col_total"], cost_col_label, ""]
        ):
            col.markdown(f"**{label}**")

        finish_to_delete = None
        for i, item in enumerate(st.session_state["selected_finishes"]):
            row_cols = st.columns([2.4, 1.1, 1.1, 1.2, 1.3, 0.6])
            row_cols[0].write(item["type"])
            row_cols[1].write(f"{item['rate']:,.2f}")
            row_cols[2].write(f"{item['area']:,.4f}")
            row_cols[3].write(f"{item['total']:,.2f}")
            row_cols[4].write("—" if item.get("total_cost") is None else f"{item['total_cost']:,.2f}")
            if row_cols[5].button("🗑️", key=f"del_finish_{i}", help="ลบแถวนี้" if lang == "TH" else "Delete this row"):
                finish_to_delete = i

        if finish_to_delete is not None:
            st.session_state["selected_finishes"].pop(finish_to_delete)
            st.rerun()

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
