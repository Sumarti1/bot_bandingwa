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
FILE_LOG = "log_akses.json"
FILE_IZIN = "daftar_izin.json"
MAKSIMAL_GMAIL = 15
BATAS_WAKTU_BALAS = 120
JEDA_CEK = 1
BATAS_SALAH_KODE = 3
WAKTU_MULAI = time.time()

# 🔐 DATA PEMILIK
SANDI_UTAMA = "Amelia"
USERNAME_PEMILIK = "Sepcyboy"
KONTAK_ADMIN = "@Sepcyboy"

# 🖼️ GAMBAR TETAP ASLI
FOTO_URL = "https://i.imgur.com/8ZbXzL9.png"

# 🌐 PENGATURAN JARINGAN
from telebot import apihelper
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"
apihelper.CONNECT_TIMEOUT = 60
apihelper.READ_TIMEOUT = 60
apihelper.SESSION = requests.Session()
apihelper.SESSION.trust_env = False

bot = telebot.TeleBot(TOKEN_BOT)
proses = {}
pengguna_terizin = set()
pengguna_diblokir = set()
balasan_diperiksa = set()
indeks_gmail = 0
percobaan_salah = {}
gagal_gmail = {}

# ==================== FUNGSI PESAN ====================
def kirim_pesan(chat_id, teks, tombol=None):
    try:
        bot.send_photo(chat_id=chat_id, photo=FOTO_URL, caption=teks, reply_markup=tombol, parse_mode="Markdown", timeout=30)
    except:
        try:
            bot.send_message(chat_id, teks, reply_markup=tombol, parse_mode="Markdown", timeout=30)
        except:
            pass

