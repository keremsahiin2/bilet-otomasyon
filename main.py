import os
import json
import time
import math
import pandas as pd
import gspread

from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

# =====================
# ENV KONTROL
# =====================
REQUIRED_ENVS = ["GOOGLE_SERVICE_ACCOUNT_JSON", "SHEET_ID"]
missing = [k for k in REQUIRED_ENVS if not os.getenv(k)]
if missing:
    raise Exception(f"❌ ENV eksik: {missing}")

# =====================
# GOOGLE SHEETS
# =====================
creds_dict = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key(os.environ["SHEET_ID"])

def ws(name):
    try:
        return spreadsheet.worksheet(name)
    except:
        return spreadsheet.add_worksheet(title=name, rows=1000, cols=30)

ws_ham = ws("HAM_VERI")
ws_ham2 = ws("HAM_VERI_2")
ws_duzgun = ws("DUZGUN_VERI")
ws_panel = ws("PANEL")

def write_df(ws, df):
    ws.clear()
    if df.empty:
        ws.update([["BOS"]])
        return
    df = df.replace([math.inf, -math.inf], "").fillna("")
    ws.update([df.columns.tolist()] + df.values.tolist())

def safe_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return 0.0

# =====================
# 1️⃣ BUBILET → HAM_VERI (PLAYWRIGHT)
# =====================
print("▶ Bubilet login + Excel indiriliyor")

with sync_playwright() as p:
    bro
