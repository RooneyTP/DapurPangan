document.addEventListener('DOMContentLoaded', () => {
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

    const promptPills = document.querySelectorAll('.prompt-template');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.querySelector('.chat-messages');

    function scrollToBottom() {
        if (chatMessages) {
            chatMessages.scrollTo({
                top: chatMessages.scrollHeight,
                behavior: 'smooth'
            });
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

    function sendMessage(){
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

        setTimeout(() => {
            const aiHTML = `
                <div class="message ai-message">
                    <div class="bubble-ai">
                        Terima kasih atas pertanyaannya! Saya sedang memproses data untuk jawaban "${text}".
                    </div>
                </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', aiHTML);
            scrollToBottom();
        }, 1000);
    }

    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

// Hitung
    const btnHitung = document.getElementById("btn-hitung");
    const inputNama = document.getElementById("input-nama");
    const inputMargin = document.getElementById("input-margin");
    const inputMin = document.getElementById("input-min");
    const inputMax = document.getElementById("input-max");

    const hasilHarga = document.getElementById("hasil-harga");
    const hasilSubtext = document.getElementById("hasil-subtext");

    btnHitung.addEventListener("click", function(){
        const nama = inputNama.value.trim() || inputNama.placeholder;
        const margin = parseFloat(inputMargin.value) || parseFloat(inputMargin.placeholder);
        const min = parseFloat(inputMin.value) || parseFloat(inputMin.placeholder);
        const max = parseFloat(inputMax.value) || parseFloat(inputMax.placeholder);

        if(min > max){
            alert("Harga Pasar Min tidak boleh lebih besar dari Harga Pasar Max!");
            return;
        }

        let hargaRekomendasi = min + ((max-min) * (margin/100));

        if(hargaRekomendasi > max){
            hargaRekomendasi = max;
        }

        hargaRekomendasi = Math.round(hargaRekomendasi/100) * 100;
        const formatHarga = new Intl.NumberFormat('id-ID').format(hargaRekomendasi);
        hasilHarga.textContent = formatHarga;
        hasilSubtext.textContent = `Berdasarkan margin target ${margin}% & analisis pasar untuk ${nama}`;
    });

    const btnSemua_Bahan = document.getElementById('btn-semua-bahan');
    const btnHari_Bahan = document.getElementById('btn-hari-bahan');

    btnSemua_Bahan.addEventListener('click', function(){
        btnSemua_Bahan.classList.add('active');
        btnHari_Bahan.classList.remove('active');
    });

    btnHari_Bahan.addEventListener('click', function(){
        btnHari_Bahan.classList.add('active');
        btnSemua_Bahan.classList.remove('active');
    });

    const btnSemua_Pesanan = document.getElementById('btn-semua-pesanan');
    const btnHari_Pesanan = document.getElementById('btn-hari-pesanan');

    btnSemua_Pesanan.addEventListener('click', function(){
        btnSemua_Pesanan.classList.add('active');
        btnHari_Pesanan.classList.remove('active');
    });

    btnHari_Pesanan.addEventListener('click', function(){
        btnSemua_Pesanan.classList.remove('active');
        btnHari_Pesanan.classList.add('active');
    });
});