import os
import json
import requests
import pandas as pd
import numpy as np
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

print("🚀 Script başladı")

# =========================
# ENV KONTROL
# =========================
BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
SHEET_ID = os.getenv("SHEET_ID")

print("🔎 ENV kontrol:")
print("BUBILET_TOKEN var mı?", bool(BUBILET_TOKEN))
print("GOOGLE_SERVICE_ACCOUNT_JSON var mı?", bool(GOOGLE_JSON))
print("SHEET_ID var mı?", bool(SHEET_ID))

if not all([BUBILET_TOKEN, GOOGLE_JSON, SHEET_ID]):
    raise Exception("❌ ENV eksik")

# =========================
# BUBILET EXCEL İNDİR
# =========================
print("⬇️ Bubilet Excel indiriliyor...")

url = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales"
params = {"FileName": "Rapor"}

headers = {
    "Authorization": BUBILET_TOKEN,
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers, params=params)

if response.status_code != 200:
    raise Exception(f"❌ Bubilet download failed: {response.status_code}")

print("✅ Excel indirildi")

# =========================
# EXCEL → DATAFRAME
# =========================
df = pd.read_excel(BytesIO(response.content))

print("📊 Excel okundu")
print("Satır:", len(df), "Sütun:", len(df.columns))

# =========================
# DATA TEMİZLE (ÇOK KRİTİK)
# =========================
df = df.replace([np.inf, -np.inf], "")
df = df.fillna("")

# =========================
# GOOGLE SHEETS BAĞLAN
# =========================
print("📤 Google Sheets bağlanıyor...")

creds_dict = json.loads(GOOGLE_JSON)

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)

gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1

# =========================
# SHEET’E YAZ
# =========================
sheet.clear()
sheet.update([df.columns.tolist()] + df.values.tolist())

print("🎉 Google Sheets başarıyla güncellendi")
