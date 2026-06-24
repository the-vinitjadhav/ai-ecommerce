// ============================================================
// FILE: frontend/js/cart.js (FIXED - No Double API Calls)
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    // Load cart, then update the count
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
        // Load cart first
        const items = await getCart(userId);
        displayCart(items);
        
        // Update count AFTER cart is loaded (no overlap)
        await updateCartCount();
    } catch (error) {
        console.error('Error loading cart:', error);
    }
}

// Display cart items
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
        html += `
            <div class="card mb-3 cart-item">
                <div class="row g-0">
                    <div class="col-md-2">
                        <img src="${item.image_url || 'images/placeholder.jpg'}" 
                             class="img-fluid rounded-start" alt="${item.product_name}">
                    </div>
                    <div class="col-md-8">
                        <div class="card-body">
                            <h5 class="card-title">${item.product_name}</h5>
                            <p class="card-text">₹${item.price} × ${item.quantity}</p>
                        </div>
                    </div>
                    <div class="col-md-2 d-flex align-items-center">
                        <button class="btn btn-danger btn-sm" onclick="removeItem(${item.product_id})">
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

// Update cart count (Safe version)
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
        // Reload cart and update count
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
            localStorage.removeItem('userId');
            localStorage.removeItem('userName');
            localStorage.removeItem('role');
            window.location.href = 'index.html';
        };
    }
}