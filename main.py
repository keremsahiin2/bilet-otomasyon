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

def write_df(ws, df):
    ws.clear()
    if df.empty:
        ws.update([["BOS"]])
        return
    df = df.replace([math.inf, -math.inf], "").fillna("")
    ws.update([df.columns.tolist()] + df.values.tolist())

# =====================
# BUBILET SESSION
# =====================
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

session = requests.Session()
session.headers.update(BASE_HEADERS)

# =====================
# 1️⃣ LOGIN
# =====================
print("🔐 Bubilet'e giriş yapılıyor...")

LOGIN_URL = "https://panelapi.bubilet.com.tr/api/auth/login"

login_payload = {
    "email": BUBILET_EMAIL,
    "password": BUBILET_PASSWORD,
}

login_headers = {
    **BASE_HEADERS,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://panel.bubilet.com.tr",
    "Referer": "https://panel.bubilet.com.tr/",
}

for attempt in range(1, 4):
    try:
        print(f"🔄 Login deneme {attempt}/3...")
        login_resp = session.post(LOGIN_URL, json=login_payload, headers=login_headers, timeout=30)
        print(f"   HTTP {login_resp.status_code}")
        if login_resp.status_code == 200:
            break
        time.sleep(attempt * 3)
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Bağlantı hatası: {e}")
        if attempt < 3:
            time.sleep(attempt * 3)
else:
    raise Exception(f"❌ Login başarısız: {login_resp.status_code} → {login_resp.text[:300]}")

# Token'ı response'dan al
try:
    token_data = login_resp.json()
    token = token_data.get("token") or token_data.get("access_token") or token_data.get("data", {}).get("token")
    if not token:
        raise Exception(f"❌ Token bulunamadı. Response: {login_resp.text[:300]}")
    print("✅ Login başarılı, token alındı")
except Exception as e:
    raise Exception(f"❌ Login response parse hatası: {e} | Raw: {login_resp.text[:300]}")

# =====================
# 2️⃣ RAPOR İNDİR
# =====================
print("📥 Bubilet Excel indiriliyor...")

REPORT_URL = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"

report_headers = {
    **BASE_HEADERS,
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "Origin": "https://panel.bubilet.com.tr",
    "Referer": "https://panel.bubilet.com.tr/",
}

response = None
for attempt in range(1, 4):
    try:
        print(f"🔄 Rapor indirme deneme {attempt}/3...")
        response = session.get(REPORT_URL, headers=report_headers, timeout=30)
        print(f"   HTTP {response.status_code}")
        if response.status_code == 200:
            print("✅ Rapor indirildi")
            break
        elif response.status_code in (429, 503):
            wait = attempt * 5
            print(f"⚠️ Rate limit, {wait}s bekleniyor...")
            time.sleep(wait)
        else:
            print(f"❌ Hata: {response.status_code}")
            time.sleep(attempt * 3)
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Bağlantı hatası: {e}")
        if attempt < 3:
            time.sleep(attempt * 3)

if response is None or response.status_code != 200:
    status = response.status_code if response else "N/A"
    body = response.text[:300] if response else "Yanıt yok"
    raise Exception(f"❌ Rapor indirilemedi: {status} → {body}")

ham_df = pd.read_excel(io.BytesIO(response.content))

# =====================
# 3️⃣ Excel indirme saati
# =====================
indirme_saati = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
ham_df.insert(len(ham_df.columns), "Excel_Indirme_Saati", indirme_saati)
ham_df["KAYNAK"] = "BUBILET"
write_df(ws_ham, ham_df)
print(f"🕒 Excel indirme saati yazıldı: {indirme_saati}")

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
        print("📡 Apps Script tetikleniyor")
        r = requests.post(APPS_SCRIPT_URL, timeout=10)
        print("📨 Apps Script response:", r.text)
    except Exception as e:
        print("⚠️ Apps Script çağrı hatası:", e)

print("\n🎉 Script BAŞARIYLA tamamlandı")
