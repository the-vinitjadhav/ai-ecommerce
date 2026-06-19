// Load admin pages on load
document.addEventListener('DOMContentLoaded', function() {
    checkAdminAuth();
    
    const path = window.location.pathname;
    
    if (path.includes('dashboard.html')) {
        loadDashboard();
    } else if (path.includes('add-product.html')) {
        const form = document.getElementById('add-product-form');
        if (form) form.addEventListener('submit', handleAddProduct);
    } else if (path.includes('orders.html')) {
        loadAllOrders();
    }
});

// Check if user is admin
function checkAdminAuth() {
    const role = localStorage.getItem('role');
    if (role !== 'admin') {
        alert('Access denied. Admin only.');
        window.location.href = '../login.html';
    }
}

// ============================================================
// DASHBOARD
// ============================================================
async function loadDashboard() {
    try {
        const products = await getProducts();
        const orders = await getAllOrders();
        
        document.getElementById('product-count').textContent = products.length;
        document.getElementById('order-count').textContent = orders.length;
        
        const totalRevenue = orders.reduce((sum, order) => sum + order.total_amount, 0);
        document.getElementById('revenue').textContent = `₹${totalRevenue}`;
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// ============================================================
// ADD PRODUCT
// ============================================================
async function handleAddProduct(e) {
    e.preventDefault();
    
    const product_name = document.getElementById('product_name').value;
    const description = document.getElementById('description').value;
    const price = parseFloat(document.getElementById('price').value);
    const stock = parseInt(document.getElementById('stock').value);
    const category_name = document.getElementById('category_name').value;
    const image_url = document.getElementById('image_url').value || null;
    
    const successAlert = document.getElementById('add-alert');
    const errorAlert = document.getElementById('add-error');
    
    if (successAlert) successAlert.classList.add('d-none');
    if (errorAlert) errorAlert.classList.add('d-none');
    
    try {
        const result = await addProduct({
            product_name,
            description,
            price,
            stock,
            category_name,
            image_url
        });
        
        if (successAlert) {
            successAlert.textContent = `Product added successfully! Product ID: ${result.product_id}`;
            successAlert.classList.remove('d-none');
        }
        
        // Clear form
        document.getElementById('add-product-form').reset();
    } catch (error) {
        if (errorAlert) {
            errorAlert.textContent = error.message;
            errorAlert.classList.remove('d-none');
        } else {
            alert('Error adding product: ' + error.message);
        }
    }
}

// ============================================================
// VIEW ALL ORDERS (ADMIN)
// ============================================================
async function loadAllOrders() {
    const container = document.getElementById('orders-container');
    if (!container) return;
    
    try {
        const orders = await getAllOrders();
        
        if (orders.length === 0) {
            container.innerHTML = '<p class="text-muted">No orders found.</p>';
            return;
        }
        
        let html = `
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Order ID</th>
                        <th>Customer</th>
                        <th>Total</th>
                        <th>Status</th>
                        <th>Date</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        orders.forEach(order => {
            const statusClass = `status-${order.status}`;
            html += `
                <tr>
                    <td>#${order.order_id}</td>
                    <td>${order.name || 'Unknown'}</td>
                    <td>₹${order.total_amount}</td>
                    <td><span class="order-status ${statusClass}">${order.status}</span></td>
                    <td>${new Date(order.order_date).toLocaleDateString()}</td>
                    <td>
                        <select class="form-select form-select-sm" onchange="updateOrderStatus(${order.order_id}, this.value)">
                            <option value="pending" ${order.status === 'pending' ? 'selected' : ''}>Pending</option>
                            <option value="confirmed" ${order.status === 'confirmed' ? 'selected' : ''}>Confirmed</option>
                            <option value="shipped" ${order.status === 'shipped' ? 'selected' : ''}>Shipped</option>
                            <option value="delivered" ${order.status === 'delivered' ? 'selected' : ''}>Delivered</option>
                            <option value="cancelled" ${order.status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                        </select>
                    </td>
                </tr>
            `;
        });
        
        html += `</tbody></table>`;
        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<div class="alert alert-danger">Error loading orders: ${error.message}</div>`;
    }
}

// ============================================================
// UPDATE ORDER STATUS
// ============================================================
async function updateOrderStatus(orderId, newStatus) {
    if (!confirm(`Update order #${orderId} to "${newStatus}"?`)) {
        return;
    }
    
    try {
        await updateOrderStatus(orderId, newStatus);
        alert('Order status updated successfully!');
        loadAllOrders(); // Reload the table
    } catch (error) {
        alert('Error updating status: ' + error.message);
    }
}