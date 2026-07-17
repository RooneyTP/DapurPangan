const API_BASE = 'http://localhost:8000/api';

// ===== INISIALISASI =====
document.addEventListener('DOMContentLoaded', async () => {
    setDate();
    await loadDashboard();
    setupNavigation();
    setupChat();
});

function setDate() {
    const days = ['Minggu','Senin','Selasa','Rabu','Kamis','Jumat','Sabtu'];
    const months = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];
    const d = new Date();
    document.getElementById('currentDate').textContent = `${days[d.getDay()]}, ${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
}

// ===== DASHBOARD =====
async function loadDashboard() {
    try {
        const res = await fetch(`${API_BASE}/dashboard`);
        const data = await res.json();
        renderDashboard(data);
    } catch (e) {
        console.warn('API offline, pakai data lokal');
        renderDashboard(getMockData());
    }
}

function renderDashboard(data) {
    // Greeting
    document.querySelector('.salutation h2').textContent = data.greeting;

    // Recommendation card
    const reco = data.recommendation;
    document.querySelector('#tab-dashboard .card:nth-child(1) .badge').textContent = reco.confidence;
    document.querySelector('#tab-dashboard .card:nth-child(1) .card-header h3').textContent = `🏭 Produksi Besok — ${reco.product}`;
    const qtyEl = document.querySelector('#tab-dashboard .card:nth-child(1) span[style*="font-size:2rem"]');
    if (qtyEl) qtyEl.textContent = reco.quantity;

    // Stock alerts
    const stockContainer = document.querySelector('#tab-dashboard .card:nth-child(2)');
    if (stockContainer && data.stock_alerts.length > 0) {
        const stockItems = stockContainer.querySelectorAll('.stock-row');
        data.stock_alerts.forEach((s, i) => {
            if (stockItems[i]) {
                stockItems[i].querySelector('.stock-name').textContent = s.name;
                stockItems[i].querySelector('.stock-qty').textContent = s.qty;
                stockItems[i].querySelector('.badge').textContent = s.status;
            }
        });
    }

    // Customer insights
    const insightContainer = document.querySelector('#tab-dashboard .card:nth-child(3)');
    if (insightContainer && data.customer_insights.length > 0) {
        const insightDivs = insightContainer.querySelectorAll('.insight');
        data.customer_insights.forEach((c, i) => {
            if (insightDivs[i+1]) {  // skip first (price alert)
                insightDivs[i+1].querySelector('strong').textContent = `${c.name} — ${c.trend}`;
                insightDivs[i+1].querySelector('p').textContent = c.note;
            }
        });
    }

    // Price alerts
    if (data.price_alerts && data.price_alerts.length > 0) {
        const p = data.price_alerts[0];
        const firstInsight = document.querySelector('#tab-dashboard .insight-alert');
        if (firstInsight) {
            firstInsight.querySelector('strong').textContent = `🚨 ${p.commodity} ${p.change}`;
            firstInsight.querySelector('p').textContent = p.detail;
        }
    }
}

function getMockData() {
    return {
        greeting: "🌅 Selamat pagi, Bu Sumi!",
        date: "",
        recommendation: { product: "Tempe", quantity: 210, lower_bound: 190, upper_bound: 230, confidence: "●●●●○ 87%" },
        stock_alerts: [
            { name: "Kedelai", qty: "50 kg", status: "🟢 AMAN" },
            { name: "Ragi", qty: "80 g", status: "🔴 KRITIS - BELI!" },
            { name: "Plastik kemasan", qty: "220 pcs", status: "🟡 WASPADA" }
        ],
        customer_insights: [
            { name: "Kantin D", trend: "⬇️ turun 30%", note: "Cek apakah ada masalah?" },
            { name: "Warung B", trend: "✅ stabil", note: "Pesanan normal" }
        ],
        price_alerts: [
            { commodity: "Kedelai", change: "naik 12%", detail: "Rp 11.500 → Rp 12.900/kg minggu depan" }
        ]
    };
}

// ===== NAVIGASI =====
function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function() {
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            const tab = document.getElementById(this.dataset.tab);
            if (tab) tab.classList.add('active');
        });
    });
}

// ===== CHAT =====
function setupChat() {
    window.sendChat = async function() {
        const input = document.getElementById('chatInput');
        const text = input.value.trim();
        const resp = document.getElementById('chatResponse');
        if (!text) { resp.innerHTML = 'Silakan ketik pertanyaan, Bu 😊'; return; }

        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();
            resp.innerHTML = `<div style="background:#FDEBD0;padding:10px 14px;border-radius:10px;color:#2C3E50;">💬 ${data.reply}</div>`;
        } catch (e) {
            resp.innerHTML = `<div style="background:#FDEBD0;padding:10px 14px;border-radius:10px;color:#2C3E50;">💬 Maaf, server sedang offline. Coba lagi nanti.</div>`;
        }
        input.value = '';
    };
}
