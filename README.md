# DapurPangan - Pusat Komando Digital untuk IRTP

> Prototipe untuk COMPFEST 18 - AI Innovation Challenge
> Tema: *AI for the Backbone of the Economy*
> Fokus: **Smart Manufacturing** + **Smart Commerce**

DapurPangan adalah platform dashboard untuk **Industri Rumah Tangga Pangan (IRTP)** - 39 juta produsen makanan skala rumahan di Indonesia.

## Fitur Utama

### Smart Manufacturing

- **Prediksi produksi harian** - model ML (scikit-learn) yang di-fine-tune otomatis dari riwayat produksi. Output: prediksi + confidence score + batas atas/bawah.
- **Rekomendasi beli stok otomatis** - hitung kebutuhan bahan dari prediksi produksi x resep - stok yang ada -> saran "Beli X kg" per bahan baku.
- **Resep & takaran bahan** - CRUD lengkap: produk, bahan, takaran, satuan. Satu produk bisa punya banyak bahan.
- **Cek kecukupan bahan untuk pesanan** - masukkan jumlah produk -> sistem hitung kebutuhan tiap bahan dari resep, bandingkan dengan stok -> notifikasi **CUKUP** / **TIDAK CUKUP** + rincian kurang berapa per bahan.
- **Peringatan harga bahan** - pantau harga komoditas dari Bapanas + fallback otomatis, alert saat naik/turun >= 10%.

### Smart Commerce

- **Catatan pesanan B2B per pelanggan** - riwayat pesanan tiap pelanggan + **proyeksi pesanan** (share riwayat 14 hari x prediksi) + alert saat tren turun >= 20%.
- **Penjualan per individu (B2C)** - catat jumlah individu x beli per orang, plus **prediksi produksi besok** (jumlah pembeli & unit) dari data penjualan - notifikasi H-1 di section Pesanan.
- **Rekomendasi harga jual** - biaya produksi dihitung dari resep x harga stok + margin, dibatasi harga pasar -> harga minimal & optimal.
- **Chat AI + AI data entry** - tanya jawab bahasa Indonesia; perintah langsung disimpan ke database, contoh:
  - "hari ini ada 100 pelanggan yang masing masing beli 1 tempe"
  - "tambah pelanggan Budi, Jl. Kenanga 5, 081234567890"
  - "stok kedelai 50 kg"
  - "pesanan Warung A 30"
  - Jika API LLM kena rate limit, jawaban fallback otomatis dibaca dari data live database.

### Umum

- **Edit & hapus data** - stok, pesanan, penjualan, pelanggan, resep, plus form edit parameter harga.
- **Import CSV dengan template** - stok, pesanan, pelanggan, penjualan. Laporan per baris: N berhasil, M gagal + alasan.

## Prasyarat

Sebelum menjalankan, pastikan sudah install:

