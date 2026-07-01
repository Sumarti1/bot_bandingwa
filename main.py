import telebot
import smtplib
import imaplib
from email.mime.text import MIMEText
import json
import time
import os
import threading
import requests
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== PENGATURAN UTAMA ====================
TOKEN_BOT = os.getenv("TOKEN_BOT")
TUJUAN_EMAIL = "support@support.whatsapp.com"
FILE_DATA = "akun_gmail.json"
FILE_BANDING = "data_banding.json"
FILE_IZIN = "daftar_izin.json"

MAKSIMAL_GMAIL = 15
BATAS_WAKTU_BALAS = 120
JEDA_CEK = 1

# 🔐 DATA PEMILIK
SANDI_UTAMA = "Amelia"
USERNAME_PEMILIK = "Sepcyboy"

# 🖼️ GAMBAR PASTI MUNCUL
FOTO_URL = "https://i.postimg.cc/0yqZJZxL/asepkanjut.png"

# 🌐 PENGATURAN JARINGAN
from telebot import apihelper
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"
apihelper.CONNECT_TIMEOUT = 60
apihelper.READ_TIMEOUT = 60

bot = telebot.TeleBot(TOKEN_BOT)
proses = {}
pengguna_terizin = set()
pengguna_diblokir = set()
balasan_diperiksa = set()
indeks_gmail = 0

# ==================== FUNGSI PESAN ====================
def kirim_pesan(chat_id, teks, tombol=None):
    try:
        bot.send_photo(chat_id=chat_id, photo=FOTO_URL, caption=teks, reply_markup=tombol, parse_mode="Markdown", timeout=30)
    except:
        try:
            bot.send_message(chat_id, teks, reply_markup=tombol, parse_mode="Markdown", timeout=30)
        except:
            pass

