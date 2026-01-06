import os
import requests
import pandas as pd
import io
import json
import gspread
import math
from google.oauth2.service_account import Credentials
from collections import defaultdict
from datetime import datetime

print("🚀 Script başladı")

# =====================
# ENV
# =====================
BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not all([BUBILET_TOKEN, SHEET_ID, GOOGLE_JSON]):
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
        return spreadsheet.add_worksheet(title=name, rows=2000, cols=30)

ws_ham = ws("HAM_VERI")
ws_ham2 = ws("HAM_VERI_2")
ws_panel = spreadsheet.worksheet("PANEL")

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

url = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"
headers = {
    "Authorization": BUBILET_TOKEN,
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

response = requests.get(url, headers=headers)
if response.status_code != 200:
    raise Exception(f"❌ Bubilet download failed: {response.status_code}")

ham_df = pd.read_excel(io.BytesIO(response.content))

# Excel indirme zamanı (EN SON SÜTUN)
indirme_saati = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
ham_df.insert(len(ham_df.columns), "Excel_Indirme_Saati", indirme_saati)
ham_df["KAYNAK"] = "BUBILET"

write_df(ws_ham, ham_df)
print(f"🕒 Excel indirme saati yazıldı: {indirme_saati}")

# =====================
# 2️⃣ HAM_VERI_2
# =====================
if ws_ham2.get_all_values() == []:
    ws_ham2.update([["2. PLATFORM BEKLENIYOR"]])

# =====================
# 3️⃣ PANEL OKUMA (🔥 SAFE MODE)
# =====================
print("📊 PANEL verileri okunuyor")

values = ws_panel.get_all_values()
headers = values[0]
rows = values[1:]

# sütun indexleri
IDX_TARIH = headers.index("Tarih")
IDX_SAAT = headers.index("Saat")
IDX_ETKINLIK = headers.index("Etkinlik")
IDX_SATIS = headers.index("Toplam Satış")

seanslar = defaultdict(lambda: defaultdict(int))

for r in rows:
    try:
        tarih = str(r[IDX_TARIH]).strip()
        saat = str(r[IDX_SAAT]).strip()
        etkinlik = str(r[IDX_ETKINLIK]).strip()
        satis = r[IDX_SATIS]

        if not tarih or not saat or not etkinlik:
            continue
        if not isinstance(satis, (int, float)) or satis == 0:
            continue

        key = f"{tarih} {saat}"
        seanslar[key][etkinlik] += int(satis)

    except Exception:
        continue

print("✅ PANEL verileri okundu")

# =====================
# 4️⃣ GITHUB RUN FLAG (APPS SCRIPT TETİK)
# =====================
flag_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
ws_panel.update("Z2", flag_time)

print(f"🚩 FLAG yazıldı → PANEL!Z2 = {flag_time}")
print("🎉 Script başarıyla tamamlandı")