# ==================== PENYIMPANAN DATA ====================
def baca_file(nama_file, default):
    try:
        with open(nama_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def simpan_file(nama_file, data):
    try:
        with open(nama_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def baca_akun(): return baca_file(FILE_DATA, [])
def simpan_akun(data): return simpan_file(FILE_DATA, data)
def baca_banding(): return baca_file(FILE_BANDING, [])
def simpan_banding(data): return simpan_file(FILE_BANDING, data)
def baca_log(): return baca_file(FILE_LOG, [])
def simpan_log(data): return simpan_file(FILE_LOG, data)
def baca_izin(): return set(baca_file(FILE_IZIN, []))
def simpan_izin(data): return simpan_file(FILE_IZIN, list(data))

pengguna_terizin.update(baca_izin())

# ==================== FUNGSI BANTU ====================
def cek_nomor(nomor):
    bersih = nomor.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "")
    return bersih if (bersih.startswith("+") and bersih[1:].isdigit() and 8<=len(bersih)<=15) else None

def cek_pemilik(user_id, username):
    return bool(username and username.lower() == USERNAME_PEMILIK.lower())

def cek_akses(user_id, username):
    if user_id in pengguna_diblokir: return False
    return cek_pemilik(user_id, username) or (user_id in pengguna_terizin)

def catat_log(aksi, detail):
    log = baca_log()
    log.append({"waktu": datetime.now().strftime("%d/%m %H:%M"), "aksi": aksi, "detail": detail})
    simpan_log(log[-50:])

def notif_admin(teks):
    for uid in pengguna_terizin:
        if cek_pemilik(uid, ""):
            kirim_pesan(uid, f"🔔 **NOTIFIKASI ADMIN**\n{teks}")

# ==================== 🔧 FUNGSI KIRIM EMAIL DENGAN TAMPILAN PROSES LANGKAH DEMI LANGKAH ====================
def kirim_email_dengan_proses(id_user, pengirim, sandi, tujuan, isi, subjek):
    # Kirim pesan awal proses dimulai
    pesan_proses = kirim_pesan(id_user, "⏳ **MEMULAI PROSES PENGIRIMAN EMAIL**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🔹 Langkah 1: Menyiapkan data pesan...")
    
    langkah = 2
    daftar_server = [
        ("smtp.gmail.com", 465, "SSL"),
        ("smtp.gmail.com", 587, "TLS"),
        ("smtp.gmail.com", 443, "SSL Alternatif")
    ]

    for host, port, tipe in daftar_server:
        try:
            teks_baru = f"⏳ **MEMULAI PROSES PENGIRIMAN EMAIL**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ Langkah 1: Data pesan siap\n🔹 Langkah {langkah}: Menghubungkan ke server `{host}:{port}` ({tipe})..."
            bot.edit_message_caption(chat_id=id_user, message_id=pesan_proses.message_id, caption=teks_baru, parse_mode="Markdown")
            time.sleep(1)

            if tipe == "SSL":
                server = smtplib.SMTP_SSL(host, port, timeout=20)
            else:
                server = smtplib.SMTP(host, port, timeout=20)
                server.ehlo()
                server.starttls()

            langkah +=1
            teks_baru = f"⏳ **MEMULAI PROSES PENGIRIMAN EMAIL**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ Langkah 1: Data pesan siap\n✅ Langkah 2: Terhubung ke server\n🔹 Langkah {langkah}: Memverifikasi akun Gmail..."
            bot.edit_message_caption(chat_id=id_user, message_id=pesan_proses.message_id, caption=teks_baru, parse_mode="Markdown")
            time.sleep(1)

            server.login(pengirim, sandi)
            
            langkah +=1
            teks_baru = f"⏳ **MEMULAI PROSES PENGIRIMAN EMAIL**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ Langkah 1: Data pesan siap\n✅ Langkah 2: Terhubung ke server\n✅ Langkah 3: Verifikasi akun BERHASIL\n🔹 Langkah {langkah}: Menyusun isi email..."
            bot.edit_message_caption(chat_id=id_user, message_id=pesan_proses.message_id, caption=teks_baru, parse_mode="Markdown")
            time.sleep(1)

            pesan = MIMEText(isi, "plain", "utf-8")
            pesan["From"] = pengirim
            pesan["To"] = tujuan
            pesan["Subject"] = subjek

            langkah +=1
            teks_baru = f"⏳ **MEMULAI PROSES PENGIRIMAN EMAIL**\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅ Langkah 1: Data pesan siap\n✅ Langkah 2: Terhubung ke server\n✅ Langkah 3: Verifikasi akun BERHASIL\n✅ Langkah 4: Isi email tersusun\n🔹 Langkah {langkah}: Mengirim ke server WhatsApp..."
            bot.edit_message_caption(chat_id=id_user, message_id=pesan_proses.message_id, caption=teks_baru, parse_mode="Markdown")
            time.sleep(1)

            server.sendmail(pengirim, tujuan, pesan.as_string())
            server.quit()

            # Selesai semua langkah
            teks_selesai = f"""✅ **PROSES PENGIRIMAN SELESAI**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Langkah 1: Data pesan siap
✅ Langkah 2: Terhubung ke server Gmail
✅ Langkah 3: Verifikasi akun BERHASIL
✅ Langkah 4: Isi email tersusun rapi
✅ Langkah 5: Email BERHASIL TERKIRIM ke WhatsApp!

📤 Dikirim dari: `{pengirim}`
📩 Tujuan: `{tujuan}`"""
            bot.edit_message_caption(chat_id=id_user, message_id=pesan_proses.message_id, caption=teks_selesai, parse_mode="Markdown", reply_markup=menu_utama(id_user))
            return True

        except Exception as e:
            pesan_error = str(e)[:60]
            teks_gagal = f"""⚠️ **GAGAL DI LANGKAH INI**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Server {host}:{port} ({tipe})
💬 Pesan kesalahan: `{pesan_error}`
🔄 Mencoba jalur lain..."""
            bot.edit_message_caption(chat_id=id_user, message_id=pesan_proses.message_id, caption=teks_gagal, parse_mode="Markdown")
            time.sleep(2)
            continue

    # Jika semua jalur gagal
    teks_akhir = f"""❌ **SEMUA JALUR PENGIRIMAN GAGAL**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 Railway Gratis memblokir port email keluar
💡 Solusi:
1. Pindah ke hosting Render / Vercel
2. Jalankan di Termux HP
3. Upgrade paket Railway"""
    bot.edit_message_caption(chat_id=id_user, message_id=pesan_proses.message_id, caption=teks_akhir, parse_mode="Markdown", reply_markup=menu_utama(id_user))
    return False

# ==================== CEK BALASAN ====================
def cek_email_balasan(email_pengirim, sandi):
    try:
        koneksi = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=20)
        koneksi.login(email_pengirim, sandi)
        koneksi.select("INBOX", readonly=True)
        _, hasil = koneksi.search(None, '(FROM "support@support.whatsapp.com" UNSEEN)')
        koneksi.logout()
        return hasil[0].split()
    except:
        return []

