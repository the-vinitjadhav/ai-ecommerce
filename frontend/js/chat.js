// ============================================================
// FILE: frontend/js/chat.js
// PURPOSE: Advanced SSE Streaming AI Chat
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
    const sendBtn = document.getElementById('send-btn');
    const thoughtBanner = document.getElementById('thought-indicator');
    const thoughtText = document.getElementById('thought-text');
    
    const userId = localStorage.getItem('userId');
    const token = localStorage.getItem('token');
    const message = input.value.trim();
    
    if (!message) return;
    if (!userId) {
        addMessage('system', 'Please login first!');
        return;
    }
    
    input.value = '';
    input.disabled = true;
    sendBtn.disabled = true;
    
    // Add user message to UI
    addMessage('user', message);
    
    // Show routing banner
    thoughtBanner.style.display = 'flex';
    thoughtText.textContent = "Supervisor is routing your request...";
    
    try {
        const BACKEND_URL = "https://ai-ecommerce-backend-barh.onrender.com"; 

        const response = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': token ? `Bearer ${token}` : ''
            },
            body: JSON.stringify({
                user_id: parseInt(userId),
                message: message
            })
        });
        
        if (!response.ok) throw new Error('API error: ' + response.status);
        
        // Setup SSE Stream Reader
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        
        // Create an empty AI bubble that we will stream text into
        let currentAIBubble = createEmptyAIBubble();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            let lines = buffer.split('\n\n');
            buffer = lines.pop(); // keep incomplete chunks in buffer

            for (let line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.substring(6).trim();
                    if (!dataStr) continue;

                    try {
                        const data = JSON.parse(dataStr);

                        if (data.type === 'thought') {
                            thoughtBanner.style.display = 'flex';
                            thoughtText.textContent = data.content;
                        } 
                        else if (data.type === 'text') {
                            if (!data.content.includes("DONE")) {
                                // Append live text to the existing bubble
                                currentAIBubble.innerHTML += data.content.replace(/\n/g, '<br>');
                                scrollToBottom();
                            }
                        } 
                        else if (data.type === 'ui_block') {
                            // Close current text bubble and inject the raw HTML Box
                            if (currentAIBubble.innerHTML === '') {
                                currentAIBubble.parentNode.remove();
                            }
                            injectHtmlBlock(data.content);
                            // Create a new empty text bubble in case LLM says more after the UI box
                            currentAIBubble = createEmptyAIBubble();
                        } 
                        else if (data.type === 'end') {
                            thoughtBanner.style.display = 'none';
                            // Clean up empty bubbles
                            if (currentAIBubble.innerHTML === '') {
                                currentAIBubble.parentNode.remove();
                            }
                        }
                    } catch (e) {
                        console.warn("Failed to parse SSE JSON", e);
                    }
                }
            }
        }
    } catch (error) {
        thoughtBanner.style.display = 'none';
        addMessage('ai', 'Sorry, I encountered an error: ' + error.message);
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
        scrollToBottom();
    }
}

function createEmptyAIBubble() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message ai';
    
    let bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    div.appendChild(bubble);
    container.appendChild(div);
    scrollToBottom();
    
    return bubble;
}

function injectHtmlBlock(htmlContent) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message ai w-100'; // Make UI blocks full width
    div.innerHTML = htmlContent;
    container.appendChild(div);
    scrollToBottom();
}

function addMessage(type, text) {
    if (type === 'system') {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'text-center text-muted py-2';
        div.innerHTML = text;
        container.appendChild(div);
        scrollToBottom();
        return;
    }
    
    const bubble = type === 'ai' ? createEmptyAIBubble() : createEmptyUserBubble();
    bubble.innerHTML = text.replace(/\n/g, '<br>');
    scrollToBottom();
}

function createEmptyUserBubble() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message user';
    
    let bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    div.appendChild(bubble);
    container.appendChild(div);
    scrollToBottom();
    
    return bubble;
}

function scrollToBottom() {
    const container = document.getElementById('chat-messages');
    container.scrollTop = container.scrollHeight;
}