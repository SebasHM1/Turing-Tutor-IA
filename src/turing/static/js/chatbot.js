document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatLog = document.getElementById('chat-log');

    if (!chatLog || !chatForm || !messageInput) return;

    const getCookie = name => {
        const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
        return m ? m.pop() : '';
    };

    function showTypingEffect(container, text, speed = 25) {
        let index = 0;
        const interval = setInterval(() => {
            if (index < text.length) {
                container.innerHTML += text.charAt(index);
                index++;
                // Re-render MathJax while typing
                if (window.MathJax && index % 10 === 0) {
                    MathJax.typesetPromise([container]).catch((err) => console.log('MathJax error:', err.message));
                }
            } else {
                clearInterval(interval);
                // Final MathJax render
                if (window.MathJax) {
                    MathJax.typesetPromise([container]).catch((err) => console.log('MathJax error:', err.message));
                }
            }
        }, speed);
    }

    chatForm.onsubmit = async function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        const sessionId = this.getAttribute('data-session-id');
        const sendUrl = this.getAttribute('data-send-url');
        const csrfInput = this.querySelector('[name=csrfmiddlewaretoken]');
        const csrfToken = csrfInput ? csrfInput.value : getCookie('csrftoken');
        
        // Clear input
        messageInput.value = '';
        
        // Add user message to chat immediately
        const userDiv = document.createElement('div');
        userDiv.className = 'user';
        userDiv.innerHTML = `<strong>User:</strong> ${message} <small>${new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute: '2-digit'})}</small>`;
        chatLog.appendChild(userDiv);
        
        // Scroll to bottom
        chatLog.scrollTop = chatLog.scrollHeight;
        
        try {
            const response = await fetch(sendUrl, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body: new URLSearchParams({
                    message: message,
                    session_id: sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.bot_message) {
                // Add bot message to chat with typing effect
                const botDiv = document.createElement('div');
                botDiv.className = 'bot';
                botDiv.innerHTML = `<strong>Bot:</strong> <span class="bot-text"></span> <small>${new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute: '2-digit'})}</small>`;
                chatLog.appendChild(botDiv);
                
                // Use typing effect for bot response
                showTypingEffect(botDiv.querySelector('.bot-text'), data.bot_message, 25);
                
            } else if (data.error) {
                // Show error message
                const errorDiv = document.createElement('div');
                errorDiv.className = 'bot error';
                errorDiv.innerHTML = `<strong>Error:</strong> ${data.error} <small>${new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute: '2-digit'})}</small>`;
                chatLog.appendChild(errorDiv);
            }
        } catch (error) {
            console.error('Error:', error);
            // Show error message to user
            const errorDiv = document.createElement('div');
            errorDiv.className = 'bot error';
            errorDiv.innerHTML = `<strong>Error:</strong> Hubo un problema al enviar el mensaje. <small>${new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute: '2-digit'})}</small>`;
            chatLog.appendChild(errorDiv);
        }
        
        // Scroll to bottom
        chatLog.scrollTop = chatLog.scrollHeight;
    };

    // Auto-scroll to bottom on page load
    if (chatLog) {
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    // Re-render MathJax on page load for existing messages
    if (window.MathJax) {
        MathJax.typesetPromise().catch((err) => console.log('MathJax error:', err.message));
    }
});


requestAnimationFrame(() => { chatLog.scrollTop = chatLog.scrollHeight; });


document.querySelectorAll('.rename-chat').forEach(btn => {
    btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        const current = (btn.parentElement.querySelector('.chat-name')?.textContent || '').trim();
        const name = prompt('Nuevo nombre del chat:', current);
        if (!name) return;

        const res = await fetch(`/chatbot/session/${id}/rename/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest' },
            body: new URLSearchParams({ name })
        });
        if (res.ok) {
            const data = await res.json();
            const label = btn.parentElement.querySelector('.chat-name');
            if (data.name && label) label.textContent = data.name;
        } else {
            alert('No se pudo renombrar el chat.');
        }
    }, { passive: true });
});