# ==================== MENU UTAMA ====================
def menu_utama(user_id):
    tombol = InlineKeyboardMarkup(row_width=2)
    tombol.add(
        InlineKeyboardButton("➕ TAMBAH GMAIL", callback_data="tambah"),
        InlineKeyboardButton("📤 KIRIM BANDING", callback_data="kirim"),
        InlineKeyboardButton("📋 DAFTAR GMAIL", callback_data="daftar")
    )
    if cek_pemilik(user_id, ""):
        tombol.add(
            InlineKeyboardButton("👥 PENGGUNA", callback_data="pengguna"),
            InlineKeyboardButton("📊 LAPORAN", callback_data="laporan"),
            InlineKeyboardButton("🗑️ HAPUS DATA", callback_data="hapus")
        )
    return tombol

# ==================== PEMANTAUAN OTOMATIS ====================
def pantau_balasan():
    print("🔍 Pemantauan dimulai")
    while True:
        try:
            akun = baca_akun()
            daftar_banding = baca_banding()
            waktu_sekarang = time.time()

            for gmail in akun:
                pesan_baru = cek_email_balasan(gmail["email"], gmail["sandi"])
                for id_pesan in pesan_baru:
                    if id_pesan in balasan_diperiksa: continue
                    balasan_diperiksa.add(id_pesan)
                    for idx, b in enumerate(daftar_banding):
                        if b["email"] == gmail["email"] and b["status"] == "TERKIRIM":
                            daftar_banding[idx]["status"] = "✅ BERHASIL DIBALAS"
                            teks = f"""✅ **BANDING BERHASIL**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{b['nomor']}`
📊 Status: ADA BALASAN DARI WA
💡 Coba masuk akun sekarang!"""
                            for uid in pengguna_terizin: kirim_pesan(uid, teks)
                            catat_log("Banding Berhasil", b['nomor'])
                            break

            ubah = False
            for idx, b in enumerate(daftar_banding):
                if b["status"] == "TERKIRIM" and (waktu_sekarang - b["waktu_kirim"]) > BATAS_WAKTU_BALAS:
                    daftar_banding[idx]["status"] = "❌ TIDAK ADA BALASAN"
                    ubah = True
            if ubah: simpan_banding(daftar_banding)
        except Exception as e:
            print(f"⚠️ Gangguan: {e}")
        time.sleep(JEDA_CEK)

# ==================== PERINTAH BOT ====================
@bot.message_handler(commands=['start'])
def tampil_awal(pesan):
    id_user = pesan.chat.id
    username = pesan.from_user.username or ""
    if id_user in pengguna_diblokir:
        kirim_pesan(id_user, "🚫 Diblokir!")
        return
    if cek_akses(id_user, username):
        jumlah_gmail = len(baca_akun())
        teks = f"""🤖 **BOT BANDING WHATSAPP**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👑 Milik @Sepcyboy
⚡ Cek Balasan: Tiap 1 Detik
📧 Sisa Akun: {jumlah_gmail}/{MAKSIMAL_GMAIL}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👇 Pilih Menu:"""
        kirim_pesan(id_user, teks, menu_utama(id_user))
    else:
        kirim_pesan(id_user, "🔒 Masukkan kode akses:")
        proses[id_user] = {"langkah": "minta_kode"}

