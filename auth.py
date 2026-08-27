"""
auth.py
========
ระบบ login แบบง่าย ไม่ต้องติดตั้งไลบรารีเสริม (ใช้ hashlib มาตรฐานของ Python เท่านั้น)
ใช้ PBKDF2-HMAC-SHA256 + salt เฉพาะคน ในการเก็บรหัสผ่าน (ไม่เก็บ plain text เลย)

วิธีตั้งค่า:
-----------
1. ข้อมูล username/password (แบบ hash แล้ว) ต้องอยู่ใน Streamlit Secrets
   ภายใต้ [credentials] — ดูตัวอย่างในไฟล์ secrets_credentials_snippet.toml
   ที่แนบมาด้วย ก็อปเนื้อหานั้นไปวางต่อท้าย secrets เดิมที่มี [sheet_api] อยู่แล้ว
   (อย่าลบของเดิม แค่เพิ่มต่อท้าย)

2. ใน app.py เพิ่มบรรทัดนี้ไว้บนสุดของไฟล์ (ก่อนโค้ดส่วนอื่นทั้งหมด):

       import auth
       auth.require_login()

   ฟังก์ชันนี้จะแสดงฟอร์ม login และ "หยุดการทำงานของสคริปต์" (st.stop())
   ถ้ายังไม่ได้ล็อกอิน ทำให้เนื้อหาด้านล่างไม่ถูกแสดงเลยจนกว่าจะล็อกอินสำเร็จ

3. (ทางเลือก) อยากมีปุ่ม logout ในแถบข้าง เรียก auth.render_logout_button()
   ที่ไหนก็ได้ในโค้ด เช่น ในส่วน sidebar

เพิ่มผู้ใช้ใหม่ทีหลัง:
---------------------
รันไฟล์ generate_credentials.py (แก้ USERNAMES ในไฟล์นั้นก่อน) จะได้ hash ใหม่
มาเพิ่มต่อท้ายใน [credentials] ของ Secrets ได้เลย ไม่ต้องแก้โค้ดไฟล์นี้
"""

import hashlib
import time
import streamlit as st


def _hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return dk.hex()


def _check_credentials(username: str, password: str) -> bool:
    creds = st.secrets.get("credentials", {})
    user_data = creds.get(username)
    if user_data is None:
        return False
    expected_hash = user_data["hash"]
    salt_hex = user_data["salt"]
    return _hash_password(password, salt_hex) == expected_hash


def require_login():
    """
    เรียกฟังก์ชันนี้บนสุดของ app.py ก่อนโค้ดส่วนอื่นทั้งหมด
    ถ้ายังไม่ล็อกอิน จะแสดงฟอร์ม login แล้วหยุดสคริปต์ทันที (st.stop())
    """
    if st.session_state.get("authenticated", False):
        return  # ล็อกอินอยู่แล้ว ปล่อยให้โค้ดส่วนที่เหลือทำงานต่อ

    st.markdown("## 🔒 เข้าสู่ระบบ / Login")

    # จำกัดจำนวนครั้งที่กรอกผิดติดกัน กันการเดารหัสแบบ brute-force ง่ายๆ
    fail_count = st.session_state.get("login_fail_count", 0)
    last_fail_time = st.session_state.get("login_last_fail_time", 0)
    if fail_count >= 5 and (time.time() - last_fail_time) < 60:
        st.error("กรอกรหัสผิดหลายครั้งเกินไป กรุณารอ 60 วินาทีแล้วลองใหม่")
        st.stop()

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("เข้าสู่ระบบ")

    if submitted:
        if _check_credentials(username.strip(), password):
            st.session_state["authenticated"] = True
            st.session_state["username"] = username.strip()
            st.session_state["login_fail_count"] = 0
            st.rerun()
        else:
            st.session_state["login_fail_count"] = fail_count + 1
            st.session_state["login_last_fail_time"] = time.time()
            st.error("Username หรือ Password ไม่ถูกต้อง")

    st.stop()  # ห้ามให้โค้ดส่วนที่เหลือของ app.py ทำงานจนกว่าจะล็อกอินสำเร็จ


def render_logout_button():
    """เรียกที่ไหนก็ได้ (เช่นใน sidebar) เพื่อแสดงปุ่ม logout"""
    username = st.session_state.get("username", "")
    if username:
        st.caption(f"เข้าสู่ระบบในชื่อ: **{username}**")
    if st.button("ออกจากระบบ / Logout"):
        st.session_state["authenticated"] = False
        st.session_state.pop("username", None)
        st.rerun()
