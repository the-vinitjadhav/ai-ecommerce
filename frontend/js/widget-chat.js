// ============================================================
// FILE: frontend/js/widget-chat.js
// PURPOSE: Global Auth Controller & Floating AI Chat Widget
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    // 1. FIX THE "FAKE LOGOUT" BUG ACROSS ALL PAGES
    enforceGlobalAuth();

    // 2. INJECT THE WIDGET HTML DIRECTLY
    const container = document.getElementById('ai-chat-widget-container');
    if (!container) return;

    // Cloud-Proof Image Fallback for the Widget Icon
    const widgetIconHTML = `<img src="images/robot.png" alt="AI" onerror="this.onerror=null; this.src='https://ui-avatars.com/api/?name=AI&background=6366f1&color=fff&rounded=true';" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;

    container.innerHTML = `
        <div id="ai-chat-widget" style="display: none; position: fixed; bottom: 25px; right: 25px; z-index: 9999; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <div id="chat-popup" style="display: none; width: 360px; height: 550px; background: white; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); flex-direction: column; overflow: hidden; margin-bottom: 15px; border: 1px solid rgba(0,0,0,0.05);">
                
                <div style="background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 25px; height: 25px;">${widgetIconHTML}</div>
                        <h6 style="margin: 0; font-weight: 700; font-size: 1.1rem; letter-spacing: 0.5px;">AI Assistant</h6>
                    </div>
                    <button id="chat-close" style="background: none; border: none; color: white; cursor: pointer; font-size: 1.8rem; line-height: 1;">&times;</button>
                </div>
                
                <div id="widget-chat-messages" style="flex: 1; padding: 20px; overflow-y: auto; background: #f8fafc; display: flex; flex-direction: column; gap: 15px;">
                    <div style="display: flex; justify-content: flex-start;">
                        <div style="background: white; border: 1px solid #e2e8f0; padding: 12px 16px; border-radius: 16px 16px 16px 4px; color: #333; font-size: 0.95rem; box-shadow: 0 2px 5px rgba(0,0,0,0.02); max-width: 85%; line-height: 1.4;">
                            👋 Welcome to AI Store! I'm your AI shopping guide. I can help you find products, compare items, or check on your order status.
                        </div>
                    </div>
                    <div id="widget-typing-indicator" style="display: none; justify-content: flex-start; align-items: center; gap: 5px; padding: 10px;">
                        <div style="width: 8px; height: 8px; background: #a855f7; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both;"></div>
                        <div style="width: 8px; height: 8px; background: #a855f7; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both; animation-delay: 0.16s;"></div>
                        <div style="width: 8px; height: 8px; background: #a855f7; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out both; animation-delay: 0.32s;"></div>
                    </div>
                </div>
                
                <div style="padding: 15px; background: white; border-top: 1px solid #eee; display: flex; gap: 10px; align-items: center;">
                    <input type="text" id="widget-chat-input" placeholder="Ask me anything..." style="flex: 1; border: 2px solid #f1f5f9; border-radius: 25px; padding: 12px 18px; font-size: 0.95rem; outline: none; transition: border 0.3s; background: #f8fafc;">
                    <button id="widget-chat-send" style="background: linear-gradient(135deg, #6366f1, #a855f7); color: white; border: none; border-radius: 50%; width: 45px; height: 45px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(99,102,241,0.3);">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16"><path d="M15.854.146a.5.5 0 0 1 .11.54l-5.819 14.547a.75.75 0 0 1-1.329.124l-3.178-4.995L.643 7.184a.75.75 0 0 1 .124-1.33L15.314.037a.5.5 0 0 1 .54.11ZM6.636 10.07l2.761 4.338L14.13 2.576zm6.787-8.201L1.591 6.602l4.339 2.76 7.494-7.493Z"/></svg>
                    </button>
                </div>
            </div>
            
            <div id="chat-toggle" style="width: 65px; height: 65px; border-radius: 50%; background: white; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4); margin-left: auto; transition: transform 0.2s; border: 2px solid #6366f1;">
                ${widgetIconHTML}
            </div>
        </div>
        <style>@keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }</style>
    `;
    
    initChatWidget();
});

// ============================================================
// GLOBAL AUTHENTICATION CONTROLLER
// ============================================================
function enforceGlobalAuth() {
    const userId = localStorage.getItem('userId');
    const loginLink = document.getElementById('login-link');
    
    if (userId && loginLink) {
        loginLink.textContent = 'Logout';
        loginLink.href = '#';
        loginLink.onclick = function(e) {
            e.preventDefault();
            localStorage.clear(); 
            window.location.href = 'index.html';
        };
    } else if (!userId && loginLink) {
        loginLink.textContent = 'Login';
        loginLink.href = 'login.html';
        loginLink.onclick = null;
    }
}

// ============================================================
// WIDGET CHAT LOGIC
// ============================================================
function initChatWidget() {
    const userId = localStorage.getItem('userId');
    const widget = document.getElementById('ai-chat-widget');
    
    // Require user to be logged in to see chat
    if (userId && widget) {
        widget.style.display = 'block';
    }

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
    if (container) container.scrollTop = container.scrollHeight;
}

async function sendWidgetMessage() {
    const input = document.getElementById('widget-chat-input');
    const userId = localStorage.getItem('userId');
    const token = localStorage.getItem('token');
    const message = input?.value.trim();
    
    if (!message || !userId) return;

    input.value = '';
    addWidgetMessage('user', message);
    
    const typingIndicator = document.getElementById('widget-typing-indicator');
    if (typingIndicator) typingIndicator.style.display = 'flex';
    scrollToBottom();

    const currentPage = window.location.pathname.split('/').pop() || 'Home';
    const cartCountElement = document.getElementById('cart-count');
    const cartCount = cartCountElement ? cartCountElement.textContent : '0';

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
        addWidgetMessage('ai', 'Sorry, I encountered an error connecting to the server.');
        console.error('Chat error:', error);
    }
}

function addWidgetMessage(type, text) {
    const container = document.getElementById('widget-chat-messages');
    const typingIndicator = document.getElementById('widget-typing-indicator');
    if (!container) return;

    const div = document.createElement('div');
    div.style.display = 'flex';
    div.style.justifyContent = type === 'user' ? 'flex-end' : 'flex-start';
    
    // UI FIX: AI bubbles are transparent so Python HTML renders perfectly without the box-in-a-box effect
    const bubbleBg = type === 'user' ? 'linear-gradient(135deg, #6366f1, #a855f7)' : 'transparent';
    const textColor = type === 'user' ? 'white' : '#333';
    const padding = type === 'user' ? '12px 16px' : '0px'; 
    const borderRadius = type === 'user' ? '16px 16px 4px 16px' : '0px';
    const shadow = type === 'user' ? '0 2px 5px rgba(0,0,0,0.02)' : 'none';
    const widthConstraint = type === 'user' ? 'auto' : '100%';

    div.innerHTML = `<div style="background: ${bubbleBg}; color: ${textColor}; padding: ${padding}; border-radius: ${borderRadius}; font-size: 0.95rem; box-shadow: ${shadow}; max-width: 90%; line-height: 1.5; word-wrap: break-word; width: ${widthConstraint};">${text}</div>`;
    
    if (typingIndicator && typingIndicator.parentNode === container) {
        container.insertBefore(div, typingIndicator);
    } else {
        container.appendChild(div);
    }
    scrollToBottom();
}