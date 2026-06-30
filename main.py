import telebot
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
import json
import time
import os
import threading
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ⚙️ KONFIGURASI UTAMA
TOKEN_BOT = os.getenv("TOKEN_BOT")
TUJUAN_EMAIL = "support@support.whatsapp.com"
FILE_DATA = "akun_gmail.json"
FILE_BANDING = "data_banding.json"
MAKSIMAL_GMAIL = 15
BATAS_WAKTU_BALAS = 120  # 2 Menit = Gagal jika tidak ada balasan
JEDA_CEK = 1  # Cek setiap 1 detik

# 🔐 DATA AKSES
SANDI_UTAMA = "Amelia"
USERNAME_PEMILIK = "Sepcyboy"
KONTAK_ADMIN = "@Sepcyboy"

# 🖼️ BRANDING
FOTO_URL = "https://raw.githubusercontent.com/Sumarti1/bot_bandingwa/main/1782676789784.png"

# 🌐 PENGATURAN KONEKSI
from telebot import apihelper
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"
apihelper.CONNECT_TIMEOUT = 30
apihelper.READ_TIMEOUT = 40
apihelper.SESSION = requests.Session()
apihelper.SESSION.trust_env = False

bot = telebot.TeleBot(TOKEN_BOT)
proses = {}
pengguna_terizin = set()
balasan_diperiksa = set()
indeks_gmail = 0

# -------------------- FUNGSI KIRIM PESAN --------------------
def kirim_pesan(chat_id, teks, tombol=None):
    try:
        bot.send_photo(
            chat_id=chat_id,
            photo=FOTO_URL,
            caption=teks,
            reply_markup=tombol,
            parse_mode="Markdown"
        )
    except:
        try:
            bot.send_message(chat_id, teks, reply_markup=tombol, parse_mode="Markdown")
        except:
            pass

