// ============================================================
// FILE: frontend/js/chat.js
// PURPOSE: Modern AI chat interface
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        addMessage('system', 'Please login to use the AI assistant.');
    }
    
    document.getElementById('chat-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const userId = localStorage.getItem('userId');
    const message = input.value.trim();
    
    if (!message) return;
    if (!userId) {
        addMessage('system', 'Please login first!');
        return;
    }
    
    input.value = '';
    addMessage('user', message);
    
    // Show typing indicator
    document.getElementById('typing-indicator').style.display = 'block';
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: parseInt(userId),
                message: message
            })
        });
        
        if (!response.ok) {
            throw new Error('API error: ' + response.status);
        }
        
        const data = await response.json();
        document.getElementById('typing-indicator').style.display = 'none';
        addMessage('ai', data.response);
        
    } catch (error) {
        document.getElementById('typing-indicator').style.display = 'none';
        addMessage('ai', 'Sorry, I encountered an error: ' + error.message);
        console.error('Chat error:', error);
    }
}

function addMessage(type, text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message ' + type;
    
    let bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    // Format AI responses with line breaks and product recommendations
    if (type === 'ai') {
        // Convert \n to <br>
        let formattedText = text.replace(/\n/g, '<br>');
        
        // Highlight product recommendations
        if (formattedText.includes('Recommended products:')) {
            bubble.innerHTML = formattedText.replace(
                /Recommended products:/g, 
                '<strong>🛍️ Recommended products:</strong>'
            );
        } else {
            bubble.innerHTML = formattedText;
        }
    } else if (type === 'system') {
        div.className = 'text-center text-muted py-2';
        bubble.innerHTML = text;
    } else {
        bubble.textContent = text;
    }
    
    div.appendChild(bubble);
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}