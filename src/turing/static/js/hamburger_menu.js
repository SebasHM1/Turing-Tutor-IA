document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    const sidebar = document.getElementById('teacher-sidebar');
    const sidebarGif = document.getElementById('sidebar-gif');
    const pageContainer = document.querySelector('.page');

    if (!sidebar || !sidebarGif || !pageContainer) {
        console.warn('Hamburger menu: elementos no encontrados');
        return;
    }

    const GIFS = {
        ABIERTO: '/static/videos/Abierto.gif',
        CERRADO: '/static/videos/Cerrado.gif',
        DERECHA: '/static/videos/Derecha.gif',
        IZQUIERDA: '/static/videos/Izquierda.gif'
    };

    let isOpen = true;

    function changeGif(newSrc) {
        sidebarGif.src = newSrc + '?t=' + Date.now();
    }

    function toggleSidebar() {
        isOpen = !isOpen;

        if (isOpen) {
            changeGif(GIFS.DERECHA);
            pageContainer.classList.remove('sidebar-closed');

            setTimeout(function () {
                changeGif(GIFS.ABIERTO);
            }, 300);
        } else {
            changeGif(GIFS.IZQUIERDA);
            pageContainer.classList.add('sidebar-closed');

            setTimeout(function () {
                changeGif(GIFS.CERRADO);
            }, 300);
        }
    }

    sidebarGif.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        toggleSidebar();
    });

    sidebarGif.style.cursor = 'pointer';
});
