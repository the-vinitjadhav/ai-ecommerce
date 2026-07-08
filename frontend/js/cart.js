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
displayCart(items)

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