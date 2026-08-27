"""
data_loader.py
================
โหลดข้อมูล Material Master Data จาก Google Sheet แทนการฝังใน app.py โดยตรง
เหตุผล: ป้องกันไม่ให้ราคา/ต้นทุนซึ่งเป็นข้อมูลธุรกิจอ่อนไหว หลุดไปกับซอร์สโค้ด
ถ้า repo ถูกเปิด public โดยไม่ตั้งใจ (หรือ collaborator fork ออกไป)

วิธีนี้ใช้ Google Apps Script เป็น JSON API endpoint แทนการเชื่อมผ่าน
Google Cloud Console + Service Account (เผื่อกรณีไม่มีบัตรเดบิต/เครดิตที่ใช้ยืนยันตัวตนกับ
Google Cloud ได้ — Apps Script ไม่ต้องผ่าน billing setup เลย)

*** ใช้ POST เท่านั้น (ไม่ใช้ GET) — token ส่งใน request body ไม่ใช่ query string ***
เพื่อไม่ให้ token มีโอกาสไปโผล่ใน browser history / proxy log / server access log

วิธีตั้งค่า (ทำครั้งเดียว):
---------------------------
1. เปิด Google Sheet ข้อมูลวัสดุ > เมนู Extensions > Apps Script
2. ลบโค้ด default (function myFunction(){}) ออกให้หมด
3. วางโค้ดทั้งหมดจากไฟล์ Code.gs (ที่แนบมาด้วย) แทนที่
4. ไปที่ไอคอนเฟือง "Project Settings" (แถบซ้าย) > เลื่อนลงหา "Script Properties"
   กด "Add script property" ตั้งชื่อ property ว่า  API_SECRET
   ค่า (value) ตั้งเป็นรหัสลับที่คาดเดายาก เช่น สุ่มด้วยเว็บ https://www.uuidgenerator.net/
   *** ห้ามใช้คำง่ายๆ เดาได้ เพราะรหัสนี้คือสิ่งเดียวที่กันคนนอกไม่ให้เข้าถึงราคา ***
5. กลับไปแท็บ Editor กด "Deploy" (มุมขวาบน) > "New deployment"
   - Select type: เลือก "Web app"
   - Execute as: Me (บัญชีของคุณ)
   - Who has access: Anyone
   กด "Deploy" ระบบจะขอ Authorize สิทธิ์ (เพราะเป็นสคริปต์ของคุณเอง กด Allow ได้เลย)
   จะได้ "Web app URL" หน้าตาแบบ https://script.google.com/macros/s/xxxxx/exec
6. เก็บค่าไว้ใน Streamlit secrets (ไม่ใช่ในโค้ด):

   [sheet_api]
   url = "https://script.google.com/macros/s/xxxxx/exec"
   token = "รหัสลับเดียวกับที่ตั้งไว้ใน API_SECRET ขั้นตอนที่ 4"

   ถ้ารันในเครื่อง (local dev): สร้างไฟล์ .streamlit/secrets.toml ด้วยเนื้อหาเดียวกัน
   แล้วเพิ่ม ".streamlit/secrets.toml" ลงใน .gitignore ทันที ก่อน commit ใดๆ

ทดสอบ endpoint ด้วย curl (ไม่ใช่เปิด URL ตรงๆ ในเบราว์เซอร์ เพราะเบราว์เซอร์ส่งแบบ GET
ซึ่ง endpoint นี้ปิดรับ GET ไว้แล้ว):

    curl -X POST "https://script.google.com/macros/s/xxxxx/exec" \\
         -H "Content-Type: application/json" \\
         -d "{\\"token\\": \\"รหัสลับของคุณ\\"}"

ติดตั้ง dependency เพิ่ม (แค่ requests พอ):
    pip install requests
"""

import requests
import streamlit as st

MATERIALS_SHEET_NAME = "Materials"
STRUCTURE_SHEET_NAME = "Structure"
COAT_PROCESS_SHEET_NAME = "CoatProcess"
MOLD_SHEET_NAME = "Mold"
WORK_SHEET_NAME = "Work"
COLOR_FINISH_SHEET_NAME = "ColorFinish"
MACHINE_SHEET_NAME = "MachineRates"