# -------------------- FUNGSI PENUNJANG DATA --------------------
def baca_akun():
    try:
        with open(FILE_DATA, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def simpan_akun(data):
    try:
        with open(FILE_DATA, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def baca_banding():
    try:
        with open(FILE_BANDING, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def simpan_banding(data):
    try:
        with open(FILE_BANDING, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def cek_nomor(nomor):
    bersih = nomor.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "")
    if bersih.startswith("+") and bersih[1:].isdigit() and len(bersih) >= 8:
        return bersih
    return None

# -------------------- KIRIM EMAIL DENGAN LAPORAN PROSES --------------------
def kirim_email(pengirim, sandi, tujuan, isi, subjek):
    log = []
    log.append("🔄 Memulai proses koneksi ke server Gmail...")
    try:
        # Coba dua port sekaligus
        for port in [587, 465]:
            try:
                if port == 587:
                    server = smtplib.SMTP("smtp.gmail.com", port, timeout=25)
                    server.ehlo()
                    log.append(f"✅ Terhubung ke port {port}")
                    server.starttls()
                    log.append("✅ Enkripsi aktif")
                else:
                    server = smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=25)
                    server.ehlo()
                    log.append(f"✅ Terhubung ke port {port}")

                server.login(pengirim, sandi)
                log.append("✅ Berhasil masuk ke akun Gmail")

                pesan = MIMEText(isi)
                pesan["From"] = pengirim
                pesan["To"] = tujuan
                pesan["Subject"] = subjek

                server.sendmail(pengirim, tujuan, pesan.as_string())
                log.append("✅ Pesan berhasil dikirim")
                server.quit()
                return True, "\n".join(log)

            except Exception as e:
                log.append(f"⚠️ Gagal di port {port}: {str(e)[:50]}")
                continue

        log.append("❌ Semua cara koneksi gagal")
        return False, "\n".join(log)

    except Exception as e:
        log.append(f"❌ Kesalahan umum: {str(e)[:50]}")
        return False, "\n".join(log)

# -------------------- CEK BALASAN --------------------
def cek_email_balasan(email, sandi):
    try:
        koneksi = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=15)
        koneksi.login(email, sandi)
        koneksi.select("INBOX", readonly=True)
        status, hasil = koneksi.search(None, '(FROM "support@support.whatsapp.com" UNSEEN)')
        pesan = []
        if status == "OK":
            pesan = hasil[0].split()
        koneksi.logout()
        return pesan
    except:
        return []

# -------------------- MENU UTAMA --------------------
def menu_utama():
    tombol = InlineKeyboardMarkup(row_width=1)
    tombol.add(
        InlineKeyboardButton("➕ TAMBAH AKUN GMAIL", callback_data="tambah"),
        InlineKeyboardButton("📤 KIRIM BANDING", callback_data="kirim"),
        InlineKeyboardButton("📋 DAFTAR GMAIL", callback_data="daftar")
    )
    return tombol

def cek_akses(user_id, username):
    if username and username.lower() == USERNAME_PEMILIK.lower():
        return True
    if user_id in pengguna_terizin:
        return True
    return False

# -------------------- PEMANTAUAN OTOMATIS --------------------
def pantau_balasan():
    while True:
        akun = baca_akun()
        daftar_banding = baca_banding()
        waktu_sekarang = time.time()

        for gmail_data in akun:
            daftar_pesan = cek_email_balasan(gmail_data["email"], gmail_data["sandi"])
            for id_pesan in daftar_pesan:
                if id_pesan in balasan_diperiksa:
                    continue
                balasan_diperiksa.add(id_pesan)

                for idx, banding in enumerate(daftar_banding):
                    if banding["email"] == gmail_data["email"] and banding["status"] == "TERKIRIM":
                        daftar_banding[idx]["status"] = "✅ BERHASIL DIBALAS"
                        teks = f"""
✅ **BANDING BERHASIL**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{banding['nomor']}`
📊 Status: ✅ ADA BALASAN

💡 Silakan coba masuk atau verifikasi akun
                        """
                        for uid in list(pengguna_terizin):
                            kirim_pesan(uid, teks)
                        break

        # Cek batas waktu 2 menit
        diperbarui = False
        for idx, banding in enumerate(daftar_banding):
            if banding["status"] == "TERKIRIM" and (waktu_sekarang - banding["waktu_kirim"]) > BATAS_WAKTU_BALAS:
                daftar_banding[idx]["status"] = "❌ GAGAL / BELUM ADA BALASAN"
                teks = f"""
❌ **STATUS BANDING**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{banding['nomor']}`
⏱️ Waktu: 2 Menit
📊 Status: ❌ GAGAL / BELUM ADA BALASAN

💡 Bisa kirim ulang atau ganti email
                """
                for uid in list(pengguna_terizin):
                    kirim_pesan(uid, teks)
                diperbarui = True

        if diperbarui:
            simpan_banding(daftar_banding)

        time.sleep(JEDA_CEK)

# -------------------- PERINTAH AWAL --------------------
@bot.message_handler(commands=['start'])
def tampil_awal(pesan):
    id_pengguna = pesan.chat.id
    if cek_akses(id_pengguna, pesan.from_user.username or ""):
        teks = """
🤖 **BOT BANDING WHATSAPP PREMIUM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👑 ASEP KANJUT PREMIUM
⚡ Cek Balasan: Setiap 1 Detik
⏱️ Batas Waktu: 2 Menit
🔄 Sistem Otomatis Berputar
🌐 Support Semua Negara

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👇 Silakan Pilih Menu Layanan:
        """
        kirim_pesan(id_pengguna, teks, menu_utama())
    else:
        kirim_pesan(id_pengguna, """
🔒 **AKSES TERBATAS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
Masukkan kode akses untuk lanjut
        """)
        proses[id_pengguna] = {"langkah": "minta_kode"}

@bot.message_handler(func=lambda m: m.chat.id in proses and proses[m.chat.id].get("langkah") == "minta_kode")
def verifikasi_kode(pesan):
    id_pengguna = pesan.chat.id
    if pesan.text.strip() == SANDI_UTAMA:
        pengguna_terizin.add(id_pengguna)
        kirim_pesan(id_pengguna, """
✅ **VERIFIKASI BERHASIL**
━━━━━━━━━━━━━━━━━━━━━━━━━━
Selamat datang! Silakan gunakan fitur
        """, menu_utama())
    else:
        kirim_pesan(id_pengguna, f"""
❌ **KODE SALAH**
━━━━━━━━━━━━━━━━━━━━━━━━━━
Hubungi: {KONTAK_ADMIN}
        """)
    del proses[id_pengguna]

# -------------------- TOMBOL MENU --------------------
@bot.callback_query_handler(func=lambda panggilan: True)
def proses_tombol(panggilan):
    id_pengguna = panggilan.message.chat.id
    if not cek_akses(id_pengguna, panggilan.from_user.username or ""):
        bot.answer_callback_query(panggilan.id, "❌ Tidak punya akses")
        return
    try:
        bot.answer_callback_query(panggilan.id, "✅ Diproses...")
        if panggilan.data == "tambah":
            if len(baca_akun()) >= MAKSIMAL_GMAIL:
                kirim_pesan(id_pengguna, "⚠️ Maksimal 15 akun Gmail")
                return
            proses[id_pengguna] = {"langkah": "input_email"}
            kirim_pesan(id_pengguna, "📩 Masukkan alamat Gmail:\nContoh: anda@gmail.com")
        elif panggilan.data == "daftar":
            daftar = baca_akun()
            if not daftar:
                teks = "📋 Belum ada akun Gmail terdaftar"
            else:
                teks = "📋 DAFTAR GMAIL TERDAFTAR:\n" + "\n".join(f"• `{a['email']}`" for a in daftar)
            kirim_pesan(id_pengguna, teks, menu_utama())
        elif panggilan.data == "kirim":
            if not baca_akun():
                kirim_pesan(id_pengguna, "⚠️ Tambah Gmail terlebih dahulu")
                return
            proses[id_pengguna] = {"langkah": "input_nomor"}
            kirim_pesan(id_pengguna, "📱 Masukkan nomor diawali tanda +:\nContoh: +628123456789")
    except:
        pass

# -------------------- PROSES INPUT & KIRIM --------------------
@bot.message_handler(func=lambda m: m.chat.id in proses)
def terima_input(pesan):
    global indeks_gmail
    id_pengguna = pesan.chat.id
    if not cek_akses(id_pengguna, pesan.from_user.username or ""):
        del proses[id_pengguna]
        return
    data = proses[id_pengguna]

    if data.get("langkah") == "input_email":
        data["email"] = pesan.text.strip()
        data["langkah"] = "input_sandi"
        kirim_pesan(id_pengguna, """
🔑 **MASUKKAN SANDI APLIKASI**
━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Verifikasi 2 Langkah WAJIB AKTIF
✅ Sandi Aplikasi 16 digit TANPA SPASI
✅ Bukan sandi biasa masuk Gmail
        """)

    elif data.get("langkah") == "input_sandi":
        akun = baca_akun()
        akun.append({"email": data["email"], "sandi": pesan.text.strip()})
        simpan_akun(akun)
        kirim_pesan(id_pengguna, f"""
✅ **BERHASIL DITAMBAHKAN**
━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email: `{data['email']}`
🔐 Siap digunakan untuk kirim banding
        """, menu_utama())
        del proses[id_pengguna]

    elif data.get("langkah") == "input_nomor":
        nomor = cek_nomor(pesan.text)
        if not nomor:
            kirim_pesan(id_pengguna, "❌ Format salah! Harus diawali + dan angka saja")
            return

        daftar_akun = baca_akun()
        gmail_pakai = daftar_akun[indeks_gmail]
        indeks_gmail = (indeks_gmail + 1) % len(daftar_akun)

        # Proses kirim + tampilkan log
        kirim_ok, log_proses = kirim_email(
            pengirim=gmail_pakai["email"],
            sandi=gmail_pakai["sandi"],
            tujuan=TUJUAN_EMAIL,
            isi=nomor,
            subjek="Permohonan Banding Akun WhatsApp"
        )

        if kirim_ok:
            daftar_banding = baca_banding()
            daftar_banding.append({
                "nomor": nomor,
                "email": gmail_pakai["email"],
                "status": "TERKIRIM",
                "waktu_kirim": time.time()
            })
            simpan_banding(daftar_banding)
            teks = f"""
✅ **BERHASIL DIKIRIM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{nomor}`
📧 Lewat: `{gmail_pakai['email']}`
⏱️ Cek Balasan: Setiap 1 Detik
⌛ Batas Waktu: 2 Menit

📋 **Proses Kirim:**
{log_proses}
            """
            kirim_pesan(id_pengguna, teks, menu_utama())
        else:
            teks = f"""
❌ **GAGAL DIKIRIM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{nomor}`
📧 Lewat: `{gmail_pakai['email']}`

📋 **Proses & Kesalahan:**
{log_proses}

💡 **Solusi:**
• Pastikan Verifikasi 2 Langkah sudah AKTIF
• Pakai Sandi Aplikasi 16 digit tanpa spasi
• Cek apakah Gmail mengizinkan akses
            """
            kirim_pesan(id_pengguna, teks, menu_utama())
        del proses[id_pengguna]

# -------------------- JALANKAN BOT --------------------
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 BOT AKTIF | Cek Setiap 1 Detik | Log Lengkap")
    print("=" * 50)
    threading.Thread(target=pantau_balasan, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(none_stop=True, interval=1, timeout=20)
        except:
            time.sleep(2)
