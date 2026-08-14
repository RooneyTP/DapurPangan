// DapurPangan — Frontend integration with FastAPI backend
// API base otomatis: pakai host yang sama dengan halaman (kalau frontend
// disajikan dari host lain), fallback ke localhost:8000 untuk dev.
const API = (() => {
    const h = window.location.hostname;
    if (h && h !== 'localhost' && h !== '127.0.0.1' && h !== '') {
        return `http://${h}:8000/api`;
    }
    return 'http://localhost:8000/api';
})();

document.addEventListener('DOMContentLoaded', () => {
    // ===================== SIDEBAR NAVIGATION =====================
    const menuItems = document.querySelectorAll('#isi-sidebar .isi');
    const sections = document.querySelectorAll('#main-frame > div');
    function switchPage(targetId){
        sections.forEach(section => {
            section.style.display = 'none';
        });
        const targetSection = document.querySelector(targetId);
        if(targetSection){
            targetSection.style.display = (targetId === '#ai-chat') ? 'flex' : 'block';
        }
        menuItems.forEach(item => {
            const link = item.querySelector('a');
            if(link && link.getAttribute('href') === targetId){
                item.classList.add('aktif');
            }else{
                item.classList.remove('aktif');
            }
        });
    }

    menuItems.forEach(item => {
        item.addEventListener('click', function(event){
            const link = this.querySelector('a');
            if(link){
                const targetId = link.getAttribute('href');
                if(targetId && targetId.startsWith('#')){
                    event.preventDefault();
                    switchPage(targetId);
                    window.location.hash = targetId;
                }
            }
        });
    });

    const initialHash = window.location.hash || '#ai-chat';
    switchPage(initialHash);

    // ===================== HELPERS =====================
    async function apiGet(path){
        const res = await fetch(`${API}${path}`);
        if(!res.ok) throw new Error(`API ${path} -> ${res.status}`);
        return res.json();
    }
    async function apiPost(path, body){
        const res = await fetch(`${API}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if(!res.ok){
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `API ${path} -> ${res.status}`);
        }
        return res.json();
    }
    const rupiah = (n) => 'Rp ' + Number(n || 0).toLocaleString('id-ID');

    // ===================== CHAT AI =====================
    const promptPills = document.querySelectorAll('.prompt-template');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.querySelector('.chat-messages');

    function scrollToBottom() {
        if (chatMessages) {
            chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: 'smooth' });
        }
    }

    promptPills.forEach(pill => {
        pill.addEventListener('click', () => {
            if (chatInput) {
                chatInput.value = pill.textContent.trim();
                chatInput.focus();
            }
        });
    });

    async function sendMessage(){
        const text = chatInput.value.trim();
        if(text == '') return;

        const userHTML = `
            <div class="message user-message" style="display: flex; justify-content: flex-end;">
                <div style="background-color: #E07C25; color: #FFFFFF; padding: 14px 20px; border-radius: 18px 18px 2px 18px; max-width: 60%; font-size: 14px; line-height: 1.5;">
                    ${text}
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', userHTML);
        chatInput.value = '';
        scrollToBottom();

        // Loading indicator
        const loadingHTML = `
            <div class="message ai-message" id="chat-loading">
                <div class="bubble-ai">⏳ Sedang memproses...</div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', loadingHTML);
        scrollToBottom();

        try {
            const data = await apiPost('/chat', { message: text });
            document.getElementById('chat-loading')?.remove();
            const aiHTML = `
                <div class="message ai-message">
                    <div class="bubble-ai">${data.reply}</div>
                </div>
            `;
            chatMessages.insertAdjacentHTML('beforeend', aiHTML);
        } catch(e) {
            document.getElementById('chat-loading')?.remove();
            const aiHTML = `
                <div class="message ai-message">
                    <div class="bubble-ai">⚠️ Gagal terhubung ke server. Pastikan backend berjalan (docker compose up).</div>
                </div>
            `;
            chatMessages.insertAdjacentHTML('beforeend', aiHTML);
        }
        scrollToBottom();
    }

    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    // ===================== REKOMENDASI HARGA =====================
    const btnHitung = document.getElementById("btn-hitung");
    const inputNama = document.getElementById("input-nama");
    const inputMargin = document.getElementById("input-margin");
    const inputMin = document.getElementById("input-min");
    const inputMax = document.getElementById("input-max");
    const hasilHarga = document.getElementById("hasil-harga");
    const hasilSubtext = document.getElementById("hasil-subtext");

    btnHitung.addEventListener("click", async function(){
        const nama = inputNama.value.trim() || inputNama.placeholder;
        const margin = parseFloat(inputMargin.value) || parseFloat(inputMargin.placeholder);
        const min = parseFloat(inputMin.value) || parseFloat(inputMin.placeholder);
        const max = parseFloat(inputMax.value) || parseFloat(inputMax.placeholder);

        if(min > max){
            alert("Harga Pasar Min tidak boleh lebih besar dari Harga Pasar Max!");
            return;
        }
        if(hasilHarga) hasilHarga.textContent = '⏳ Menghitung...';
        if(hasilSubtext) hasilSubtext.textContent = 'Menghubungi AI DapurPangan...';

        try {
            const data = await apiGet(`/pricing/recommendation?product_id=1&margin_pct=${margin}&market_low=${min}&market_high=${max}`);
            if(hasilHarga) hasilHarga.textContent = rupiah(data.price_optimal);
            if(hasilSubtext){
                hasilSubtext.textContent =
                    `Biaya produksi ${rupiah(data.production_cost)} per unit. ` +
                    `Harga minimal ${rupiah(data.price_minimum)} (margin ${data.margin_pct}%). ` +
                    `Rekomendasi AI untuk ${nama}: ${rupiah(data.price_optimal)} (kompetitif di pasar ${rupiah(data.market_price_low)}-${rupiah(data.market_price_high)}).`;
            }
        } catch(e) {
            if(hasilHarga) hasilHarga.textContent = '—';
            if(hasilSubtext) hasilSubtext.textContent = `⚠️ ${e.message}. Pastikan backend berjalan.`;
        }
    });

    // ===================== STOK BAHAN =====================
    let stocksCache = [];
    async function loadStocks(filter = 'semua'){
        const listEl = document.getElementById('list-stok');
        if(!listEl) return;
        try {
            if(filter === 'semua' || stocksCache.length === 0){
                stocksCache = await apiGet('/stocks/');
            }
            const stocks = (filter === 'hari')
                ? stocksCache.filter(s => s.status !== 'aman')  // yang perlu perhatian hari ini
                : stocksCache;
            const statusBadge = (s) => {
                if(s.status === 'kritis') return '<span style="color:#E74C3C;">🔴 KRITIS</span>';
                if(s.status === 'waspada') return '<span style="color:#F39C12;">🟡 WASPADA</span>';
                return '<span style="color:#27AE60;">🟢 AMAN</span>';
            };
            listEl.innerHTML = stocks.map(s => `
                <div class="box-list">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                        <div>
                            <strong>${s.ingredient_name}</strong>
                            <div style="font-size:13px;color:#888;">${s.quantity} ${s.unit} • ${rupiah(s.price_per_unit)}/${s.unit}</div>
                        </div>
                        ${statusBadge(s)}
                    </div>
                </div>
            `).join('') || '<div class="box-list">Tidak ada data untuk filter ini.</div>';
        } catch(e) {
            listEl.innerHTML = `<div class="box-list">⚠️ ${e.message}</div>`;
        }
    }

    const btnSimpanBahan = document.getElementById('btn-simpan-bahan');
    if(btnSimpanBahan){
        btnSimpanBahan.addEventListener('click', async function(){
            const nama = document.getElementById('input-nama-bahan').value.trim();
            const jumlah = parseFloat(document.getElementById('input-jumlah-bahan').value);
            const satuan = document.getElementById('input-satuan-bahan').value;
            const harga = parseFloat(document.getElementById('input-harga-bahan').value);
            if(!nama || !jumlah || !satuan){
                alert('Lengkapi Nama, Jumlah, dan Satuan!');
                return;
            }
            try {
                await apiPost('/stocks/', {
                    ingredient_name: nama,
                    quantity: jumlah,
                    unit: satuan,
                    price_per_unit: harga || null
                });
                alert(`✅ Stok ${nama} berhasil ditambahkan!`);
                document.getElementById('tambah-bahan').setAttribute('hidden','');
                loadStocks();
            } catch(e) {
                alert(`❌ ${e.message}`);
            }
        });
    }

    // ===================== PESANAN =====================
    async function loadOrders(filter = 'hari'){
        const listEl = document.getElementById('list-pesanan');
        if(!listEl) return;
        try {
            const path = (filter === 'hari') ? '/orders/today' : '/orders/';
            const orders = await apiGet(path);
            listEl.innerHTML = orders.map(o => `
                <div class="box-list">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                        <div>
                            <strong>${o.customer_name}</strong>
                            <div style="font-size:13px;color:#888;">${o.product_name} • ${o.quantity} unit • ${o.status}</div>
                        </div>
                        <span style="font-size:12px;">${o.date}</span>
                    </div>
                </div>
            `).join('') || '<div class="box-list">Belum ada pesanan.</div>';
        } catch(e) {
            listEl.innerHTML = `<div class="box-list">⚠️ ${e.message}</div>`;
        }
    }

    const btnSimpanPesanan = document.getElementById('btn-simpan-pesanan');
    if(btnSimpanPesanan){
        btnSimpanPesanan.addEventListener('click', async function(){
            const namaPlg = document.getElementById('input-nama-pemesan').value.trim();
            const namaProduk = document.getElementById('input-produk-pesanan').value.trim();
            const jumlah = parseInt(document.getElementById('input-jumlah-pesanan').value);
            const tanggal = document.getElementById('input-tanggal-pesanan').value || new Date().toISOString().split('T')[0];

            if(!namaPlg || !namaProduk || !jumlah){
                alert('Lengkapi Nama Pelanggan, Produk, dan Jumlah!');
                return;
            }
            try {
                // Cari pelanggan & produk by nama
                const customers = await apiGet('/customers');
                const products = await apiGet('/products');
                let cust = customers.find(c => c.name.toLowerCase() === namaPlg.toLowerCase());
                let prod = products.find(p => p.name.toLowerCase() === namaProduk.toLowerCase());
                if(!cust){
                    cust = await apiPost('/customers', { name: namaPlg, address: '', phone: '' });
                }
                if(!prod){
                    alert(`Produk "${namaProduk}" tidak ditemukan. Gunakan nama produk yang sudah ada.`);
                    return;
                }
                await apiPost('/orders/', {
                    customer_id: cust.id,
                    product_id: prod.id,
                    date: tanggal,
                    quantity: jumlah,
                    status: 'pending'
                });
                alert(`✅ Pesanan ${namaPlg} (${jumlah} ${namaProduk}) disimpan!`);
                document.getElementById('tambah-pesanan').setAttribute('hidden','');
                loadOrders();
            } catch(e) {
                alert(`❌ ${e.message}`);
            }
        });
    }

    // ===================== PELANGGAN =====================
    async function loadCustomers(){
        const listEl = document.getElementById('list-pelanggan');
        if(!listEl) return;
        try {
            const customers = await apiGet('/customers');
            listEl.innerHTML = customers.map(c => `
                <div class="box-list">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                        <div>
                            <strong>${c.name}</strong>
                            <div style="font-size:13px;color:#888;">${c.address || '-'} • ${c.phone || '-'}</div>
                        </div>
                    </div>
                </div>
            `).join('') || '<div class="box-list">Belum ada pelanggan.</div>';
        } catch(e) {
            listEl.innerHTML = `<div class="box-list">⚠️ ${e.message}</div>`;
        }
    }

    const btnSimpanPelanggan = document.getElementById('btn-simpan-pelanggan');
    if(btnSimpanPelanggan){
        btnSimpanPelanggan.addEventListener('click', async function(){
            const nama = document.getElementById('input-nama-pelanggan').value.trim();
            const alamat = document.getElementById('input-Alamat-pelanggan').value.trim();
            const telp = document.getElementById('input-telepon').value.trim();
            if(!nama){
                alert('Nama pelanggan wajib diisi!');
                return;
            }
            try {
                await apiPost('/customers', { name: nama, address: alamat, phone: telp });
                alert(`✅ Pelanggan ${nama} berhasil ditambahkan!`);
                document.getElementById('tambah-pelanggan').setAttribute('hidden','');
                loadCustomers();
            } catch(e) {
                alert(`❌ ${e.message}`);
            }
        });
    }

    // ===================== FILTER TOGGLES (berfungsi memfilter data) =====================
    function bindFilter(btnSemua, btnHari, onFilter){
        if(!btnSemua || !btnHari) return;
        btnSemua.addEventListener('click', function(){
            btnSemua.classList.add('active');
            btnHari.classList.remove('active');
            if(onFilter) onFilter('semua');
        });
        btnHari.addEventListener('click', function(){
            btnHari.classList.add('active');
            btnSemua.classList.remove('active');
            if(onFilter) onFilter('hari');
        });
    }
    // Stok: 'semua' = semua bahan, 'hari' = yang kritis/waspada
    bindFilter(document.getElementById('btn-semua-bahan'), document.getElementById('btn-hari-bahan'), (f) => loadStocks(f));
    // Pesanan: 'semua' = riwayat, 'hari' = pesanan hari ini
    bindFilter(document.getElementById('btn-semua-pesanan'), document.getElementById('btn-hari-pesanan'), (f) => loadOrders(f));
    // Pelanggan: data statis per-request, dua filter sama-sama ambil semua
    bindFilter(document.getElementById('btn-semua-pelanggan'), document.getElementById('btn-hari-pelanggan'), (f) => loadCustomers());

    // ===================== TOMBOL "TAMBAH DATA" (toggle form) =====================
    // Setiap tombol .btn-tambah punya data-target → form id yang ditampilkan/di-sembunyikan
    const btnTambahList = document.querySelectorAll('.btn-tambah');
    btnTambahList.forEach(button => {
        button.addEventListener('click', function(){
            const targetId = this.getAttribute('data-target');
            const targetForm = document.getElementById(targetId);
            if(targetForm){
                if(targetForm.hasAttribute('hidden')){
                    targetForm.removeAttribute('hidden');
                    this.textContent = 'Tutup Form';
                } else {
                    targetForm.setAttribute('hidden', '');
                    this.textContent = 'Tambah Data';
                }
            }
        });
    });

    // ===================== INIT LOAD =====================
    loadStocks();
    loadOrders();
    loadCustomers();
});
