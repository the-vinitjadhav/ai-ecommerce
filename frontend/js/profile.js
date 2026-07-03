document.addEventListener('DOMContentLoaded', async function() {
    const userId = localStorage.getItem('userId');
    const role = localStorage.getItem('role'); // Grab the role
    
    // Security check
    if (!userId) {
        if (typeof showToast === 'function') showToast('Please login to view your profile.', 'error');
        setTimeout(() => window.location.href = 'login.html', 1500);
        return;
    }

    // Unhide dashboard button if user is an admin
    const adminProfLink = document.getElementById('admin-profile-link');
    if (adminProfLink && role === 'admin') {
        adminProfLink.style.display = 'block';
    }

    // Load Data
    await loadUserProfile(userId);
    await loadUserOrders(userId);

    // Bind form submit
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileUpdate);
    }
});
async function loadUserProfile(userId) {
    try {
        const user = await getUserProfile(userId);
        
        // Update Sidebar
        document.getElementById('sidebar-name').textContent = user.name;
        document.getElementById('sidebar-email').textContent = user.email;
        document.getElementById('profile-avatar').textContent = user.name.charAt(0).toUpperCase();

        // Populate Form
        document.getElementById('prof-name').value = user.name || '';
        document.getElementById('prof-email').value = user.email || '';
        document.getElementById('prof-phone').value = user.phone || '';
        document.getElementById('prof-address').value = user.address || '';
        document.getElementById('prof-city').value = user.city || '';
        document.getElementById('prof-pincode').value = user.pincode || '';

    } catch (error) {
        console.error("Failed to load profile:", error);
    }
}

async function handleProfileUpdate(e) {
    e.preventDefault();
    const userId = localStorage.getItem('userId');

    const profileData = {
        name: document.getElementById('prof-name').value,
        phone: document.getElementById('prof-phone').value,
        address: document.getElementById('prof-address').value,
        city: document.getElementById('prof-city').value,
        pincode: document.getElementById('prof-pincode').value
    };

    try {
        await updateUserProfile(userId, profileData);
        if (typeof showToast === 'function') showToast('Profile updated successfully!', 'success');
        
        // Update the sidebar name instantly
        document.getElementById('sidebar-name').textContent = profileData.name;
        localStorage.setItem('userName', profileData.name);
    } catch (error) {
        if (typeof showToast === 'function') showToast('Failed to update profile.', 'error');
    }
}

async function loadUserOrders(userId) {
    try {
        const orders = await getUserOrders(userId);
        const tbody = document.getElementById('user-orders-body');
        tbody.innerHTML = '';

        if (orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-muted">You have no orders yet. Go buy something! 🛒</td></tr>';
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
                <td class="ps-4 fw-bold text-primary">#${order.order_id}</td>
                <td>${orderDate}</td>
                <td class="fw-bold">₹${order.total_amount}</td>
                <td><span class="badge ${badgeClass}">${order.status.toUpperCase()}</span></td>
            `;
            tbody.appendChild(tr);
        });

    } catch (error) {
        console.error("Failed to load orders:", error);
        document.getElementById('user-orders-body').innerHTML = '<tr><td colspan="4" class="text-center text-danger">Failed to load orders.</td></tr>';
    }
}

function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}