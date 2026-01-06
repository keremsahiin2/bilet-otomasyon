/**
 * ⏱️ Time-driven trigger ile çalışır (5 dk)
 * GitHub run başarılıysa (PANEL!Z2 değiştiyse)
 * SADECE 1 KEZ mail gönderir
 */
function githubRunKontrolVeMail() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) {
    Logger.log("⏳ Kilit alınamadı, çıkılıyor");
    return;
  }

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName("PANEL");

    const flag = sheet.getRange("Z2").getValue();   // GitHub run timestamp
    const lastSent = sheet.getRange("Z3").getValue(); // Mail kilidi

    // Flag yoksa çık
    if (!flag) {
      Logger.log("🚫 Z2 boş, çıkıldı");
      return;
    }

    // Aynı run için mail zaten atıldıysa çık
    if (flag === lastSent) {
      Logger.log("⏭️ Bu run için mail zaten gönderilmiş");
      return;
    }

    // 📧 Mail gönder
    const mailGonderildi = gunlukSeansMailiGonder();

    // ❗ SADECE mail başarıyla gittiyse kilitle
    if (mailGonderildi === true) {
      sheet.getRange("Z3").setValue(flag);
      Logger.log("✅ Mail gönderildi ve kilitlendi");
    } else {
      Logger.log("⚠️ Mail gönderilemedi, kilitlenmedi");
    }

  } catch (err) {
    Logger.log("❌ HATA: " + err);
  } finally {
    lock.releaseLock();
  }
}

/**
 * 📧 Seans bazlı satış maili
 * @returns {boolean} mail gönderildiyse true
 */
function gunlukSeansMailiGonder() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName("PANEL");
    const data = sheet.getDataRange().getValues();

    const tz = ss.getSpreadsheetTimeZone();
    const gunler = ["Pazar","Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi"];

    let seanslar = {};

    for (let i = 1; i < data.length; i++) {
      const tarih = data[i][0]; // Tarih
      const saat = data[i][1];  // Saat
      const etkinlik = data[i][2];
      const satis = data[i][3];

      if (!tarih || !saat || !etkinlik || !satis || satis == 0) continue;

      const dt = new Date(tarih);
      const gun = gunler[dt.getDay()];
      const tarihStr = Utilities.formatDate(dt, tz, "dd.MM.yyyy");
      const saatStr = Utilities.formatDate(new Date(saat), tz, "HH:mm");

      const key = `${tarihStr} ${gun} ${saatStr}`;

      if (!seanslar[key]) seanslar[key] = {};
      seanslar[key][etkinlik] = (seanslar[key][etkinlik] || 0) + Number(satis);
    }

    if (Object.keys(seanslar).length === 0) {
      Logger.log("📭 Gönderilecek seans yok");
      return false;
    }

    let body = "Merhaba,\n\nGüncel seans bazlı satış raporu:\n\n";

    Object.keys(seanslar).sort().forEach(seans => {
      body += `${seans} seansı\n`;
      Object.keys(seanslar[seans]).forEach(etkinlik => {
        body += `- ${seanslar[seans][etkinlik]} ${etkinlik}\n`;
      });
      body += "\n";
    });

    body += "İyi çalışmalar.";

    // 📧 ALICILAR
    const alicilar = [
      "biletkontrolssa@gmail.com"
      // "ikinci@mail.com",
      // "ucuncu@mail.com"
    ];

    MailApp.sendEmail({
      to: alicilar.join(","),
      subject: "Günlük Seans Bazlı Satış Raporu",
      body: body
    });

    Logger.log("📧 Mail başarıyla gönderildi");
    return true;

  } catch (err) {
    Logger.log("❌ Mail gönderim hatası: " + err);
    return false;
  }
}
