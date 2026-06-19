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
                <div class="card product-card h-100">
                    <img src="${product.image_url || 'https://via.placeholder.com/300x200?text=No+Image'}" 
                         class="card-img-top" alt="${product.product_name}">
                    <div class="card-body">
                        <h5 class="card-title">${product.product_name}</h5>
                        <p class="card-text text-muted">${product.description || ''}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="price">₹${product.price}</span>
                            <span class="stock-badge badge ${product.stock > 0 ? 'bg-success' : 'bg-danger'}">
                                ${product.stock > 0 ? 'In Stock' : 'Out of Stock'}
                            </span>
                        </div>
                        <div class="mt-2">
                            <button class="btn btn-primary btn-sm w-100" onclick="addToCart(${product.product_id})">
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
        const products = await searchProducts(keyword);
        displayProducts(products);
    } catch (error) {
        console.error('Error searching products:', error);
    }
}

// Add to cart
async function addToCart(productId) {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        alert('Please login first!');
        window.location.href = 'login.html';
        return;
    }
    
    try {
        await addToCart(userId, productId, 1);
        updateCartCount();
        alert('Product added to cart!');
    } catch (error) {
        alert('Error adding to cart: ' + error.message);
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
    }
}

// Check authentication
function checkAuth() {
    const userId = localStorage.getItem('userId');
    const role = localStorage.getItem('role');
    const loginLink = document.getElementById('login-link');
    const adminLink = document.getElementById('admin-link');
    
    if (userId) {
        if (loginLink) {
            loginLink.textContent = 'Logout';
            loginLink.href = '#';
            loginLink.onclick = function(e) {
                e.preventDefault();
                logout();
            };
        }
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