import os
import json
import time
import math
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =====================
# ENV KONTROL
# =====================
REQUIRED_ENVS = ["GOOGLE_SERVICE_ACCOUNT_JSON", "SHEET_ID"]
missing = [k for k in REQUIRED_ENVS if not os.getenv(k)]
if missing:
    raise Exception(f"❌ ENV eksik: {missing}")

# =====================
# GOOGLE SHEETS BAĞLANTI
# =====================
creds_dict = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(creds)

spreadsheet = gc.open_by_key(os.environ["SHEET_ID"])

def get_or_create_ws(title):
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=1000, cols=30)

ws_ham_1 = get_or_create_ws("HAM_VERI")
ws_ham_2 = get_or_create_ws("HAM_VERI_2")
ws_duzgun = get_or_create_ws("DUZGUN_VERI")
ws_panel = get_or_create_ws("PANEL")

# =====================
# YARDIMCI FONKSİYONLAR
# =====================
def clear_and_write(ws, df: pd.DataFrame):
    ws.clear()
    if df.empty:
        ws.update([["BOS"]])
        return
    df = df.replace([math.inf, -math.inf], "")
    df = df.fillna("")
    ws.update([df.columns.tolist()] + df.values.tolist())

def safe_float(x):
    try:
        if x == "" or x is None:
            return 0.0
        return float(str(x).replace(",", "."))
    except:
        return 0.0

# =====================
# 1) BUBILET → HAM_VERI
# =====================
# NOT:
# Bubilet tarafında şu an HEADERS / COOKIE ile çalışan endpoint kullanıyorsun.
# Aşağıdaki örnek "Authorization" header'ı ENV'den beklemez.
# Playwright ile indirdiğin Excel/JSON'u burada request ile çektiğin senaryoya uygundur.

BUBILET_REPORT_URL = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"

# Eğer şu an request ile çekiyorsan ve header gerekiyorsa,
# GitHub Actions'ta secret olarak eklediğin değeri burada okuyabilirsin.
# Örn: BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
# headers = {"Authorization": f"Bearer {BUBILET_TOKEN}"}

def fetch_bubilet_ham():
    # ⚠️ Eğer 401 alırsan bu kısım TOKEN aşamasında güncellenecek
    resp = requests.get(BUBILET_REPORT_URL)
    if resp.status_code != 200:
        raise Exception(f"Bubilet download failed: {resp.status_code}")

    # Excel geliyorsa:
    content_type = resp.headers.get("Content-Type", "")
    if "spreadsheet" in content_type or resp.content[:4] == b"PK\x03\x04":
        df = pd.read_excel(pd.io.common.BytesIO(resp.content))
    else:
        # JSON gelirse
        df = pd.DataFrame(resp.json())

    df["KAYNAK"] = "BUBILET"
    return df

print("▶ Bubilet HAM veri çekiliyor")
ham1_df = fetch_bubilet_ham()
clear_and_write(ws_ham_1, ham1_df)

# =====================
# 2) HAM_VERI_2 (ŞİMDİLİK BOŞ)
# =====================
# İleride 2. site buraya yazılacak
if ws_ham_2.get_all_values():
    ham2_df = pd.DataFrame(ws_ham_2.get_all_records())
else:
    ham2_df = pd.DataFrame()

# =====================
# 3) DUZGUN_VERI (BİRLEŞTİR + TEMİZLE)
# =====================
def normalize_ham(df: pd.DataFrame, platform_name: str):
    if df.empty:
        return df

    # Kolon adlarını normalize et (örnek)
    col_map = {}
    for c in df.columns:
        lc = c.lower()
        if "tarih" in lc or "date" in lc:
            col_map[c] = "Tarih"
        elif "etkinlik" in lc or "event" in lc:
            col_map[c] = "Etkinlik"
        elif "bilet" in lc or "adet" in lc:
            col_map[c] = "Satilan_Bilet"
        elif "ciro" in lc or "tutar" in lc or "amount" in lc:
            col_map[c] = "Ciro"

    df = df.rename(columns=col_map)

    for col in ["Tarih", "Etkinlik", "Satilan_Bilet", "Ciro"]:
        if col not in df.columns:
            df[col] = ""

    df["Platform"] = platform_name
    df["Satilan_Bilet"] = df["Satilan_Bilet"].apply(safe_float)
    df["Ciro"] = df["Ciro"].apply(safe_float)

    return df[["Tarih", "Etkinlik", "Platform", "Satilan_Bilet", "Ciro"]]

duzgun_1 = normalize_ham(ham1_df, "BUBILET")
duzgun_2 = normalize_ham(ham2_df, "PLATFORM_2")

duzgun_df = pd.concat([duzgun_1, duzgun_2], ignore_index=True)
clear_and_write(ws_duzgun, duzgun_df)

# =====================
# 4) PANEL (TOPLAM)
# =====================
if not duzgun_df.empty:
    panel_df = (
        duzgun_df
        .groupby(["Tarih", "Etkinlik"], as_index=False)
        .agg({
            "Satilan_Bilet": "sum",
            "Ciro": "sum"
        })
        .sort_values(["Tarih", "Etkinlik"])
)
else:
    panel_df = pd.DataFrame()

clear_and_write(ws_panel, panel_df)

print("✅ Sheets akışı tamamlandı")
