// ============================================================
// FILE: frontend/js/auth.js
// PURPOSE: Login and Register logic
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
});

// ============================================================
// LOGIN FUNCTION
// ============================================================
async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const alertDiv = document.getElementById('login-alert');
    
    if (alertDiv) alertDiv.classList.add('d-none');
    
    console.log('Attempting login with:', { email, password });
    
    try {
        const result = await loginUser({ email, password });
        
        console.log('Login successful:', result);
        
        localStorage.setItem('userId', result.user_id);
        localStorage.setItem('userName', result.name);
        localStorage.setItem('role', result.role);
        
        alert('Login successful! Welcome ' + result.name);
        window.location.href = 'index.html';
        
    } catch (error) {
        console.error('Login error:', error);
        if (alertDiv) {
            alertDiv.textContent = error.message || 'Login failed. Check credentials.';
            alertDiv.classList.remove('d-none');
        } else {
            alert('Login failed: ' + error.message);
        }
    }
}

// ============================================================
// REGISTER FUNCTION
// ============================================================
async function handleRegister(e) {
    e.preventDefault();
    
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const phone = document.getElementById('phone').value;
    const address = document.getElementById('address').value;
    const city = document.getElementById('city').value;
    const pincode = document.getElementById('pincode').value;
    const alertDiv = document.getElementById('register-alert');
    
    if (alertDiv) alertDiv.classList.add('d-none');
    
    try {
        await registerUser({
            name, email, password, phone, address, city, pincode
        });
        
        alert('Registration successful! Please login.');
        window.location.href = 'login.html';
        
    } catch (error) {
        console.error('Register error:', error);
        if (alertDiv) {
            alertDiv.textContent = error.message || 'Registration failed.';
            alertDiv.classList.remove('d-none');
        } else {
            alert('Registration failed: ' + error.message);
        }
    }
}