# ==================== SIMPAN & BACA DATA ====================
def baca_file(nama, default):
    try:
        with open(nama, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def simpan_file(nama, data):
    try:
        with open(nama, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        return True
    except: return False

def baca_akun(): return baca_file(FILE_DATA, [])
def simpan_akun(d): return simpan_file(FILE_DATA, d)
def baca_banding(): return baca_file(FILE_BANDING, [])
def simpan_banding(d): return simpan_file(FILE_BANDING, d)
def baca_izin(): return set(baca_file(FILE_IZIN, []))
def simpan_izin(d): return simpan_file(FILE_IZIN, list(d))

pengguna_terizin.update(baca_izin())

# ==================== FUNGSI BANTU ====================
def cek_nomor(nomor):
    n = nomor.strip().replace(" ","").replace("-","").replace("(","").replace(")","").replace(".","")
    return n if (n.startswith("+") and n[1:].isdigit() and 8<=len(n)<=15) else None

def cek_pemilik(u, n): return bool(n and n.lower() == USERNAME_PEMILIK.lower())
def cek_akses(u, n): return u not in pengguna_diblokir and (cek_pemilik(u,n) or u in pengguna_terizin)

# ==================== KIRIM EMAIL DENGAN TAMPILAN PROSES ====================
def kirim_email_proses(id_user, pengirim, sandi, tujuan, isi, subjek):
    pesan = kirim_pesan(id_user, "⏳ **MEMULAI PENGIRIMAN**\n🔹 Menyiapkan data...")
    if not pesan: return False

    server_list = [("smtp.gmail.com",465,"SSL"), ("smtp.gmail.com",587,"TLS"), ("smtp.gmail.com",443,"SSL")]
    for host, port, tipe in server_list:
        try:
            bot.edit_message_caption(id_user, pesan.message_id,
                f"⏳ **PROSES PENGIRIMAN**\n✅ Data siap\n🔹 Hubung `{host}:{port}`...", parse_mode="Markdown")
            time.sleep(1)

            if tipe == "SSL":
                srv = smtplib.SMTP_SSL(host, port, timeout=20)
            else:
                srv = smtplib.SMTP(host, port, timeout=20)
                srv.ehlo(); srv.starttls()

            bot.edit_message_caption(id_user, pesan.message_id,
                "⏳ **PROSES PENGIRIMAN**\n✅ Terhubung\n🔹 Verifikasi akun...", parse_mode="Markdown")
            time.sleep(1)

            srv.login(pengirim, sandi)
            msg = MIMEText(isi, "plain", "utf-8")
            msg["From"] = pengirim; msg["To"] = tujuan; msg["Subject"] = subjek
            srv.sendmail(pengirim, tujuan, msg.as_string())
            srv.quit()

            bot.edit_message_caption(id_user, pesan.message_id,
                f"✅ **BERHASIL TERKIRIM!**\n📤 Dari: `{pengirim}`", parse_mode="Markdown", reply_markup=menu_utama(id_user))
            return True
        except Exception as e:
            try: bot.edit_message_caption(id_user, pesan.message_id, f"⚠️ Gagal di sini: `{str(e)[:50]}`\n🔄 Coba jalur lain...", parse_mode="Markdown")
            except: pass
            time.sleep(2)

    bot.edit_message_caption(id_user, pesan.message_id,
        "❌ **SEMUA JALUR GAGAL**\nRailway Gratis memblokir port email.\nPindah ke Render/Termux ya!", parse_mode="Markdown", reply_markup=menu_utama(id_user))
    return False

# ==================== CEK BALASAN ====================
def cek_balasan(email, sandi):
    try:
        srv = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=20)
        srv.login(email, sandi)
        srv.select("INBOX", readonly=True)
        _, x = srv.search(None, '(FROM "support@support.whatsapp.com" UNSEEN)')
        srv.logout()
        return x[0].split()
    except: return []

# ==================== MENU UTAMA ====================
def menu_utama(user_id):
    t = InlineKeyboardMarkup(row_width=2)
    t.add(InlineKeyboardButton("➕ TAMBAH GMAIL", callback_data="tambah"),
          InlineKeyboardButton("📤 KIRIM BANDING", callback_data="kirim"),
          InlineKeyboardButton("📋 DAFTAR GMAIL", callback_data="daftar"))
    return t

# ==================== JALANKAN BOT ====================
@bot.message_handler(commands=['start'])
def mulai(msg):
    if cek_akses(msg.chat.id, msg.from_user.username or ""):
        teks = f"""🤖 **BOT BANDING WHATSAPP**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👑 Milik @Sepcyboy
⚡ Cek Balasan: Tiap 1 Detik
📧 Sisa Akun: {len(baca_akun())}/{MAKSIMAL_GMAIL}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👇 Pilih Menu:"""
        kirim_pesan(msg.chat.id, teks, menu_utama(msg.chat.id))
    else:
        kirim_pesan(msg.chat.id, "🔒 Masukkan kode akses:")
        proses[msg.chat.id] = {"langkah":"kode"}

@bot.message_handler(func=lambda m: m.chat.id in proses)
def inputan(msg):
    id = msg.chat.id
    l = proses[id].get("langkah")
    if l == "kode":
        if msg.text.strip() == SANDI_UTAMA:
            pengguna_terizin.add(id); simpan_izin(pengguna_terizin)
            kirim_pesan(id, "✅ **BERHASIL MASUK!**", menu_utama(id))
        else: kirim_pesan(id, "❌ Kode salah!")
    elif l == "input_email":
        proses[id]["email"] = msg.text.strip()
        proses[id]["langkah"] = "input_sandi"
        kirim_pesan(id, "🔑 Masukkan Sandi Aplikasi 16 digit:")
    elif l == "input_sandi":
        a = baca_akun(); a.append({"email":proses[id]["email"], "sandi":msg.text.strip()}); simpan_akun(a)
        kirim_pesan(id, f"✅ BERHASIL TAMBAH:\n`{proses[id]['email']}`", menu_utama(id))
    elif l == "input_nomor":
        nomor = cek_nomor(msg.text)
        if not nomor: kirim_pesan(id, "❌ Format salah! Awalan +"); return
        a = baca_akun(); g = a[indeks_gmail]; global indeks_gmail; indeks_gmail = (indeks_gmail+1)%len(a)
        kirim_email_proses(id, g["email"], g["sandi"], TUJUAN_EMAIL,
            f"Banding nomor {nomor}. Mohon bantuannya.", "Pemulihan Akun WA")
    del proses[id]

@bot.callback_query_handler(func=lambda c: True)
def tombol(c):
    id = c.message.chat.id
    if not cek_akses(id, c.from_user.username or ""):
        bot.answer_callback_query(c.id, "❌ Gak izin!"); return
    bot.answer_callback_query(c.id, "✅ Diproses...")
    if c.data == "tambah":
        if len(baca_akun())>=MAKSIMAL_GMAIL: kirim_pesan(id, f"⚠️ Batas {MAKSIMAL_GMAIL}!"); return
        proses[id] = {"langkah":"input_email"}; kirim_pesan(id, "📩 Masukkan Gmail:")
    elif c.data == "daftar":
        d = "\n".join(f"• `{x['email']}`" for x in baca_akun()) or "Belum ada"
        kirim_pesan(id, f"📋 **DAFTAR GMAIL**\n{d}", menu_utama(id))
    elif c.data == "kirim":
        if not baca_akun(): kirim_pesan(id, "⚠️ Tambah Gmail dulu!"); return
        proses[id] = {"langkah":"input_nomor"}; kirim_pesan(id, "📱 Masukkan nomor awalan +:")

if __name__ == "__main__":
    print("🚀 BOT SIAP PAKAI!")
    while True:
        try: bot.infinity_polling(none_stop=True, interval=1, timeout=30)
        except Exception as e: print(f"Restart: {e}"); time.sleep(3)
                                       
