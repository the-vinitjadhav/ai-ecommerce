// ============================================================
// FILE: frontend/js/admin.js
// PURPOSE: Unified Admin Dashboard Logic & Analytics
// ============================================================
let globalProductsList = []; 
let salesChartInstance = null;

document.addEventListener('DOMContentLoaded', async function() {
    checkAdminAuth();

    if (window.location.pathname.includes('admin.html')) {
        await loadDashboardStats();
        
        const form = document.getElementById('add-product-form');
        if (form) form.addEventListener('submit', handleAddProduct);

        const editForm = document.getElementById('edit-product-form');
        if (editForm) editForm.addEventListener('submit', handleEditProduct);
    }
});

function checkAdminAuth() {
    const role = localStorage.getItem('role');
    if (role !== 'admin') {
        alert('Access denied. Admins only.');
        window.location.href = 'index.html';
    }
}

async function loadDashboardStats() {
    try {
        // These rely on api.js being correctly linked with your Render Backend URL
        const [orders, products] = await Promise.all([
            getAllOrders(),
            getProducts()
        ]);

        globalProductsList = products; 

        // Update top cards
        const totalRevenue = orders.reduce((sum, order) => sum + parseFloat(order.total_amount), 0);
        document.getElementById('total-revenue').textContent = `₹${totalRevenue.toLocaleString('en-IN')}`;
        document.getElementById('total-orders').textContent = orders.length;
        document.getElementById('total-products').textContent = products.length;

        // Render Tables & Charts
        renderOrdersTable(orders);
        renderChart(orders);
        renderProductsTable(products);

    } catch (error) {
        console.error('Error loading dashboard:', error);
        alert("Failed to load dashboard data. Please check connection.");
    }
}

function renderOrdersTable(orders) {
    const tbody = document.getElementById('admin-orders-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4">No orders found.</td></tr>';
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
            <td class="ps-3 fw-bold text-muted">#${order.order_id}</td>
            <td class="fw-bold">${order.name || 'Unknown'}</td>
            <td>${orderDate}</td>
            <td class="fw-bold text-success">₹${order.total_amount}</td>
            <td><span class="badge ${badgeClass} px-3 py-2 rounded-pill">${order.status.toUpperCase()}</span></td>
            <td>
                <select class="form-select form-select-sm d-inline-block w-auto bg-light border-0" onchange="updateStatus(${order.order_id}, this.value)">
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
        alert(`Order #${orderId} marked as ${newStatus}`);
        loadDashboardStats(); 
    } catch (error) {
        alert('Failed to update order');
    }
}

async function handleAddProduct(e) {
    e.preventDefault();
    
    // I removed the file upload logic since you are running on Vercel/Render 
    // and storing physical image files on the server won't persist anyway. URL is best!
    const productData = {
        product_name: document.getElementById('prod-name').value,
        price: parseFloat(document.getElementById('prod-price').value),
        stock: parseInt(document.getElementById('prod-stock').value),
        category_name: document.getElementById('prod-category').value,
        image_url: document.getElementById('prod-image-url').value,
        description: "New product added by Admin."
    };

    try {
        await addProduct(productData);
        alert('Product added successfully!');
        document.getElementById('add-product-form').reset();
        loadDashboardStats(); 
    } catch (error) {
        alert('Error adding product: ' + error.message);
        console.error(error);
    }
}

function renderProductsTable(products) {
    const tbody = document.getElementById('admin-products-body'); // The fixed ID!
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (products.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4">No products found.</td></tr>';
        return;
    }

    products.forEach((product, index) => {
        const tr = document.createElement('tr');
        const imageSrc = product.image_url ? product.image_url : 'https://via.placeholder.com/50';
        const stockDisplay = product.stock < 5 
            ? `<span class="badge bg-danger rounded-pill px-3">${product.stock} (Low!)</span>` 
            : `<span class="badge bg-light text-dark border px-3">${product.stock}</span>`;

        tr.innerHTML = `
            <td class="ps-3 fw-bold text-muted">${index + 1}</td>
            <td><img src="${imageSrc}" alt="${product.product_name}" class="shadow-sm" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;"></td>
            <td class="fw-bold">${product.product_name} <br><small class="text-muted">ID: #${product.product_id} | ${product.category_name}</small></td>
            <td class="fw-bold text-primary">₹${product.price}</td>
            <td>${stockDisplay}</td>
            <td>
                <button class="btn btn-sm btn-light border me-2 shadow-sm rounded-pill px-3" onclick="openEditModal(${product.product_id})">✏️ Edit</button>
                <button class="btn btn-sm btn-danger shadow-sm rounded-pill px-3" onclick="handleDeleteProduct(${product.product_id}, '${product.product_name.replace(/'/g, "\\'")}')">🗑️ Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function openEditModal(productId) {
    const product = globalProductsList.find(p => p.product_id === productId);
    if (!product) return;

    document.getElementById('edit-prod-id').value = product.product_id;
    document.getElementById('edit-prod-name').value = product.product_name;
    document.getElementById('edit-prod-price').value = product.price;
    document.getElementById('edit-prod-stock').value = product.stock;
    document.getElementById('edit-prod-category').value = product.category_name;
    document.getElementById('edit-prod-image-url').value = product.image_url || '';

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
        alert('Product updated successfully!');
        
        const modalElement = document.getElementById('editProductModal');
        const modalInstance = bootstrap.Modal.getInstance(modalElement);
        modalInstance.hide();
        
        loadDashboardStats();
    } catch (error) {
        alert('Error updating product: ' + error.message);
    }
}

async function handleDeleteProduct(productId, productName) {
    if (!confirm(`Delete "${productName}" forever? This cannot be undone.`)) {
        return; 
    }

    try {
        await apiDeleteProduct(productId);
        alert(`Product deleted successfully!`);
        loadDashboardStats(); 
    } catch (error) {
        alert('Failed to delete product.');
    }
}

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