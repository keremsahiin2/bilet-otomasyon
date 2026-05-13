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
BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
SHEET_ID      = os.getenv("SHEET_ID")
GOOGLE_JSON   = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

if not all([BUBILET_TOKEN, SHEET_ID, GOOGLE_JSON]):
    raise Exception("❌ ENV eksik: BUBILET_TOKEN, SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON gerekli")
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
# 1️⃣ BUBILET → HAM_VERI
# =====================
print("📥 Bubilet Excel indiriliyor...")

URL = "https://oldpanel.api.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"

token = BUBILET_TOKEN.strip()
if not token.lower().startswith("bearer "):
    token = f"Bearer {token}"

headers = {
    "authorization": token,
    "accept": "application/json",
    "accept-language": "tr,en-US;q=0.9,en;q=0.8",
    "cache-control": "no-cache",
    "content-type": "application/json; charset=utf-8",
    "origin": "https://panel.bubilet.com.tr",
    "pragma": "no-cache",
    "referer": "https://panel.bubilet.com.tr/",
    "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Opera";v="130"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 OPR/130.0.0.0",
}

response = None
for attempt in range(1, 4):
    try:
        print(f"🔄 Deneme {attempt}/3...")
        response = requests.get(URL, headers=headers, timeout=30)
        print(f"   HTTP {response.status_code}")
        if response.status_code == 200:
            print("✅ Rapor indirildi")
            break
        elif response.status_code in (429, 503):
            time.sleep(attempt * 5)
        else:
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
# 2️⃣ Excel indirme saati
# =====================
indirme_saati = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
ham_df.insert(len(ham_df.columns), "Excel_Indirme_Saati", indirme_saati)
ham_df["KAYNAK"] = "BUBILET"
write_df(ws_ham, ham_df)
print(f"🕒 Excel indirme saati yazıldı: {indirme_saati}")

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
        print("📡 Apps Script tetikleniyor")
        r = requests.post(APPS_SCRIPT_URL, timeout=10)
        print("📨 Apps Script response:", r.text)
    except Exception as e:
        print("⚠️ Apps Script çağrı hatası:", e)

print("\n🎉 Script BAŞARIYLA tamamlandı")
