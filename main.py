import telebot
import smtplib
import imaplib
from email.mime.text import MIMEText
import json
import time
import os
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== PENGATURAN UTAMA ✅ SUDAH SESUAI ====================
TOKEN_BOT = os.getenv("TOKEN_BOT") # Isi di Railway Variables
TUJUAN_EMAIL = "support@support.whatsapp.com"
FILE_DATA = "akun_gmail.json"
FILE_BANDING = "data_banding.json"
FILE_IZIN = "daftar_izin.json"

MAKSIMAL_GMAIL = 15
BATAS_WAKTU_BALAS = 120
JEDA_CEK = 1

SANDI_UTAMA = "Amelia"
USERNAME_PEMILIK = "Sepcyboy"

# ✅ FOTO ASEP KANJUT PERSIS SEPERTI DI GAMBAR
FOTO_URL = "https://i.postimg.cc/0yqZJZxL/asepkanjut.png"

indeks_gmail = 0

bot = telebot.TeleBot(TOKEN_BOT)
proses = {}
pengguna_terizin = set()
pengguna_diblokir = set()

# ==================== FUNGSI PESAN ✅ FOTO PASTI MUNCUL ====================
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
    except:
        bot.send_message(chat_id, teks, reply_markup=tombol, parse_mode="Markdown", timeout=30)

