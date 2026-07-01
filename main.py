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

# 🖼️ GAMBAR AMAN
FOTO_URL = "https://raw.githubusercontent.com/Sumarti1/bot_bandingwa/main/1782676789784.png"

# 🌐 PERBAIKAN KONEKSI
from telebot import apihelper
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"
apihelper.CONNECT_TIMEOUT = 35
apihelper.READ_TIMEOUT = 45
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

# ==================== FUNGSI PESAN & DATA ====================
def kirim_pesan(chat_id, teks, tombol=None):
    try:
        bot.send_photo(chat_id=chat_id, photo=FOTO_URL, caption=teks, reply_markup=tombol, parse_mode="Markdown", timeout=20)
    except:
        try:
            bot.send_message(chat_id, teks + "\n\n🖼️ [Gambar tidak dimuat]", reply_markup=tombol, parse_mode="Markdown", timeout=20)
        except:
            pass

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

# Muat daftar izin tersimpan
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
    """Kirim pesan khusus ke pemilik"""
    for uid in pengguna_terizin:
        if cek_pemilik(uid, ""):
            kirim_pesan(uid, f"🔔 **NOTIFIKASI ADMIN**\n{teks}")

# ==================== KIRIM EMAIL & CEK BALASAN ====================
def kirim_email(pengirim, sandi, tujuan, isi, subjek):
    log = ["🔄 Memulai pengiriman..."]
    for port, tipe in [(587, "TLS"), (465, "SSL")]:
        try:
            log.append(f"🔌 Hubungkan ke port {port} ({tipe})")
            if port == 587:
                server = smtplib.SMTP("smtp.gmail.com", port, timeout=25)
                server.ehlo()
                server.starttls()
            else:
                server = smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=25)
                server.ehlo()
            server.login(pengirim, sandi)
            log.append("✅ Masuk Gmail berhasil")
            pesan = MIMEText(isi, "plain", "utf-8")
            pesan["From"] = pengirim
            pesan["To"] = tujuan
            pesan["Subject"] = subjek
            server.sendmail(pengirim, tujuan, pesan.as_string())
            server.quit()
            gagal_gmail[pengirim] = 0
            log.append("✅ Email TERKIRIM!")
            return True, "\n".join(log)
        except Exception as e:
            log.append(f"⚠️ Gagal port {port}: {str(e)[:60]}")
            gagal_gmail[pengirim] = gagal_gmail.get(pengirim, 0) + 1
            if gagal_gmail[pengirim] >= 3:
                notif_admin(f"⚠️ Akun `{pengirim}` gagal 3x berturut-turut! Cek segera ya.")
    log.append("❌ Semua koneksi gagal!")
    return False, "\n".join(log)

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

# ==================== MENU UTAMA & ADMIN ====================
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
            InlineKeyboardButton("📜 RIWAYAT", callback_data="riwayat"),
            InlineKeyboardButton("🔔 SIARAN", callback_data="siaran"),
            InlineKeyboardButton("⚙️ PENGATURAN", callback_data="pengaturan"),
            InlineKeyboardButton("🗑️ HAPUS DATA", callback_data="hapus")
        )
    return tombol

# ==================== PEMANTAUAN OTOMATIS ====================
def pantau_balasan():
    print("🔍 Pemantauan dimulai (tiap 1 detik)")
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
                    daftar_banding[idx]["status"] = "❌ GAGAL / TIDAK ADA BALASAN"
                    teks = f"""❌ **LAPORAN BANDING**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Nomor: `{b['nomor']}`
⏱️ Waktu: 2 Menit
📊 Status: Belum ada balasan"""
                    for uid in pengguna_terizin: kirim_pesan(uid, teks)
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
        kirim_pesan(id_user, "🚫 Diblokir karena terlalu banyak salah kode!")
        return
    if cek_akses(id_user, username):
        jumlah_gmail = len(baca_akun())
        teks = f"""🤖 **BOT BANDING WHATSAPP PREMIUM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👑 Milik @Sepcyboy
⚡ Cek Balasan: Tiap 1 Detik
⏱️ Tunggu Maksimal: 2 Menit
📧 Sisa Gmail: {jumlah_gmail}/{MAKSIMAL_GMAIL}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👇 Pilih Menu Layanan:"""
        kirim_pesan(id_user, teks, menu_utama(id_user))
    else:
        kirim_pesan(id_user, "🔒 **AKSES TERBATAS**\nMasukkan kode akses:")
        proses[id_user] = {"langkah": "minta_kode"}

