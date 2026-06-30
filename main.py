import telebot
import smtplib
import imaplib
import email
import json
import time
import os
import threading
import requests
from email.mime.text import MIMEText
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import InputFile

# ⚙️ KONFIGURASI UTAMA
TOKEN_BOT = os.getenv("TOKEN_BOT")
TUJUAN_EMAIL = "support@support.whatsapp.com"
FILE_DATA = "akun_gmail.json"
FILE_BANDING = "data_banding.json"
MAKSIMAL_GMAIL = 15
BATAS_WAKTU_BALAS = 120  # 2 Menit

# 🔐 DATA AKSES
SANDI_UTAMA = "Amelia"
USERNAME_PEMILIK = "Sepcyboy"
KONTAK_ADMIN = "@Sepcyboy"

# 🖼️ BRANDING
FOTO_PATH = "1782676789784.png"

# 🌐 PENGATURAN KONEKSI STABIL
from telebot import apihelper
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"
apihelper.CONNECT_TIMEOUT = 25
apihelper.READ_TIMEOUT = 35
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
        if os.path.exists(FOTO_PATH):
            foto = InputFile(FOTO_PATH)
            bot.send_photo(
                chat_id,
                foto,
                caption=teks,
                reply_markup=tombol,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            bot.send_message(
                chat_id,
                teks,
                reply_markup=tombol,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
    except Exception as e:
        print(f"[SISTEM] Info: {e}")
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

# -------------------- SISTEM PEMANTAUAN --------------------
def pantau_balasan():
    while True:
        akun = baca_akun()
        daftar_banding = baca_banding()
        waktu_sekarang = time.time()

        for gmail_data in akun:
            try:
                koneksi = imaplib.IMAP4_SSL("imap.gmail.com")
                koneksi.login(gmail_data["email"], gmail_data["sandi"])
                koneksi.select("INBOX")

                status, hasil = koneksi.search(None, '(FROM "support@support.whatsapp.com" UNSEEN)')
                if status != "OK":
                    koneksi.logout()
                    continue

                daftar_id = hasil[0].split()
                for id_surat in daftar_id:
                    if id_surat in balasan_diperiksa:
                        continue
                    balasan_diperiksa.add(id_surat)

                    for idx, banding in enumerate(daftar_banding):
                        if banding["email"] == gmail_data["email"] and banding["status"] == "TERKIRIM":
                            daftar_banding[idx]["status"] = "DIBALAS"
                            teks_notif = f"""
✅ **BANDING BERHASIL DIBALAS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{banding['nomor']}`
📊 Status: ✅ SUKSES

💡 Silakan coba masuk atau verifikasi akun Anda sekarang
                            """
                            for uid in list(pengguna_terizin):
                                try: kirim_pesan(uid, teks_notif)
                                except: pass
                            break

                koneksi.logout()

            except Exception as err:
                print(f"[SISTEM] Cek Email: {err}")

        diperbarui = False
        for idx, banding in enumerate(daftar_banding):
            if banding["status"] == "TERKIRIM" and (waktu_sekarang - banding["waktu_kirim"]) > BATAS_WAKTU_BALAS:
                daftar_banding[idx]["status"] = "BELUM ADA TANGGAPAN"
                teks_notif = f"""
ℹ️ **INFORMASI STATUS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{banding['nomor']}`
⏳ Status: Belum ada tanggapan

💡 Anda dapat mengirim ulang permohonan jika diperlukan
                """
                for uid in list(pengguna_terizin):
                    try: kirim_pesan(uid, teks_notif)
                    except: pass
                diperbarui = True

        if diperbarui:
            simpan_banding(daftar_banding)

        time.sleep(2)

# -------------------- PERINTAH AWAL --------------------
@bot.message_handler(commands=['start'])
def tampil_awal(pesan):
    id_pengguna = pesan.chat.id
    if cek_akses(id_pengguna, pesan.from_user.username or ""):
        teks = """
🤖 **BOT BANDING WHATSAPP PREMIUM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👑 ASEP KANJUT PREMIUM
⚡ Layanan Stabil & Berkecepatan Tinggi
🔄 Sistem Pengiriman Otomatis Berputar
📡 Pemantauan Balasan Secara Real-Time
🌐 Support All Negara

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👇 Silakan Pilih Menu Layanan:
        """
        kirim_pesan(id_pengguna, teks, menu_utama())
    else:
        kirim_pesan(id_pengguna, """
🔒 **AKSES SISTEM TERBATAS**
━━━━━━━━━━━━━━━━━━━━━━━━━━
Masukkan kode akses untuk masuk ke layanan premium
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
Selamat datang di layanan premium
Silakan gunakan fitur yang tersedia
        """, menu_utama())
    else:
        kirim_pesan(id_pengguna, f"""
❌ **KODE AKSES SALAH**
━━━━━━━━━━━━━━━━━━━━━━━━━━
Silakan hubungi Admin untuk bantuan
📞 Kontak: {KONTAK_ADMIN}
        """)
    del proses[id_pengguna]

# -------------------- TOMBOL MENU --------------------
@bot.callback_query_handler(func=lambda panggilan: True)
def proses_tombol(panggilan):
    id_pengguna = panggilan.message.chat.id
    if not cek_akses(id_pengguna, panggilan.from_user.username or ""):
        bot.answer_callback_query(panggilan.id, "❌ Anda tidak memiliki izin akses")
        return
    try:
        bot.answer_callback_query(panggilan.id, "✅ Sedang diproses...")
        if panggilan.data == "tambah":
            if len(baca_akun()) >= MAKSIMAL_GMAIL:
                kirim_pesan(id_pengguna, """
⚠️ **BATAS MAKSIMAL TERCAPAI**
━━━━━━━━━━━━━━━━━━━━━━━━━━
Tidak dapat menambahkan akun baru
                """)
                return
            proses[id_pengguna] = {"langkah": "input_email"}
            kirim_pesan(id_pengguna, """
📩 **MASUKKAN ALAMAT GMAIL**
━━━━━━━━━━━━━━━━━━━━━━━━━━
Contoh: namaanda@gmail.com
            """)

        elif panggilan.data == "daftar":
            daftar = baca_akun()
            if not daftar:
                teks = """
📋 **DAFTAR AKUN GMAIL**
━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Belum ada akun yang terdaftar
                """
            else:
                teks = """
📋 **DAFTAR AKUN GMAIL TERDAFTAR**
━━━━━━━━━━━━━━━━━━━━━━━━━━
""" + "\n".join(f"• `{akun['email']}`" for akun in daftar)
            kirim_pesan(id_pengguna, teks, menu_utama())

        elif panggilan.data == "kirim":
            if not baca_akun():
                kirim_pesan(id_pengguna, """
⚠️ **BELUM ADA AKUN GMAIL**
━━━━━━━━━━━━━━━━━━━━━━━━━━
Silakan tambahkan akun terlebih dahulu
                """)
                return
            proses[id_pengguna] = {"langkah": "input_nomor"}
            kirim_pesan(id_pengguna, """
📱 **MASUKKAN NOMOR BANDING**
━━━━━━━━━━━━━━━━━━━━━━━━━━
Contoh: +6281234567890
            """)

    except Exception as err:
        print(f"[SISTEM] Kesalahan Menu: {err}")

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
Gunakan sandi aplikasi dari pengaturan keamanan Gmail
            """)

    elif data.get("langkah") == "input_sandi":
        akun = baca_akun()
        akun.append({"email": data["email"], "sandi": pesan.text.strip()})
        simpan_akun(akun)
        kirim_pesan(id_pengguna, f"""
✅ **BERHASIL DITAMBAHKAN**
━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email: `{data['email']}`
        """, menu_utama())
        del proses[id_pengguna]

    elif data.get("langkah") == "input_nomor":
        nomor = cek_nomor(pesan.text)
        if not nomor:
            kirim_pesan(id_pengguna, """
❌ **FORMAT TIDAK SESUAI**
━━━━━━━━━━━━━━━━━━━━━━━━━━
Pastikan nomor diawali tanda +
Contoh: +6281234567890
            """)
            return

        daftar_akun = baca_akun()
        total = len(daftar_akun)
        gmail_pakai = daftar_akun[indeks_gmail]
        indeks_gmail = (indeks_gmail + 1) % total

        try:
            pesan_email = MIMEText(nomor)
            pesan_email["From"] = gmail_pakai["email"]
            pesan_email["To"] = TUJUAN_EMAIL
            pesan_email["Subject"] = "Permohonan Banding Akun WhatsApp"

            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
            server.starttls()
            server.login(gmail_pakai["email"], gmail_pakai["sandi"])
            server.sendmail(gmail_pakai["email"], TUJUAN_EMAIL, pesan_email.as_string())
            server.quit()

            daftar_banding = baca_banding()
            daftar_banding.append({
                "nomor": nomor,
                "email": gmail_pakai["email"],
                "status": "TERKIRIM",
                "waktu_kirim": time.time()
            })
            simpan_banding(daftar_banding)

            teks_hasil = f"""
✅ **PESAN SUKSES TERKIRIM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{nomor}`
📤 Dikirim Melalui: `{gmail_pakai['email']}`
⏳ Status: Menunggu Tanggapan

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Sistem akan memantau secara otomatis
            """
            kirim_pesan(id_pengguna, teks_hasil, menu_utama())

        except Exception as err:
            print(f"[SISTEM] Gagal Kirim: {err}")
            teks_gagal = f"""
❌ **GAGAL TERKIRIM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{nomor}`
📤 Gagal Melalui: `{gmail_pakai['email']}`
⚠️ Kemungkinan: Sandi salah / Koneksi terputus

💡 Periksa kembali lalu kirim ulang
            """
            kirim_pesan(id_pengguna, teks_gagal, menu_utama())

        del proses[id_pengguna]

# -------------------- JALANKAN SISTEM --------------------
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 SISTEM BANDING WHATSAPP PREMIUM AKTIF")
    print("🔄 Mode: Otomatis Berurutan & Berputar")
    print("⏱️ Cek Balasan: Setiap 2 Menit")
    print("=" * 60)
    threading.Thread(target=pantau_balasan, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(none_stop=True, interval=2, timeout=30)
        except Exception as err:
            print(f"[SISTEM] Menyambung Ulang: {err}")
            time.sleep(5)
              
