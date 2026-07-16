# Zephyrus — Pusat Komando Digital untuk IRTP

> Rebrand dari DapurPangan AI. Prototipe awal versi sederhana.

Zephyrus adalah platform dashboard terintegrasi untuk **Industri Rumah Tangga Pangan (IRTP)** — 39 juta produsen makanan skala rumahan di Indonesia.

## Tiga Pilar

| Pilar | Fungsi |
|---|---|
| 🏭 **Smart Manufacturing** | Prediksi produksi, manajemen stok, peringatan harga bahan |
| 📦 **Smart Logistics** | Optimasi rute kirim, status pengiriman, prediksi basi |
| 🛒 **Smart Commerce** | Catatan pesanan, prediksi permintaan, rekomendasi harga |

## Prototipe Awal (v0.1)

Prototipe ini adalah **single-page HTML** dengan data dummy (mock data) yang menampilkan:
- Dashboard utama "Dapur Hari Ini"
- 3 modul navigasi bottom
- AI Insights & Chat
- PWA-ready (manifest + service worker)

### Cara Jalankan

Buka `index.html` langsung di browser (Chrome Mobile / Desktop).
Atau deploy static file ke hosting manapun.

## Tech Stack Prototipe

- HTML5 + CSS3 (Tailwind-like utility classes, custom)
- Vanilla JavaScript (ES6+)
- PWA: manifest.json + sw.js
- **Zero dependency — buka langsung di browser**