@bot.message_handler(func=lambda m: m.chat.id in proses and proses[m.chat.id].get("langkah") == "minta_kode")
def cek_kode(pesan):
    id_user = pesan.chat.id
    kode = pesan.text.strip()
    if kode == SANDI_UTAMA:
        pengguna_terizin.add(id_user)
        simpan_izin(pengguna_terizin)
        percobaan_salah[id_user] = 0
        catat_log("Akses Diberikan", f"ID: {id_user}")
        notif_admin(f"Pengguna baru masuk!\nID: `{id_user}`")
        kirim_pesan(id_user, "✅ **BERHASIL MASUK**\nSelamat pakai bot!", menu_utama(id_user))
    else:
        percobaan_salah[id_user] = percobaan_salah.get(id_user, 0) + 1
        sisa = BATAS_SALAH_KODE - percobaan_salah[id_user]
        if sisa <= 0:
            pengguna_diblokir.add(id_user)
            catat_log("Diblokir", f"ID: {id_user}")
            kirim_pesan(id_user, "🚫 **DIBLOKIR**\nTerlalu banyak salah kode!")
        else:
            kirim_pesan(id_user, f"❌ KODE SALAH!\nSisa percobaan: {sisa} kali")
    del proses[id_user]

@bot.callback_query_handler(func=lambda c: True)
def tombol_tekan(c):
    global SANDI_UTAMA
    id_user = c.message.chat.id
    username = c.from_user.username or ""
    if not cek_akses(id_user, username):
        bot.answer_callback_query(c.id, "❌ Tidak punya akses!")
        return
    bot.answer_callback_query(c.id, "✅ Diproses...")
    data = c.data

    # Menu Umum
    if data == "tambah":
        if len(baca_akun()) >= MAKSIMAL_GMAIL:
            kirim_pesan(id_user, f"⚠️ Batas {MAKSIMAL_GMAIL} akun!")
            return
        proses[id_user] = {"langkah": "input_email"}
        kirim_pesan(id_user, "📩 Masukkan Gmail:")
    elif data == "daftar":
        daftar = "\n".join(f"• `{a['email']}`" for a in baca_akun()) or "Belum ada akun"
        kirim_pesan(id_user, f"📋 DAFTAR GMAIL:\n{daftar}", menu_utama(id_user))
    elif data == "kirim":
        if not baca_akun():
            kirim_pesan(id_user, "⚠️ Tambah Gmail dulu ya!")
            return
        proses[id_user] = {"langkah": "input_nomor"}
        kirim_pesan(id_user, "📱 Masukkan nomor awalan +:")

    # MENU KHUSUS ADMIN
    elif data == "pengguna" and cek_pemilik(id_user, username):
        teks = "👥 **DAFTAR PENGGUNA IZIN**\n━━━━━━━━━━━━━━━━━━━━\n"
        if pengguna_terizin:
            for no, uid in enumerate(pengguna_terizin,1):
                teks += f"{no}. ID: `{uid}`\n"
        else: teks += "Belum ada pengguna"
        teks += "\n\nKirim ID untuk tambah/ketik `hapus ID` untuk cabut akses"
        kirim_pesan(id_user, teks, menu_utama(id_user))
        proses[id_user] = {"langkah": "atur_pengguna"}
    elif data == "laporan" and cek_pemilik(id_user, username):
        semua = baca_banding()
        berh = sum(1 for x in semua if x["status"] == "✅ BERHASIL DIBALAS")
        gagal = sum(1 for x in semua if "GAGAL" in x["status"])
        kirim = sum(1 for x in semua if x["status"] == "TERKIRIM")
        hidup = time.strftime("%j hari %H jam %M menit", time.gmtime(time.time() - WAKTU_MULAI))
        teks = f"""📊 **LAPORAN SISTEM**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏳ Bot Menyala: {hidup}
📤 Total Banding: {len(semua)}
✅ Berhasil: {berh}
❌ Gagal: {gagal}
⏳ Menunggu: {kirim}
👥 Pengguna Aktif: {len(pengguna_terizin)}"""
        kirim_pesan(id_user, teks, menu_utama(id_user))
    elif data == "riwayat" and cek_pemilik(id_user, username):
        semua = baca_banding()[-5:][::-1]
        teks = "📜 **RIWAYAT 5 TERAKHIR**\n━━━━━━━━━━━━━━━━━━━━\n"
        if not semua: teks += "Belum ada riwayat"
        else:
            for n, b in enumerate(semua,1):
                teks += f"{n}. {b['nomor']}\n   {b['status']}\n"
        kirim_pesan(id_user, teks, menu_utama(id_user))
    elif data == "siaran" and cek_pemilik(id_user, username):
        proses[id_user] = {"langkah": "pesan_siaran"}
        kirim_pesan(id_user, "🔔 Ketik pesan yang mau disebar ke semua pengguna:")
    elif data == "pengaturan" and cek_pemilik(id_user, username):
        tombol = InlineKeyboardMarkup(row_width=1)
        tombol.add(InlineKeyboardButton("🔑 GANTI KODE AKSES", callback_data="ganti_kode"))
        tombol.add(InlineKeyboardButton("⬅️ KEMBALI", callback_data="kembali"))
        kirim_pesan(id_user, "⚙️ **PENGATURAN ADMIN**", tombol)
    elif data == "ganti_kode" and cek_pemilik(id_user, username):
        proses[id_user] = {"langkah": "kode_baru"}
        kirim_pesan(id_user, "🔑 Masukkan kode akses baru:")
    elif data == "kembali":
        kirim_pesan(id_user, "✅ Kembali ke menu utama", menu_utama(id_user))
    elif data == "hapus" and cek_pemilik(id_user, username):
        proses[id_user] = {"langkah": "konfirmasi_hapus"}
        kirim_pesan(id_user, "⚠️ Ketik `YA HAPUS` untuk bersihkan semua data!")

