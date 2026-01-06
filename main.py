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
        return spreadsheet.add_worksheet(title=name, rows=1000, cols=30)

ws_ham = ws("HAM_VERI")
ws_ham2 = ws("HAM_VERI_2")
ws_duzgun = ws("DUZGUN_VERI")

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
# 2️⃣ HAM_VERI_2 (ŞİMDİLİK BOŞ)
# =====================
if ws_ham2.get_all_values() == []:
    ws_ham2.update([["2. PLATFORM BEKLENIYOR"]])

# =====================
# 3️⃣ HAM → DUZGUN_VERI
# =====================
def safe_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return 0.0

def normalize(df, platform):
    rename = {}
    for c in df.columns:
        l = c.lower()
        if "tarih" in l:
            rename[c] = "Tarih"
        elif "etkinlik" in l:
            rename[c] = "Etkinlik"
        elif "bilet" in l or "adet" in l:
            rename[c] = "Satilan_Bilet"
        elif "ciro" in l or "tutar" in l:
            rename[c] = "Ciro"

    df = df.rename(columns=rename)

    for col in ["Tarih", "Etkinlik", "Satilan_Bilet", "Ciro"]:
        if col not in df:
            df[col] = ""

    df["Platform"] = platform
    df["Satilan_Bilet"] = df["Satilan_Bilet"].apply(safe_float)
    df["Ciro"] = df["Ciro"].apply(safe_float)

    return df[["Tarih", "Etkinlik", "Platform", "Satilan_Bilet", "Ciro"]]

duzgun_df = normalize(ham_df, "BUBILET")
write_df(ws_duzgun, duzgun_df)

print("🎉 HAM_VERI → DUZGUN_VERI tamamlandı")
