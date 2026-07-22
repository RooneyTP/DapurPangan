# 🌬️ DapurPangan — Pusat Komando Digital untuk IRTP

> Prototipe untuk COMPFEST 18 — AI Innovation Challenge  
> Tema: *AI for the Backbone of the Economy*  
> Fokus: **🏭 Smart Manufacturing** + **🛒 Smart Commerce**

DapurPangan adalah platform dashboard untuk **Industri Rumah Tangga Pangan (IRTP)** — 39 juta produsen makanan skala rumahan di Indonesia.

## Dua Pilar Utama

| Pilar | Fungsi |
|---|---|
| 🏭 **Smart Manufacturing** | Prediksi produksi (ML fine-tuned), manajemen stok, peringatan harga bahan |
| 🛒 **Smart Commerce** | Catatan pesanan, prediksi permintaan, rekomendasi harga, analisis pelanggan |

## Struktur Project

```
DapurPangan/
├── frontend/              ← PWA dashboard (HTML+CSS+JS) [referensi, tunggu Figma]
├── backend/               ← FastAPI backend
│   ├── app/
│   │   ├── main.py        ← App entry + seed data Bu Sumi
│   │   ├── models.py      ← Database models (Product, Stock, Order, Customer...)
│   │   ├── schemas.py     ← Pydantic response models
│   │   ├── services/
│   │   │   ├── predictor.py    ← ML fine-tuning prediksi produksi (scikit-learn)
│   │   │   └── llm.py          ← LLM chat (OpenCodeZen + fallback)
│   │   └── routers/
│   │       ├── production.py   ← Dashboard & prediksi produksi
│   │       ├── stock.py        ← CRUD stok bahan baku
│   │       ├── orders.py       ← Pesanan & pelanggan
│   │       └── chat.py         ← Tanya DapurPangan
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml     ← Backend + PostgreSQL
└── README.md
```

## Cara Jalankan

### Opsi 1: Full Stack (Docker)

```bash
cd DapurPangan
docker compose up -d
# API: http://localhost:8000/docs
# Frontend: buka frontend/index.html
```

### Opsi 2: Backend Only
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API Endpoints

| Method | Endpoint | Modul |
|---|---|---|
| GET | `/api/dashboard` | 🏭 Ringkasan + prediksi produksi |
| GET/POST | `/api/stocks/` | 🏭 Manajemen stok |
| GET/POST | `/api/orders/` | 🛒 Pesanan pelanggan |
| GET | `/api/orders/today` | 🛒 Pesanan hari ini |
| GET | `/api/orders/analytics` | 🛒 Analisis pelanggan |
| POST | `/api/chat` | 🤖 Tanya DapurPangan (LLM + RAG) |
| GET | `/docs` | 📋 Dokumentasi API (Swagger) |

## Machine Learning & Fine-Tuning

**FR-MFG-001 — Prediksi Produksi:**
- Model: LinearRegression (scikit-learn) dengan feature engineering
- Fine-tuning: retrain otomatis setiap ada data produksi baru
- Fitur: hari, tanggal, bulan, flag event liburan
- Output: prediksi + confidence score + upper/lower bound
- Confidence meningkat seiring data: 63% (7 titik) → 91% (30 titik)

**Chatbot:**
- OpenCodeZen API (OpenAI-compatible) + rule-based fallback
- Dual mode: coba LLM dulu, fallback ke response lokal jika offline

## Tech Stack

| Layer | Teknologi |
|---|---|
| Frontend | HTML5 + CSS3 + Vanilla JS (referensi) |
| Backend | Python FastAPI + SQLAlchemy |
| Database | PostgreSQL 16 |
| ML Model | scikit-learn (fine-tuned daily) |
| LLM | OpenCodeZen (OpenAI-compatible) |
| Container | Docker Compose |

---

*DapurPangan v0.2 — Fokus Smart Manufacturing + Smart Commerce*  
*Dibuat untuk COMPFEST 18 AI Innovation Challenge*