@bot.message_handler(func=lambda m: m.chat.id in proses and proses[m.chat.id].get("langkah") == "minta_kode")
def cek_kode(pesan):
    id_user = pesan.chat.id
    if pesan.text.strip() == SANDI_UTAMA:
        pengguna_terizin.add(id_user)
        simpan_izin(pengguna_terizin)
        kirim_pesan(id_user, "✅ BERHASIL MASUK!", menu_utama(id_user))
    else:
        kirim_pesan(id_user, "❌ Kode salah!")
    del proses[id_user]

@bot.callback_query_handler(func=lambda c: True)
def tombol_tekan(c):
    id_user = c.message.chat.id
    username = c.from_user.username or ""
    if not cek_akses(id_user, username):
        bot.answer_callback_query(c.id, "❌ Tidak izin!")
        return
    bot.answer_callback_query(c.id, "✅ Diproses...")
    data = c.data

    if data == "tambah":
        proses[id_user] = {"langkah": "input_email"}
        kirim_pesan(id_user, "📩 Masukkan alamat Gmail:")
    elif data == "daftar":
        daftar = "\n".join(f"• `{a['email']}`" for a in baca_akun()) or "Belum ada"
        kirim_pesan(id_user, f"📋 DAFTAR GMAIL:\n{daftar}", menu_utama(id_user))
    elif data == "kirim":
        if not baca_akun():
            kirim_pesan(id_user, "⚠️ Tambah Gmail dulu!")
            return
        proses[id_user] = {"langkah": "input_nomor"}
        kirim_pesan(id_user, "📱 Masukkan nomor awalan +:")

@bot.message_handler(func=lambda m: m.chat.id in proses)
def input_data(pesan):
    global indeks_gmail
    id_user = pesan.chat.id
    langkah = proses[id_user].get("langkah")

    if langkah == "input_email":
        proses[id_user]["email"] = pesan.text.strip()
        proses[id_user]["langkah"] = "input_sandi"
        kirim_pesan(id_user, "🔑 Masukkan Sandi Aplikasi 16 digit:")
    elif langkah == "input_sandi":
        akun = baca_akun()
        akun.append({"email": proses[id_user]["email"], "sandi": pesan.text.strip()})
        simpan_akun(akun)
        kirim_pesan(id_user, f"✅ BERHASIL TAMBAH:\n`{proses[id_user]['email']}`", menu_utama(id_user))
        del proses[id_user]
    elif langkah == "input_nomor":
        nomor = cek_nomor(pesan.text)
        if not nomor:
            kirim_pesan(id_user, "❌ Format salah! Awalan +")
            return
        daftar = baca_akun()
        gmail_pakai = daftar[indeks_gmail]
        indeks_gmail = (indeks_gmail +1) % len(daftar)
        
        # ✅ PANGGIL FUNGSI DENGAN TAMPILAN PROSES LENGKAP
        berhasil = kirim_email_dengan_proses(
            id_user,
            gmail_pakai["email"],
            gmail_pakai["sandi"],
            TUJUAN_EMAIL,
            f"Saya mengajukan banding untuk nomor {nomor}. Mohon verifikasi kembali, terima kasih.",
            "Permohonan Pemulihan Akun WhatsApp"
        )
        
        if berhasil:
            data_baru = {"nomor":nomor, "email":gmail_pakai["email"], "status":"TERKIRIM", "waktu_kirim":time.time()}
            semua = baca_banding()
            semua.append(data_baru)
            simpan_banding(semua)
            catat_log("Kirim Banding", nomor)
        del proses[id_user]

# ==================== JALANKAN BOT ====================
if __name__ == "__main__":
    print("="*60)
    print("🚀 TAMPILAN PROSES KIRIM DITAMBAHKAN!")
    print("="*60)
    threading.Thread(target=pantau_balasan, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"⚠️ Restart: {e}")
            time.sleep(3)
          
