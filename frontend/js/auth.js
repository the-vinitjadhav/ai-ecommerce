// ============================================================
// FILE: frontend/js/auth.js
// PURPOSE: Handle Login and Registration forms and redirects
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
});

async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    try {
        const data = await loginUser({ email, password });
        
        // SECURE: Save the new JWT Token and user data
        if (data.access_token) {
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('userId', data.user_id);
            localStorage.setItem('userName', data.name);
            localStorage.setItem('role', data.role);
            
            if (typeof showToast === 'function') {
                showToast(data.message || 'Login successful!', 'success');
            }
            
            // THE MAGIC REDIRECT: Send admins to the dashboard!
            setTimeout(() => {
                if (data.role === 'admin') {
                    window.location.href = 'admin.html';
                } else {
                    window.location.href = 'index.html';
                }
            }, 1000);
        } else {
            throw new Error(data.error || 'Login failed');
        }
    } catch (error) {
        if (typeof showToast === 'function') {
            showToast(error.message, 'error');
        } else {
            alert(error.message);
        }
    }
}

async function handleRegister(e) {
    e.preventDefault();
    
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    // Optional fields
    const phone = document.getElementById('phone')?.value || null;
    const address = document.getElementById('address')?.value || null;
    const city = document.getElementById('city')?.value || null;
    const pincode = document.getElementById('pincode')?.value || null;
    
    try {
        const data = await registerUser({ name, email, password, phone, address, city, pincode });
        
        if (data.error) throw new Error(data.error);
        
        if (typeof showToast === 'function') {
            showToast('Registration successful! Please login.', 'success');
        }
        
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 1500);
        
    } catch (error) {
        if (typeof showToast === 'function') {
            showToast(error.message, 'error');
        } else {
            alert(error.message);
        }
    }
}