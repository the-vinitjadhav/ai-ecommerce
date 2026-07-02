// ============================================================
// FILE: frontend/js/admin.js
// PURPOSE: Unified Admin Dashboard Logic & Analytics
// ============================================================
let globalProductsList = []; // Stores products so the Edit button can find them!
let salesChartInstance = null;

document.addEventListener('DOMContentLoaded', async function() {
    // 1. SECURITY GUARD: Instantly kick out non-admins
    checkAdminAuth();

    // 2. Load the unified dashboard if we are on admin.html
    if (window.location.pathname.includes('admin.html')) {
        await loadDashboardStats();
        
        const form = document.getElementById('add-product-form');
        if (form) form.addEventListener('submit', handleAddProduct);

        // Listen for the new Edit form submission
        const editForm = document.getElementById('edit-product-form');
        if (editForm) editForm.addEventListener('submit', handleEditProduct);
    }
});

function checkAdminAuth() {
    const role = localStorage.getItem('role');
    if (role !== 'admin') {
        if (typeof showToast === 'function') {
            showToast('Access denied. Admin only.', 'error');
        } else {
            alert('Access denied. Admin only.');
        }
        setTimeout(() => window.location.href = 'index.html', 1500);
    }
}

// ============================================================
// DASHBOARD ANALYTICS & TABLES
// ============================================================
async function loadDashboardStats() {
    try {
        // Fetch data simultaneously for speed
        const [orders, products] = await Promise.all([
            getAllOrders(),
            getProducts()
        ]);

        globalProductsList = products; // Save for the edit modal

        // Calculate Totals
        const totalRevenue = orders.reduce((sum, order) => sum + parseFloat(order.total_amount), 0);
        
        // Update DOM Elements
        document.getElementById('total-revenue').textContent = `₹${totalRevenue.toLocaleString('en-IN')}`;
        document.getElementById('total-orders').textContent = orders.length;
        document.getElementById('total-products').textContent = products.length;

        // Render the UI components
        renderOrdersTable(orders);
        renderChart(orders);
        renderProductsTable(products);

    } catch (error) {
        if (typeof showToast === 'function') showToast('Error loading dashboard data', 'error');
        console.error('Error loading dashboard:', error);
    }
}

