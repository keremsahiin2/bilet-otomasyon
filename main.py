import os
import json
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# =====================
# 1. ENV KONTROLLERİ
# =====================

BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not BUBILET_TOKEN:
    raise Exception("BUBILET_TOKEN yok")

if not SHEET_ID:
    raise Exception("SHEET_ID yok")

if not GOOGLE_JSON:
    raise Exception("GOOGLE_SERVICE_ACCOUNT_JSON yok")

print("✅ ENV değişkenleri OK")

# =====================
# 2. GOOGLE SHEETS BAĞLANTISI
# =====================

creds_dict = json.loads(GOOGLE_JSON)

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)

spreadsheet = gc.open_by_key(SHEET_ID)
worksheet = spreadsheet.sheet1

print("✅ Google Sheets bağlantısı OK")

# =====================
# 3. BUBILET EXCEL İNDİR
# =====================

url = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"

headers = {
    "Authorization": f"Bearer {BUBILET_TOKEN}",
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

response = requests.get(url, headers=headers)

if response.status_code != 200:
    raise Exception(f"Bubilet API hata verdi: {response.status_code}")

print("✅ Bubilet Excel indirildi")

# =====================
# 4. EXCEL OKU
# =====================

excel_bytes = BytesIO(response.content)
df = pd.read_excel(excel_bytes)

if df.empty:
    raise Exception("Excel boş geldi")

print(f"✅ Excel okundu ({len(df)} satır)")

# =====================
# 5. GOOGLE SHEETS'E YAZ
# =====================

worksheet.clear()
worksheet.update(
    [df.columns.tolist()] + df.fillna("").values.tolist()
)

print("🚀 Google Sheets güncellendi")