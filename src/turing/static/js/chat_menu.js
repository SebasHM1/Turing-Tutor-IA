document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // Manejo del menú de 3 puntos de cada chat
    const chatMenuButtons = document.querySelectorAll('.chat-menu-btn');

    // Cerrar menú al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.chat-menu')) {
            document.querySelectorAll('.chat-menu-dropdown.open').forEach(menu => {
                menu.classList.remove('open');
            });
        }
    });

    chatMenuButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const chatId = this.getAttribute('data-chat-id');
            const dropdown = document.getElementById('chat-menu-' + chatId);

            // Cerrar otros menús abiertos
            document.querySelectorAll('.chat-menu-dropdown.open').forEach(menu => {
                if (menu !== dropdown) {
                    menu.classList.remove('open');
                }
            });

            // Toggle del menú actual
            dropdown.classList.toggle('open');
        });
    });

    // Función para obtener cookie CSRF
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Renombrado mediante botón en el menú de 3 puntos
    const renameButtons = document.querySelectorAll('.chat-rename-btn');
    renameButtons.forEach(button => {
        button.addEventListener('click', async function(e) {
            e.preventDefault();
            e.stopPropagation();

            const chatId = this.getAttribute('data-chat-id');
            const chatNameEl = document.querySelector(`.chat-name[data-id="${chatId}"]`);

            if (!chatNameEl) return;

            const originalName = chatNameEl.textContent.trim();
            chatNameEl.contentEditable = 'true';
            chatNameEl.focus();

            // Seleccionar todo el texto
            const range = document.createRange();
            range.selectNodeContents(chatNameEl);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);

            // Cerrar el menú dropdown
            const dropdown = document.getElementById('chat-menu-' + chatId);
            if (dropdown) dropdown.classList.remove('open');

            // Manejar blur (cuando pierde el foco)
            const blurHandler = async function() {
                if (this.contentEditable === 'false') return;

                this.contentEditable = 'false';
                const newName = this.textContent.trim();

                if (!newName || newName === originalName) {
                    this.textContent = originalName;
                    return;
                }

                try {
                    const response = await fetch(`/chatbot/session/${chatId}/rename/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken'),
                            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        body: new URLSearchParams({ name: newName }),
                    });

                    if (response.ok) {
                        const data = await response.json();
                        if (data.name) this.textContent = data.name;
                    } else {
                        this.textContent = originalName;
                        alert('No se pudo renombrar el chat.');
                    }
                } catch (error) {
                    this.textContent = originalName;
                    alert('Error al renombrar el chat.');
                }

                // Remover listeners
                this.removeEventListener('blur', blurHandler);
                this.removeEventListener('keydown', keyHandler);
            };

            // Manejar teclas
            const keyHandler = function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.blur();
                } else if (e.key === 'Escape') {
                    this.textContent = originalName;
                    this.contentEditable = 'false';
                    this.removeEventListener('blur', blurHandler);
                    this.removeEventListener('keydown', keyHandler);
                }
            };

            chatNameEl.addEventListener('blur', blurHandler);
            chatNameEl.addEventListener('keydown', keyHandler);
        });
    });

    // Confirmación de eliminación
    const deleteForms = document.querySelectorAll('.chat-delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('¿Estás seguro de que quieres eliminar este chat?')) {
                e.preventDefault();
            }
        });
    });
});
