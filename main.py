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
APPS_SCRIPT_URL  = os.getenv("APPS_SCRIPT_URL")

if not all([BUBILET_EMAIL, BUBILET_PASSWORD, SHEET_ID, GOOGLE_JSON]):
    raise Exception("❌ ENV eksik: BUBILET_EMAIL, BUBILET_PASSWORD, SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON gerekli")
print("✅ ENV OK")

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
# 1️⃣ BUBILET LOGIN → TOKEN AL
# =====================
print("🔐 Bubilet'e giriş yapılıyor...")

session = requests.Session()

login_url = "https://oldpanel.api.bubilet.com.tr/token"
login_payload = {
    "username": BUBILET_EMAIL,
    "password": BUBILET_PASSWORD
}
login_headers = {
    "Content-Type": "application/json; charset=UTF-8",
    "Accept": "application/json",
    "Accept-Language": "tr,en-US;q=0.9,en;q=0.8",
    "Origin": "https://panel.bubilet.com.tr",
    "Referer": "https://panel.bubilet.com.tr/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 OPR/130.0.0.0",
    "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Opera";v="130"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site"
}

login_resp = session.post(login_url, json=login_payload, headers=login_headers, timeout=30)

if login_resp.status_code != 200:
    raise Exception(f"❌ Login başarısız: {login_resp.status_code} → {login_resp.text[:300]}")

login_data = login_resp.json()
print(f"✅ Login response: {json.dumps(login_data)[:200]}")

token = (
    login_data.get("token") or
    login_data.get("accessToken") or
    login_data.get("access_token") or
    login_data.get("data", {}).get("token") or
    login_data.get("Token") or
    login_data.get("bearer")
)

if not token:
    raise Exception(f"❌ Token alınamadı. Login response: {json.dumps(login_data)[:300]}")

BUBILET_TOKEN = f"Bearer {token}"
print("✅ Token alındı")

# =====================
# 2️⃣ BUBILET → HAM_VERI
# =====================
print("📥 Bubilet Excel indiriliyor...")

url = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"
session.headers.update({
    "Authorization": BUBILET_TOKEN,
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "Origin": "https://panel.bubilet.com.tr",
    "Referer": "https://panel.bubilet.com.tr/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 OPR/130.0.0.0"
})

response = session.get(url, timeout=30)

if response.status_code != 200:
    raise Exception(f"❌ Bubilet Excel indirme başarısız: {response.status_code} → {response.text[:200]}")

ham_df = pd.read_excel(io.BytesIO(response.content))
print(f"✅ Excel indirildi: {len(ham_df)} satır")

# =====================
# 3️⃣ Excel indirme saati
# =====================
indirme_saati = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
ham_df.insert(len(ham_df.columns), "Excel_Indirme_Saati", indirme_saati)
ham_df["KAYNAK"] = "BUBILET"
write_df(ws_ham, ham_df)
print(f"🕒 HAM_VERI yazıldı: {indirme_saati}")

# =====================
# 4️⃣ HAM_VERI_2 (şimdilik boş)
# =====================
if ws_ham2.get_all_values() == []:
    ws_ham2.update([["2. PLATFORM BEKLENIYOR"]])

# =====================
# 5️⃣ GITHUB RUN FLAG
# =====================
run_id = f"RUN_{int(time.time() * 1000)}"
ws_panel.update("Z2", [[run_id]])
print(f"🚩 RUN FLAG yazıldı → PANEL!Z2 = {run_id}")

# =====================
# 6️⃣ APPS SCRIPT TETİKLE (opsiyonel)
# =====================
if APPS_SCRIPT_URL:
    try:
        print("📡 Apps Script tetikleniyor...")
        r = session.post(APPS_SCRIPT_URL, timeout=10)
        print("📨 Apps Script response:", r.text)
    except Exception as e:
        print("⚠️ Apps Script çağrı hatası:", e)

print("\n🎉 Script BAŞARIYLA tamamlandı")