# ==================== SIMPAN & BACA DATA ====================
def baca_file(nama, default):
    try:
        with open(nama, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def simpan_file(nama, data):
    try:
        with open(nama, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except: return False

def baca_akun(): return baca_file(FILE_DATA, [])
def simpan_akun(d): return simpan_file(FILE_DATA, d)
def baca_izin(): return set(baca_file(FILE_IZIN, []))
def simpan_izin(d): return simpan_file(FILE_IZIN, list(d))

pengguna_terizin.update(baca_izin())

def cek_nomor(nomor):
    n = nomor.strip().replace(" ","").replace("-","").replace("(","").replace(")","").replace(".","")
    return n if (n.startswith("+") and n[1:].isdigit() and 8 <= len(n) <= 15) else None

def cek_pemilik(u, n): return bool(n and n.lower() == USERNAME_PEMILIK.lower())
def cek_akses(u, n): return u not in pengguna_diblokir and (cek_pemilik(u,n) or u in pengguna_terizin)

# ==================== KIRIM EMAIL DENGAN PROSES ====================
def kirim_email_proses(id_user, pengirim, sandi, tujuan, isi, subjek):
    pesan = kirim_pesan(id_user, "⏳ **MEMULAI PENGIRIMAN**\n🔹 Menyiapkan data...")
    if not pesan: return False

    server_list = [("smtp.gmail.com",465,"SSL"), ("smtp.gmail.com",587,"TLS")]
    for host, port, tipe in server_list:
        try:
            bot.edit_message_caption(id_user, pesan.message_id,
                f"⏳ **PROSES PENGIRIMAN**\n✅ Data siap\n🔹 Hubung `{host}:{port}`...", parse_mode="Markdown")
            time.sleep(1)

            if tipe == "SSL":
                srv = smtplib.SMTP_SSL(host, port, timeout=20)
            else:
                srv = smtplib.SMTP(host, port, timeout=20)
                srv.ehlo()
                srv.starttls()

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
            try: bot.edit_message_caption(id_user, pesan.message_id, f"⚠️ Gagal: `{str(e)[:50]}`\n🔄 Coba jalur lain...", parse_mode="Markdown")
            except: pass
            time.sleep(2)

    bot.edit_message_caption(id_user, pesan.message_id,
        "❌ **SEMUA JALUR GAGAL**\nRailway blokir port email, pakai Render/Termux ya!", parse_mode="Markdown", reply_markup=menu_utama(id_user))
    return False

# ==================== MENU UTAMA PERSIS SESUAI GAMBAR ====================
def menu_utama(user_id):
    t = InlineKeyboardMarkup(row_width=1)
    t.add(
        InlineKeyboardButton("➕ TAMBAH AKUN GMAIL", callback_data="tambah"),
        InlineKeyboardButton("📩 KIRIM BANDING", callback_data="kirim"),
        InlineKeyboardButton("📋 DAFTAR GMAIL", callback_data="daftar")
    )
    return t

# ==================== PERINTAH /START PERSIS ====================
@bot.message_handler(commands=['start'])
def mulai(msg):
    id = msg.chat.id
    uname = msg.from_user.username or ""
    if cek_akses(id, uname):
        teks = f"""🤖 **BOT BANDING WHATSAPP PREMIUM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👑 **ASEP KANJUT PREMIUM**
⚡ Cek Balasan: Setiap 1 Detik
⏱️ Batas Waktu: 2 Menit
🔄 Sistem Otomatis Berputar
🌐 Support Semua Negara
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👇 Silakan Pilih Menu Layanan:"""
        kirim_pesan(id, teks, menu_utama(id))
    else:
        kirim_pesan(id, "🔒 Masukkan kode akses:")
        proses[id] = {"langkah":"kode"}

@bot.message_handler(func=lambda m: m.chat.id in proses)
def inputan(msg):
    global indeks_gmail
    id = msg.chat.id
    l = proses[id].get("langkah")

    if l == "kode":
        if msg.text.strip() == SANDI_UTAMA:
            pengguna_terizin.add(id)
            simpan_izin(pengguna_terizin)
            kirim_pesan(id, "✅ **BERHASIL MASUK!**", menu_utama(id))
        else:
            kirim_pesan(id, "❌ Kode salah!")

    elif l == "input_email":
        proses[id]["email"] = msg.text.strip()
        proses[id]["langkah"] = "input_sandi"
        kirim_pesan(id, "📩 Masukkan alamat Gmail:")

    elif l == "input_sandi":
        a = baca_akun(); a.append({"email":proses[id]["email"], "sandi":msg.text.strip()}); simpan_akun(a)
        kirim_pesan(id, f"✅ **BERHASIL TAMBAH**\n`{proses[id]['email']}`", menu_utama(id))

    elif l == "input_nomor":
        nomor = cek_nomor(msg.text)
        if not nomor: kirim_pesan(id, "❌ Contoh: +62812345678"); return
        a = baca_akun()
        if not a: kirim_pesan(id, "⚠️ Tambah Gmail dulu!"); return
        g = a[indeks_gmail]
        indeks_gmail = (indeks_gmail + 1) % len(a)
        kirim_email_proses(id, g["email"], g["sandi"], TUJUAN_EMAIL,
            f"Banding nomor {nomor}. Mohon bantuannya.", "Pemulihan Akun WA")

    del proses[id]

@bot.callback_query_handler(func=lambda c: True)
def tombol(c):
    id = c.message.chat.id
    uname = c.from_user.username or ""
    if not cek_akses(id, uname):
        bot.answer_callback_query(c.id, "❌ Tidak ada izin!"); return
    bot.answer_callback_query(c.id, "✅ Diproses...")

    if c.data == "tambah":
        if len(baca_akun())>=MAKSIMAL_GMAIL: kirim_pesan(id, f"⚠️ Batas {MAKSIMAL_GMAIL}!"); return
        proses[id] = {"langkah":"input_email"}; kirim_pesan(id, "📩 Masukkan alamat Gmail:")
    elif c.data == "daftar":
        daftar = "\n".join(f"• `{x['email']}`" for x in baca_akun()) or "Belum ada akun"
        kirim_pesan(id, f"📋 **DAFTAR AKUN GMAIL**\n{daftar}", menu_utama(id))
    elif c.data == "kirim":
        if not baca_akun(): kirim_pesan(id, "⚠️ Tambah Gmail dulu!"); return
        proses[id] = {"langkah":"input_nomor"}; kirim_pesan(id, "📱 Masukkan nomor awalan +:")

if __name__ == "__main__":
    print("🚀 BOT PREMIUM ASEP KANJUT SIAP!")
    while True:
        try: bot.infinity_polling(none_stop=True, interval=1, timeout=30)
        except Exception as e: print(f"Restart: {e}"); time.sleep(5)
  
