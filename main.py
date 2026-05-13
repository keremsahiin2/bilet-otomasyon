import os
import requests
import pandas as pd
import io
import json
import gspread
import math
import time
from google.oauth2.service_account import Credentials
from datetime import datetime

print("🚀 Script başladı")

# =====================
# ENV
# =====================
BUBILET_EMAIL    = os.getenv("BUBILET_EMAIL")
BUBILET_PASSWORD = os.getenv("BUBILET_PASSWORD")
SHEET_ID         = os.getenv("SHEET_ID")
GOOGLE_JSON      = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
APPS_SCRIPT_URL  = os.getenv("APPS_SCRIPT_URL")  # opsiyonel

if not all([BUBILET_EMAIL, BUBILET_PASSWORD, SHEET_ID, GOOGLE_JSON]):
    raise Exception("❌ ENV eksik: BUBILET_EMAIL, BUBILET_PASSWORD, SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON gerekli")

print("✅ ENV OK")

# =====================
# 🔐 BUBİLET LOGIN → TOKEN
# =====================
print("🔐 Bubilet'e login olunuyor...")

login_response = requests.post(
    "https://panelapi.bubilet.com.tr/api/auth/login",
    json={"email": BUBILET_EMAIL, "password": BUBILET_PASSWORD},
    timeout=15
)

if login_response.status_code != 200:
    raise Exception(f"❌ Bubilet login başarısız: {login_response.status_code} → {login_response.text}")

login_data = login_response.json()
access_token = login_data.get("access_token")
token_type   = login_data.get("token_type", "bearer").capitalize()  # "bearer" → "Bearer"

if not access_token:
    raise Exception("❌ access_token alınamadı")

BUBILET_TOKEN = f"{token_type} {access_token}"
print(f"✅ Token alındı (token_type: {token_type})")

# =====================
# GOOGLE SHEETS
# =====================
creds_dict = json.loads(GOOGLE_JSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SHEET_ID)

def ws(name):
    try:
        return spreadsheet.worksheet(name)
    except:
        return spreadsheet.add_worksheet(title=name, rows=2000, cols=30)

ws_ham   = ws("HAM_VERI")
ws_ham2  = ws("HAM_VERI_2")
ws_panel = ws("PANEL")

def write_df(sheet, df):
    sheet.clear()
    if df.empty:
        sheet.update([["BOS"]])
        return
    df = df.replace([math.inf, -math.inf], "").fillna("")
    sheet.update([df.columns.tolist()] + df.values.tolist())

# =====================
# 1️⃣ BUBILET → HAM_VERI
# =====================
print("📥 Bubilet Excel indiriliyor...")

url = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"
headers = {
    "Authorization": BUBILET_TOKEN,
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

response = requests.get(url, headers=headers, timeout=30)

if response.status_code != 200:
    raise Exception(f"❌ Bubilet Excel indirme başarısız: {response.status_code} → {response.text[:200]}")

ham_df = pd.read_excel(io.BytesIO(response.content))
print(f"✅ Excel indirildi: {len(ham_df)} satır")

# =====================
# 2️⃣ Excel indirme saati
# =====================
indirme_saati = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
ham_df.insert(len(ham_df.columns), "Excel_Indirme_Saati", indirme_saati)
ham_df["KAYNAK"] = "BUBILET"

write_df(ws_ham, ham_df)
print(f"🕒 HAM_VERI yazıldı: {indirme_saati}")

# =====================
# 3️⃣ HAM_VERI_2 (şimdilik boş)
# =====================
if ws_ham2.get_all_values() == []:
    ws_ham2.update([["2. PLATFORM BEKLENIYOR"]])

# =====================
# 4️⃣ GITHUB RUN FLAG
# =====================
run_id = f"RUN_{int(time.time() * 1000)}"
ws_panel.update("Z2", [[run_id]])
print(f"🚩 RUN FLAG yazıldı → PANEL!Z2 = {run_id}")

# =====================
# 5️⃣ APPS SCRIPT TETİKLE (opsiyonel)
# =====================
if APPS_SCRIPT_URL:
    try:
        print("📡 Apps Script tetikleniyor...")
        r = requests.post(APPS_SCRIPT_URL, timeout=10)
        print("📨 Apps Script response:", r.text)
    except Exception as e:
        print("⚠️ Apps Script çağrı hatası:", e)

print("\n🎉 Script BAŞARIYLA tamamlandı")
