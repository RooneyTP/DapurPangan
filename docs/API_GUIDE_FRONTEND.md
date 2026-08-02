# 📡 Panduan API DapurPangan untuk Frontend

> Panduan ini khusus untuk developer frontend. Backend sudah siap — tinggal dipanggil.

## 1. Cara Menjalankan Backend

```bash
cd DapurPangan
docker compose up -d
# API: http://localhost:8000
# Dokumentasi interaktif: http://localhost:8000/docs (SWAGGER!)
```

**Tanpa Docker (dev cepat):**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## 2. Aturan Dasar

| Hal | Nilai |
|---|---|
| **Base URL** | `http://localhost:8000/api` |
| **Format data** | JSON |
| **CORS** | ✅ Sudah di-enable — frontend boleh dari mana aja |
| **Auth** | Belum ada (akan ditambah) |
| **Port** | 8000 |

**Contoh fetch sederhana:**
```js
const API = 'http://localhost:8000/api';

async function getDashboard() {
  const res = await fetch(`${API}/dashboard`);
  const data = await res.json();
  console.log(data);
}
```

---

## 3. Daftar Endpoint Lengkap

### 🏠 Dashboard — `GET /api/dashboard`
**Response:**
```json
{
  "greeting": "🌅 Selamat pagi, Bu Sumi!",
  "date": "Jumat, 17 Juli 2026",
  "recommendation": {
    "product": "Tempe",
    "quantity": 200,
    "lower_bound": 192,
    "upper_bound": 208,
    "confidence": "●●●●●●○○○○ 63%",
    "fine_tuned": true,
    "data_points": 7
  },
  "stock_alerts": [
    { "name": "Kedelai", "qty": "50 kg", "status": "🟢 AMAN" },
    { "name": "Ragi", "qty": "0.08 kg", "status": "🔴 KRITIS - BELI!" }
  ],
  "customer_insights": [
    { "name": "Kantin D", "trend": "⬇️ turun 30%", "note": "Cek apakah ada masalah?" }
  ],
  "price_alerts": [
    { "commodity": "Kedelai", "change": "naik 12%", "detail": "..." }
  ]
}
```
**💡 Dipakai untuk:** halaman utama "Dapur Hari Ini" — rekomendasi produksi, status stok, insight.

---

### 📦 Stok Bahan Baku

#### List stok — `GET /api/stocks/`
```json
[
  {
    "id": 1,
    "ingredient_name": "Kedelai",
    "quantity": 50,
    "unit": "kg",
    "price_per_unit": 11500,
    "min_warning": 15,
    "min_critical": 5,
    "status": "aman",
    "updated_at": "2026-07-17T..."
  }
]
```
**💡 `status` sudah dihitung backend:** `aman` / `waspada` / `kritis`.

#### Tambah stok — `POST /api/stocks/`
```json
// Request body:
{
  "ingredient_name": "Gula",
  "quantity": 10,
  "unit": "kg",
  "price_per_unit": 18000
}
```

#### Ubah jumlah stok — `PATCH /api/stocks/{id}/adjust?delta=-5`
`delta` bisa negatif (stok berkurang) atau positif (stok bertambah).
**Response:** `{ "message": "Stok Gula = 5 kg" }`

---

### 🛒 Pesanan & Pelanggan

#### List pesanan — `GET /api/orders`
```json
[
  {
    "id": 1,
    "customer_id": 1,
    "product_id": 1,
    "date": "2026-07-17",
    "quantity": 30,
    "status": "pending",
    "customer_name": "Warung A",
    "product_name": "Tempe"
  }
]
```

#### Pesanan hari ini — `GET /api/orders/today`
Sama formatnya, tapi hanya pesanan tanggal hari ini.

#### Buat pesanan — `POST /api/orders`
```json
{
  "customer_id": 1,
  "product_id": 1,
  "date": "2026-07-17",
  "quantity": 35,
  "status": "pending"
}
```

#### List pelanggan — `GET /api/customers`
```json
[
  { "id": 1, "name": "Warung A", "address": "Jl. Mawar No. 12", "phone": "0812-xxx", "notes": null }
]
```

