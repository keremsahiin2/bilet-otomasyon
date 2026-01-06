import os
import json
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not all([BUBILET_TOKEN, SHEET_ID, GOOGLE_JSON]):
    raise Exception("ENV eksik")

print("▶ ENV tamam")

# 🔽 Bubilet Excel URL
URL = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"

headers = {
    "Authorization": f"Bearer {BUBILET_TOKEN}",
    "Accept": "application/json"
}

print("▶ Bubilet Excel indiriliyor")
resp = requests.get(URL, headers=headers)

if resp.status_code != 200:
    raise Exception(f"Bubilet Excel download failed: {resp.status_code}")

with open("rapor.xlsx", "wb") as f:
    f.write(resp.content)

print("✅ Excel indirildi")

# Google Sheets bağlantısı
creds_dict = json.loads(GOOGLE_JSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1

df = pd.read_excel("rapor.xlsx")

sheet.clear()
sheet.update([df.columns.values.tolist()] + df.values.tolist())

print("✅ Google Sheets güncellendi")
