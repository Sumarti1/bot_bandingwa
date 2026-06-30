import telebot
import smtplib
import imaplib
import json
import time
import os
import threading
import requests
from email.mime.text import MIMEText
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ⚙️ KONFIGURASI UTAMA
TOKEN_BOT = os.getenv("TOKEN_BOT")
TUJUAN_EMAIL = "support@support.whatsapp.com"
FILE_DATA = "akun_gmail.json"
FILE_BANDING = "data_banding.json"
MAKSIMAL_GMAIL = 15
BATAS_WAKTU_BALAS = 120  # 2 Menit = dianggap gagal kalau tidak ada balasan

# 🔐 DATA AKSES
SANDI_UTAMA = "Amelia"
USERNAME_PEMILIK = "Sepcyboy"
KONTAK_ADMIN = "@Sepcyboy"

# 🖼️ LINK FOTO
FOTO_URL = "https://raw.githubusercontent.com/Sumarti1/bot_bandingwa/main/1782676789784.png"

# 🌐 PENGATURAN KONEKSI
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
        bot.send_photo(
            chat_id=chat_id,
            photo=FOTO_URL,
            caption=teks,
            reply_markup=tombol,
            parse_mode="Markdown"
        )
    except Exception as e:
        try:
            bot.send_message(
                chat_id=chat_id,
                text=teks,
                reply_markup=tombol,
                parse_mode="Markdown"
            )
        except:
            pass

# -------------------- FUNGSI PENUNJANG --------------------
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

# -------------------- PEMANTAUAN SETIAP 1 DETIK --------------------
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
                            daftar_banding[idx]["status"] = "BERHASIL DIBALAS"
                            teks_notif = f"""
✅ **BANDING BERHASIL**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{banding['nomor']}`
📊 Status: ✅ ADA BALASAN

💡 Silakan coba masuk / verifikasi akun
                            """
                            for uid in list(pengguna_terizin):
                                kirim_pesan(uid, teks_notif)
                            break

                koneksi.logout()
            except Exception as err:
                pass

        # Cek yang lewat 2 menit = GAGAL
        diperbarui = False
        for idx, banding in enumerate(daftar_banding):
            if banding["status"] == "TERKIRIM" and (waktu_sekarang - banding["waktu_kirim"]) > BATAS_WAKTU_BALAS:
                daftar_banding[idx]["status"] = "GAGAL / BELUM ADA BALASAN"
                teks_notif = f"""
❌ **STATUS BANDING**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{banding['nomor']}`
⏱️ Waktu: 2 Menit
📊 Status: ❌ GAGAL / BELUM ADA BALASAN

💡 Bisa kirim ulang atau ganti email
                """
                for uid in list(pengguna_terizin):
                    kirim_pesan(uid, teks_notif)
                diperbarui = True

        if diperbarui:
            simpan_banding(daftar_banding)

        # ✅ CEK SETIAP 1 DETIK
        time.sleep(1)

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
            kirim_pesan(id_pengguna, "📩 Masukkan alamat Gmail:")
        elif panggilan.data == "daftar":
            daftar = baca_akun()
            if not daftar:
                teks = "📋 Belum ada akun Gmail terdaftar"
            else:
                teks = "📋 DAFTAR GMAIL:\n" + "\n".join(f"• `{a['email']}`" for a in daftar)
            kirim_pesan(id_pengguna, teks, menu_utama())
        elif panggilan.data == "kirim":
            if not baca_akun():
                kirim_pesan(id_pengguna, "⚠️ Tambah Gmail dulu ya")
                return
            proses[id_pengguna] = {"langkah": "input_nomor"}
            kirim_pesan(id_pengguna, "📱 Masukkan nomor diawali +:\nContoh: +628123456789")
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
        kirim_pesan(id_pengguna, "🔑 Masukkan SANDI APLIKASI Gmail:")

    elif data.get("langkah") == "input_sandi":
        akun = baca_akun()
        akun.append({"email": data["email"], "sandi": pesan.text.strip()})
        simpan_akun(akun)
        kirim_pesan(id_pengguna, f"✅ Gmail `{data['email']}` berhasil ditambahkan", menu_utama())
        del proses[id_pengguna]

    elif data.get("langkah") == "input_nomor":
        nomor = cek_nomor(pesan.text)
        if not nomor:
            kirim_pesan(id_pengguna, "❌ Format salah! Gunakan +62...")
            return

        daftar_akun = baca_akun()
        gmail_pakai = daftar_akun[indeks_gmail]
        indeks_gmail = (indeks_gmail + 1) % len(daftar_akun)

        try:
            pesan_email = MIMEText(nomor)
            pesan_email["From"] = gmail_pakai["email"]
            pesan_email["To"] = TUJUAN_EMAIL
            pesan_email["Subject"] = "Permohonan Banding Akun WhatsApp"

            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
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

            teks = f"""
✅ **TERKIRIM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{nomor}`
📧 Lewat: `{gmail_pakai['email']}`
⏱️ Cek Balasan: Setiap 1 Detik
⌛ Batas Waktu: 2 Menit

💡 Menunggu balasan dari WhatsApp
            """
            kirim_pesan(id_pengguna, teks, menu_utama())
        except:
            kirim_pesan(id_pengguna, "❌ Gagal kirim! Cek sandi aplikasi Gmail", menu_utama())
        del proses[id_pengguna]

# -------------------- JALANKAN BOT --------------------
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 BOT AKTIF | Cek Setiap 1 Detik | Batas 2 Menit")
    print("=" * 50)
    threading.Thread(target=pantau_balasan, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(none_stop=True, interval=1, timeout=15)
        except:
            time.sleep(2)
