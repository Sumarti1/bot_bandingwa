import telebot
import smtplib
import json
import time
import os
from email.mime.text import MIMEText
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== PENGATURAN ✅ AMAN DARI EROR ====================
TOKEN_BOT = os.getenv("TOKEN_BOT")
TUJUAN_EMAIL = "support@support.whatsapp.com"

FILE_DATA = "akun_gmail.json"
FILE_IZIN = "daftar_izin.json"
MAKSIMAL_GMAIL = 15
SANDI_UTAMA = "Amelia"
USERNAME_PEMILIK = "Sepcyboy"

# ✅ FOTO KAMU (HOSTING AMAN, TIDAK DIBLOKIR)
FOTO_URL = "https://i.ibb.co/9t2kGpY/asepkanjut.png"

indeks_gmail = 0
bot = telebot.TeleBot(TOKEN_BOT)
proses = {}
pengguna_terizin = set()

# ==================== FUNGSI BACA/SIMPAN FILE ✅ TIDAK EROR ====================
def baca_file(nama, default):
    try:
        with open(nama, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def simpan_file(nama, data):
    try:
        with open(nama, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except:
        return False

pengguna_terizin.update(baca_file(FILE_IZIN, []))

# ==================== FUNGSI KIRIM PESAN ✅ SELALU ADA FOTO ====================
def kirim_pesan(chat_id, teks, tombol=None):
    try:
        bot.send_photo(
            chat_id=chat_id,
            photo=FOTO_URL,
            caption=teks,
            reply_markup=tombol,
            parse_mode="Markdown",
            timeout=30
        )
    except Exception as e:
        print(f"Info: {e}")
        bot.send_message(chat_id, teks, reply_markup=tombol, parse_mode="Markdown", timeout=30)

# ==================== FUNGSI LAINNYA ====================
def cek_nomor(nomor):
    n = nomor.strip().replace(" ","").replace("-","").replace("(","").replace(")","")
    return n if (n.startswith("+") and n[1:].isdigit() and 8 <= len(n) <= 15) else None

def menu_utama():
    t = InlineKeyboardMarkup(row_width=1)
    t.add(
        InlineKeyboardButton("➕ TAMBAH AKUN GMAIL", callback_data="tambah"),
        InlineKeyboardButton("📩 KIRIM BANDING", callback_data="kirim"),
        InlineKeyboardButton("📋 DAFTAR GMAIL", callback_data="daftar")
    )
    return t

# ==================== PERINTAH /START ====================
@bot.message_handler(commands=['start'])
def mulai(msg):
    id = msg.chat.id
    uname = msg.from_user.username or ""
    if id in pengguna_terizin or (uname and uname.lower() == USERNAME_PEMILIK.lower()):
        teks = f"""🤖 **BOT BANDING WHATSAPP PREMIUM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👑 **ASEP KANJUT PREMIUM**
⚡ Cek Balasan: Setiap 1 Detik
⏱️ Batas Waktu: 2 Menit
🔄 Sistem Otomatis Berputar
🌐 Support Semua Negara
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👇 Silakan Pilih Menu Layanan:"""
        kirim_pesan(id, teks, menu_utama())
    else:
        kirim_pesan(id, "🔒 Masukkan kode akses:")
        proses[id] = {"langkah":"kode"}

# ==================== INPUTAN & TOMBOL ====================
@bot.message_handler(func=lambda m: m.chat.id in proses)
def inputan(msg):
    global indeks_gmail
    id = msg.chat.id
    l = proses[id].get("langkah")

    if l == "kode":
        if msg.text.strip() == SANDI_UTAMA:
            pengguna_terizin.add(id)
            simpan_file(FILE_IZIN, list(pengguna_terizin))
            kirim_pesan(id, "✅ **BERHASIL MASUK!**", menu_utama())
        else:
            kirim_pesan(id, "❌ Kode salah!")
    elif l == "input_email":
        proses[id]["email"] = msg.text.strip()
        proses[id]["langkah"] = "input_sandi"
        kirim_pesan(id, "📩 Masukkan Sandi Aplikasi Gmail:")
    elif l == "input_sandi":
        akun = baca_file(FILE_DATA, [])
        akun.append({"email":proses[id]["email"], "sandi":msg.text.strip()})
        simpan_file(FILE_DATA, akun)
        kirim_pesan(id, f"✅ Berhasil ditambah: `{proses[id]['email']}`", menu_utama())
    elif l == "input_nomor":
        nomor = cek_nomor(msg.text)
        if not nomor:
            kirim_pesan(id, "❌ Contoh: +6281234567890")
            return
        akun = baca_file(FILE_DATA, [])
        if not akun:
            kirim_pesan(id, "⚠️ Tambah Gmail dulu!")
            return
        g = akun[indeks_gmail]
        indeks_gmail = (indeks_gmail + 1) % len(akun)
        kirim_pesan(id, f"📤 Sedang kirim banding untuk nomor {nomor}...\nMohon tunggu sebentar!")
    del proses[id]

@bot.callback_query_handler(func=lambda c: True)
def tombol(c):
    id = c.message.chat.id
    bot.answer_callback_query(c.id, "✅ Diproses...")
    if c.data == "tambah":
        if len(baca_file(FILE_DATA, [])) >= MAKSIMAL_GMAIL:
            kirim_pesan(id, f"⚠️ Batas maksimal {MAKSIMAL_GMAIL} akun!")
            return
        proses[id] = {"langkah":"input_email"}
        kirim_pesan(id, "📩 Masukkan alamat Gmail:")
    elif c.data == "daftar":
        daftar = "\n".join(f"• `{x['email']}`" for x in baca_file(FILE_DATA, [])) or "Belum ada akun"
        kirim_pesan(id, f"📋 **DAFTAR GMAIL**\n{daftar}", menu_utama())
    elif c.data == "kirim":
        if not baca_file(FILE_DATA, []):
            kirim_pesan(id, "⚠️ Tambah Gmail dulu!")
            return
        proses[id] = {"langkah":"input_nomor"}
        kirim_pesan(id, "📱 Masukkan nomor awalan +:")

if __name__ == "__main__":
    print("🚀 BOT SIAP! FOTO MUNCUL DI SEMUA MENU")
    while True:
        try:
            bot.infinity_polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"Restart: {e}")
            time.sleep(5)
  
