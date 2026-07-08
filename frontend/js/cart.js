// ============================================================
// FILE: frontend/js/cart.js (CLOUD & UI FIXED)
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    loadCartAndUpdate();
    checkAuth();
});

async function loadCartAndUpdate() {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        window.location.href = 'login.html';
        return;
    }
    
    try {
        const items = await getCart(userId);
        displayCart(items);
        await updateCartCount();
    } catch (error) {
        console.error('Error loading cart:', error);
    }
}

// Display cart items with Cloud Image Validation & Premium UI
function displayCart(items) {
    const emptyCart = document.getElementById('empty-cart');
    const cartItems = document.getElementById('cart-items');
    const cartItemsList = document.getElementById('cart-items-list');
    const cartTotal = document.getElementById('cart-total');
    
    if (!items || items.length === 0) {
        emptyCart.style.display = 'block';
        cartItems.style.display = 'none';
        return;
    }
    
    emptyCart.style.display = 'none';
    cartItems.style.display = 'block';
    
    let total = 0;
    let html = '';
    
    items.forEach(item => {
        total += item.total_price;
        
        // 1. CLOUD URL VALIDATOR: 
        // If it's a local database path (doesn't start with http), use a placeholder instantly.
        const validImgSrc = (item.image_url && item.image_url.startsWith('http')) 
            ? item.image_url 
            : 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&q=80&w=200';

        // 2. PREMIUM UI: Perfect square image, truncated long text, and pill buttons.
        html += `
            <div class="card mb-3 border-0 shadow-sm cart-item" style="border-radius: 16px; transition: transform 0.2s;">
                <div class="row g-0 align-items-center p-3">
                    
                    <div class="col-3 col-md-2 text-center">
                        <img src="${validImgSrc}" 
                             alt="${item.product_name}"
                             style="width: 80px; height: 80px; object-fit: cover; border-radius: 12px; background: #f8fafc; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                    </div>
                    
                    <div class="col-6 col-md-8 px-3">
                        <div class="card-body p-0">
                            <h6 class="card-title fw-bold text-dark mb-1" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.3;">
                                ${item.product_name}
                            </h6>
                            <p class="card-text text-muted mb-0">
                                <span class="fw-bold text-primary">₹${item.price}</span> 
                                <span class="mx-2 text-muted">×</span> 
                                <span class="fw-bold">${item.quantity}</span>
                            </p>
                        </div>
                    </div>
                    
                    <div class="col-3 col-md-2 text-end">
                        <button class="btn btn-danger btn-sm rounded-pill px-4 fw-bold shadow-sm" onclick="removeItem(${item.product_id})">
                            Remove
                        </button>
                    </div>
                    
                </div>
            </div>
        `;
    });
    
    cartItemsList.innerHTML = html;
    cartTotal.textContent = `₹${total}`;
}

// Update cart count
async function updateCartCount() {
    const userId = localStorage.getItem('userId');
    const cartCount = document.getElementById('cart-count');
    
    if (!userId || !cartCount) return;
    
    try {
        const items = await getCart(userId);
        const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
        cartCount.textContent = totalItems;
    } catch (error) {
        console.error('Error updating cart count:', error);
        cartCount.textContent = '0';
    }
}

// Remove item from cart
async function removeItem(productId) {
    const userId = localStorage.getItem('userId');
    if (!userId) return;
    
    try {
        await removeFromCart(userId, productId);
        await loadCartAndUpdate();
    } catch (error) {
        alert('Error removing item: ' + error.message);
    }
}

// Checkout
async function checkout() {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        alert('Please login first!');
        return;
    }
    
    if (!confirm('Are you sure you want to place this order?')) {
        return;
    }
    
    try {
        const result = await placeOrder(userId);
        alert('Order placed successfully! Order ID: ' + result.order_id);
        window.location.href = 'orders.html';
    } catch (error) {
        alert('Error placing order: ' + error.message);
    }
}

// Check authentication
function checkAuth() {
    const userId = localStorage.getItem('userId');
    const loginLink = document.getElementById('login-link');
    
    if (userId && loginLink) {
        loginLink.textContent = 'Logout';
        loginLink.href = '#';
        loginLink.onclick = function(e) {
            e.preventDefault();
            // FIXED: Removed the JWT token to actually secure the logout
            localStorage.removeItem('token'); 
            localStorage.removeItem('userId');
            localStorage.removeItem('userName');
            localStorage.removeItem('role');
            window.location.href = 'index.html';
        };
    }
}