@bot.message_handler(func=lambda m: m.chat.id in proses)
def input_data(pesan):
    global indeks_gmail, SANDI_UTAMA
    id_user = pesan.chat.id
    username = pesan.from_user.username or ""
    if not cek_akses(id_user, username):
        del proses[id_user]
        return
    langkah = proses[id_user].get("langkah")

    if langkah == "input_email":
        proses[id_user]["email"] = pesan.text.strip()
        proses[id_user]["langkah"] = "input_sandi"
        kirim_pesan(id_user, "🔑 Masukkan Sandi Aplikasi 16 digit:")
    elif langkah == "input_sandi":
        akun = baca_akun()
        akun.append({"email": proses[id_user]["email"], "sandi": pesan.text.strip()})
        simpan_akun(akun)
        catat_log("Tambah Akun", proses[id_user]["email"])
        kirim_pesan(id_user, f"✅ BERHASIL TAMBAH:\n`{proses[id_user]['email']}`", menu_utama(id_user))
        del proses[id_user]
    elif langkah == "input_nomor":
        nomor = cek_nomor(pesan.text)
        if not nomor:
            kirim_pesan(id_user, "❌ Format salah! Awalan +")
            return
        daftar = baca_akun()
        gmail_pakai = daftar[indeks_gmail]
        indeks_gmail = (indeks_gmail + 1) % len(daftar)
        ok, log = kirim_email(gmail_pakai["email"], gmail_pakai["sandi"], TUJUAN_EMAIL,
            f"Banding nomor {nomor}. Mohon verifikasi kembali, terima kasih.",
            "Pemulihan Akun WhatsApp")
        if ok:
            data_baru = {"nomor":nomor, "email":gmail_pakai["email"], "status":"TERKIRIM", "waktu_kirim":time.time()}
            semua = baca_banding()
            semua.append(data_baru)
            simpan_banding(semua)
            catat_log("Kirim Banding", nomor)
            kirim_pesan(id_user, f"✅ TERKIRIM KE:\n{nomor}\nLewat: {gmail_pakai['email']}", menu_utama(id_user))
        else:
            kirim_pesan(id_user, f"❌ GAGAL:\n{log}", menu_utama(id_user))
        del proses[id_user]

    # FITUR ADMIN
    elif langkah == "atur_pengguna" and cek_pemilik(id_user, username):
        teks = pesan.text.strip()
        if teks.lower().startswith("hapus "):
            try:
                target = int(teks.split()[1])
                if target in pengguna_terizin:
                    pengguna_terizin.remove(target)
                    simpan_izin(pengguna_terizin)
                    catat_log("Cabut Akses", f"ID: {target}")
                    kirim_pesan(id_user, f"✅ Akses ID `{target}` dicabut!", menu_utama(id_user))
                else: kirim_pesan(id_user, "❌ ID tidak ditemukan", menu_utama(id_user))
            except: kirim_pesan(id_user, "❌ Format: hapus 123456789", menu_utama(id_user))
        elif teks.isdigit():
            target = int(teks)
            pengguna_terizin.add(target)
            simpan_izin(pengguna_terizin)
            catat_log("Kasih Akses", f"ID: {target}")
            kirim_pesan(id_user, f"✅ Akses diberikan ke ID `{target}`!", menu_utama(id_user))
        else: kirim_pesan(id_user, "❌ Masukkan ID angka saja", menu_utama(id_user))
        del proses[id_user]
    elif langkah == "pesan_siaran" and cek_pemilik(id_user, username):
        isi = pesan.text.strip()
        berhasil = 0
        for uid in list(pengguna_terizin):
            try: kirim_pesan(uid, f"📢 **PENGUMUMAN ADMIN**\n\n{isi}"); berhasil +=1
            except: pass
        kirim_pesan(id_user, f"✅ Pesan terkirim ke {berhasil} pengguna!", menu_utama(id_user))
        catat_log("Pesan Siaran", f"Ke {berhasil} pengguna")
        del proses[id_user]
    elif langkah == "kode_baru" and cek_pemilik(id_user, username):
        SANDI_UTAMA = pesan.text.strip()
        kirim_pesan(id_user, "✅ Kode akses berhasil diubah!", menu_utama(id_user))
        catat_log("Ganti Kode", "Berhasil diubah")
        del proses[id_user]
    elif langkah == "konfirmasi_hapus" and cek_pemilik(id_user, username):
        if pesan.text.strip().upper() == "YA HAPUS":
            simpan_banding([]); simpan_akun([]); gagal_gmail.clear()
            catat_log("Hapus Data", "Semua dibersihkan")
            kirim_pesan(id_user, "✅ SEMUA DATA DIHAPUS!", menu_utama(id_user))
        else: kirim_pesan(id_user, "❌ Dibatalkan", menu_utama(id_user))
        del proses[id_user]

# ==================== JALANKAN BOT ====================
if __name__ == "__main__":
    print("="*65)
    print("🚀 VERSI ADMIN LENGKAP | SIAP DIPAKAI")
    print("🖼️ Gambar aman | ⚡ Cek 1 detik | Fitur Admin Penuh")
    print("="*65)
    threading.Thread(target=pantau_balasan, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"⚠️ Restart: {e}")
            time.sleep(3)
  
