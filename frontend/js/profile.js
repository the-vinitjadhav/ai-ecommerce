// ============================================================
// FILE: frontend/js/profile.js
// PURPOSE: Self-Contained Profile Dashboard Logic
// ============================================================

// THE FIX: Define the absolute backend URL so fetches don't fail!
const BACKEND_URL = "https://ai-ecommerce-backend-barh.onrender.com";

document.addEventListener('DOMContentLoaded', async function() {
    const userId = localStorage.getItem('userId');
    const role = localStorage.getItem('role');

    // 1. Security check: Kick out unauthenticated users
    if (!userId) {
        alert('Please login to view your profile.');
        window.location.href = 'login.html';
        return;
    }

    // 2. Unhide Admin link if applicable
    const adminLink = document.getElementById('admin-link');
    if (adminLink && role === 'admin') {
        adminLink.style.display = 'block';
    }

    // 3. Load all data securely from Render backend
    await loadUserProfile(userId);
    await loadUserOrders(userId);

    // 4. Bind the save button
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileUpdate);
    }
});

// ============================================================
// DATA FETCHING FUNCTIONS
// ============================================================
async function loadUserProfile(userId) {
    try {
        const token = localStorage.getItem('token');
        // Fetch using the absolute URL
        const response = await fetch(`${BACKEND_URL}/api/auth/profile/${userId}`, {
            headers: { 'Authorization': token ? `Bearer ${token}` : '' }
        });
        
        if (!response.ok) throw new Error("Failed to fetch profile");
        
        const user = await response.json();
        if (user.error) throw new Error(user.error);

        // Safeguard against missing names
        const safeName = user.name || 'Awesome Customer';

        // Update Sidebar Elements
        document.getElementById('sidebar-name').textContent = safeName;
        document.getElementById('sidebar-email').textContent = user.email || 'No email on file';
        
        const avatarElem = document.getElementById('profile-avatar');
        if (avatarElem) avatarElem.textContent = safeName.charAt(0).toUpperCase();

        // Populate Form Inputs
        document.getElementById('prof-name').value = user.name || '';
        document.getElementById('prof-email').value = user.email || '';
        document.getElementById('prof-phone').value = user.phone || '';
        document.getElementById('prof-address').value = user.address || '';
        document.getElementById('prof-city').value = user.city || '';
        document.getElementById('prof-pincode').value = user.pincode || '';

    } catch (error) {
        console.error("Profile Load Error:", error);
        document.getElementById('sidebar-name').textContent = "Error loading profile";
        document.getElementById('sidebar-email').textContent = "Please refresh the page";
    }
}

async function loadUserOrders(userId) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${BACKEND_URL}/api/orders/${userId}`, {
            headers: { 'Authorization': token ? `Bearer ${token}` : '' }
        });
        
        if (!response.ok) throw new Error("Failed to fetch orders");
        
        const orders = await response.json();
        const tbody = document.getElementById('user-orders-body');
        if (!tbody) return;
        
        tbody.innerHTML = ''; // Clear the "Loading..." text

        if (orders.error) throw new Error(orders.error);

        // Handle empty order history gracefully
        if (!orders || orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center py-5 text-muted">You have no orders yet. Time to go shopping! 🛒</td></tr>';
            return;
        }

        // Generate table rows for each order
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
        console.error("Order Load Error:", error);
        const tbody = document.getElementById('user-orders-body');
        if (tbody) tbody.innerHTML = '<tr><td colspan="4" class="text-center py-5 text-danger">Failed to load order history. Please try again later.</td></tr>';
    }
}

// ============================================================
// FORM SUBMISSION LOGIC
// ============================================================
async function handleProfileUpdate(e) {
    e.preventDefault();
    const userId = localStorage.getItem('userId');
    const token = localStorage.getItem('token');
    const submitBtn = e.target.querySelector('button[type="submit"]');

    // Gather data from form
    const profileData = {
        name: document.getElementById('prof-name').value.trim(),
        phone: document.getElementById('prof-phone').value.trim(),
        address: document.getElementById('prof-address').value.trim(),
        city: document.getElementById('prof-city').value.trim(),
        pincode: document.getElementById('prof-pincode').value.trim()
    };

    // UI Feedback: Show saving state
    const originalBtnText = submitBtn.textContent;
    submitBtn.textContent = 'Saving...';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${BACKEND_URL}/api/auth/profile/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token ? `Bearer ${token}` : ''
            },
            body: JSON.stringify(profileData)
        });
        
        if (!response.ok) throw new Error("Failed to update profile");
        
        // Show success notification
        if (typeof showToast === 'function') showToast('Profile updated successfully!', 'success');
        else alert('Profile updated successfully!');
        
        // Instantly update the sidebar visually so the user doesn't have to refresh
        const safeName = profileData.name || 'User';
        document.getElementById('sidebar-name').textContent = safeName;
        
        const avatarElem = document.getElementById('profile-avatar');
        if (avatarElem) avatarElem.textContent = safeName.charAt(0).toUpperCase();
        
        // Update local storage so the navbar uses the new name
        localStorage.setItem('userName', safeName);

    } catch (error) {
        console.error('Update Error:', error);
        if (typeof showToast === 'function') showToast('Failed to update profile.', 'error');
        else alert('Failed to save changes. Please try again.');
    } finally {
        // Restore button state
        submitBtn.textContent = originalBtnText;
        submitBtn.disabled = false;
    }
}

// ============================================================
// GLOBAL LOGOUT
// ============================================================
window.logout = function() {
    localStorage.clear();
    window.location.href = 'index.html';
};