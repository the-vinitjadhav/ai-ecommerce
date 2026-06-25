// ============================================================
// FILE: frontend/js/product-detail.js
// PURPOSE: Dynamic routing and rendering for single product
// ============================================================

document.addEventListener('DOMContentLoaded', async function() {
    checkAuth();
    updateCartCount();

    // 1. Get the Product ID from the URL (e.g., product.html?id=2)
    const urlParams = new URLSearchParams(window.location.search);
    const productId = urlParams.get('id');

    // If no ID is found, kick them back to the main products page
    if (!productId) {
        window.location.href = 'products.html';
        return;
    }

    try {
        // 2. Fetch the specific product from the backend
        const product = await getProduct(productId);
        
        // 3. Populate the HTML elements
        document.getElementById('detail-title').textContent = product.product_name;
        document.getElementById('detail-category').textContent = product.category_name || 'General';
        document.getElementById('detail-price').textContent = `₹${product.price}`;
        document.getElementById('detail-desc').textContent = product.description || 'No description available for this product.';
        
        // Handle Image Fallback
        const imgEl = document.getElementById('detail-img');
        imgEl.src = product.image_url || 'images/placeholder.jpg';
        imgEl.onerror = () => { imgEl.src = 'https://via.placeholder.com/600x400?text=No+Image'; };

        // Handle Stock Badge
        const stockBadge = document.getElementById('detail-stock');
        if (product.stock > 0) {
            stockBadge.textContent = 'In Stock';
            stockBadge.className = 'badge bg-success';
        } else {
            stockBadge.textContent = 'Out of Stock';
            stockBadge.className = 'badge bg-danger';
            document.getElementById('detail-add-btn').disabled = true;
        }

        // 4. Bind the Add to Cart button
        document.getElementById('detail-add-btn').addEventListener('click', () => handleDetailAddToCart(product.product_id));

        // 5. Load Related Products
        loadRelatedProducts(product.category_name, product.product_id);

    } catch (error) {
        console.error("Failed to load product details:", error);
        document.getElementById('detail-title').textContent = "Product not found";
    }
});

// Custom Add to Cart that reads the Quantity input
async function handleDetailAddToCart(productId) {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        if (window.showToast) showToast('Please login to add items.', 'error');
        else alert('Please login to add items.');
        setTimeout(() => window.location.href = 'login.html', 1500);
        return;
    }

    const qty = parseInt(document.getElementById('detail-qty').value) || 1;

    try {
        await addToCart(userId, productId, qty);
        if (window.showToast) showToast('Added to Cart!', 'success');
        else alert('Added to Cart!');
        await updateCartCount();
    } catch (error) {
        if (window.showToast) showToast('Error: ' + error.message, 'error');
        else alert('Error: ' + error.message);
    }
}

// Load 3 random products from the same category
async function loadRelatedProducts(categoryName, currentProductId) {
    const container = document.getElementById('related-products-container');
    try {
        const allProducts = await getProducts();
        
        // Filter products to match category but exclude the one we are currently looking at
        let related = allProducts.filter(p => p.category_name === categoryName && p.product_id != currentProductId);
        
        // If not enough in category, just show random products
        if (related.length < 3) {
            related = allProducts.filter(p => p.product_id != currentProductId);
        }

        // Shuffle and pick top 3
        related = related.sort(() => 0.5 - Math.random()).slice(0, 3);

        if (related.length === 0) {
            container.innerHTML = '<p class="text-muted">No related products found.</p>';
            return;
        }

        let html = '';
        related.forEach(product => {
            html += `
                <div class="col-md-4 mb-4">
                    <div class="card product-card h-100" style="cursor: pointer;" onclick="window.location.href='product.html?id=${product.product_id}'">
                        <img src="${product.image_url || 'images/placeholder.jpg'}" 
                             class="card-img-top" alt="${product.product_name}"
                             onerror="this.onerror=null; this.src='https://via.placeholder.com/300x250?text=No+Image';">
                        <div class="card-body text-center">
                            <h5 class="card-title" style="font-size: 1rem;">${product.product_name}</h5>
                            <span class="price">₹${product.price}</span>
                        </div>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;

    } catch (error) {
        console.error("Failed to load related products", error);
    }
}

// ============================================================
// UI FUNCTIONS FOR NAVBAR
// ============================================================
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

function checkAuth() {
    const userId = localStorage.getItem('userId');
    const loginLink = document.getElementById('login-link');
    
    if (userId && loginLink) {
        loginLink.textContent = 'Logout';
        loginLink.href = '#';
        loginLink.onclick = function(e) {
            e.preventDefault();
            logout();
        };
    }
}

function logout() {
    localStorage.removeItem('userId');
    localStorage.removeItem('userName');
    localStorage.removeItem('role');
    window.location.href = 'index.html';
}