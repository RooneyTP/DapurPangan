# 🌬️ DapurPangan — Pusat Komando Digital untuk IRTP

> Prototipe untuk COMPFEST 18 — AI Innovation Challenge  
> Tema: *AI for the Backbone of the Economy*  
> Fokus: **🏭 Smart Manufacturing** + **🛒 Smart Commerce**

DapurPangan adalah platform dashboard untuk **Industri Rumah Tangga Pangan (IRTP)** — 39 juta produsen makanan skala rumahan di Indonesia.

## Prasyarat

Sebelum menjalankan, pastikan sudah install:

| Opsi | Wajib Install | Catatan |
|---|---|---|
| **Opsi 1 (Docker)** | [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Cara paling mudah — database & backend otomatis |
| **Opsi 2 (Tanpa Docker)** | [Python 3.11+](https://www.python.org/downloads/) | Untuk menjalankan backend langsung |
| **Keduanya** | [Git](https://git-scm.com/downloads) | Untuk mengambil kode dari GitHub |

## Cara Dapatkan Kode

```bash
git clone https://github.com/RooneyTP/DapurPangan.git
cd DapurPangan
```

> Sudah punya foldernya? Langsung `cd DapurPangan` saja.

## Dua Pilar Utama

| Pilar | Fungsi |
|---|---|
| 🏭 **Smart Manufacturing** | Prediksi produksi (ML fine-tuned), manajemen stok, peringatan harga bahan |
| 🛒 **Smart Commerce** | Catatan pesanan, rekomendasi harga, rekomendasi harga jual, chat AI |

## Struktur Project

```
DapurPangan/
├── frontend/              ← Website tim (landing page + dashboard AI)
│   ├── HTML/
│   │   ├── index.html         ← Landing page
│   │   └── AI Dashboard.html  ← Dashboard AI (chat, harga, stok, pesanan, pelanggan)
│   ├── CSS/                   ← Styling
│   ├── JS/script.js           ← Logika + integrasi API
│   └── Image/                 ← Logo & asset SVG
├── backend/               ← FastAPI backend
│   ├── app/
│   │   ├── main.py        ← App entry + seed data Bu Sumi
│   │   ├── models.py      ← Database models (Product, Stock, Order, Customer, Recipe)
│   │   ├── schemas.py     ← Pydantic response models
│   │   ├── services/
│   │   │   ├── predictor.py    ← ML fine-tuning prediksi produksi (scikit-learn)
│   │   │   ├── llm.py          ← LLM chat (OpenCodeZen + fallback)
│   │   │   ├── pricing.py      ← Rekomendasi harga jual
│   │   │   └── prices.py       ← Peringatan harga komoditas (Bapanas + fallback)
│   │   └── routers/
│   │       ├── production.py   ← Dashboard & prediksi produksi
│   │       ├── stock.py        ← CRUD stok bahan baku
│   │       ├── orders.py       ← Pesanan & pelanggan
│   │       ├── pricing.py      ← Endpoint rekomendasi harga
│   │       ├── prices.py       ← Endpoint peringatan harga
│   │       ├── recipe.py       ← CRUD resep produk
│   │       └── chat.py         ← Tanya DapurPangan
│   ├── .env.example        ← Template API key (salin ke .env)
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml     ← Backend + PostgreSQL
└── README.md
```

## Cara Jalankan

### Opsi 1: Full Stack (Docker) — direkomendasikan

> **Penting:** pastikan Docker Desktop sudah **terbuka & berjalan** (tunggu logo Docker di system tray hijau) sebelum lanjut.

```bash
# 1. Setup API key chat (sekali saja, OPSIONAL — lihat penjelasan di bawah)
# Windows (CMD/PowerShell):
copy backend\.env.example backend\.env
# macOS / Linux / Git Bash:
# cp backend/.env.example backend/.env
# lalu edit backend/.env → isi OPencodeZen_API_KEY (pakai Notepad/VS Code)

# 2. Jalankan (butuh beberapa menit saat pertama kali — download image)
docker compose up -d

# 3. Cek backend hidup: buka http://localhost:8000/docs (harus muncul Swagger UI)

# 4. Buka dashboard: frontend/HTML/AI Dashboard.html (double-click file)
```

> **Apa itu `.env` dan `OPencodeZen_API_KEY`?**
> `.env` adalah file konfigurasi rahasia (tidak ikut di-upload ke GitHub). Isinya API key untuk chat AI.
> - **Tidak punya API key? TIDAK MASALAH** — chat tetap bisa dipakai dengan jawaban bawaan (fallback), hanya kurang "cerdas".
> - Mau key gratis: daftar di opencode.ai → buat API key → tempel ke `backend/.env` menggantikan `OPencodeZen_API_KEY=...`.

> Data contoh (Bu Sumi: tempe, stok, 4 pelanggan, 14 hari pesanan) di-seed otomatis saat pertama kali jalan.

### Opsi 2: Backend Only (tanpa Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# API: http://localhost:8000/docs
# Dashboard: buka frontend/HTML/AI Dashboard.html di browser
```

> Tanpa Docker, backend memakai database SQLite lokal (`backend/daparpangan.db`) — cukup untuk dicoba. Untuk produksi pakai Docker (PostgreSQL).

## Troubleshooting

| Masalah | Penyebab & Solusi |
|---|---|
| `docker compose up -d` error / tidak jalan | Docker Desktop belum dibuka → buka dulu & tunggu sampai siap |
| `http://localhost:8000/docs` tidak terbuka | Backend belum selesai start → tunggu 1-2 menit, lalu `docker compose logs backend` untuk lihat log |
| Dashboard tidak menampilkan data | Pastikan backend SUDAH jalan dulu, baru buka dashboard |
| Chat menjawab "Maaf, saya belum paham" terus | API key kosong/salah → chat pakai jawaban fallback. Isi `backend/.env` dengan key valid, lalu `docker compose restart backend` |
| Port 8000 sudah dipakai program lain | Matikan program itu, atau ganti port di `docker-compose.yml` (`8000:8000` → `8001:8000`) lalu akses `http://localhost:8001/docs` |
| Ingin reset data demo | `docker compose down -v && docker compose up -d` (menghapus database & seed ulang) |

## Coba Fitur (Walkthrough 5 Menit)

1. **Dashboard** — buka `http://localhost:8000/docs` → expand `GET /api/dashboard` → **Try it out** → Execute. Lihat prediksi produksi, status stok, insight pelanggan.
2. **Rekomendasi harga** — `GET /api/pricing/recommendation` → Execute → dapat harga jual minimal & optimal.
3. **Chat AI** — buka `frontend/HTML/AI Dashboard.html` → tab **AI Chat** → tanya *"berapa produksi besok?"* atau *"stok apa yang perlu dibeli?"*.
4. **Input data** — di dashboard HTML: tab **Stok Bahan** → Tambah Data; tab **Pesanan** → tambah pesanan baru.
5. **Reset data** kalau sudah berantakan: lihat tabel Troubleshooting di atas.

## API Endpoints

| Method | Endpoint | Modul |
|---|---|---|
| GET | `/api/dashboard` | 🏭 Ringkasan + prediksi produksi (ML fine-tuned) |
| GET | `/api/products` | 🏭 Daftar produk |
| GET/POST | `/api/stocks/` | 🏭 Manajemen stok (+ `PATCH /{stock_id}/adjust`) |
| GET/POST | `/api/recipes/` | 🏭 CRUD resep produk |
| GET | `/api/recipes/product/{product_id}` | 🏭 Bahan per produk |
| PATCH/DELETE | `/api/recipes/{recipe_id}` | 🏭 Ubah/hapus bahan resep |
| GET/POST | `/api/orders/` | 🛒 Pesanan pelanggan |
| GET | `/api/orders/today` | 🛒 Pesanan hari ini |
| GET/POST | `/api/customers` | 🛒 Pelanggan |
| GET | `/api/pricing/recommendation` | 🛒 Rekomendasi harga jual |
| GET | `/api/prices/` | 🏭 Harga komoditas |
| GET | `/api/prices/alerts` | 🏭 Peringatan harga (naik/turun >10%) |
| POST | `/api/chat` | 🤖 Tanya DapurPangan (LLM + fallback) |
| GET | `/docs` | 📋 Dokumentasi API (Swagger) |

## Machine Learning & Fine-Tuning

**FR-MFG-001 — Prediksi Produksi:**
- Model: LinearRegression (scikit-learn) dengan feature engineering
- Fine-tuning: retrain otomatis setiap ada data produksi baru
- Fitur: hari, tanggal, bulan, flag event liburan
- Output: prediksi + confidence score + upper/lower bound
- Confidence meningkat seiring data: 63% (7 titik) → 91% (30 titik)

**FR-COM-002 — Rekomendasi Harga Jual:**
- Hitung biaya produksi dari resep × harga bahan baku (tabel stok)
- Output: harga minimal (margin target) + harga optimal (dibatasi harga pasar)

**Chatbot:**
- OpenCodeZen API (OpenAI-compatible, model `deepseek-v4-flash-free`) + rule-based fallback
- Dual mode: coba LLM dulu, fallback ke response lokal jika offline/rate-limit

## Tech Stack

| Layer | Teknologi |
|---|---|
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Backend | Python FastAPI + SQLAlchemy |
| Database | PostgreSQL 16 |
| ML Model | scikit-learn (fine-tuned daily) |
| LLM | DeepSeek V4 Flash via OpenCodeZen |
| Container | Docker Compose |

---

*DapurPangan v0.1.0 — Fokus Smart Manufacturing + Smart Commerce*  
*Dibuat untuk COMPFEST 18 AI Innovation Challenge*
