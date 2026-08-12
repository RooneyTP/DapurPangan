document.addEventListener('DOMContentLoaded', () => {
    const menuItems = document.querySelectorAll('#isi-sidebar .isi');
    const sections = document.querySelectorAll('#main-frame > div');
    function switchPage(targetId){
        sections.forEach(section => {
            section.style.display = 'none';
        });

        const targetSection = document.querySelector(targetId);

        if(targetSection){
            targetSection.style.display= 'block'
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
});