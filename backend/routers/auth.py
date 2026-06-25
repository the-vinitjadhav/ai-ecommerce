from fastapi import APIRouter
from backend.database import get_db_connection, close_db_connection
from backend.models import UserRegister, UserLogin
from backend.security import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register")
def register(user: UserRegister):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE email = %s", (user.email,))
    if cursor.fetchone():
        cursor.close()
        close_db_connection(conn)
        return {"error": "Email already registered"}
        
    hashed_pwd = get_password_hash(user.password)
    
    cursor.execute("""
        INSERT INTO users (name, email, password, phone, address, city, pincode)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user.name, user.email, hashed_pwd, user.phone, user.address, user.city, user.pincode))
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    return {"message": "User registered securely"}

@router.post("/login")
def login(login_data: UserLogin):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM users WHERE email = %s", (login_data.email,))
    user = cursor.fetchone()
    
    if user and verify_password(login_data.password, user['password']):
        token = create_access_token({"sub": str(user['user_id']), "role": "customer"})
        cursor.close()
        close_db_connection(conn)
        return {"user_id": user['user_id'], "name": user['name'], "role": "customer", "access_token": token, "message": "Login successful"}
        
    cursor.execute("SELECT * FROM admins WHERE email = %s", (login_data.email,))
    admin = cursor.fetchone()
    
    if admin and verify_password(login_data.password, admin['password']):
        token = create_access_token({"sub": str(admin['admin_id']), "role": "admin"})
        cursor.close()
        close_db_connection(conn)
        return {"user_id": admin['admin_id'], "name": admin['name'], "role": "admin", "access_token": token, "message": "Admin Login successful"}

    cursor.close()
    close_db_connection(conn)
    return {"error": "Invalid email or password"}