// ============================================================
// FILE: frontend/js/widget-chat.js
// PURPOSE: SSE Streaming Chat Widget
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    enforceGlobalAuth();
    const container = document.getElementById('ai-chat-widget-container');
    if (!container) return;

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
                
                <div id="widget-thought-indicator" style="display: none; background: #f8fafc; padding: 8px 15px; font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #e2e8f0; align-items: center; gap: 8px;">
                    <div class="spinner-border text-primary" role="status" style="width: 12px; height: 12px; border-width: 2px;"></div>
                    <span id="widget-thought-text" style="font-weight: 600;">Agent reasoning...</span>
                </div>

                <div id="widget-chat-messages" style="flex: 1; padding: 20px; overflow-y: auto; background: #f8fafc; display: flex; flex-direction: column; gap: 15px;">
                    <div style="display: flex; justify-content: flex-start;">
                        <div style="background: white; border: 1px solid #e2e8f0; padding: 12px 16px; border-radius: 16px 16px 16px 4px; color: #333; font-size: 0.95rem; box-shadow: 0 2px 5px rgba(0,0,0,0.02); max-width: 85%; line-height: 1.4;">
                            👋 Welcome to AI Store! I'm powered by LangGraph. How can I assist you today?
                        </div>
                    </div>
                </div>
                
                <div style="padding: 15px; background: white; border-top: 1px solid #eee; display: flex; gap: 10px; align-items: center;">
                    <input type="text" id="widget-chat-input" placeholder="Type your request here..." style="flex: 1; border: 2px solid #f1f5f9; border-radius: 25px; padding: 12px 18px; font-size: 0.95rem; outline: none; transition: border 0.3s; background: #f8fafc;">
                    <button id="widget-chat-send" style="background: linear-gradient(135deg, #6366f1, #a855f7); color: white; border: none; border-radius: 50%; width: 45px; height: 45px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(99,102,241,0.3);">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16"><path d="M15.854.146a.5.5 0 0 1 .11.54l-5.819 14.547a.75.75 0 0 1-1.329.124l-3.178-4.995L.643 7.184a.75.75 0 0 1 .124-1.33L15.314.037a.5.5 0 0 1 .54.11ZM6.636 10.07l2.761 4.338L14.13 2.576zm6.787-8.201L1.591 6.602l4.339 2.76 7.494-7.493Z"/></svg>
                    </button>
                </div>
            </div>
            
            <div id="chat-toggle" style="width: 65px; height: 65px; border-radius: 50%; background: white; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4); margin-left: auto; transition: transform 0.2s; border: 2px solid #6366f1;">
                ${widgetIconHTML}
            </div>
        </div>
    `;
    
    initChatWidget();
});

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

function initChatWidget() {
    const userId = localStorage.getItem('userId');
    const widget = document.getElementById('ai-chat-widget');
    
    if (userId && widget) widget.style.display = 'block';

    document.getElementById('chat-toggle')?.addEventListener('click', function() {
        const popup = document.getElementById('chat-popup');
        popup.style.display = popup.style.display === 'none' ? 'flex' : 'none';
        scrollToWidgetBottom();
    });

    document.getElementById('chat-close')?.addEventListener('click', function() {
        document.getElementById('chat-popup').style.display = 'none';
    });

    document.getElementById('widget-chat-input')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendWidgetMessage();
    });

    document.getElementById('widget-chat-send')?.addEventListener('click', sendWidgetMessage);
}

function scrollToWidgetBottom() {
    const container = document.getElementById('widget-chat-messages');
    if (container) container.scrollTop = container.scrollHeight;
}

async function sendWidgetMessage() {
    const input = document.getElementById('widget-chat-input');
    const sendBtn = document.getElementById('widget-chat-send');
    const thoughtBanner = document.getElementById('widget-thought-indicator');
    const thoughtText = document.getElementById('widget-thought-text');

    const userId = localStorage.getItem('userId');
    const token = localStorage.getItem('token');
    const message = input?.value.trim();
    
    if (!message || !userId) return;

    input.value = '';
    input.disabled = true;
    sendBtn.disabled = true;
    
    addWidgetMessage('user', message);
    
    thoughtBanner.style.display = 'flex';
    thoughtText.textContent = "Routing request...";
    scrollToWidgetBottom();

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
        
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        
        // SSE Stream parsing logic
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let currentAIBubble = createEmptyWidgetAIBubble();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            let lines = buffer.split('\n\n');
            buffer = lines.pop(); 

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
                                currentAIBubble.innerHTML += data.content.replace(/\n/g, '<br>');
                                scrollToWidgetBottom();
                            }
                        } 
                        else if (data.type === 'ui_block') {
                            if (currentAIBubble.innerHTML === '') currentAIBubble.parentNode.remove();
                            injectWidgetHtmlBlock(data.content);
                            currentAIBubble = createEmptyWidgetAIBubble();
                        } 
                        else if (data.type === 'end') {
                            thoughtBanner.style.display = 'none';
                            if (currentAIBubble.innerHTML === '') currentAIBubble.parentNode.remove();
                        }
                    } catch (e) {}
                }
            }
        }
        
    } catch (error) {
        thoughtBanner.style.display = 'none';
        addWidgetMessage('ai', 'Connection error occurred.');
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
        scrollToWidgetBottom();
    }
}

function createEmptyWidgetAIBubble() {
    const container = document.getElementById('widget-chat-messages');
    const div = document.createElement('div');
    div.style.display = 'flex';
    div.style.justifyContent = 'flex-start';
    
    const bubble = document.createElement('div');
    bubble.style.background = 'white';
    bubble.style.border = '1px solid #e2e8f0';
    bubble.style.padding = '12px 16px';
    bubble.style.borderRadius = '16px 16px 16px 4px';
    bubble.style.color = '#333';
    bubble.style.fontSize = '0.95rem';
    bubble.style.boxShadow = '0 2px 5px rgba(0,0,0,0.02)';
    bubble.style.maxWidth = '85%';
    bubble.style.lineHeight = '1.4';
    
    div.appendChild(bubble);
    container.appendChild(div);
    scrollToWidgetBottom();
    return bubble;
}

function injectWidgetHtmlBlock(htmlContent) {
    const container = document.getElementById('widget-chat-messages');
    const div = document.createElement('div');
    div.style.display = 'flex';
    div.style.justifyContent = 'flex-start';
    div.style.width = '100%';
    div.innerHTML = htmlContent;
    container.appendChild(div);
    scrollToWidgetBottom();
}

function addWidgetMessage(type, text) {
    if (type === 'ai') {
        const bubble = createEmptyWidgetAIBubble();
        bubble.innerHTML = text.replace(/\n/g, '<br>');
    } else {
        const container = document.getElementById('widget-chat-messages');
        const div = document.createElement('div');
        div.style.display = 'flex';
        div.style.justifyContent = 'flex-end';
        
        div.innerHTML = `<div style="background: linear-gradient(135deg, #6366f1, #a855f7); color: white; padding: 12px 16px; border-radius: 16px 16px 4px 16px; font-size: 0.95rem; box-shadow: 0 2px 5px rgba(0,0,0,0.02); max-width: 85%; line-height: 1.4;">${text}</div>`;
        container.appendChild(div);
    }
    scrollToWidgetBottom();
}