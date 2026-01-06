import os
import requests
import pandas as pd
import io
import json
import gspread
from google.oauth2.service_account import Credentials

print("🚀 Script başladı")

# === ENV ===
BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

print("ENV kontrolü:")
print("BUBILET_TOKEN var mı?", bool(BUBILET_TOKEN))
print("SHEET_ID var mı?", bool(SHEET_ID))
print("GOOGLE_JSON var mı?", bool(GOOGLE_JSON))

if not all([BUBILET_TOKEN, SHEET_ID, GOOGLE_JSON]):
    raise Exception("❌ ENV eksik")

# === 1️⃣ Bubilet Excel indir ===
url = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"

headers = {
    "Authorization": BUBILET_TOKEN,
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

response = requests.get(url, headers=headers)

if response.status_code != 200:
    raise Exception(f"❌ Bubilet download failed: {response.status_code}")

print("✅ Bubilet Excel indirildi")

df = pd.read_excel(io.BytesIO(response.content))

# NaN / inf temizle (Google Sheets JSON hatası için)
df = df.replace([float("inf"), float("-inf")], "")
df = df.fillna("")

# === 2️⃣ Google Sheets bağlan ===
creds_dict = json.loads(GOOGLE_JSON)

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open_by_key(SHEET_ID).sheet1
sheet.clear()

sheet.update([df.columns.tolist()] + df.values.tolist())

print("🎉 Google Sheets güncellendi")
