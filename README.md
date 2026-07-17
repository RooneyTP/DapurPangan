# 🌬️ Zephyrus — Pusat Komando Digital untuk IRTP

> **Rebrand dari DapurPangan AI**  
> Prototipe untuk COMPFEST 18 — AI Innovation Challenge  
> Tema: *AI for the Backbone of the Economy*

Zephyrus adalah platform dashboard terintegrasi untuk **Industri Rumah Tangga Pangan (IRTP)** — 39 juta produsen makanan skala rumahan di Indonesia.

## Tiga Pilar

| Pilar | Fungsi |
|---|---|
| 🏭 **Smart Manufacturing** | Prediksi produksi, manajemen stok, peringatan harga bahan |
| 📦 **Smart Logistics** | Optimasi rute kirim, status pengiriman, prediksi basi |
| 🛒 **Smart Commerce** | Catatan pesanan, prediksi permintaan, rekomendasi harga |

## Struktur Project

```
Zephyrus/
├── frontend/              ← PWA dashboard (HTML+CSS+JS)
│   ├── index.html         ← Dashboard utama "Dapur Hari Ini"
│   ├── js/app.js          ← API client (fetch dari backend)
│   ├── manifest.json      ← PWA manifest
│   └── sw.js              ← Service Worker (offline cache)
├── backend/               ← FastAPI backend
│   ├── app/
│   │   ├── main.py        ← App entry + seed data
│   │   ├── database.py    ← SQLAlchemy config
│   │   ├── models.py      ← Database models
│   │   ├── schemas.py     ← Pydantic schemas
│   │   └── routers/
│   │       ├── production.py  ← Dashboard & produksi
│   │       ├── stock.py       ← Manajemen stok
│   │       ├── orders.py      ← Pesanan & pelanggan
│   │       └── chat.py        ← Chat AI sederhana
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml     ← Backend + PostgreSQL
├── .gitignore
└── README.md
```

## Cara Jalankan

### Opsi 1: Frontend Only (Static)
Buka `frontend/index.html` langsung di browser.
Data static/mock — cocok untuk demo cepat.

### Opsi 2: Full Stack (Docker)

```bash
# Clone / masuk folder project
cd Zephyrus

# Jalankan backend + database
docker compose up -d

# Buka:
# - Dashboard: http://localhost:8000 (redirect ke /docs)
# - API Docs:  http://localhost:8000/docs
# - Frontend:  buka frontend/index.html di browser
```

API akan tersedia di `http://localhost:8000/api`.

### Opsi 3: Backend Only (Dev)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API Endpoints

| Method | Endpoint | Keterangan |
|---|---|---|
| GET | `/api/dashboard` | Ringkasan "Dapur Hari Ini" |
| GET | `/api/stocks/` | Daftar stok bahan baku |
| POST | `/api/stocks/` | Tambah stok baru |
| PATCH | `/api/stocks/{id}/adjust` | Ubah jumlah stok |
| GET | `/api/customers` | Daftar pelanggan |
| GET | `/api/orders` | Semua pesanan |
| GET | `/api/orders/today` | Pesanan hari ini |
| POST | `/api/orders` | Buat pesanan baru |
| GET | `/api/orders/analytics` | Analisis pelanggan |
| POST | `/api/chat` | Tanya Zephyrus (rule-based) |

## Tech Stack

| Layer | Teknologi |
|---|---|
| Frontend | HTML5 + CSS3 + Vanilla JS (PWA) |
| Backend | Python FastAPI + SQLAlchemy |
| Database | PostgreSQL 16 |
| Container | Docker Compose |
| Deployment | `docker compose up` |

## Persyaratan AIC COMPFEST 18

- ✅ **MVP Scope**: UI input-output sederhana, backend sinkron, AI static inference
- ✅ **Docker Compose**: Backend siap dijalankan dengan `docker compose up`
- ✅ **Frontend**: PWA mobile-first, Bahasa Indonesia
- ✅ **GitHub**: Source code di repository ini

---

*Zephyrus v0.1 — Dibuat untuk COMPFEST 18 AI Innovation Challenge*
