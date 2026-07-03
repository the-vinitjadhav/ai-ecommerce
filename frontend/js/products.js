// ============================================================
// FILE: frontend/js/products.js
// ============================================================

// Load products on page load
document.addEventListener('DOMContentLoaded', function() {
    loadProducts();
    updateCartCount();
    checkAuth();
});

// Load all products
async function loadProducts() {
    try {
        const products = await getProducts();
        displayProducts(products);
    } catch (error) {
        console.error('Error loading products:', error);
    }
}

// Display products
function displayProducts(products) {
    const container = document.getElementById('products-container') || document.getElementById('featured-products');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (products.length === 0) {
        container.innerHTML = '<div class="col-12 text-center"><p>No products found.</p></div>';
        return;
    }
    
    products.forEach(product => {
        const card = `
            <div class="col-md-4 mb-4">
                <div class="card product-card h-100 shadow-sm">
                    <a href="product.html?id=${product.product_id}">
                        <img src="${product.image_url || 'images/placeholder.jpg'}" 
                             class="card-img-top" alt="${product.product_name}"
                             style="height: 200px; object-fit: contain; padding: 1rem;"
                             onerror="this.onerror=null; this.src='https://via.placeholder.com/300x250?text=No+Image';">
                    </a>
                    
                    <div class="card-body d-flex flex-column">
                        <a href="product.html?id=${product.product_id}" style="text-decoration: none; color: inherit;">
                            <h5 class="card-title fw-bold">${product.product_name}</h5>
                        </a>
                        <p class="card-text text-muted small">${product.description || ''}</p>
                        
                        <div class="mt-auto">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="price fs-5 text-primary fw-bold">₹${product.price}</span>
                                <span class="stock-badge badge ${product.stock > 0 ? 'bg-success' : 'bg-danger'}">
                                    ${product.stock > 0 ? 'In Stock' : 'Out of Stock'}
                                </span>
                            </div>
                            <button class="btn btn-primary w-100" style="background-color: #667eea; border: none;" onclick="handleUserCartClick(${product.product_id})">
                              Add to Cart
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML += card;
    });
}

// Search products
async function searchProducts() {
    const keyword = document.getElementById('search-input').value;
    if (!keyword) {
        loadProducts();
        return;
    }
    
    try {
        const products = await apiSearchProducts(keyword);
        displayProducts(products);
    } catch (error) {
        console.error('Error searching products:', error);
    }
}

// Add to cart safely without loops
async function handleUserCartClick(productId) {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        showToast('Please login first!', 'error'); 
        setTimeout(() => window.location.href = 'login.html', 1500); 
        return;
    }
    
    try {
        const response = await fetch(`http://127.0.0.1:8000/api/cart/${userId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId, quantity: 1 })
        });

        if (!response.ok) throw new Error("Backend CRUD failed");

        showToast('Product added to cart!', 'success'); 

        const cartResponse = await fetch(`http://127.0.0.1:8000/api/cart/${userId}`);
        const cartItems = await cartResponse.json();
        const totalItems = cartItems.reduce((sum, item) => sum + item.quantity, 0);
        document.getElementById('cart-count').textContent = totalItems;

    } catch (error) {
        showToast('Error: ' + error.message, 'error'); 
    }
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

// Check authentication
// Check authentication
function checkAuth() {
    const userId = localStorage.getItem('userId');
    const role = localStorage.getItem('role');
    const loginLink = document.getElementById('login-link');
    const adminLink = document.getElementById('admin-link');
    const profileLink = document.getElementById('profile-link'); // Grab our new profile link
    
    if (userId) {
        if (loginLink) {
            loginLink.textContent = 'Logout';
            loginLink.href = '#';
            loginLink.onclick = function(e) {
                e.preventDefault();
                logout();
            };
        }
        
        // Show the Profile button to logged-in users
        if (profileLink) {
            profileLink.style.display = 'block';
        }
        
        // Show the Admin button only to administrators
        if (adminLink && role === 'admin') {
            adminLink.style.display = 'block';
        }
    }
}

// Logout function
function logout() {
    localStorage.removeItem('userId');
    localStorage.removeItem('userName');
    localStorage.removeItem('role');
    window.location.href = 'index.html';
}