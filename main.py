import os
import json
import time
import pandas as pd
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

EMAIL = os.getenv("BUBILET_EMAIL")
PASSWORD = os.getenv("BUBILET_PASSWORD")
SHEET_ID = os.getenv("SHEET_ID")
GJSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not EMAIL or not PASSWORD:
    raise Exception("BUBILET_EMAIL / BUBILET_PASSWORD yok")

if not SHEET_ID or not GJSON:
    raise Exception("Google Sheet env eksik")

# ---- Google Sheets ----
creds_dict = json.loads(GJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(creds)
sh = gc.open_by_key(SHEET_ID)
ws = sh.sheet1

download_path = "/tmp/bubilet.xlsx"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    # 1) Login
    page.goto("https://partner.bubilet.com/")
    page.fill('input[name="email"]', EMAIL)
    page.fill('input[name="password"]', PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    # 2) Rapor sayfası
    page.goto("https://partner.bubilet.com/reports/sales")

    # 3) Excel indir
    with page.expect_download() as d:
        page.click("text=Excel")
    download = d.value
    download.save_as(download_path)

    browser.close()

# ---- Excel → Sheet ----
df = pd.read_excel(download_path)
ws.clear()
ws.update([df.columns.values.tolist()] + df.values.tolist())

print("✅ Rapor başarıyla Sheet'e yazıldı")
