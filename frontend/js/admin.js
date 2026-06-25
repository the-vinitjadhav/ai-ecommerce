// ============================================================
// FILE: frontend/js/admin.js
// PURPOSE: Unified Admin Dashboard Logic & Analytics
// ============================================================

document.addEventListener('DOMContentLoaded', async function() {
    // 1. SECURITY GUARD: Instantly kick out non-admins
    checkAdminAuth();

    // 2. Load the unified dashboard if we are on admin.html
    if (window.location.pathname.includes('admin.html')) {
        await loadDashboardStats();
        
        const form = document.getElementById('add-product-form');
        if (form) form.addEventListener('submit', handleAddProduct);
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
// DASHBOARD ANALYTICS & ORDERS TABLE
// ============================================================
async function loadDashboardStats() {
    try {
        // Fetch data simultaneously for speed
        const [orders, products] = await Promise.all([
            getAllOrders(),
            getProducts()
        ]);

        // Calculate Totals
        const totalRevenue = orders.reduce((sum, order) => sum + parseFloat(order.total_amount), 0);
        
        // Update DOM Elements
        document.getElementById('total-revenue').textContent = `₹${totalRevenue.toLocaleString('en-IN')}`;
        document.getElementById('total-orders').textContent = orders.length;
        document.getElementById('total-products').textContent = products.length;

        // Render the UI components
        renderOrdersTable(orders);
        renderChart(orders);

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
        // Create color-coded status badges
        let badgeClass = 'bg-secondary';
        if (order.status === 'delivered') badgeClass = 'bg-success';
        if (order.status === 'shipped') badgeClass = 'bg-primary';
        if (order.status === 'cancelled') badgeClass = 'bg-danger';
        if (order.status === 'pending') badgeClass = 'bg-warning text-dark';

        // Format Date
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

// ============================================================
// UPDATE ORDER STATUS
// ============================================================
async function updateStatus(orderId, newStatus) {
    if (!confirm(`Update order #${orderId} to "${newStatus}"?`)) {
        loadDashboardStats(); // Resets the dropdown if they cancel
        return;
    }
    
    try {
        await apiUpdateOrderStatus(orderId, newStatus);
        if (typeof showToast === 'function') showToast(`Order #${orderId} marked as ${newStatus}`, 'success');
        loadDashboardStats(); // Refresh the table and chart instantly
    } catch (error) {
        if (typeof showToast === 'function') showToast('Failed to update order', 'error');
    }
}

// ============================================================
// ADD PRODUCT
// ============================================================
async function handleAddProduct(e) {
    e.preventDefault(); // Prevent page reload
    
    const productData = {
        product_name: document.getElementById('prod-name').value,
        price: parseFloat(document.getElementById('prod-price').value),
        stock: parseInt(document.getElementById('prod-stock').value),
        category_name: document.getElementById('prod-category').value,
        image_url: document.getElementById('prod-image').value || null,
        description: "New product added by Admin."
    };

    try {
        await addProduct(productData);
        if (typeof showToast === 'function') showToast('Product added successfully!', 'success');
        document.getElementById('add-product-form').reset();
        loadDashboardStats(); // Refresh the product count
    } catch (error) {
        if (typeof showToast === 'function') showToast('Error adding product', 'error');
        console.error(error);
    }
}

// ============================================================
// CHART.JS ANALYTICS
// ============================================================
let salesChartInstance = null;

function renderChart(orders) {
    const canvas = document.getElementById('revenueChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    // Process order data to group revenue by Status
    const statusData = { pending: 0, shipped: 0, delivered: 0, cancelled: 0 };
    orders.forEach(o => {
        if (statusData[o.status] !== undefined) {
            statusData[o.status] += parseFloat(o.total_amount);
        }
    });

    // Destroy the old chart before drawing a new one to prevent overlap glitches
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