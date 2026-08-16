# 🌬️ DapurPangan — Pusat Komando Digital untuk IRTP

> Prototipe untuk COMPFEST 18 — AI Innovation Challenge  
> Tema: *AI for the Backbone of the Economy*  
> Fokus: **🏭 Smart Manufacturing** + **🛒 Smart Commerce**

DapurPangan adalah platform dashboard untuk **Industri Rumah Tangga Pangan (IRTP)** — 39 juta produsen makanan skala rumahan di Indonesia.

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

```bash
cd DapurPangan

# 1. Setup API key chat (sekali saja)
cp backend/.env.example backend/.env
# lalu edit backend/.env → isi OPencodeZen_API_KEY

# 2. Jalankan
docker compose up -d

# API docs: http://localhost:8000/docs
# Frontend: buka frontend/HTML/AI Dashboard.html di browser
```

> Data contoh (Bu Sumi: tempe, stok, 4 pelanggan, 14 hari pesanan) di-seed otomatis saat pertama kali jalan.

### Opsi 2: Backend Only (tanpa Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# API: http://localhost:8000/docs
```

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

*DapurPangan v0.2 — Fokus Smart Manufacturing + Smart Commerce*  
*Dibuat untuk COMPFEST 18 AI Innovation Challenge*
