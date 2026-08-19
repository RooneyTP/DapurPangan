// DapurPangan - Frontend integration with FastAPI backend
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
    async function apiPut(path, body){
        const res = await fetch(`${API}${path}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if(!res.ok){
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `API ${path} -> ${res.status}`);
        }
        return res.json();
    }
    async function apiPatch(path, body){
        const res = await fetch(`${API}${path}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if(!res.ok){
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `API ${path} -> ${res.status}`);
        }
        return res.json();
    }
    async function apiDelete(path){
        const res = await fetch(`${API}${path}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        });
        if(!res.ok){
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `API ${path} -> ${res.status}`);
        }
        return res.json();
    }
    const rupiah = (n) => 'Rp ' + Math.round(Number(n || 0)).toLocaleString('id-ID');
    // Escape HTML untuk mencegah XSS saat data API / input user di-render via innerHTML
    function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
    // Format angka: integer tampil tanpa desimal, desimal dibiarkan apa adanya
    const fmtNum = (n) => Number.isInteger(n) ? n : n;

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
                    ${esc(text)}
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', userHTML);
        chatInput.value = '';
        scrollToBottom();

        // Loading indicator
        const loadingHTML = `
            <div class="message ai-message" id="chat-loading">
                <div class="bubble-ai">Sedang memproses...</div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', loadingHTML);
        scrollToBottom();

        try {
            const data = await apiPost('/chat', { message: text });
            document.getElementById('chat-loading')?.remove();
            const aiHTML = `
                <div class="message ai-message">
                    <div class="bubble-ai">${esc(data.reply)}</div>
                </div>
            `;
            chatMessages.insertAdjacentHTML('beforeend', aiHTML);
        } catch(e) {
            document.getElementById('chat-loading')?.remove();
            const aiHTML = `
                <div class="message ai-message">
                    <div class="bubble-ai"> Gagal terhubung ke server. Pastikan backend berjalan (docker compose up).</div>
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

    // Muat riwayat chat dari backend saat halaman dibuka (memori percakapan setelah refresh)
    async function loadChatHistory(){
        if (!chatMessages) return;
        let msgs;
        try {
            msgs = await apiGet('/chat/history');
        } catch(e) {
            return; // endpoint error/404 -> diam, biarkan greeting statis
        }
        if (!Array.isArray(msgs) || msgs.length === 0) return; // kosong -> biarkan greeting statis
        chatMessages.innerHTML = '';
        msgs.forEach(m => {
            if (m.role === 'user') {
                chatMessages.insertAdjacentHTML('beforeend', `
                    <div class="message user-message" style="display: flex; justify-content: flex-end;">
                        <div style="background-color: #E07C25; color: #FFFFFF; padding: 14px 20px; border-radius: 18px 18px 2px 18px; max-width: 60%; font-size: 14px; line-height: 1.5;">
                            ${esc(m.content)}
                        </div>
                    </div>
                `);
            } else if (m.role === 'assistant') {
                chatMessages.insertAdjacentHTML('beforeend', `
                    <div class="message ai-message">
                        <div class="bubble-ai">${esc(m.content)}</div>
                    </div>
                `);
            }
        });
        scrollToBottom();
    }

    // ===================== REKOMENDASI HARGA =====================
    let lastParams = null;
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
        lastParams = { nama: nama, margin: margin, min: min, max: max };
        if(hasilHarga) hasilHarga.textContent = 'Menghitung...';
        if(hasilSubtext) hasilSubtext.textContent = 'Menghubungi AI DapurPangan...';

        try {
            // Cari produk by nama (biar input nama benar-benar berfungsi)
            let productId = 1;
            const namaInput = inputNama.value.trim();
            if(namaInput && namaInput !== inputNama.placeholder){
                const products = await apiGet('/products');
                const found = products.find(p => p.name.toLowerCase() === namaInput.toLowerCase());
                if(!found){
                    if(hasilHarga) hasilHarga.textContent = '-';
                    if(hasilSubtext) hasilSubtext.textContent = ` Produk "${namaInput}" tidak ditemukan. Produk tersedia: ${products.map(p => p.name).join(', ')}.`;
                    return;
                }
                productId = found.id;
            }
            const data = await apiGet(`/pricing/recommendation?product_id=${productId}&margin_pct=${margin}&market_low=${min}&market_high=${max}`);
            if(hasilHarga) hasilHarga.textContent = rupiah(data.price_optimal);
            if(hasilSubtext){
                hasilSubtext.textContent =
                    `Biaya produksi ${rupiah(data.production_cost)} per unit. ` +
                    `Harga minimal ${rupiah(data.price_minimum)} (margin ${data.margin_pct}%). ` +
                    `Rekomendasi AI untuk ${data.product_name}: ${rupiah(data.price_optimal)} (kompetitif di pasar ${rupiah(data.market_price_low)}-${rupiah(data.market_price_high)}).`;
            }
        } catch(e) {
            if(hasilHarga) hasilHarga.textContent = '-';
            if(hasilSubtext) hasilSubtext.textContent = ` ${e.message}. Pastikan backend berjalan.`;
        }
    });

    // Tombol aksi di bawah hasil rekomendasi
    const btnEditParam = document.getElementById('btn-edit-param');
    const btnResetHasil = document.getElementById('btn-reset-hasil');
    if(btnEditParam){
        btnEditParam.addEventListener('click', function(){
            if(lastParams){
                if(inputNama) inputNama.value = lastParams.nama;
                if(inputMargin) inputMargin.value = lastParams.margin;
                if(inputMin) inputMin.value = lastParams.min;
                if(inputMax) inputMax.value = lastParams.max;
            }
            const formParam = (inputNama && inputNama.closest('.box')) || document.querySelector('#rekomendasi-harga .box');
            if(formParam) formParam.scrollIntoView({ behavior: 'smooth' });
            if(inputMargin) inputMargin.focus();
        });
    }
    if(btnResetHasil){
        btnResetHasil.addEventListener('click', function(){
            if(hasilHarga) hasilHarga.textContent = '0';
            if(hasilSubtext) hasilSubtext.textContent = 'Berdasarkan margin target & analisis pasar';
        });
    }

    // ===================== STOK BAHAN =====================
    let stocksCache = [];
    async function loadStocks(filter = 'semua'){
        const listEl = document.getElementById('list-stok');
        if(!listEl) return;
        try {
            // Selalu ambil data terbaru dari server (cache dikosongkan sebelum fetch)
            stocksCache = [];
            stocksCache = await apiGet('/stocks/');
            const stocks = (filter === 'hari')
                ? stocksCache.filter(s => s.status !== 'aman')  // yang perlu perhatian hari ini
                : stocksCache;
            const statusBadge = (s) => {
                if(s.status === 'kritis') return '<span style="color:#E74C3C;">KRITIS</span>';
                if(s.status === 'waspada') return '<span style="color:#F39C12;">WASPADA</span>';
                return '<span style="color:#27AE60;">AMAN</span>';
            };
            listEl.innerHTML = stocks.map(s => `
                <div class="box-list">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                        <div>
                            <strong>${esc(s.ingredient_name)}</strong>
                            <div style="font-size:13px;color:#888;">${esc(s.quantity)} ${esc(s.unit)} - ${rupiah(s.price_per_unit)}/${esc(s.unit)}</div>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                            ${statusBadge(s)}
                            <button data-id="${s.id}" data-action="edit" style="font-size:12px;padding:4px 10px;border-radius:4px;border:1px solid #2980B9;background:#fff;color:#2980B9;cursor:pointer;">Edit</button>
                            <button data-id="${s.id}" data-action="delete" style="font-size:12px;padding:4px 10px;border-radius:4px;border:1px solid #E74C3C;background:#fff;color:#E74C3C;cursor:pointer;">Hapus</button>
                        </div>
                    </div>
                </div>
            `).join('') || '<div class="box-list">Tidak ada data untuk filter ini.</div>';
        } catch(e) {
            listEl.innerHTML = `<div class="box-list"> ${esc(e.message)}</div>`;
        }
    }

    // ---- Rekomendasi Beli Hari Ini (AI) ----
    async function loadStockRec(){
        const box = document.getElementById('rec-stok-box');
        if(!box) return;
        try {
            const data = await apiGet('/stocks/recommendations');
            if(!data || !data.items || data.items.length === 0){
                box.innerHTML = '';
                return;
            }
            const aksi = (it) => {
                if(it.action === 'beli') return `<span style="color:#E74C3C;font-weight:bold;">BELI ${fmtNum(it.deficit)} ${esc(it.unit)}</span>`;
                if(it.action === 'waspada') return `<span style="color:#F39C12;">Sisa tipis</span>`;
                return `<span style="color:#27AE60;">Cukup</span>`;
            };
            box.innerHTML = `
                <h2 class="section-heading">Rekomendasi Beli Hari Ini</h2>
                <div style="font-size:13px;color:#888;margin-bottom:8px;">Prediksi produksi: ${fmtNum(data.predicted_production)} bungkus (${esc(data.date)})</div>
                ${data.items.map(it => `
                    <div class="box-list" style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                        <div>
                            <strong>${esc(it.ingredient_name)}</strong>
                            <div style="font-size:13px;color:#888;">Stok ${fmtNum(it.stock)} ${esc(it.unit)} - Kebutuhan ${fmtNum(it.needed)} ${esc(it.unit)}</div>
                        </div>
                        ${aksi(it)}
                    </div>
                `).join('')}
            `;
        } catch(e) {
            box.innerHTML = '';
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
                if(editingStockId){
                    await apiPut('/stocks/' + editingStockId, {
                        ingredient_name: nama,
                        quantity: jumlah,
                        unit: satuan,
                        price_per_unit: harga || null,
                        min_warning: editingStockMinWarning,
                        min_critical: editingStockMinCritical
                    });
                    alert(`Stok ${nama} berhasil diperbarui!`);
                } else {
                    await apiPost('/stocks/', {
                        ingredient_name: nama,
                        quantity: jumlah,
                        unit: satuan,
                        price_per_unit: harga || null
                    });
                    alert(`Stok ${nama} berhasil ditambahkan!`);
                }
                resetStockForm();
                loadStocks();
                loadStockRec();
            } catch(e) {
                alert(`${e.message}`);
            }
        });
    }

    // ---- Edit / Hapus stok ----
    let editingStockId = null;
    // Ambang stok baris yang sedang diedit: WAJIB dikirim ulang saat PUT karena
    // backend (batch 1) membuat min_warning/min_critical optional + partial update;
    // kalau tidak dikirim, nilainya bisa ikut ter-update/hilang.
    let editingStockMinWarning = null;
    let editingStockMinCritical = null;
    const formBahan = document.getElementById('tambah-bahan');
    const judulBahan = document.querySelector('#tambah-bahan .section-heading');
    const btnTambahBahan = document.getElementById('btn-tambah-bahan');
    const btnBatalBahan = document.getElementById('btn-batal-bahan');

    function resetStockForm(){
        editingStockId = null;
        editingStockMinWarning = null;
        editingStockMinCritical = null;
        if(judulBahan) judulBahan.textContent = 'Tambah Bahan Baku';
        if(btnSimpanBahan) btnSimpanBahan.textContent = 'Simpan';
        const inpNama = document.getElementById('input-nama-bahan');
        const inpJumlah = document.getElementById('input-jumlah-bahan');
        const inpSatuan = document.getElementById('input-satuan-bahan');
        const inpHarga = document.getElementById('input-harga-bahan');
        if(inpNama) inpNama.value = '';
        if(inpJumlah) inpJumlah.value = '';
        if(inpSatuan) inpSatuan.value = '';
        if(inpHarga) inpHarga.value = '';
        if(formBahan) formBahan.setAttribute('hidden','');
        if(btnTambahBahan) btnTambahBahan.textContent = 'Tambah Data';
        if(btnBatalBahan) btnBatalBahan.setAttribute('hidden','');
    }

    const listStokEl = document.getElementById('list-stok');
    if(listStokEl){
        listStokEl.addEventListener('click', async function(e){
            const btn = e.target.closest('button[data-action]');
            if(!btn) return;
            const id = btn.getAttribute('data-id');
            const action = btn.getAttribute('data-action');
            if(action === 'edit'){
                let stock = stocksCache.find(s => String(s.id) === String(id));
                if(!stock){
                    try {
                        stock = (await apiGet('/stocks/')).find(s => String(s.id) === String(id));
                    } catch(err) {
                        alert(`${err.message}`);
                        return;
                    }
                }
                if(!stock) return;
                editingStockId = stock.id;
                editingStockMinWarning = (stock.min_warning != null) ? stock.min_warning : null;
                editingStockMinCritical = (stock.min_critical != null) ? stock.min_critical : null;
                const inpNama = document.getElementById('input-nama-bahan');
                const inpJumlah = document.getElementById('input-jumlah-bahan');
                const inpSatuan = document.getElementById('input-satuan-bahan');
                const inpHarga = document.getElementById('input-harga-bahan');
                if(inpNama) inpNama.value = stock.ingredient_name || '';
                if(inpJumlah) inpJumlah.value = (stock.quantity != null) ? stock.quantity : '';
                if(inpSatuan) inpSatuan.value = stock.unit || '';
                if(inpHarga) inpHarga.value = (stock.price_per_unit != null) ? stock.price_per_unit : '';
                if(judulBahan) judulBahan.textContent = 'Edit Bahan Baku';
                if(btnSimpanBahan) btnSimpanBahan.textContent = 'Simpan Perubahan';
                if(btnTambahBahan) btnTambahBahan.textContent = 'Tutup Form';
                if(btnBatalBahan) btnBatalBahan.removeAttribute('hidden');
                if(formBahan){
                    formBahan.removeAttribute('hidden');
                    formBahan.scrollIntoView({ behavior: 'smooth' });
                }
            } else if(action === 'delete'){
                const stock = stocksCache.find(s => String(s.id) === String(id));
                const namaStok = stock ? stock.ingredient_name : 'ini';
                if(!confirm(`Hapus stok "${namaStok}"?`)) return;
                try {
                    await apiDelete('/stocks/' + id);
                    alert('Stok berhasil dihapus!');
                    loadStocks();
                    loadStockRec();
                } catch(err) {
                    alert(`${err.message}`);
                }
            }
        });
    }

    if(btnBatalBahan){
        btnBatalBahan.addEventListener('click', resetStockForm);
    }

    // ===================== PESANAN =====================
    let lastOrdersFilter = 'hari';
    let ordersCache = [];
    async function loadOrders(filter = 'hari'){
        lastOrdersFilter = filter;
        const listEl = document.getElementById('list-pesanan');
        if(!listEl) return;
        try {
            const path = (filter === 'hari') ? '/orders/today' : '/orders/';
            ordersCache = await apiGet(path);
            listEl.innerHTML = ordersCache.map(o => `
                <div class="box-list">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                        <div>
                            <strong>${esc(o.customer_name)}</strong>
                            <div style="font-size:13px;color:#888;">${esc(o.product_name)} - ${esc(o.quantity)} unit - ${esc(o.status)}</div>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                            <span style="font-size:12px;">${esc(o.date)}</span>
                            <button data-id="${o.id}" data-action="edit" style="font-size:12px;padding:4px 10px;border-radius:4px;border:1px solid #2980B9;background:#fff;color:#2980B9;cursor:pointer;">Edit</button>
                            <button data-id="${o.id}" data-action="delete" style="font-size:12px;padding:4px 10px;border-radius:4px;border:1px solid #E74C3C;background:#fff;color:#E74C3C;cursor:pointer;">Hapus</button>
                        </div>
                    </div>
                </div>
            `).join('') || '<div class="box-list">Belum ada pesanan.</div>';
        } catch(e) {
            listEl.innerHTML = `<div class="box-list"> ${esc(e.message)}</div>`;
        }
    }

    // ---- Proyeksi Pesanan (AI) ----
    async function loadOrderProj(){
        const box = document.getElementById('proj-pesanan-box');
        if(!box) return;
        try {
            const data = await apiGet('/orders/projection');
            if(!data || !data.items || data.items.length === 0){
                box.innerHTML = '';
                return;
            }
            const trend = (it) => {
                const pct = fmtNum(it.trend_pct);
                if(it.alert) return `<span style="color:#E74C3C;font-weight:bold;">turun ${pct}%</span>`;
                if(it.trend === 'turun') return `turun ${pct}%`;
                if(it.trend === 'naik') return `<span style="color:#27AE60;">naik ${pct}%</span>`;
                return `<span style="color:#888;">stabil</span>`;
            };
            box.innerHTML = `
                <h2 class="section-heading">Proyeksi Pesanan</h2>
                <div style="font-size:13px;color:#888;margin-bottom:8px;">Perkiraan total permintaan: ${fmtNum(data.predicted_total)} bungkus</div>
                ${data.items.slice(0, 5).map(it => `
                    <div class="box-list" style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                        <div><strong>${esc(it.customer_name)}</strong></div>
                        <div style="text-align:right;font-size:13px;">${fmtNum(it.projected_qty)} unit (${fmtNum(it.share_pct)}%) ${trend(it)}</div>
                    </div>
                `).join('')}
            `;
        } catch(e) {
            box.innerHTML = '';
        }
    }

    const btnSimpanPesanan = document.getElementById('btn-simpan-pesanan');
    if(btnSimpanPesanan){
        btnSimpanPesanan.addEventListener('click', async function(){
            const namaPlg = document.getElementById('input-nama-pemesan').value.trim();
            const namaProduk = document.getElementById('input-produk-pesanan').value.trim();
            const jumlah = parseInt(document.getElementById('input-jumlah-pesanan').value);
            const tanggal = document.getElementById('input-tanggal-pesanan').value || new Date().toISOString().split('T')[0];
            const statusEl = document.getElementById('input-status-pesanan');
            const status = (statusEl && statusEl.value) ? statusEl.value : 'pending';

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
                const payload = {
                    customer_id: cust.id,
                    product_id: prod.id,
                    date: tanggal,
                    quantity: jumlah,
                    status: status
                };
                if(editingOrderId){
                    await apiPut('/orders/' + editingOrderId, payload);
                    alert(`Pesanan ${namaPlg} (${jumlah} ${namaProduk}) diperbarui!`);
                } else {
                    await apiPost('/orders/', payload);
                    alert(`Pesanan ${namaPlg} (${jumlah} ${namaProduk}) disimpan!`);
                }
                resetOrderForm();
                loadOrders(lastOrdersFilter || 'hari');
                loadOrderProj();
                loadSalesPrediction();
            } catch(e) {
                alert(`${e.message}`);
            }
        });
    }

    // ---- Edit / Hapus pesanan ----
    let editingOrderId = null;
    const formPesanan = document.getElementById('tambah-pesanan');
    const judulPesanan = document.querySelector('#tambah-pesanan .section-heading');
    const btnTambahPesanan = document.getElementById('btn-tambah-pesanan');
    const btnBatalPesanan = document.getElementById('btn-batal-pesanan');

    function resetOrderForm(){
        editingOrderId = null;
        if(judulPesanan) judulPesanan.textContent = 'Tambah Pesanan';
        if(btnSimpanPesanan) btnSimpanPesanan.textContent = 'Simpan';
        const ids = ['input-nama-pemesan','input-produk-pesanan','input-jumlah-pesanan','input-tanggal-pesanan'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if(el) el.value = '';
        });
        const selStatus = document.getElementById('input-status-pesanan');
        if(selStatus) selStatus.value = 'pending';
        if(formPesanan) formPesanan.setAttribute('hidden','');
        if(btnTambahPesanan) btnTambahPesanan.textContent = 'Tambah Data';
        if(btnBatalPesanan) btnBatalPesanan.setAttribute('hidden','');
    }

    const listPesananEl = document.getElementById('list-pesanan');
    if(listPesananEl){
        listPesananEl.addEventListener('click', async function(e){
            const btn = e.target.closest('button[data-action]');
            if(!btn) return;
            const id = btn.getAttribute('data-id');
            const action = btn.getAttribute('data-action');
            if(action === 'edit'){
                let order = ordersCache.find(o => String(o.id) === String(id));
                if(!order){
                    try {
                        const path = (lastOrdersFilter === 'hari') ? '/orders/today' : '/orders/';
                        order = (await apiGet(path)).find(o => String(o.id) === String(id));
                    } catch(err) {
                        alert(`${err.message}`);
                        return;
                    }
                }
                if(!order) return;
                editingOrderId = order.id;
                const inpNamaPlg = document.getElementById('input-nama-pemesan');
                const inpProduk = document.getElementById('input-produk-pesanan');
                const inpJumlah = document.getElementById('input-jumlah-pesanan');
                const inpTanggal = document.getElementById('input-tanggal-pesanan');
                const selStatus = document.getElementById('input-status-pesanan');
                if(inpNamaPlg) inpNamaPlg.value = order.customer_name || '';
                if(inpProduk) inpProduk.value = order.product_name || '';
                if(inpJumlah) inpJumlah.value = (order.quantity != null) ? order.quantity : '';
                if(inpTanggal) inpTanggal.value = order.date || '';
                if(selStatus) selStatus.value = order.status || 'pending';
                if(judulPesanan) judulPesanan.textContent = 'Edit Pesanan';
                if(btnSimpanPesanan) btnSimpanPesanan.textContent = 'Simpan Perubahan';
                if(btnTambahPesanan) btnTambahPesanan.textContent = 'Tutup Form';
                if(btnBatalPesanan) btnBatalPesanan.removeAttribute('hidden');
                if(formPesanan){
                    formPesanan.removeAttribute('hidden');
                    formPesanan.scrollIntoView({ behavior: 'smooth' });
                }
            } else if(action === 'delete'){
                const order = ordersCache.find(o => String(o.id) === String(id));
                const namaOrder = order ? `${order.customer_name} (${order.product_name})` : 'ini';
                if(!confirm(`Hapus pesanan "${namaOrder}"?`)) return;
                try {
                    await apiDelete('/orders/' + id);
                    alert('Pesanan berhasil dihapus!');
                    loadOrders(lastOrdersFilter || 'hari');
                    loadOrderProj();
                    loadSalesPrediction();
                } catch(err) {
                    alert(`${err.message}`);
                }
            }
        });
    }

    if(btnBatalPesanan){
        btnBatalPesanan.addEventListener('click', resetOrderForm);
    }

    // ===================== RESEP =====================
    let recipesCache = [];
    let productsCache = [];
    let editingRecipeId = null;

    async function loadProductsCache(){
        try {
            productsCache = await apiGet('/products');
        } catch(e) {
            productsCache = [];
        }
    }

    // Isi dropdown produk di panel "Cek Kebutuhan" dari produk yang punya resep
    function fillCekProdukSelect(){
        const sel = document.getElementById('pilih-produk-cek');
        if(!sel) return;
        const seen = {};
        const prodIds = [];
        recipesCache.forEach(r => {
            if(!seen[r.product_id]){
                seen[r.product_id] = true;
                prodIds.push(r.product_id);
            }
        });
        const prev = sel.value;
        sel.innerHTML = prodIds.map(pid => {
            const prod = productsCache.find(p => p.id === pid);
            const label = prod ? prod.name : 'Produk ' + pid;
            return `<option value="${pid}">${esc(label)}</option>`;
        }).join('');
        if(prev && prodIds.some(pid => String(pid) === String(prev))){
            sel.value = prev;
        }
    }

    async function loadRecipes(){
        const listEl = document.getElementById('list-resep');
        if(!listEl) return;
        try {
            if(!productsCache.length) await loadProductsCache();
            recipesCache = await apiGet('/recipes/');
            listEl.innerHTML = recipesCache.map(r => {
                const prod = productsCache.find(p => p.id === r.product_id);
                const namaProduk = prod ? prod.name : 'Produk ' + r.product_id;
                return `
                    <div class="box-list">
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                            <div>
                                <strong>${esc(namaProduk)} - ${esc(r.ingredient_name)}</strong>
                                <div style="font-size:13px;color:#888;">${fmtNum(r.quantity_per_unit)} ${esc(r.unit)} per unit produk</div>
                            </div>
                            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                                <button data-id="${r.id}" data-action="edit" style="font-size:12px;padding:4px 10px;border-radius:4px;border:1px solid #2980B9;background:#fff;color:#2980B9;cursor:pointer;">Edit</button>
                                <button data-id="${r.id}" data-action="delete" style="font-size:12px;padding:4px 10px;border-radius:4px;border:1px solid #E74C3C;background:#fff;color:#E74C3C;cursor:pointer;">Hapus</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('') || '<div class="box-list">Belum ada resep. Tambahkan resep produk dulu.</div>';
            fillCekProdukSelect();
        } catch(e) {
            listEl.innerHTML = `<div class="box-list"> ${esc(e.message)}</div>`;
        }
    }

    // ---- Cek Kebutuhan Bahan untuk Pesanan ----
    const btnCekResep = document.getElementById('btn-cek-resep');
    if(btnCekResep){
        btnCekResep.addEventListener('click', cekKebutuhan);
    }

    async function cekKebutuhan(){
        const hasilEl = document.getElementById('hasil-cek-resep');
        if(!hasilEl) return;
        const jumlah = parseInt(document.getElementById('input-jumlah-cek').value);
        if(!jumlah || jumlah < 1){
            alert('Masukkan jumlah produk dulu');
            return;
        }
        try {
            if(!recipesCache.length){
                try {
                    recipesCache = await apiGet('/recipes/');
                } catch(e) {
                    recipesCache = [];
                }
            }
            if(!recipesCache.length){
                hasilEl.innerHTML = '<div style="color:#F39C12;">Belum ada resep. Tambahkan resep dulu.</div>';
                return;
            }
            let productId = parseInt(document.getElementById('pilih-produk-cek').value);
            if(!productId){
                productId = recipesCache[0].product_id;
            }
            const data = await apiGet(`/recipes/check?product_id=${productId}&quantity=${jumlah}`);
            let html = '';
            if(data.sufficient){
                html = `<div style="color:#27AE60;font-weight:bold;margin-bottom:6px;">Stok CUKUP untuk ${fmtNum(data.quantity)} ${esc(data.product_name)}</div>`;
            } else {
                html = `<div style="color:#E74C3C;font-weight:bold;margin-bottom:6px;">Stok TIDAK CUKUP untuk ${fmtNum(data.quantity)} ${esc(data.product_name)}</div>`;
            }
            html += (data.items || []).map(it => {
                const rincian = `${esc(it.ingredient_name)}: butuh ${fmtNum(it.needed)} ${esc(it.unit)}, stok ${fmtNum(it.stock)} ${esc(it.unit)}`;
                if(it.enough){
                    return `<div style="color:#27AE60;">${rincian} - cukup</div>`;
                }
                return `<div style="color:#E74C3C;">${rincian} - KURANG ${fmtNum(it.deficit)} ${esc(it.unit)}</div>`;
            }).join('');
            hasilEl.innerHTML = html;
        } catch(e) {
            hasilEl.innerHTML = `<div style="color:#E74C3C;"> ${esc(e.message)}</div>`;
        }
    }

    // ---- Simpan (tambah / edit) resep ----
    const btnSimpanResep = document.getElementById('btn-simpan-resep');
    if(btnSimpanResep){
        btnSimpanResep.addEventListener('click', async function(){
            const namaProduk = document.getElementById('input-produk-resep').value.trim();
            const namaBahan = document.getElementById('input-bahan-resep').value.trim();
            const takaran = parseFloat(document.getElementById('input-takaran-resep').value);
            const satuan = document.getElementById('input-satuan-resep').value;
            if(!namaProduk || !namaBahan || !takaran || takaran <= 0 || !satuan){
                alert('Lengkapi Nama Produk, Nama Bahan, Takaran (> 0), dan Satuan!');
                return;
            }
            try {
                if(!productsCache.length) await loadProductsCache();
                const prod = productsCache.find(p => p.name.toLowerCase() === namaProduk.toLowerCase());
                if(!prod){
                    alert(`Produk "${namaProduk}" tidak ditemukan. Gunakan nama produk yang sudah ada.`);
                    return;
                }
                const payload = {
                    product_id: prod.id,
                    ingredient_name: namaBahan,
                    quantity_per_unit: takaran,
                    unit: satuan
                };
                if(editingRecipeId){
                    await apiPatch('/recipes/' + editingRecipeId, payload);
                    alert(`Resep ${namaProduk} - ${namaBahan} berhasil diperbarui!`);
                } else {
                    await apiPost('/recipes/', payload);
                    alert(`Resep ${namaProduk} - ${namaBahan} berhasil ditambahkan!`);
                }
                resetRecipeForm();
                loadRecipes();
            } catch(e) {
                alert(`${e.message}`);
            }
        });
    }

    // ---- Edit / Hapus resep ----
    const formResep = document.getElementById('tambah-resep');
    const judulResep = document.querySelector('#tambah-resep .section-heading');
    const btnTambahResep = document.getElementById('btn-tambah-resep');
    const btnBatalResep = document.getElementById('btn-batal-resep');

    function resetRecipeForm(){
        editingRecipeId = null;
        if(judulResep) judulResep.textContent = 'Tambah Resep';
        if(btnSimpanResep) btnSimpanResep.textContent = 'Simpan';
        const ids = ['input-produk-resep','input-bahan-resep','input-takaran-resep'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if(el) el.value = '';
        });
        const selSatuan = document.getElementById('input-satuan-resep');
        if(selSatuan) selSatuan.value = '';
        if(formResep) formResep.setAttribute('hidden','');
        if(btnTambahResep) btnTambahResep.textContent = 'Tambah Data';
        if(btnBatalResep) btnBatalResep.setAttribute('hidden','');
    }

    const listResepEl = document.getElementById('list-resep');
    if(listResepEl){
        listResepEl.addEventListener('click', async function(e){
            const btn = e.target.closest('button[data-action]');
            if(!btn) return;
            const id = btn.getAttribute('data-id');
            const action = btn.getAttribute('data-action');
            if(action === 'edit'){
                let recipe = recipesCache.find(r => String(r.id) === String(id));
                if(!recipe){
                    try {
                        recipe = (await apiGet('/recipes/')).find(r => String(r.id) === String(id));
                    } catch(err) {
                        alert(`${err.message}`);
                        return;
                    }
                }
                if(!recipe) return;
                editingRecipeId = recipe.id;
                const prod = productsCache.find(p => p.id === recipe.product_id);
                const inpProduk = document.getElementById('input-produk-resep');
                const inpBahan = document.getElementById('input-bahan-resep');
                const inpTakaran = document.getElementById('input-takaran-resep');
                const inpSatuan = document.getElementById('input-satuan-resep');
                if(inpProduk) inpProduk.value = prod ? prod.name : '';
                if(inpBahan) inpBahan.value = recipe.ingredient_name || '';
                if(inpTakaran) inpTakaran.value = (recipe.quantity_per_unit != null) ? recipe.quantity_per_unit : '';
                if(inpSatuan) inpSatuan.value = recipe.unit || '';
                if(judulResep) judulResep.textContent = 'Edit Resep';
                if(btnSimpanResep) btnSimpanResep.textContent = 'Simpan Perubahan';
                if(btnTambahResep) btnTambahResep.textContent = 'Tutup Form';
                if(btnBatalResep) btnBatalResep.removeAttribute('hidden');
                if(formResep){
                    formResep.removeAttribute('hidden');
                    formResep.scrollIntoView({ behavior: 'smooth' });
                }
            } else if(action === 'delete'){
                const recipe = recipesCache.find(r => String(r.id) === String(id));
                const prod = recipe ? productsCache.find(p => p.id === recipe.product_id) : null;
                const namaResep = recipe
                    ? `${prod ? prod.name : 'Produk ' + recipe.product_id} - ${recipe.ingredient_name}`
                    : 'ini';
                if(!confirm(`Hapus resep "${namaResep}"?`)) return;
                try {
                    await apiDelete('/recipes/' + id);
                    alert('Resep berhasil dihapus!');
                    loadRecipes();
                } catch(err) {
                    alert(`${err.message}`);
                }
            }
        });
    }

    if(btnBatalResep){
        btnBatalResep.addEventListener('click', resetRecipeForm);
    }

    // ===================== PELANGGAN =====================
    let customersCache = [];
    async function loadCustomers(){
        const listEl = document.getElementById('list-pelanggan');
        if(!listEl) return;
        try {
            customersCache = await apiGet('/customers');
            listEl.innerHTML = customersCache.map(c => `
                <div class="box-list">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                        <div>
                            <strong>${esc(c.name)}</strong>
                            <div style="font-size:13px;color:#888;">${esc(c.address || '-')} - ${esc(c.phone || '-')}</div>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                            <button data-id="${c.id}" data-action="edit" style="font-size:12px;padding:4px 10px;border-radius:4px;border:1px solid #2980B9;background:#fff;color:#2980B9;cursor:pointer;">Edit</button>
                            <button data-id="${c.id}" data-action="delete" style="font-size:12px;padding:4px 10px;border-radius:4px;border:1px solid #E74C3C;background:#fff;color:#E74C3C;cursor:pointer;">Hapus</button>
                        </div>
                    </div>
                </div>
            `).join('') || '<div class="box-list">Belum ada pelanggan.</div>';
        } catch(e) {
            listEl.innerHTML = `<div class="box-list"> ${esc(e.message)}</div>`;
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
                if(editingCustomerId){
                    await apiPut('/customers/' + editingCustomerId, { name: nama, address: alamat, phone: telp });
                    alert(`Pelanggan ${nama} berhasil diperbarui!`);
                } else {
                    await apiPost('/customers', { name: nama, address: alamat, phone: telp });
                    alert(`Pelanggan ${nama} berhasil ditambahkan!`);
                }
                resetCustomerForm();
                loadCustomers();
            } catch(e) {
                alert(`${e.message}`);
            }
        });
    }

    // ---- Edit / Hapus pelanggan ----
    let editingCustomerId = null;
    const formPelanggan = document.getElementById('tambah-pelanggan');
    const judulPelanggan = document.querySelector('#tambah-pelanggan .section-heading');
    const btnTambahPelanggan = document.getElementById('btn-tambah-pelanggan');
    const btnBatalPelanggan = document.getElementById('btn-batal-pelanggan');

    function resetCustomerForm(){
        editingCustomerId = null;
        if(judulPelanggan) judulPelanggan.textContent = 'Tambah Pelanggan';
        if(btnSimpanPelanggan) btnSimpanPelanggan.textContent = 'Simpan';
        const ids = ['input-nama-pelanggan','input-Alamat-pelanggan','input-telepon'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if(el) el.value = '';
        });
        if(formPelanggan) formPelanggan.setAttribute('hidden','');
        if(btnTambahPelanggan) btnTambahPelanggan.textContent = 'Tambah Data';
        if(btnBatalPelanggan) btnBatalPelanggan.setAttribute('hidden','');
    }

    const listPelangganEl = document.getElementById('list-pelanggan');
    if(listPelangganEl){
        listPelangganEl.addEventListener('click', async function(e){
            const btn = e.target.closest('button[data-action]');
            if(!btn) return;
            const id = btn.getAttribute('data-id');
            const action = btn.getAttribute('data-action');
            if(action === 'edit'){
                let cust = customersCache.find(c => String(c.id) === String(id));
                if(!cust){
                    try {
                        cust = (await apiGet('/customers')).find(c => String(c.id) === String(id));
                    } catch(err) {
                        alert(`${err.message}`);
                        return;
                    }
                }
                if(!cust) return;
                editingCustomerId = cust.id;
                const inpNama = document.getElementById('input-nama-pelanggan');
                const inpAlamat = document.getElementById('input-Alamat-pelanggan');
                const inpTelp = document.getElementById('input-telepon');
                if(inpNama) inpNama.value = cust.name || '';
                if(inpAlamat) inpAlamat.value = cust.address || '';
                if(inpTelp) inpTelp.value = cust.phone || '';
                if(judulPelanggan) judulPelanggan.textContent = 'Edit Pelanggan';
                if(btnSimpanPelanggan) btnSimpanPelanggan.textContent = 'Simpan Perubahan';
                if(btnTambahPelanggan) btnTambahPelanggan.textContent = 'Tutup Form';
                if(btnBatalPelanggan) btnBatalPelanggan.removeAttribute('hidden');
                if(formPelanggan){
                    formPelanggan.removeAttribute('hidden');
                    formPelanggan.scrollIntoView({ behavior: 'smooth' });
                }
            } else if(action === 'delete'){
                const cust = customersCache.find(c => String(c.id) === String(id));
                const namaCust = cust ? cust.name : 'ini';
                if(!confirm(`Hapus pelanggan "${namaCust}"?`)) return;
                try {
                    await apiDelete('/customers/' + id);
                    alert('Pelanggan berhasil dihapus!');
                    loadCustomers();
                } catch(err) {
                    alert(`${err.message}`);
                }
            }
        });
    }

    if(btnBatalPelanggan){
        btnBatalPelanggan.addEventListener('click', resetCustomerForm);
    }

    // ===================== PENJUALAN (B2C per individu) =====================
    let salesCache = [];
    let lastSalesFilter = 'hari';
    let editingSaleId = null;

    async function loadSales(filter = 'hari'){
        lastSalesFilter = filter;
        const listEl = document.getElementById('list-penjualan');
        if(!listEl) return;
        try {
            const path = (filter === 'hari') ? '/sales/today' : '/sales/';
            salesCache = await apiGet(path);
            listEl.innerHTML = salesCache.map(s => `
                <div class="box-list">
                    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                        <div>
                            <strong>${esc(s.product_name)}</strong>
                            <div style="font-size:13px;color:#888;">${s.individual_count} orang x ${s.quantity_per_individual} = ${s.total_quantity} unit</div>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                            <span style="font-size:12px;">${esc(s.date)}</span>
                            <button data-id="${s.id}" data-action="edit" style="font-size:12px;padding:4px 10px;border-radius:4px;border:1px solid #2980B9;background:#fff;color:#2980B9;cursor:pointer;">Edit</button>
                            <button data-id="${s.id}" data-action="delete" style="font-size:12px;padding:4px 10px;border-radius:4px;border:1px solid #E74C3C;background:#fff;color:#E74C3C;cursor:pointer;">Hapus</button>
                        </div>
                    </div>
                </div>
            `).join('') || '<div class="box-list">Belum ada penjualan.</div>';
        } catch(e) {
            listEl.innerHTML = `<div class="box-list"> ${esc(e.message)}</div>`;
        }
    }

    // ---- Prediksi Produksi Besok (AI) - notifikasi H-1 di section Pesanan ----
    async function loadSalesPrediction(){
        const box = document.getElementById('box-prediksi-besok');
        if(!box) return;
        try {
            const pred = await apiGet('/sales/prediction');
            if(!pred || (pred.predicted_units == 0 && pred.predicted_individuals == 0)){
                box.innerHTML = '<h2 class="section-heading">Prediksi Produksi Besok</h2><div style="font-size:13px;color:#888;">Belum ada data penjualan individu. Catat penjualan dulu (Tambah Data di menu Penjualan).</div>';
                return;
            }
            box.innerHTML = `
                <h2 class="section-heading">Prediksi Produksi Besok (${esc(pred.date)})</h2>
                <div style="font-size:13px;color:#888;margin-bottom:8px;">~${fmtNum(pred.predicted_units)} unit produksi - ~${fmtNum(pred.predicted_individuals)} pembeli (dari ${pred.data_points} hari data penjualan individu, confidence ${pred.confidence_pct}%).</div>
            `;
        } catch(e) {
            box.innerHTML = '';
        }
    }

    const btnSimpanPenjualan = document.getElementById('btn-simpan-penjualan');
    if(btnSimpanPenjualan){
        btnSimpanPenjualan.addEventListener('click', async function(){
            const namaProduk = document.getElementById('input-produk-penjualan').value.trim();
            const individu = parseInt(document.getElementById('input-individu-penjualan').value);
            const perIndividu = parseInt(document.getElementById('input-perindividu-penjualan').value);
            const tanggal = document.getElementById('input-tanggal-penjualan').value || new Date().toISOString().split('T')[0];
            if(!namaProduk || !individu || !perIndividu){
                alert('Lengkapi Nama Produk, Jumlah Individu, dan Beli per Individu!');
                return;
            }
            if(individu < 1 || perIndividu < 1){
                alert('Jumlah Individu dan Beli per Individu harus minimal 1!');
                return;
            }
            try {
                // Cari produk by nama (harus sudah ada)
                const products = await apiGet('/products');
                const prod = products.find(p => p.name.toLowerCase() === namaProduk.toLowerCase());
                if(!prod){
                    alert(`Produk "${namaProduk}" tidak ditemukan. Gunakan nama produk yang sudah ada.`);
                    return;
                }
                const payload = {
                    product_id: prod.id,
                    date: tanggal,
                    individual_count: individu,
                    quantity_per_individual: perIndividu
                };
                if(editingSaleId){
                    await apiPut('/sales/' + editingSaleId, payload);
                    alert(`Penjualan ${namaProduk} (${individu} individu) diperbarui!`);
                } else {
                    await apiPost('/sales/', payload);
                    alert(`Penjualan ${namaProduk} (${individu} individu) disimpan!`);
                }
                resetSaleForm();
                loadSales(lastSalesFilter || 'hari');
                loadSalesPrediction();
            } catch(e) {
                alert(`${e.message}`);
            }
        });
    }

    // ---- Edit / Hapus penjualan ----
    const formPenjualan = document.getElementById('tambah-penjualan');
    const judulPenjualan = document.querySelector('#tambah-penjualan .section-heading');
    const btnTambahPenjualan = document.getElementById('btn-tambah-penjualan');
    const btnBatalPenjualan = document.getElementById('btn-batal-penjualan');

    function resetSaleForm(){
        editingSaleId = null;
        if(judulPenjualan) judulPenjualan.textContent = 'Tambah Penjualan';
        if(btnSimpanPenjualan) btnSimpanPenjualan.textContent = 'Simpan';
        const ids = ['input-produk-penjualan','input-individu-penjualan','input-perindividu-penjualan','input-tanggal-penjualan'];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if(el) el.value = '';
        });
        if(formPenjualan) formPenjualan.setAttribute('hidden','');
        if(btnTambahPenjualan) btnTambahPenjualan.textContent = 'Tambah Data';
        if(btnBatalPenjualan) btnBatalPenjualan.setAttribute('hidden','');
    }

    const listPenjualanEl = document.getElementById('list-penjualan');
    if(listPenjualanEl){
        listPenjualanEl.addEventListener('click', async function(e){
            const btn = e.target.closest('button[data-action]');
            if(!btn) return;
            const id = btn.getAttribute('data-id');
            const action = btn.getAttribute('data-action');
            if(action === 'edit'){
                let sale = salesCache.find(s => String(s.id) === String(id));
                if(!sale){
                    try {
                        const path = (lastSalesFilter === 'hari') ? '/sales/today' : '/sales/';
                        sale = (await apiGet(path)).find(s => String(s.id) === String(id));
                    } catch(err) {
                        alert(`${err.message}`);
                        return;
                    }
                }
                if(!sale) return;
                editingSaleId = sale.id;
                const inpProduk = document.getElementById('input-produk-penjualan');
                const inpIndividu = document.getElementById('input-individu-penjualan');
                const inpPerIndividu = document.getElementById('input-perindividu-penjualan');
                const inpTanggal = document.getElementById('input-tanggal-penjualan');
                if(inpProduk) inpProduk.value = sale.product_name || '';
                if(inpIndividu) inpIndividu.value = (sale.individual_count != null) ? sale.individual_count : '';
                if(inpPerIndividu) inpPerIndividu.value = (sale.quantity_per_individual != null) ? sale.quantity_per_individual : '';
                if(inpTanggal) inpTanggal.value = sale.date || '';
                if(judulPenjualan) judulPenjualan.textContent = 'Edit Penjualan';
                if(btnSimpanPenjualan) btnSimpanPenjualan.textContent = 'Simpan Perubahan';
                if(btnTambahPenjualan) btnTambahPenjualan.textContent = 'Tutup Form';
                if(btnBatalPenjualan) btnBatalPenjualan.removeAttribute('hidden');
                if(formPenjualan){
                    formPenjualan.removeAttribute('hidden');
                    formPenjualan.scrollIntoView({ behavior: 'smooth' });
                }
            } else if(action === 'delete'){
                const sale = salesCache.find(s => String(s.id) === String(id));
                const namaSale = sale ? `${sale.product_name} (${sale.date})` : 'ini';
                if(!confirm(`Hapus penjualan "${namaSale}"?`)) return;
                try {
                    await apiDelete('/sales/' + id);
                    alert('Penjualan berhasil dihapus!');
                    loadSales(lastSalesFilter || 'hari');
                    loadSalesPrediction();
                } catch(err) {
                    alert(`${err.message}`);
                }
            }
        });
    }

    if(btnBatalPenjualan){
        btnBatalPenjualan.addEventListener('click', resetSaleForm);
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
    // Pelanggan: TIDAK ada endpoint data pelanggan per hari. Tombol "Hari Ini"
    // di-DISABLE dengan penjelasan jujur (anti-fitur-bohongan) - daftar pelanggan
    // selalu menampilkan semua pelanggan.
    const btnHariPelanggan = document.getElementById('btn-hari-pelanggan');
    if(btnHariPelanggan){
        btnHariPelanggan.disabled = true;
        btnHariPelanggan.title = 'Tidak tersedia: daftar pelanggan selalu menampilkan semua pelanggan';
        btnHariPelanggan.style.opacity = '0.45';
        btnHariPelanggan.style.cursor = 'not-allowed';
    }
    bindFilter(document.getElementById('btn-semua-pelanggan'), btnHariPelanggan, (f) => loadCustomers());
    // Penjualan: 'semua' = riwayat, 'hari' = penjualan hari ini
    bindFilter(document.getElementById('btn-semua-penjualan'), document.getElementById('btn-hari-penjualan'), (f) => loadSales(f));

    // ===================== TOMBOL "TAMBAH DATA" (toggle form) =====================
    // Setiap tombol .btn-tambah punya data-target -> form id yang ditampilkan/di-sembunyikan
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
                    // Tutup form: reset penuh (state edit + input + hidden + label tombol)
                    // agar membuka form lagi selalu dalam mode "tambah baru", bukan update (PUT)
                    if(targetId === 'tambah-bahan'){
                        resetStockForm();
                    } else if(targetId === 'tambah-pesanan'){
                        resetOrderForm();
                    } else if(targetId === 'tambah-pelanggan'){
                        resetCustomerForm();
                    } else if(targetId === 'tambah-penjualan'){
                        resetSaleForm();
                    } else if(targetId === 'tambah-resep'){
                        resetRecipeForm();
                    } else {
                        targetForm.setAttribute('hidden', '');
                        this.textContent = 'Tambah Data';
                    }
                }
            }
        });
    });

    // ===================== IMPORT CSV =====================
    const TEMPLATE_STOCKS = 'ingredient_name,quantity,unit,price_per_unit,min_warning,min_critical\nKedelai,50,kg,11500,15,5';
    const TEMPLATE_CUSTOMERS = 'name,address,phone,notes\nWarung A,Jl. Mawar No. 12,0812-xxxx-xxxx,';
    const TEMPLATE_ORDERS = 'customer_name,product_name,date,quantity,status\nWarung A,Tempe,2026-08-17,30,delivered';

    function createImportUI(kind, panelId, fileId, btnUploadId, btnTemplateId, hasilId, templateContent, onDone){
        const panel = document.getElementById(panelId);
        const fileInput = document.getElementById(fileId);
        const btnUpload = document.getElementById(btnUploadId);
        const btnTemplate = document.getElementById(btnTemplateId);
        const hasil = document.getElementById(hasilId);
        if(!panel || !fileInput || !btnUpload || !btnTemplate || !hasil) return;

        // Download template CSV
        btnTemplate.addEventListener('click', function(){
            const blob = new Blob([templateContent], { type: 'text/csv;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `template-${kind}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });

        // Upload CSV -> POST /api/import/{kind} (body = file mentah)
        btnUpload.addEventListener('click', async function(){
            if(!fileInput.files || fileInput.files.length === 0){
                alert('Pilih file CSV dulu');
                return;
            }
            const file = fileInput.files[0];
            if(hasil) hasil.innerHTML = 'Mengupload...';
            try {
                const res = await fetch(`${API}/import/${kind}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'text/csv' },
                    body: file
                });
                if(!res.ok){
                    let msg = `Import gagal (HTTP ${res.status})`;
                    try {
                        const errJson = await res.json();
                        msg = (errJson && typeof errJson.detail === 'string') ? errJson.detail : JSON.stringify(errJson);
                    } catch(e2) {
                        const txt = await res.text().catch(() => '');
                        if(txt) msg = txt;
                    }
                    if(hasil) hasil.innerHTML = `<div style="color:#E74C3C;"> ${esc(msg)}</div>`;
                    return;
                }
                const data = await res.json();
                let html = `<div style="color:#27AE60;">Berhasil import ${data.imported} baris</div>`;
                if(data.failed > 0){
                    html += `<div style="color:#E74C3C;">Gagal ${data.failed} baris</div>`;
                    if(data.errors && data.errors.length){
                        html += data.errors.map(err =>
                            `<div>Baris ${err.row}: ${esc(err.reason)}</div>`
                        ).join('');
                    }
                }
                if(hasil) hasil.innerHTML = html;
                if(fileInput) fileInput.value = '';
                if(onDone) onDone();
            } catch(e) {
                if(hasil) hasil.innerHTML = `<div style="color:#E74C3C;"> ${esc(e.message)}</div>`;
            }
        });
    }

    // Toggle panel import (pola sama seperti toggle form .btn-tambah, id sendiri)
    function bindImportToggle(btnId, panelId){
        const btn = document.getElementById(btnId);
        const panel = document.getElementById(panelId);
        if(!btn || !panel) return;
        btn.addEventListener('click', function(){
            if(panel.hasAttribute('hidden')){
                panel.removeAttribute('hidden');
                btn.textContent = 'Tutup Import';
            } else {
                panel.setAttribute('hidden', '');
                btn.textContent = 'Import CSV';
            }
        });
    }

    // Stok
    createImportUI(
        'stocks', 'panel-import-bahan', 'file-import-bahan',
        'btn-upload-bahan', 'btn-template-bahan', 'hasil-import-bahan',
        TEMPLATE_STOCKS,
        () => { loadStocks(); loadStockRec(); }
    );
    bindImportToggle('btn-import-bahan', 'panel-import-bahan');

    // Pesanan
    createImportUI(
        'orders', 'panel-import-pesanan', 'file-import-pesanan',
        'btn-upload-pesanan', 'btn-template-pesanan', 'hasil-import-pesanan',
        TEMPLATE_ORDERS,
        () => { loadOrders(lastOrdersFilter || 'hari'); loadOrderProj(); loadSalesPrediction(); }
    );
    bindImportToggle('btn-import-pesanan', 'panel-import-pesanan');

    // Pelanggan
    createImportUI(
        'customers', 'panel-import-pelanggan', 'file-import-pelanggan',
        'btn-upload-pelanggan', 'btn-template-pelanggan', 'hasil-import-pelanggan',
        TEMPLATE_CUSTOMERS,
        () => { loadCustomers(); }
    );
    bindImportToggle('btn-import-pelanggan', 'panel-import-pelanggan');

    // Penjualan
    const TEMPLATE_SALES = 'date,product_name,individual_count,quantity_per_individual\n2026-08-17,Tempe,100,1';
    createImportUI(
        'sales', 'panel-import-penjualan', 'file-import-penjualan',
        'btn-upload-penjualan', 'btn-template-penjualan', 'hasil-import-penjualan',
        TEMPLATE_SALES,
        () => { loadSales(lastSalesFilter || 'hari'); loadSalesPrediction(); }
    );
    bindImportToggle('btn-import-penjualan', 'panel-import-penjualan');

    // ===================== INIT LOAD =====================
    loadStocks();
    loadStockRec();
    loadOrders();
    loadOrderProj();
    loadCustomers();
    loadSales();
    loadSalesPrediction();
    loadRecipes();
    loadProductsCache();
    loadChatHistory();
});
