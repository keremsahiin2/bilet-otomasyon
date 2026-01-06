import os
import time
import json
import pandas as pd
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

EMAIL = os.getenv("BUBILET_EMAIL")
PASSWORD = os.getenv("BUBILET_PASSWORD")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not all([EMAIL, PASSWORD, SHEET_ID, GOOGLE_JSON]):
    raise Exception("ENV eksik")

print("▶ Script başladı")

# Google Sheets
creds_dict = json.loads(GOOGLE_JSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    print("▶ Bubilet login sayfası")
    page.goto("https://panel.bubilet.com.tr/", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)

    # 🔥 GÜNCEL SELECTOR STRATEJİSİ
    email_input = page.locator("input").nth(0)
    password_input = page.locator("input").nth(1)

    email_input.fill(EMAIL)
    password_input.fill(PASSWORD)

    page.locator("button").nth(0).click()

    page.wait_for_load_state("networkidle")
    time.sleep(5)

    print("▶ Satış raporuna gidiliyor")
    page.goto("https://panel.bubilet.com.tr/satis-rapor", wait_until="load")
    time.sleep(5)

    print("▶ Excel indiriliyor")
    with page.expect_download() as download_info:
        page.locator("text=Excel indir").click()

    download = download_info.value
    path = download.path()

    print("▶ Excel alındı:", path)

    df = pd.read_excel(path)

    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

    print("✅ Google Sheets güncellendi")

    browser.close()
