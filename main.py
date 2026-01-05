import os
import json
import requests
import pandas as pd
from io import BytesIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials

print("🚀 Script başladı")

# ===============================
# ENV KONTROL
# ===============================
BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

print("🔍 ENV kontrol:")
print("BUBILET_TOKEN var mı?", bool(BUBILET_TOKEN))
print("SHEET_ID var mı?", bool(SHEET_ID))
print("GOOGLE JSON var mı?", bool(GOOGLE_JSON))

if not BUBILET_TOKEN:
    raise Exception("BUBILET_TOKEN yok")

if not SHEET_ID:
    raise Exception("SHEET_ID yok")

if not GOOGLE_JSON:
    raise Exception("GOOGLE_SERVICE_ACCOUNT_JSON yok")

# ===============================
# BUBILET EXCEL İNDİR
# ===============================
url = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"

headers = {
    "Authorization": f"Bearer {BUBILET_TOKEN}",
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

print("⬇️ Bubilet Excel indiriliyor...")
response = requests.get(url, headers=headers)

if response.status_code != 200:
    raise Exception(f"Bubilet download failed: {response.status_code}")

df = pd.read_excel(BytesIO(response.content))
print(f"✅ Excel okundu: {len(df)} satır")

# ===============================
# GOOGLE SHEETS BAĞLAN
# ===============================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(GOOGLE_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open_by_key(SHEET_ID).sheet1
sheet.clear()
sheet.update([df.columns.values.tolist()] + df.values.tolist())

print("🎉 Google Sheets güncellendi")
