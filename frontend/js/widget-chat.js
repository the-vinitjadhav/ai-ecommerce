// ============================================================
// FILE: frontend/js/widget-chat.js
// PURPOSE: Floating AI Chat Widget with Global Injection
// ============================================================

document.addEventListener('DOMContentLoaded', async function() {
    // 1. Find the empty container on the current page
    const container = document.getElementById('ai-chat-widget-container');
    if (!container) return;

    try {
        // 2. Fetch the widget HTML from the server
        const response = await fetch('/chat-widget.html');
        if (!response.ok) throw new Error("Failed to fetch widget HTML");
        
        const html = await response.text();
        
        // 3. Inject the HTML into the page safely
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = html;
        
        // Extract just the widget part (ignores duplicate script tags)
        const widgetNode = tempDiv.querySelector('#ai-chat-widget');
        if (widgetNode) {
            container.appendChild(widgetNode);
            // 4. Initialize the logic now that the HTML is on the screen!
            initChatWidget();
        }
        
    } catch (error) {
        console.error('Error loading chat widget:', error);
    }
});

// ============================================================
// WIDGET INITIALIZATION & LOGIC
// ============================================================
function initChatWidget() {
    const userId = localStorage.getItem('userId');
    const widget = document.getElementById('ai-chat-widget');
    
    // Only show the widget bubble if the user is logged in
    if (userId && widget) {
        widget.style.display = 'block';
    }

    // Add the typing indicator using the NEW CSS classes
    const messagesContainer = document.getElementById('widget-chat-messages');
    if (messagesContainer && !document.getElementById('widget-typing-indicator')) {
        messagesContainer.innerHTML += `
            <div id="widget-typing-indicator" class="msg-row msg-ai" style="display: none;">
                <div class="typing-bubble">
                    <div class="typing-dots"><span></span><span></span><span></span></div>
                </div>
            </div>
        `;
    }

    // Bind UI Event Listeners safely using optional chaining (?)
    document.getElementById('chat-toggle')?.addEventListener('click', function() {
        const popup = document.getElementById('chat-popup');
        popup.style.display = popup.style.display === 'none' ? 'flex' : 'none';
        scrollToBottom();
    });

    document.getElementById('chat-close')?.addEventListener('click', function() {
        document.getElementById('chat-popup').style.display = 'none';
    });

    document.getElementById('widget-chat-input')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendWidgetMessage();
    });

    document.getElementById('widget-chat-send')?.addEventListener('click', sendWidgetMessage);
}

function scrollToBottom() {
    const container = document.getElementById('widget-chat-messages');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

// ============================================================
// AI API COMMUNICATION
// ============================================================
async function sendWidgetMessage() {
    const input = document.getElementById('widget-chat-input');
    const userId = localStorage.getItem('userId');
    const token = localStorage.getItem('token');
    const message = input?.value.trim();
    
    if (!message || !userId) return;

    input.value = '';
    addWidgetMessage('user', message);
    
    // Show Typing Indicator
    const typingIndicator = document.getElementById('widget-typing-indicator');
    if (typingIndicator) typingIndicator.style.display = 'flex';
    scrollToBottom();

    // Harvest Context (Page name & Cart Count)
    const currentPage = window.location.pathname.split('/').pop() || 'Home';
    const cartCountElement = document.getElementById('cart-count');
    const cartCount = cartCountElement ? cartCountElement.textContent : '0';

   try {
        const response = await fetch('/api/chat', { 
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': token ? `Bearer ${token}` : ''
            },
            body: JSON.stringify({
                user_id: parseInt(userId),
                message: message,
                context: { page: currentPage, cart_items: cartCount } 
            })
        });
        
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        const data = await response.json();
        
        if (typingIndicator) typingIndicator.style.display = 'none';
        addWidgetMessage('ai', data.response);
        
    } catch (error) {
        if (typingIndicator) typingIndicator.style.display = 'none';
        addWidgetMessage('ai', 'Sorry, I encountered an error. Please try again.');
        console.error('Chat error:', error);
    }
}

function addWidgetMessage(type, text) {
    const container = document.getElementById('widget-chat-messages');
    const typingIndicator = document.getElementById('widget-typing-indicator');
    if (!container) return;

    const div = document.createElement('div');
    
    // Use the sleek new CSS classes instead of inline styles
    div.className = `msg-row ${type === 'user' ? 'msg-user' : 'msg-ai'}`;
    div.innerHTML = `<div class="bubble ${type === 'user' ? 'bubble-user' : 'bubble-ai'}">${text}</div>`;
    
    // Always insert the message BEFORE the typing indicator so the dots stay at the bottom
    if (typingIndicator && typingIndicator.parentNode === container) {
        container.insertBefore(div, typingIndicator);
    } else {
        container.appendChild(div);
    }
    scrollToBottom();
}