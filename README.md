# 📋 Pastely

Platform modern untuk berbagi teks, kode, dan link. Mirip JustPaste.it tapi lebih keren.

**Stack:** Flask · Supabase · Tailwind CSS · highlight.js

---

## 🚀 Setup Lokal

### 1. Clone & install dependencies

```bash
cd pastely
pip install -r requirements.txt
```

### 2. Konfigurasi environment

```bash
cp .env.example .env
```

Edit `.env` dan isi:
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...  (anon key, bukan service key)
SECRET_KEY=isi-dengan-string-acak-panjang
```

### 3. Setup database Supabase

1. Buka project Supabase kamu
2. Pergi ke **SQL Editor**
3. Copy-paste isi `schema.sql` dan jalankan

### 4. Jalankan aplikasi

```bash
python app.py
```

Buka `http://localhost:5000`

---

## ☁️ Deploy ke Vercel

1. Push project ke GitHub
2. Import ke Vercel
3. Tambahkan environment variables di Settings → Environment Variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SECRET_KEY`
4. Deploy!

`vercel.json` sudah dikonfigurasi untuk Flask.

---

## 📁 Struktur Project

```
pastely/
├── app.py              # Entry point Flask
├── config.py           # Konfigurasi dari .env
├── schema.sql          # SQL untuk Supabase
├── requirements.txt
├── vercel.json
├── routes/
│   ├── paste.py        # Buat, lihat, edit, hapus paste
│   ├── auth.py         # Login, register, profil
│   └── dashboard.py    # Dashboard user
├── static/
│   ├── css/style.css   # Custom CSS
│   └── js/main.js      # Script utama
└── templates/          # Jinja2 templates
```

---

## ✨ Fitur

- **3 mode paste:** Teks, Kode (syntax highlight), Link (redirect preview + countdown)
- **Auth username + PIN 4 angka** — tanpa email
- **Visibilitas:** Publik / Unlisted / Privat (password)
- **Kedaluwarsa:** 1 jam, 1 hari, 7 hari, 30 hari
- **Burn after read** — otomatis hapus setelah dibuka
- **Dashboard** — kelola semua paste
- **Profil publik** — `/u/<username>`
- **Fork paste** — clone paste orang lain
- **Pencarian** — cari paste publik berdasarkan judul
- **WIB timezone** — semua waktu tampil dalam WIB
- **Fully responsive** — mobile-first
