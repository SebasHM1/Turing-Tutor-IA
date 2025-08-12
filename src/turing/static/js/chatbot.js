(function () {
    const chatLog = document.getElementById('chat-log');
    const form = document.getElementById('chat-form');
    const input = document.getElementById('message-input');
    if (!chatLog || !form || !input) return;

    const sendUrl = form.dataset.sendUrl || '';
    const sessionId = form.dataset.sessionId || '';

    // CSRF seguro, toma del input si existe o del cookie si no
    const getCookie = name => {
        const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return m ? m.pop() : '';
    };
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    const csrfToken = csrfInput ? csrfInput.value : getCookie('csrftoken');

    function showTypingEffect(container, text, speed = 25) {
        let index = 0;
        const interval = setInterval(() => {
            if (index < text.length) {
                container.innerHTML += text.charAt(index);
                index++;
            } else {
                clearInterval(interval);
            }
        }, speed);
    }

    form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const message = input.value.trim();
        if (!message) return;
        input.value = '';

        // Agrega el mensaje del usuario
        const userDiv = document.createElement('div');
        userDiv.className = 'user';
        userDiv.innerHTML = `<strong>User:</strong> ${message} <small>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small>`;
        chatLog.appendChild(userDiv);
        chatLog.scrollTop = chatLog.scrollHeight;

        try {
            const res = await fetch(sendUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
                body: new URLSearchParams({ message, session_id: sessionId })
            });
            const data = await res.json();

            if (data.bot_message) {
                const botDiv = document.createElement('div');
                botDiv.className = 'bot';
                botDiv.innerHTML = `<strong>Bot:</strong> <span class="bot-text"></span> <small>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small>`;
                chatLog.appendChild(botDiv);
                showTypingEffect(botDiv.querySelector('.bot-text'), data.bot_message, 25);
                chatLog.scrollTop = chatLog.scrollHeight;
            } else {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'bot error';
                errorDiv.innerHTML = `<strong>Error:</strong> ${data.error || 'There was an error'} <small>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small>`;
                chatLog.appendChild(errorDiv);
                chatLog.scrollTop = chatLog.scrollHeight;
            }
        } catch (err) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'bot error';
            errorDiv.innerHTML = `<strong>Error:</strong> Network error <small>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</small>`;
            chatLog.appendChild(errorDiv);
            chatLog.scrollTop = chatLog.scrollHeight;
        }
    });
})();
