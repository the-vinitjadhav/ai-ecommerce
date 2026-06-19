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
    return apiFetch('/auth/register', {   // ✅ CORRECT
        method: 'POST',
        body: JSON.stringify(userData)
    });
}

async function loginUser(credentials) {
    return apiFetch('/auth/login', {     // ✅ CORRECT
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

async function searchProducts(keyword) {
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

async function addToCart(userId, productId, quantity = 1) {
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

async function updateOrderStatus(orderId, status) {
    return apiFetch(`/admin/orders/${orderId}`, {
        method: 'PUT',
        body: JSON.stringify({ status })
    });
}