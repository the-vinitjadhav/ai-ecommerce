// ============================================================
// FILE: frontend/js/widget-chat.js
// PURPOSE: Floating AI Chat Widget Logic
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    // Show widget if user is logged in
    const userId = localStorage.getItem('userId');
    if (userId) {
        document.getElementById('ai-chat-widget').style.display = 'block';
    }

    // Toggle chat popup
    document.getElementById('chat-toggle').addEventListener('click', function() {
        const popup = document.getElementById('chat-popup');
        popup.style.display = popup.style.display === 'none' ? 'flex' : 'none';
    });

    // Close chat popup
    document.getElementById('chat-close').addEventListener('click', function() {
        document.getElementById('chat-popup').style.display = 'none';
    });

    // Send message on Enter key
    document.getElementById('widget-chat-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendWidgetMessage();
        }
    });

    // Send message on button click
    document.getElementById('widget-chat-send').addEventListener('click', function() {
        sendWidgetMessage();
    });
});

async function sendWidgetMessage() {
    const input = document.getElementById('widget-chat-input');
    const userId = localStorage.getItem('userId');
    const message = input.value.trim();
    
    if (!message || !userId) return;
    
    input.value = '';
    addWidgetMessage('user', message);
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: parseInt(userId),
                message: message
            })
        });
        
        if (!response.ok) throw new Error('API error');
        const data = await response.json();
        addWidgetMessage('ai', data.response);
        
    } catch (error) {
        addWidgetMessage('ai', 'Sorry, I encountered an error.');
        console.error('Chat error:', error);
    }
}

function addWidgetMessage(type, text) {
    const container = document.getElementById('widget-chat-messages');
    const div = document.createElement('div');
    
    if (type === 'user') {
        div.style.textAlign = 'right';
        div.style.marginBottom = '12px';
        div.innerHTML = `<div style="display:inline-block; background:#667eea; color:white; padding:10px 15px; border-radius:18px; border-bottom-right-radius:4px; max-width:80%;">${text}</div>`;
    } else if (type === 'ai') {
        div.style.textAlign = 'left';
        div.style.marginBottom = '12px';
        // Render HTML for AI responses
        div.innerHTML = `<div style="display:inline-block; background:white; color:#333; padding:10px 15px; border-radius:18px; border-bottom-left-radius:4px; max-width:80%; box-shadow:0 2px 5px rgba(0,0,0,0.05);">${text}</div>`;
    }
    
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
