(function () {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    function init() {
        if (window.__chatbotInit) return;
        window.__chatbotInit = true;

        const CHAT_POLL_MS = 2000;
        const ENABLE_TYPING_EFFECT = true;
        const TYPING_SPEED_MS = 15;

        function getCookie(name) {
            const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
            return m ? m.pop() : '';
        }

        function escapeHTML(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        function typesetLatex(container) {
            if (window.MathJax && window.MathJax.typesetPromise) {
                return window.MathJax.typesetPromise([container]).catch(() => { });
            }
            return Promise.resolve();
        }

        async function typeOutHTML(containerEl, html, speed = TYPING_SPEED_MS) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            const plainText = tempDiv.textContent || '';

            let displayedChars = 0;
            containerEl.textContent = '';

            return new Promise((resolve) => {
                const interval = setInterval(() => {
                    if (displayedChars < plainText.length) {
                        containerEl.textContent = plainText.substring(0, displayedChars + 1);
                        displayedChars++;
                    } else {
                        clearInterval(interval);
                        containerEl.innerHTML = html;
                        typesetLatex(containerEl).then(resolve);
                    }
                }, speed);
            });
        }
        const chatForm = document.getElementById('chat-form');
        const chatLog = document.getElementById('chat-log');
        const messageInput = document.getElementById('message-input');

        if (!chatForm || !chatLog || !messageInput) return;

        const state = {
            lastMessageId: null,
            isPolling: false,
            isSending: false,
            processedMessageIds: new Set(),
            pendingUserMessage: null
        };

        (function initLastId() {
            const nodes = chatLog.querySelectorAll('[data-msg-id]');
            nodes.forEach(node => {
                const id = node.dataset.msgId;
                if (id) {
                    state.processedMessageIds.add(id);
                    state.lastMessageId = id;
                }
            });
        })();

        function messageExists(msgId) {
            return msgId && state.processedMessageIds.has(String(msgId));
        }

        function markMessageProcessed(msgId) {
            if (msgId) {
                state.processedMessageIds.add(String(msgId));
                state.lastMessageId = String(msgId);
            }
        }

        function createUserMessage(text, msgId = null) {
            const div = document.createElement('div');
            div.className = 'user';
            if (msgId) {
                div.dataset.msgId = String(msgId);
            } else {
                div.dataset.tempId = Date.now().toString();
            }
            const time = new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
            div.innerHTML = `<strong>User:</strong> ${escapeHTML(text)} <small>${time}</small>`;
            return div;
        }

        async function createBotMessage(html, msgId, timestamp) {
            const div = document.createElement('div');
            div.className = 'bot';
            div.dataset.msgId = String(msgId);
            const time = timestamp || new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });

            if (ENABLE_TYPING_EFFECT) {
                div.innerHTML = `<strong>Assistant:</strong> <span class="bot-text"></span> <small>${time}</small>`;
                chatLog.appendChild(div);
                scrollToBottom();
                const span = div.querySelector('.bot-text');
                await typeOutHTML(span, html, TYPING_SPEED_MS);
            } else {
                div.innerHTML = `<strong>Assistant:</strong> <span class="bot-text">${html}</span> <small>${time}</small>`;
                chatLog.appendChild(div);
                await typesetLatex(div);
            }
            return div;
        }

        function scrollToBottom() {
            requestAnimationFrame(() => {
                chatLog.scrollTop = chatLog.scrollHeight;
            });
        }

        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = (messageInput.value || '').trim();
            if (!text || state.isSending) return;

            const sessionId = chatForm.getAttribute('data-session-id');
            const sendUrl = chatForm.getAttribute('data-send-url');
            const csrfToken = chatForm.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

            state.isSending = true;
            messageInput.disabled = true;
            messageInput.value = '';

            const userMsgDiv = createUserMessage(text);
            state.pendingUserMessage = userMsgDiv;
            chatLog.appendChild(userMsgDiv);
            scrollToBottom();

            try {
                const response = await fetch(sendUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: new URLSearchParams({ message: text, session_id: sessionId }),
                });

                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                await response.json();
                setTimeout(() => pollNewMessages(), 300);

            } catch (error) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'bot';
                const time = new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
                errorDiv.innerHTML = `<strong>Assistant:</strong> <span class="bot-text">Error al enviar el mensaje.</span> <small>${time}</small>`;
                chatLog.appendChild(errorDiv);
                scrollToBottom();
            } finally {
                state.isSending = false;
                messageInput.disabled = false;
                messageInput.focus();
            }
        });

        async function pollNewMessages() {
            if (state.isPolling) return;
            state.isPolling = true;

            const sessionId = chatForm.getAttribute('data-session-id');
            if (!sessionId) {
                state.isPolling = false;
                return;
            }

            const params = new URLSearchParams({ session_id: sessionId });
            if (state.lastMessageId) params.append('after_id', state.lastMessageId);

            try {
                const response = await fetch(`/chatbot/poll_messages/?${params.toString()}`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });

                if (!response.ok) {
                    state.isPolling = false;
                    return;
                }

                const data = await response.json();
                const messages = Array.isArray(data.messages) ? data.messages : [];
                if (messages.length === 0) {
                    state.isPolling = false;
                    return;
                }

                for (const msg of messages) {
                    if (messageExists(msg.id)) continue;

                    if (msg.sender === 'user') {
                        if (state.pendingUserMessage && state.pendingUserMessage.parentNode) {
                            state.pendingUserMessage.dataset.msgId = String(msg.id);
                            delete state.pendingUserMessage.dataset.tempId;
                            state.pendingUserMessage.innerHTML = `<strong>User:</strong> ${msg.html} <small>${msg.timestamp}</small>`;
                            state.pendingUserMessage = null;
                        } else {
                            const userDiv = createUserMessage('', msg.id);
                            userDiv.innerHTML = `<strong>User:</strong> ${msg.html} <small>${msg.timestamp}</small>`;
                            chatLog.appendChild(userDiv);
                        }
                        markMessageProcessed(msg.id);
                        scrollToBottom();

                    } else if (msg.sender === 'bot') {
                        await createBotMessage(msg.html, msg.id, msg.timestamp);
                        markMessageProcessed(msg.id);
                        scrollToBottom();
                    }
                }

            } catch (error) {
            } finally {
                state.isPolling = false;
            }
        }

        let pollingTimer = setInterval(() => {
            if (!state.isSending) pollNewMessages();
        }, CHAT_POLL_MS);

        document.querySelectorAll('.rename-chat').forEach((btn) => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();

                const id = btn.dataset.id;
                const currentName = btn.parentElement.querySelector('.chat-name')?.textContent.trim() || '';
                const newName = prompt('Nuevo nombre del chat:', currentName);
                if (!newName || newName === currentName) return;

                try {
                    const response = await fetch(`/chatbot/session/${id}/rename/`, {
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
                        const label = btn.parentElement.querySelector('.chat-name');
                        if (data.name && label) label.textContent = data.name;
                    } else {
                        alert('No se pudo renombrar el chat.');
                    }
                } catch (error) {
                    alert('Error al renombrar el chat.');
                }
            });
        });

        scrollToBottom();
        typesetLatex(chatLog);
        messageInput.focus();

        window.addEventListener('beforeunload', () => {
            if (pollingTimer) clearInterval(pollingTimer);
        });
    }
})();

