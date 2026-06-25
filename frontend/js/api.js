// ============================================================
// FILE: frontend/js/api.js
// PURPOSE: All API calls to the backend
// ============================================================

// API base URL
const API_BASE = 'http://127.0.0.1:8000/api';

// ============================================================
// Generic fetch function
// ============================================================
async function apiFetch(endpoint, options = {}) {
    // Ensure method is defaulted to GET if not provided
    const method = options.method || 'GET';
    
    const url = `${API_BASE}${endpoint}`;
    console.log(`[API] ${method} ${url}`);

    try {
        const response = await fetch(url, {
            ...options,
            method: method,  // Explicitly set method
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            let errorMessage = 'Request failed';
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorData.error || errorMessage;
            } catch (e) {
                errorMessage = response.statusText || errorMessage;
            }
            throw new Error(errorMessage);
        }
        
        return response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ============================================================
// AUTH FUNCTIONS
// ============================================================
async function registerUser(userData) {
    return apiFetch('/auth/register', {   
        method: 'POST',
        body: JSON.stringify(userData)
    });
}

async function loginUser(credentials) {
    return apiFetch('/auth/login', {     
        method: 'POST',
        body: JSON.stringify(credentials)
    });
}

// ============================================================
// PRODUCT FUNCTIONS
// ============================================================
async function getProducts() {
    return apiFetch('/products/');
}

// FIXED: Renamed to avoid global collision
async function apiSearchProducts(keyword) {
    return apiFetch(`/products/search/?keyword=${keyword}`);
}

async function getProduct(id) {
    return apiFetch(`/products/${id}`);
}

// ============================================================
// CART FUNCTIONS
// ============================================================
async function getCart(userId) {
    return apiFetch(`/cart/${userId}`);
}

// FIXED: Renamed to avoid global collision
async function apiAddToCart(userId, productId, quantity = 1) {
    return apiFetch(`/cart/${userId}`, {
        method: 'POST',
        body: JSON.stringify({ product_id: productId, quantity })
    });
}

async function removeFromCart(userId, productId) {
    return apiFetch(`/cart/${userId}/${productId}`, {
        method: 'DELETE'
    });
}

async function clearCart(userId) {
    return apiFetch(`/cart/clear/${userId}`, {
        method: 'DELETE'
    });
}

// ============================================================
// ORDER FUNCTIONS
// ============================================================
async function placeOrder(userId) {
    return apiFetch(`/orders/${userId}`, {
        method: 'POST',
        body: JSON.stringify({ user_id: userId, total_amount: 0, status: 'pending' })
    });
}

async function getUserOrders(userId) {
    return apiFetch(`/orders/${userId}`);
}

async function getOrderDetails(userId, orderId) {
    return apiFetch(`/orders/${userId}/${orderId}`);
}

async function cancelOrder(userId, orderId) {
    return apiFetch(`/orders/cancel/${userId}/${orderId}`, {
        method: 'PUT'
    });
}

// ============================================================
// ADMIN FUNCTIONS
// ============================================================
async function addProduct(productData) {
    return apiFetch('/admin/products', {
        method: 'POST',
        body: JSON.stringify(productData)
    });
}

async function getAllOrders() {
    return apiFetch('/admin/orders');
}

// FIXED: Renamed to avoid global collision
async function apiUpdateOrderStatus(orderId, status) {
    return apiFetch(`/admin/orders/${orderId}`, {
        method: 'PUT',
        body: JSON.stringify({ status })
    });
}

// ============================================================
// TOAST NOTIFICATION SYSTEM (Modern UI Popups)
// ============================================================
function showToast(message, type = 'success') {
    // Check if container exists, if not create it
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    // Create the toast element
    const toast = document.createElement('div');
    toast.className = `custom-toast ${type}`;
    
    // Add icon based on success or error
    const icon = type === 'success' ? '✅' : '⚠️';
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    
    // Add to screen
    container.appendChild(toast);

    // Remove it smoothly after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'fadeOutDown 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Make it globally accessible to all files (REPLACES THE BROKEN CODE)
window.showToast = showToast;