import os
import requests
import pandas as pd
import io
import json
import gspread
import math
from google.oauth2.service_account import Credentials

print("🚀 Script başladı")

# =====================
# ENV
# =====================
BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

print("ENV kontrolü:")
print("BUBILET_TOKEN var mı?", bool(BUBILET_TOKEN))
print("SHEET_ID var mı?", bool(SHEET_ID))
print("GOOGLE_JSON var mı?", bool(GOOGLE_JSON))

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

print("✅ Bubilet Excel indirildi")

ham_df = pd.read_excel(io.BytesIO(response.content))
ham_df["KAYNAK"] = "BUBILET"

write_df(ws_ham, ham_df)

# =====================
# 2️⃣ HAM_VERI_2 (İLERİDE 2. PLATFORM)
# =====================
if ws_ham2.get_all_values() == []:
    ws_ham2.update([["2. PLATFORM BEKLENIYOR"]])

print("🎉 Sadece HAM_VERI yazıldı. DUZGUN_VERI ve PANEL Sheets tarafından yönetiliyor.")