@st.cache_data(ttl=300, show_spinner="กำลังโหลดข้อมูลราคาล่าสุด...")
def _fetch_all_sheets() -> dict:
    """
    เรียก Apps Script Web App ด้วย POST หนึ่งครั้ง ได้ข้อมูลทุก tab กลับมาพร้อมกันเป็น JSON เดียว
    token ส่งใน request body (ไม่ใช่ query string) เพื่อไม่ให้หลุดผ่าน log
    cache ไว้ 300 วินาที (5 นาที) — กด "Clear cache" ใน Streamlit menu เพื่อบังคับโหลดใหม่ทันที
    """
    url = st.secrets["sheet_api"]["url"]
    token = st.secrets["sheet_api"]["token"]
    resp = requests.post(url, json={"token": token}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(
            f"Sheet API ปฏิเสธคำขอ: {data['error']} — เช็คว่า token ใน Streamlit secrets "
            f"ตรงกับ API_SECRET ใน Apps Script Script Properties หรือไม่"
        )
    return data


def _get_sheet_rows(sheet_name: str) -> list:
    all_data = _fetch_all_sheets()
    return all_data.get(sheet_name, [])


def _to_float(value, default=0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_nested_category_db(sheet_name: str) -> dict:
    """
    ตัวช่วยทั่วไปสำหรับโหลด sheet ที่มีโครงสร้างซ้อนหมวดหมู่แบบ
    category / item_name / price / cost — ใช้ได้กับทั้ง Materials และ Structure
    """
    rows = _get_sheet_rows(sheet_name)
    db: dict = {}
    for row in rows:
        category = str(row.get("category", "")).strip()
        item_name = str(row.get("item_name", "")).strip()
        if not category or not item_name:
            continue
        db.setdefault(category, {})[item_name] = {
            "price": _to_float(row.get("price")),
            "cost": _to_float(row.get("cost")),
        }
    return db


def load_material_master_db() -> dict:
    return load_nested_category_db(MATERIALS_SHEET_NAME)


def load_structure_db() -> dict:
    return load_nested_category_db(STRUCTURE_SHEET_NAME)


def load_rate_dict(sheet_name: str, key_col: str, value_col: str) -> dict:
    rows = _get_sheet_rows(sheet_name)
    result = {}
    for row in rows:
        key = str(row.get(key_col, "")).strip()
        if not key:
            continue
        result[key] = _to_float(row.get(value_col))
    return result


def load_mold_rates() -> dict:
    return load_rate_dict(MOLD_SHEET_NAME, "mold_type", "rate")


def load_color_finish_db() -> dict:
    rows = _get_sheet_rows(COLOR_FINISH_SHEET_NAME)
    result = {}
    for row in rows:
        name = str(row.get("finish_name", "")).strip()
        if not name:
            continue
        result[name] = {
            "price": _to_float(row.get("price")),
            "cost": _to_float(row.get("cost")),
        }
    return result


def load_machine_rates():
    rows = _get_sheet_rows(MACHINE_SHEET_NAME)
    machine_types = {}
    machine_default_rates = {}
    for row in rows:
        name = str(row.get("machine_name", "")).strip()
        if not name:
            continue
        machine_types[name] = str(row.get("billing_unit", "")).strip()
        machine_default_rates[name] = _to_float(row.get("default_rate"))
    return machine_types, machine_default_rates


def load_work_rates() -> dict:
    rows = _get_sheet_rows(WORK_SHEET_NAME)
    result = {}
    for row in rows:
        name = str(row.get("work_name", "")).strip()
        if not name:
            continue
        result[name] = {
            "rate": _to_float(row.get("rate")),
            "billing": str(row.get("billing_unit", "")).strip(),
        }
    return result


def check_for_duplicate_items(db: dict) -> list:
    warnings = []
    for category, items in db.items():
        seen = set()
        for name in items:
            if name in seen:
                warnings.append(f"พบชื่อวัสดุซ้ำ: '{name}' ในหมวด '{category}'")
            seen.add(name)
    return warnings
