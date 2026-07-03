// ============================================================
// FILE: frontend/js/api.js
// PURPOSE: All API calls to the backend
// ============================================================

// API base URL
const API_BASE = 'http://127.0.0.1:8000/api';

// ============================================================
// Generic fetch function (With JWT Token Injection)
// ============================================================
async function apiFetch(endpoint, options = {}) {
    const method = options.method || 'GET';
    const url = `${API_BASE}${endpoint}`;
    
    const token = localStorage.getItem('token');
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(url, {
            ...options,
            method: method,
            headers: headers
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

async function getUserProfile(userId) {
    return apiFetch(`/auth/profile/${userId}`);
}

async function updateUserProfile(userId, profileData) {
    return apiFetch(`/auth/profile/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(profileData)
    });
}

// ============================================================
// PRODUCT FUNCTIONS
// ============================================================
async function getProducts() {
    return apiFetch('/products/');
}

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

// ---> THIS WAS THE MISSING FUNCTION <---
async function apiUpdateProduct(productId, productData) {
    return apiFetch(`/admin/products/${productId}`, {
        method: 'PUT',
        body: JSON.stringify(productData)
    });
}

async function getAllOrders() {
    return apiFetch('/admin/orders');
}

async function apiUpdateOrderStatus(orderId, status) {
    return apiFetch(`/admin/orders/${orderId}`, {
        method: 'PUT',
        body: JSON.stringify({ status })
    });
}

async function apiDeleteProduct(productId) {
    return apiFetch(`/admin/products/${productId}`, {
        method: 'DELETE'
    });
}

// Custom fetch for files because it uses FormData instead of JSON
async function uploadImageFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const token = localStorage.getItem('token');
    const headers = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/admin/upload-image`, {
        method: 'POST',
        headers: headers,
        body: formData 
    });

    if (!response.ok) throw new Error('Image upload failed');
    return response.json();
}

// ============================================================
// TOAST NOTIFICATION SYSTEM
// ============================================================
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `custom-toast ${type}`;
    
    const icon = type === 'success' ? '✅' : '⚠️';
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOutDown 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

window.showToast = showToast;