| Opsi | Wajib Install | Catatan |
|---|---|---|
| **Opsi 1 (Docker)**| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Cara paling mudah - database & backend otomatis |
| **Opsi 2 (Tanpa Docker)**| [Python 3.11+](https://www.python.org/downloads/) | Untuk menjalankan backend langsung |
| **Keduanya**| [Git](https://git-scm.com/downloads) | Untuk mengambil kode dari GitHub |

## Cara Dapatkan Kode

```bash
git clone https://github.com/RooneyTP/DapurPangan.git
cd DapurPangan
```

> Sudah punya foldernya? Langsung `cd DapurPangan` saja.

## Struktur Project

```text
DapurPangan/
|-- frontend/                (Website tim: landing page + dashboard AI)
|   |-- HTML/
|   |   |-- index.html            (Landing page)
|   |   |-- AI Dashboard.html     (Dashboard: chat, stok, pesanan, penjualan, resep, import)
|   |-- CSS/
|   |   |-- style.css             (Styling landing page)
|   |   |-- AI Dashboard.css      (Styling dashboard)
|   |-- JS/
|   |   |-- script.js             (Logika + integrasi API)
|   |-- Image/                    (Logo & asset SVG)
|-- backend/                 (FastAPI backend)
|   |-- app/
|   |   |-- main.py               (App entry + seed data Bu Sumi)
|   |   |-- models.py             (Database models: Product, Stock, Order, Customer, Recipe, Sale)
|   |   |-- schemas.py            (Pydantic response models)
|   |   |-- services/
|   |   |   |-- predictor.py      (ML fine-tuning prediksi produksi - scikit-learn)
|   |   |   |-- llm.py            (LLM chat: OpenCodeZen + fallback)
|   |   |   |-- pricing.py        (Rekomendasi harga jual)
|   |   |   |-- prices.py         (Peringatan harga komoditas: Bapanas + fallback)
|   |   |   |-- data_entry.py     (AI data entry: parse perintah -> simpan data)
|   |   |-- routers/
|   |   |   |-- production.py     (Dashboard & prediksi produksi)
|   |   |   |-- stock.py          (CRUD stok + rekomendasi beli)
|   |   |   |-- orders.py         (Pesanan, proyeksi pesanan, pelanggan)
|   |   |   |-- sales.py          (Penjualan B2C + prediksi penjualan)
|   |   |   |-- pricing.py        (Endpoint rekomendasi harga)
|   |   |   |-- prices.py         (Endpoint peringatan harga)
|   |   |   |-- recipe.py         (CRUD resep + cek kecukupan bahan)
|   |   |   |-- chat.py           (Tanya DapurPangan + AI data entry)
|   |   |   |-- importer.py       (Import CSV: stok, pelanggan, pesanan, penjualan)
|   |-- .env.example              (Template API key - salin ke .env)
|   |-- Dockerfile
|   |-- requirements.txt
|-- docker-compose.yml       (Backend + PostgreSQL)
|-- README.md
```

## Cara Jalankan

### Opsi 1: Full Stack (Docker) - direkomendasikan

> **Penting:** pastikan Docker Desktop sudah **terbuka & berjalan** (tunggu logo Docker di system tray hijau) sebelum lanjut.

```bash
# 1. Setup API key chat (sekali saja, OPSIONAL - lihat penjelasan di bawah)
# Windows (CMD/PowerShell):
copy backend\.env.example backend\.env
# macOS / Linux / Git Bash:
# cp backend/.env.example backend/.env
# lalu edit backend/.env -> isi OPencodeZen_API_KEY (pakai Notepad/VS Code)

# 2. Jalankan (butuh beberapa menit saat pertama kali - download image)
docker compose up -d

# 3. Cek backend hidup: buka http://localhost:8000/docs (harus muncul Swagger UI)

# 4. Buka dashboard: frontend/HTML/AI Dashboard.html (double-click file)
```

> **Apa itu `.env` dan `OPencodeZen_API_KEY`?**
> `.env` adalah file konfigurasi rahasia (tidak ikut di-upload ke GitHub). Isinya API key untuk chat AI.
> - **Tidak punya API key? TIDAK MASALAH** - chat tetap bisa dipakai dengan jawaban bawaan (fallback), hanya kurang "cerdas".
> - Mau key gratis: daftar di opencode.ai -> buat API key -> tempel ke `backend/.env` menggantikan `OPencodeZen_API_KEY=...`.

> Data contoh (Bu Sumi: tempe, stok, 4 pelanggan, 14 hari pesanan) di-seed otomatis saat pertama kali jalan.

### Opsi 2: Backend Only (tanpa Docker)

```bash
cd backend
pip install -r requirements.txt
# WAJIB: set env DATABASE_URL sqlite dulu (lihat catatan di bawah)
# Windows CMD:
set DATABASE_URL=sqlite:///./daparpangan.db
# macOS / Linux / Git Bash:
# export DATABASE_URL=sqlite:///./daparpangan.db
python -m uvicorn app.main:app --reload
# API: http://localhost:8000/docs
# Dashboard: buka frontend/HTML/AI Dashboard.html di browser
```

> **Catatan:** TANPA env `DATABASE_URL`, backend otomatis memakai SQLite lokal (`backend/daparpangan.db`, dibuat saat pertama kali start) - mode lokal tanpa Docker langsung jalan. Env `DATABASE_URL` HANYA perlu di-set untuk pindah ke PostgreSQL (docker-compose sudah menyetelnya otomatis ke `db:5432`). File database `backend/daparpangan.db` dibuat otomatis saat pertama kali jalan. Untuk produksi tetap pakai Docker (PostgreSQL).

## Troubleshooting

| Masalah | Penyebab & Solusi |
|---|---|
| `docker compose up -d` error / tidak jalan | Docker Desktop belum dibuka -> buka dulu & tunggu sampai siap |
| `http://localhost:8000/docs` tidak terbuka | Backend belum selesai start -> tunggu 1-2 menit, lalu `docker compose logs backend` untuk lihat log |
| Dashboard tidak menampilkan data | Pastikan backend SUDAH jalan dulu, baru buka dashboard |
| "connection refused" / error port 5432 saat start tanpa Docker | Belum set env `DATABASE_URL` sqlite -> lihat Opsi 2: set `DATABASE_URL=sqlite:///./daparpangan.db` dulu sebelum uvicorn |
| Chat menjawab "Maaf..." atau data terlihat basi | API LLM gratis kena rate limit -> fallback otomatis baca data live DB; isi `backend/.env` dengan key valid untuk jawaban LLM |
| Dua server uvicorn jalan bersamaan | Jangan jalankan dua server uvicorn sekaligus di port 8000 -> matikan yang lama (Ctrl+C) dulu, atau ganti port dengan `--port` |
| Chat menjawab "Maaf, saya belum paham" terus | API key kosong/salah -> chat pakai jawaban fallback. Isi `backend/.env` dengan key valid, lalu `docker compose restart backend` |
| Port 8000 sudah dipakai program lain | Matikan program itu, atau ganti port di `docker-compose.yml` (`8000:8000` -> `8001:8000`) lalu akses `http://localhost:8001/docs` |
| Ingin reset data demo | `docker compose down -v && docker compose up -d` (menghapus database & seed ulang) |

## Coba Fitur (Walkthrough 5 Menit)

1. **Dashboard** - buka `http://localhost:8000/docs` -> expand `GET /api/dashboard` -> **Try it out** -> Execute. Lihat prediksi produksi, status stok, insight pelanggan.
2. **Cek kecukupan bahan** - `GET /api/recipes/check` -> masukkan jumlah produk -> lihat notifikasi CUKUP / TIDAK CUKUP + rincian kekurangan.
3. **Rekomendasi beli stok** - `GET /api/stocks/recommendations` -> Execute -> dapat saran "Beli X kg" per bahan baku.
4. **Rekomendasi harga** - `GET /api/pricing/recommendation` -> Execute -> dapat harga jual minimal & optimal.
5. **Chat AI + AI data entry** - buka `frontend/HTML/AI Dashboard.html` -> tab **AI Chat** -> tanya *"berapa produksi besok?"* atau ketik perintah seperti *"stok kedelai 50 kg"*.
6. **Import CSV** - tombol **Import CSV** di tiap section -> upload file CSV sesuai template -> lihat laporan per baris (N berhasil, M gagal).
7. **Edit & hapus data** - di dashboard HTML: tab **Stok Bahan** / **Pesanan** / **Penjualan** / **Pelanggan** -> Edit atau Hapus; tambah data baru lewat tombol Tambah Data.
8. **Reset data** kalau sudah berantakan: lihat tabel Troubleshooting di atas.

## API Endpoints

| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/api/dashboard` | Ringkasan + prediksi produksi (ML fine-tuned) |
| GET | `/api/products` | Daftar produk |
| GET/POST | `/api/stocks/` | Manajemen stok bahan baku |
| PUT/DELETE | `/api/stocks/{id}` | Edit / hapus stok |
| PATCH | `/api/stocks/{id}/adjust` | Penyesuaian stok (masuk/keluar) |
| GET | `/api/stocks/recommendations` | Rekomendasi beli stok otomatis |
| GET/POST | `/api/orders/` | Pesanan pelanggan (B2B) |
| PUT/DELETE | `/api/orders/{id}` | Edit / hapus pesanan |
| GET | `/api/orders/today` | Pesanan hari ini |
| GET | `/api/orders/projection` | Proyeksi pesanan (share 14 hari x prediksi, alert turun >= 20%) |
| GET/POST | `/api/customers` | Pelanggan |
| PUT/DELETE | `/api/customers/{id}` | Edit / hapus pelanggan |
| GET/POST | `/api/sales/` | Penjualan per individu (B2C) |
| PUT/DELETE | `/api/sales/{id}` | Edit / hapus penjualan |
| GET | `/api/sales/today` | Penjualan hari ini |
| GET | `/api/sales/prediction` | Prediksi produksi besok (jumlah pembeli & unit) |
| GET/POST | `/api/recipes/` | Resep & takaran bahan (CRUD) |
| PATCH/DELETE | `/api/recipes/{id}` | Ubah / hapus bahan resep |
| GET | `/api/recipes/check` | Cek kecukupan bahan (CUKUP / TIDAK CUKUP) |
| GET | `/api/recipes/product/{product_id}` | Bahan per produk |
| GET | `/api/pricing/recommendation` | Rekomendasi harga jual |
| GET | `/api/prices/` | Harga komoditas |
| GET | `/api/prices/alerts` | Peringatan harga (naik/turun >= 10%) |
| POST | `/api/chat` | Tanya DapurPangan + AI data entry (LLM + fallback) |
| GET | `/api/chat/history` | Riwayat percakapan chat (memori percakapan) |
| POST | `/api/import/stocks` | Import CSV stok (laporan per baris) |
| POST | `/api/import/customers` | Import CSV pelanggan (laporan per baris) |
| POST | `/api/import/orders` | Import CSV pesanan (laporan per baris) |
| POST | `/api/import/sales` | Import CSV penjualan (laporan per baris) |
| GET | `/docs` | Dokumentasi API (Swagger) |

## Machine Learning & Fine-Tuning

**FR-MFG-001 - Prediksi Produksi:**
- Model: LinearRegression (scikit-learn) dengan feature engineering
- Fine-tuning: model produksi di-train ulang saat server start dari riwayat di
  database; model penjualan B2C di-retrain setiap pemanggilan prediksi; tidak
  ada jalur input data produksi baru selain seed/riwayat di database
- Fitur: hari, tanggal, bulan, penanda akhir tahun (Desember >= 20)
- Output: prediksi + confidence score + upper/lower bound
- Confidence meningkat seiring data: 63% (7 titik) -> 91% (30 titik)

**FR-MFG-002 - Rekomendasi Beli Stok:**
- Hitung kebutuhan bahan = prediksi produksi x takaran resep - stok yang ada
- Output: daftar bahan yang perlu dibeli + jumlah ("Beli X kg")

**FR-COM-001 - Proyeksi Pesanan B2B:**
- Share riwayat pesanan 14 hari x prediksi produksi per pelanggan
- Alert otomatis saat tren pesanan turun >= 20%

**FR-COM-002 - Rekomendasi Harga Jual:**
- Hitung biaya produksi dari resep x harga bahan baku (tabel stok)
- Output: harga minimal (margin target) + harga optimal (dibatasi harga pasar)

**FR-COM-003 - Prediksi Penjualan B2C:**
- Model: LinearRegression (scikit-learn, instance `sales_predictor`) - SUDAH fine-tuned
  otomatis dari riwayat penjualan B2C (retrain dari database setiap kali
  diprediksi; live: 35 data points, confidence 92%)
- Prediksi produksi besok dari data penjualan: jumlah pembeli & unit
- Notifikasi H-1 di section Pesanan

**Chatbot & AI Data Entry:**
- OpenCodeZen API (OpenAI-compatible, model `deepseek-v4-flash-free`) + rule-based fallback
- Dual mode: coba LLM dulu, fallback ke response lokal jika offline/rate-limit
- AI data entry: perintah bahasa Indonesia diparse lalu langsung disimpan ke database
- KONTEKS DATABASE (RAG sederhana): sebelum LLM menjawab, sistem membaca data live
  dari database (stok terkini, prediksi produksi, prediksi penjualan, rekomendasi
  harga, top pelanggan) lalu menyisipkannya ke prompt - jawaban selalu berbasis
  data aktual, bukan angka basi
- MEMORI CHAT: riwayat percakapan disimpan di database dan dipakai sebagai konteks
  jawaban berikutnya (percakapan berlanjut, tidak dimulai dari nol setiap pesan)
- Catatan jujur: chatbot TIDAK di-fine-tune karena memakai LLM pihak ketiga via API;
  model yang di-fine-tune adalah 2 predictor prediksi (FR-MFG-001 & FR-COM-003)

## Tech Stack

| Layer | Teknologi |
|---|---|
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Backend | Python FastAPI + SQLAlchemy |
| Database | PostgreSQL 16 (Docker) / SQLite (lokal tanpa Docker) |
| ML Model | scikit-learn (fine-tuned daily) |
| LLM | DeepSeek V4 Flash via OpenCodeZen |
| Container | Docker Compose |

---

*DapurPangan v0.1.0 - Fokus Smart Manufacturing + Smart Commerce*
*Dibuat untuk COMPFEST 18 AI Innovation Challenge*
