print("GitHub + Codespaces çalışıyor")
import os
import requests
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO

# --------------------
# ENV
# --------------------
BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not BUBILET_TOKEN:
    raise Exception("BUBILET_TOKEN yok")
if not SHEET_ID:
    raise Exception("SHEET_ID yok")
if not GOOGLE_JSON:
    raise Exception("GOOGLE_SERVICE_ACCOUNT_JSON yok")

# --------------------
# GOOGLE SHEETS
# --------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    json.loads(GOOGLE_JSON),
    scope
)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1  # ilk tab

# --------------------
# BUBILET EXCEL
# --------------------
URL = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"

headers = {
    "Authorization": BUBILET_TOKEN,
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

response = requests.get(URL, headers=headers)
response.raise_for_status()

df = pd.read_excel(BytesIO(response.content))
df["platform"] = "bubilet"

# --------------------
# SHEET'E YAZ
# --------------------
sheet.clear()
sheet.update([df.columns.tolist()] + df.values.tolist())

print("✅ Bubilet Excel alındı ve Google Sheets'e yazıldı")