#### Tambah pelanggan — `POST /api/customers`
```json
{
  "name": "Warung E",
  "address": "Jl. Kenanga No. 3",
  "phone": "0815-xxx"
}
```

#### Analisis pelanggan — `GET /api/orders/analytics`
```json
[
  { "name": "Warung A", "address": "Jl. Mawar No. 12", "orders_7d": 7, "orders_30d": 30, "trend": "✅ stabil" },
  { "name": "Kantin D", "address": "SMK N 1", "orders_7d": 4, "orders_30d": 28, "trend": "⬇️ turun" }
]
```

---

### 💰 Rekomendasi Harga — `GET /api/pricing/recommendation`

**Query params:**
| Param | Default | Arti |
|---|---|---|
| `product_id` | 1 | Produk yang dihitung |
| `margin_pct` | 20 | Margin target (%) |
| `market_low` | 4500 | Harga pasar terendah |
| `market_high` | 5500 | Harga pasar tertinggi |

**Contoh:**
```
GET /api/pricing/recommendation?product_id=1&margin_pct=20&market_low=4500&market_high=5500
```

**Response:**
```json
{
  "product_id": 1,
  "product_name": "Tempe",
  "production_cost": 1181.25,
  "breakdown": [
    { "ingredient": "Kedelai", "quantity_per_unit": 0.1, "unit": "kg",
      "price_per_unit": 11500, "cost_per_unit": 1150 },
    { "ingredient": "Ragi", "quantity_per_unit": 0.0005, "unit": "kg",
      "price_per_unit": 62500, "cost_per_unit": 31.25 }
  ],
  "margin_pct": 20,
  "price_minimum": 1418,
  "price_optimal": 1536,
  "market_price_low": 4500,
  "market_price_high": 5500,
  "note": "Biaya produksi per bungkus: Rp 1.181. Harga jual minimal Rp 1.418..."
}
```

---

### 🤖 Chat AI — `POST /api/chat`
```json
// Request:
{ "message": "Berapa harga jual tempe yang aman?" }

// Response:
{ "reply": "💡 Biaya produksi per tempe: Rp 1.181. Harga jual aman: Rp 1.418-Rp 1.536..." }
```
**💡 Backend otomatis coba LLM (OpenCodeZen) dulu, fallback ke jawaban lokal kalau API mati.**

---

## 4. Mock Data untuk Development

Backend otomatis terisi data contoh (seed) saat pertama kali jalan:

| Data | Isi |
|---|---|
| Produk | Tempe (shelf-life 2 hari) |
| Resep | Kedelai 0.1kg + Ragi 0.0005kg per bungkus |
| Stok | Kedelai 50kg, Ragi 80g, Plastik 220pcs |
| Pelanggan | Warung A, Warung B, Pasar C, Kantin D |
| Pesanan | 7 hari terakhir (trend turun di Kantin D) |
| Produksi | 7 hari terakhir (untuk training ML) |

**Kalau mau reset data:** hapus volume docker → `docker compose down -v && docker compose up -d`

---

## 5. Tips Integrasi

1. **Mulai dari `/api/dashboard`** — ini satu call yang sudah berisi semua data halaman utama.
2. **Gunakan `/docs`** — Swagger UI di `http://localhost:8000/docs` bisa langsung dicoba (tombol "Try it out") tanpa nulis kode.
3. **Error handling** — backend balas `{"detail": "..."}` dengan status 4xx/5xx. Frontend harus handle:
   ```js
   if (!res.ok) {
     const err = await res.json();
     alert(err.detail || 'Terjadi kesalahan');
   }
   ```
4. **Format Rupiah** — angka dari API adalah `number`. Format di frontend:
   ```js
   const rupiah = (n) => 'Rp ' + n.toLocaleString('id-ID');
   ```

---

## 6. Roadmap Backend (yang akan datang)

| Fitur | Status |
|---|---|
| Auth (login per IRTP) | 🔜 Rencana |
| CRUD resep | 🔜 Rencana |
| Laporan mingguan | 🔜 Rencana |
| Integrasi harga Bapanas | 🔜 Rencana |

> Backend tidak akan berubah format — endpoint baru hanya **ditambahkan**, bukan diubah. Frontend aman.
