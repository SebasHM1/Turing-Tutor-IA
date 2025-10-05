// static/js/chatbot.js
// Chat con envío AJAX, polling incremental, typing del bot y render de LaTeX.

(function () {
    if (window.__chatbotInit) return;
    window.__chatbotInit = true;

    // ===== Ajustes ============================================================
    const CHAT_POLL_MS = 3000;
    const ENABLE_TYPING_EFFECT = true;
    const TYPING_SPEED_MS = 20;

    // ===== Utils ==============================================================
    function getCookie(name) {
        const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return m ? m.pop() : '';
    }

    function renderHTMLForMessage(sender, html, time) {
        const who = sender === 'bot' ? 'Assistant' : 'User';
        const t = time || new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
        return `<strong>${who}:</strong> ${html} <small>${t}</small>`;
    }

    function createMsgNode(sender, html, id, time) {
        const div = document.createElement('div');
        div.className = sender; // "user" | "bot"
        if (id) div.dataset.msgId = String(id);
        div.innerHTML = renderHTMLForMessage(sender, html, time);
        return div;
    }

    function typesetLatex(container) {
        if (window.MathJax && window.MathJax.typesetPromise) {
            try { return window.MathJax.typesetPromise([container]); } catch { }
        }
        return Promise.resolve();
    }

    async function typeOutHTML(containerEl, html, speed = TYPING_SPEED_MS) {
        return new Promise((resolve) => {
            let i = 0;
            const total = html.length;
            containerEl.innerHTML = '';
            const interval = setInterval(async () => {
                if (i < total) {
                    containerEl.innerHTML += html.charAt(i++);
                    // re-typeset ocasionalmente para fórmulas largas
                    if (window.MathJax && i % 30 === 0) {
                        try { await window.MathJax.typesetPromise([containerEl]); } catch { }
                    }
                } else {
                    clearInterval(interval);
                    typesetLatex(containerEl).then(resolve);
                }
            }, speed);
        });
    }

    // ===== DOM ================================================================
    const chatForm = document.getElementById('chat-form');
    const chatLog = document.getElementById('chat-log');
    const messageInput = document.getElementById('message-input');
    if (!chatForm || !chatLog || !messageInput) return;

    // ===== Estado =============================================================
    let lastMessageId = (function initLastId() {
        const nodes = chatLog.querySelectorAll('[data-msg-id]');
        if (!nodes.length) return null;
        return nodes[nodes.length - 1].dataset.msgId || null;
    })();

    // ===== Envío de mensajes ==================================================
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const text = (messageInput.value || '').trim();
        if (!text) return;

        const sessionId = chatForm.getAttribute('data-session-id');
        const sendUrl = chatForm.getAttribute('data-send-url');
        const csrfToken = (chatForm.querySelector('[name=csrfmiddlewaretoken]')?.value) || getCookie('csrftoken');

        // 1) Muestra el mensaje del usuario “pendiente” (se reconciliará tras el poll)
        const pending = document.createElement('div');
        pending.className = 'user';
        pending.dataset.pending = '1';
        pending.innerHTML = renderHTMLForMessage('user', text);
        chatLog.appendChild(pending);
        chatLog.scrollTop = chatLog.scrollHeight;

        // 2) Limpia input
        messageInput.value = '';

        // 3) Envía
        try {
            await fetch(sendUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: new URLSearchParams({ message: text, session_id: sessionId }),
            });
        } catch {
            const err = createMsgNode('bot', 'Error enviando el mensaje.', '', null);
            chatLog.appendChild(err);
            chatLog.scrollTop = chatLog.scrollHeight;
            await typesetLatex(err);
        }

        // 4) Fuerza un poll inmediato para sincronizar
        await pollNewMessages();
    });

    // ===== Polling ============================================================
    let pollingTimer = null;

    async function pollNewMessages() {
        const sessionId = chatForm.getAttribute('data-session-id');
        if (!sessionId) return;

        const params = new URLSearchParams({ session_id: sessionId });
        if (lastMessageId) params.append('after_id', lastMessageId);

        try {
            const resp = await fetch(`/chatbot/poll_messages/?${params.toString()}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (!resp.ok) return;
            const data = await resp.json();
            const list = Array.isArray(data.messages) ? data.messages : [];
            if (!list.length) return;

            for (const m of list) {
                // Reemplaza el “pendiente” del usuario por el oficial (con id)
                if (m.sender === 'user') {
                    const pending = chatLog.querySelector('.user[data-pending="1"]');
                    if (pending) {
                        pending.innerHTML = renderHTMLForMessage('user', m.html, m.timestamp);
                        pending.dataset.msgId = String(m.id);
                        delete pending.dataset.pending;
                        lastMessageId = String(m.id);
                        await typesetLatex(pending);
                        continue;
                    }
                }

                // Añade mensaje nuevo
                if (m.sender === 'bot' && ENABLE_TYPING_EFFECT) {
                    // estructura del nodo: strong + span + small
                    const div = document.createElement('div');
                    div.className = 'bot';
                    div.dataset.msgId = String(m.id);
                    const t = m.timestamp || new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
                    div.innerHTML = `<strong>Assistant:</strong> <span class="bot-text"></span> <small>${t}</small>`;
                    const span = div.querySelector('.bot-text');
                    chatLog.appendChild(div);
                    chatLog.scrollTop = chatLog.scrollHeight;

                    await typeOutHTML(span, m.html);
                } else {
                    const node = createMsgNode(m.sender, m.html, m.id, m.timestamp);
                    chatLog.appendChild(node);
                    await typesetLatex(node);
                }

                lastMessageId = String(m.id);
            }

            chatLog.scrollTop = chatLog.scrollHeight;
        } catch {
        }
    }

    if (!pollingTimer) {
        pollingTimer = setInterval(pollNewMessages, CHAT_POLL_MS);
    }

    (function initRenameHandlers() {
        document.querySelectorAll('.rename-chat').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const id = btn.dataset.id;
                const current = (btn.parentElement.querySelector('.chat-name')?.textContent || '').trim();
                const name = prompt('Nuevo nombre del chat:', current);
                if (!name) return;

                try {
                    const res = await fetch(`/chatbot/session/${id}/rename/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken'),
                            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                            'X-Requested-With': 'XMLHttpRequest',
                        },
                        body: new URLSearchParams({ name }),
                    });
                    if (res.ok) {
                        const data = await res.json();
                        const label = btn.parentElement.querySelector('.chat-name');
                        if (data.name && label) label.textContent = data.name;
                    } else {
                        alert('No se pudo renombrar el chat.');
                    }
                } catch {
                    alert('No se pudo renombrar el chat.');
                }
            }, { passive: true });
        });
    })();

    requestAnimationFrame(() => { chatLog.scrollTop = chatLog.scrollHeight; });
    typesetLatex(chatLog);
})();