function renderOrdersTable(orders) {
    const tbody = document.getElementById('admin-orders-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No orders found.</td></tr>';
        return;
    }

    orders.forEach(order => {
        let badgeClass = 'bg-secondary';
        if (order.status === 'delivered') badgeClass = 'bg-success';
        if (order.status === 'shipped') badgeClass = 'bg-primary';
        if (order.status === 'cancelled') badgeClass = 'bg-danger';
        if (order.status === 'pending') badgeClass = 'bg-warning text-dark';

        const orderDate = new Date(order.order_date).toLocaleDateString();

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>#${order.order_id}</td>
            <td class="fw-bold">${order.name || 'Unknown'}</td>
            <td>${orderDate}</td>
            <td>₹${order.total_amount}</td>
            <td><span class="badge ${badgeClass}">${order.status.toUpperCase()}</span></td>
            <td>
                <select class="form-select form-select-sm d-inline-block w-auto" onchange="updateStatus(${order.order_id}, this.value)">
                    <option value="" selected disabled>Change...</option>
                    <option value="pending" ${order.status === 'pending' ? 'selected' : ''}>Pending</option>
                    <option value="shipped" ${order.status === 'shipped' ? 'selected' : ''}>Shipped</option>
                    <option value="delivered" ${order.status === 'delivered' ? 'selected' : ''}>Delivered</option>
                    <option value="cancelled" ${order.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                </select>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function updateStatus(orderId, newStatus) {
    if (!confirm(`Update order #${orderId} to "${newStatus}"?`)) {
        loadDashboardStats(); 
        return;
    }
    
    try {
        await apiUpdateOrderStatus(orderId, newStatus);
        if (typeof showToast === 'function') showToast(`Order #${orderId} marked as ${newStatus}`, 'success');
        loadDashboardStats(); 
    } catch (error) {
        if (typeof showToast === 'function') showToast('Failed to update order', 'error');
    }
}

// ============================================================
// ADD PRODUCT
// ============================================================
async function handleAddProduct(e) {
    e.preventDefault();
    
    let finalImageUrl = document.getElementById('prod-image-url').value || null;
    const imageFile = document.getElementById('prod-image-file').files[0];

    try {
        if (imageFile) {
            if (typeof showToast === 'function') showToast('Uploading image...', 'success');
            const uploadResult = await uploadImageFile(imageFile);
            finalImageUrl = uploadResult.url; 
        }

        const productData = {
            product_name: document.getElementById('prod-name').value,
            price: parseFloat(document.getElementById('prod-price').value),
            stock: parseInt(document.getElementById('prod-stock').value),
            category_name: document.getElementById('prod-category').value,
            image_url: finalImageUrl,
            description: "New product added by Admin."
        };

        await addProduct(productData);
        if (typeof showToast === 'function') showToast('Product added successfully!', 'success');
        
        document.getElementById('add-product-form').reset();
        loadDashboardStats(); 
        
    } catch (error) {
        if (typeof showToast === 'function') showToast('Error adding product: ' + error.message, 'error');
        console.error(error);
    }
}

// ============================================================
// MANAGE PRODUCTS TABLE & DELETE LOGIC
// ============================================================
function renderProductsTable(products) {
    const tbody = document.getElementById('admin-products-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No products found.</td></tr>';
        return;
    }

    products.forEach((product, index) => {
        const tr = document.createElement('tr');
        
        const imageSrc = product.image_url ? product.image_url : 'https://via.placeholder.com/50';
        
        const stockDisplay = product.stock < 5 
            ? `<span class="text-danger fw-bold">${product.stock} (Low!)</span>` 
            : product.stock;

        tr.innerHTML = `
            <td><b>${index + 1}</b></td>
            <td><img src="${imageSrc}" alt="${product.product_name}" style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px;"></td>
            <td class="fw-bold">${product.product_name} <br><small class="text-muted">ID: #${product.product_id}</small></td>
            <td>₹${product.price}</td>
            <td>${stockDisplay}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary me-2" onclick="openEditModal(${product.product_id})">
                    ✏️ Edit
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="handleDeleteProduct(${product.product_id}, '${product.product_name.replace(/'/g, "\\'")}')">
                    🗑️ Delete
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// ============================================================
// EDIT PRODUCT LOGIC
// ============================================================
function openEditModal(productId) {
    // Find the exact product from our global list
    const product = globalProductsList.find(p => p.product_id === productId);
    if (!product) return;

    // Populate the popup form
    document.getElementById('edit-prod-id').value = product.product_id;
    document.getElementById('edit-prod-name').value = product.product_name;
    document.getElementById('edit-prod-price').value = product.price;
    document.getElementById('edit-prod-stock').value = product.stock;
    document.getElementById('edit-prod-category').value = product.category_name;
    document.getElementById('edit-prod-image-url').value = product.image_url || '';

    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('editProductModal'));
    modal.show();
}

async function handleEditProduct(e) {
    e.preventDefault();
    
    const productId = document.getElementById('edit-prod-id').value;
    const productData = {
        product_name: document.getElementById('edit-prod-name').value,
        price: parseFloat(document.getElementById('edit-prod-price').value),
        stock: parseInt(document.getElementById('edit-prod-stock').value),
        category_name: document.getElementById('edit-prod-category').value,
        image_url: document.getElementById('edit-prod-image-url').value || null,
        description: "Updated by Admin."
    };

    try {
        await apiUpdateProduct(productId, productData);
        if (typeof showToast === 'function') showToast('Product updated successfully!', 'success');
        
        // Hide the modal
        const modalElement = document.getElementById('editProductModal');
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        modalInstance.hide();
        
        // Refresh the table instantly
        loadDashboardStats();
    } catch (error) {
        if (typeof showToast === 'function') showToast('Error updating product: ' + error.message, 'error');
        console.error(error);
    }
}

async function handleDeleteProduct(productId, productName) {
    if (!confirm(`Are you absolutely sure you want to delete "${productName}"? This cannot be undone.`)) {
        return; 
    }

    try {
        await apiDeleteProduct(productId);
        
        if (typeof showToast === 'function') {
            showToast(`Product deleted successfully!`, 'success');
        }
        
        loadDashboardStats(); 
    } catch (error) {
        if (typeof showToast === 'function') {
            showToast('Failed to delete product: ' + error.message, 'error');
        } else {
            alert('Failed to delete product.');
        }
        console.error(error);
    }
}

// ============================================================
// CHART.JS ANALYTICS
// ============================================================
function renderChart(orders) {
    const canvas = document.getElementById('revenueChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    const statusData = { pending: 0, shipped: 0, delivered: 0, cancelled: 0 };
    orders.forEach(o => {
        if (statusData[o.status] !== undefined) {
            statusData[o.status] += parseFloat(o.total_amount);
        }
    });

    if (salesChartInstance) {
        salesChartInstance.destroy();
    }

    salesChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Pending', 'Shipped', 'Delivered', 'Cancelled'],
            datasets: [{
                data: [statusData.pending, statusData.shipped, statusData.delivered, statusData.cancelled],
                backgroundColor: ['#ffc107', '#0d6efd', '#198754', '#dc3545'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}

function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}