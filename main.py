import os
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

print("▶ Script başladı")

TOKEN = os.getenv("BUBILET_AUTH_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not all([TOKEN, SHEET_ID, GOOGLE_JSON]):
    raise Exception("ENV eksik")

print("▶ ENV tamam")

url = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

response = requests.get(url, headers=headers)

if response.status_code != 200:
    raise Exception(f"Bubilet download failed: {response.status_code}")

print("▶ Excel indirildi")

df = pd.read_excel(BytesIO(response.content))

creds = Credentials.from_service_account_info(
    eval(GOOGLE_JSON),
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1

sheet.clear()
sheet.update([df.columns.tolist()] + df.values.tolist())

print("✅ Google Sheets güncellendi")