(() => {
    const form = document.getElementById('chat-form');
    const textarea = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn') || (form ? form.querySelector('button[type="submit"]') : null);
    if (!form || !textarea) return;

    const autoresize = () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 160) + 'px';
    };
    textarea.addEventListener('input', autoresize);
    queueMicrotask(autoresize);

    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            form.requestSubmit();
        }
    });

    if (sendBtn && sendBtn.type !== 'submit') {
        sendBtn.addEventListener('click', (e) => {
            e.preventDefault();
            form.requestSubmit();
        });
    }

    window.WRITE_INSTANT = true;

    if (window.typeWriter) {
        window.typeWriter = (el, html) => { el.innerHTML = html; enhanceCodeBlocks(el); };
    }
})();

// ======= Mejora visual de <pre><code> + botón Copiar =======
function enhanceCodeBlocks(scope) {
    const root = scope && scope.querySelectorAll ? scope : document;
    root.querySelectorAll('pre').forEach(pre => {
        if (pre.dataset.enhanced) return;
        const code = pre.querySelector('code') || pre.firstElementChild || pre;
        // Barra superior
        const bar = document.createElement('div');
        bar.className = 'code-toolbar';
        // Etiqueta de lenguaje (si existe class="language-xyz")
        const cls = (code.getAttribute('class') || '').match(/language-([a-z0-9+#-]+)/i);
        if (cls && cls[1]) {
            const label = document.createElement('span');
            label.className = 'code-label';
            label.textContent = cls[1].toLowerCase();
            bar.appendChild(label);
        }
        // Botón copiar
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'copy-btn';
        btn.textContent = 'Copiar';
        btn.addEventListener('click', async () => {
            const text = code.innerText || code.textContent || '';
            try {
                await navigator.clipboard.writeText(text);
                btn.classList.add('copied');
                btn.textContent = 'Copiado ✓';
                setTimeout(() => { btn.classList.remove('copied'); btn.textContent = 'Copiar'; }, 1200);
            } catch (e) {
                btn.textContent = 'Error';
                setTimeout(() => (btn.textContent = 'Copiar'), 1200);
            }
        });
        bar.appendChild(btn);

        pre.appendChild(bar);
        pre.dataset.enhanced = '1';
    });
}

// 1) Ejecutar al cargar
document.addEventListener('DOMContentLoaded', () => enhanceCodeBlocks(document));

// 2) Ejecutar cuando entren nuevos mensajes al chat
(() => {
    const log = document.getElementById('chat-log');
    if (!log) return;
    const obs = new MutationObserver(muts => {
        muts.forEach(m => m.addedNodes.forEach(n => {
            if (n.nodeType === 1) enhanceCodeBlocks(n);
        }));
    });
    obs.observe(log, { childList: true, subtree: true });
})();

(() => {
    const form = document.getElementById('chat-form');
    const input = document.getElementById('message-input');
    const sendBtn = form?.querySelector('button[type="submit"]');

    if (!form || !input || !sendBtn) return;

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const start = input.selectionStart;
            const end = input.selectionEnd;
            const value = input.value;
            input.value = value.substring(0, start) + '\n' + value.substring(end);
            input.selectionStart = input.selectionEnd = start + 1;
        }
    });

    sendBtn.addEventListener('click', (e) => {
        e.preventDefault();
        form.requestSubmit();
    });

    const autoresize = () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 180) + 'px';
    };
    input.addEventListener('input', autoresize);
    autoresize();
})();

