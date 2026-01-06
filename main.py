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
BILETINAL_TOKEN = os.getenv("BILETINAL_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

print("BUBILET_TOKEN:", bool(BUBILET_TOKEN))
print("BILETINAL_TOKEN:", bool(BILETINAL_TOKEN))
print("SHEET_ID:", bool(SHEET_ID))
print("GOOGLE_JSON:", bool(GOOGLE_JSON))

if not all([BUBILET_TOKEN, BILETINAL_TOKEN, SHEET_ID, GOOGLE_JSON]):
    raise Exception("❌ ENV eksik")

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
        return spreadsheet.add_worksheet(title=name, rows=3000, cols=40)

ws_ham = ws("HAM_VERI")
ws_ham2 = ws("HAM_VERI_2")
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
print("📥 Bubilet Excel indiriliyor")

bubilet_url = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"
bubilet_headers = {
    "Authorization": BUBILET_TOKEN,
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

resp = requests.get(bubilet_url, headers=bubilet_headers, timeout=30)
if resp.status_code != 200:
    raise Exception(f"❌ Bubilet download failed: {resp.status_code}")

ham_df = pd.read_excel(io.BytesIO(resp.content))
ham_df["Excel_Indirme_Saati"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
ham_df["KAYNAK"] = "BUBILET"

write_df(ws_ham, ham_df)
print("✅ Bubilet HAM_VERI yazıldı")

# =====================
# 2️⃣ BİLETİNİAL → HAM_VERI_2 (BROWSER TAKLİTLİ)
# =====================
print("📡 Biletinial API çağrılıyor")

BILETINIAL_URL = "https://reportapi2.biletinial.com/api/Report/GetActiveEventDetailList"

biletinal_headers = {
    "Authorization": f"Bearer {BILETINAL_TOKEN}",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Origin": "https://partner.biletinial.com",
    "Referer": "https://partner.biletinial.com/",
}

params = {
    "FirstDate": datetime.now().strftime("%a, %d %b %Y 00:00:00 GMT"),
    "LastDate": datetime.now().strftime("%a, %d %b %Y 23:59:59 GMT"),
    "lang": "tr"
}

resp = requests.get(
    BILETINIAL_URL,
    headers=biletinal_headers,
    params=params,
    timeout=30
)

print("🔎 Biletinial status:", resp.status_code)
print("🔎 Biletinial response (ilk 500):", resp.text[:500])

if resp.status_code != 200:
    raise Exception("❌ Biletinial API hata verdi")

json_data = resp.json()
data = json_data.get("Data", [])

rows = []
for item in data:
    rows.append({
        "EventName": item.get("EventName"),
        "SeanceDate": item.get("SeanceDate"),
        "City": item.get("CityName"),
        "Venue": item.get("CinemaBranchName"),
        "SoldToday": item.get("SalesTicketTotalCount"),
        "TotalAmount": item.get("TotalAmount"),
        "Currency": item.get("Currency"),
        "WebLink": item.get("WebLink"),
        "KAYNAK": "BILETINAL"
    })

df_biletinal = pd.DataFrame(rows)
write_df(ws_ham2, df_biletinal)

print(f"✅ Biletinial HAM_VERI_2 yazıldı ({len(df_biletinal)} kayıt)")

# =====================
# 3️⃣ RUN FLAG
# =====================
run_id = f"RUN_{int(time.time() * 1000)}"
ws_panel.update("Z2", [[run_id]])
print(f"🚩 RUN FLAG yazıldı → {run_id}")

# =====================
# 4️⃣ APPS SCRIPT
# =====================
if APPS_SCRIPT_URL:
    try:
        print("📡 Apps Script tetikleniyor")
        requests.post(APPS_SCRIPT_URL, timeout=10)
    except Exception as e:
        print("⚠️ Apps Script hata:", e)

print("\n🎉 TÜM SÜREÇ BAŞARIYLA TAMAMLANDI")
