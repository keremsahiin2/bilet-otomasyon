import os
import requests
import pandas as pd
import io
import json
import gspread
import math
from google.oauth2.service_account import Credentials
from collections import defaultdict
from datetime import datetime

print("🚀 Script başladı")

# =====================
# ENV
# =====================
BUBILET_TOKEN = os.getenv("BUBILET_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

print("ENV kontrolü:")
print("BUBILET_TOKEN var mı?", bool(BUBILET_TOKEN))
print("SHEET_ID var mı?", bool(SHEET_ID))
print("GOOGLE_JSON var mı?", bool(GOOGLE_JSON))

if not all([BUBILET_TOKEN, SHEET_ID, GOOGLE_JSON]):
    raise Exception("❌ ENV eksik")

# =====================
# GOOGLE SHEETS
# =====================
creds_dict = json.loads(GOOGLE_JSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SHEET_ID)

def ws(name):
    try:
        return spreadsheet.worksheet(name)
    except:
        return spreadsheet.add_worksheet(title=name, rows=2000, cols=30)

ws_ham = ws("HAM_VERI")
ws_ham2 = ws("HAM_VERI_2")

def write_df(ws, df):
    ws.clear()
    if df.empty:
        ws.update([["BOS"]])
        return
    df = df.replace([math.inf, -math.inf], "").fillna("")
    ws.update([df.columns.tolist()] + df.values.tolist())

# =====================
# 1️⃣ BUBILET → HAM_VERI
# =====================
print("📥 Bubilet Excel indiriliyor")

url = "https://panelapi.bubilet.com.tr/api/reports/company/2677/sales?FileName=Rapor"
headers = {
    "Authorization": BUBILET_TOKEN,  # Bearer TOKEN
    "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
}

response = requests.get(url, headers=headers)

if response.status_code != 200:
    raise Exception(f"❌ Bubilet download failed: {response.status_code}")

print("✅ Bubilet Excel indirildi")

ham_df = pd.read_excel(io.BytesIO(response.content))

# 🔥 EN SON SÜTUNA EXCEL İNDİRME SAATİ
indirme_saati = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
son_index = len(ham_df.columns)
ham_df.insert(son_index, "Excel_Indirme_Saati", indirme_saati)

ham_df["KAYNAK"] = "BUBILET"

write_df(ws_ham, ham_df)

print(f"🕒 Excel indirme saati yazıldı: {indirme_saati}")

# =====================
# 2️⃣ HAM_VERI_2
# =====================
if ws_ham2.get_all_values() == []:
    ws_ham2.update([["2. PLATFORM BEKLENIYOR"]])

print("✅ HAM_VERI yazıldı")

# =====================
# 3️⃣ PANEL → MAIL FORMAT
# =====================
ws_panel = spreadsheet.worksheet("PANEL")
rows = ws_panel.get_all_records()

GUN_MAP = {
    0: "Pazartesi",
    1: "Salı",
    2: "Çarşamba",
    3: "Perşembe",
    4: "Cuma",
    5: "Cumartesi",
    6: "Pazar"
}

seanslar = defaultdict(lambda: defaultdict(int))

for r in rows:
    tarih = str(r.get("Tarih", "")).strip()
    saat = str(r.get("Saat", "")).strip()
    etkinlik = str(r.get("Etkinlik", "")).strip()
    satis = r.get("Toplam Satış", 0)

    if not tarih or not saat or not etkinlik:
        continue
    if not isinstance(satis, (int, float)) or satis == 0:
        continue

    key = f"{tarih} {saat}"
    seanslar[key][etkinlik] += int(satis)

# =====================
# MAIL BODY
# =====================
mail_body = "Merhaba,\n\nGüncel seans bazlı satış raporu:\n\n"

for key in sorted(seanslar.keys()):
    dt = datetime.strptime(key, "%d.%m.%Y %H:%M")
    gun = GUN_MAP[dt.weekday()]
    baslik = f"{dt.strftime('%d.%m.%Y')} {gun} {dt.strftime('%H:%M')}"

    mail_body += f"{baslik} seansı\n"

    for etkinlik, adet in seanslar[key].items():
        mail_body += f"- {adet} {etkinlik}\n"

    mail_body += "\n"

mail_body += "İyi çalışmalar."

print("\n📧 MAIL METNİ:\n")
print(mail_body)

print("\n🎉 Script başarıyla tamamlandı")
