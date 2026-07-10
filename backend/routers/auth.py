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
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (user.email,))
        if cursor.fetchone():
            return {"error": "Email already registered"}
            
        hashed_pwd = get_password_hash(user.password)
        
        # Safely handling missing fields during registration using getattr
        cursor.execute("""
            INSERT INTO users (name, email, password, phone, address, city, pincode)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            user.name, 
            user.email, 
            hashed_pwd, 
            getattr(user, 'phone', None), 
            getattr(user, 'address', None), 
            getattr(user, 'city', None), 
            getattr(user, 'pincode', None)
        ))
        conn.commit()
        return {"message": "User registered securely"}
    except Exception as e:
        print(f"DATABASE ERROR in register: {e}")
        return {"error": str(e)}
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_db_connection(conn)

@router.post("/login")
def login(login_data: UserLogin):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users WHERE email = %s", (login_data.email,))
        user = cursor.fetchone()
        
        if user and verify_password(login_data.password, user['password']):
            token = create_access_token({"sub": str(user['user_id']), "role": "customer"})
            return {"user_id": user['user_id'], "name": user['name'], "role": "customer", "access_token": token, "message": "Login successful"}
            
        cursor.execute("SELECT * FROM admins WHERE email = %s", (login_data.email,))
        admin = cursor.fetchone()
        
        if admin and verify_password(login_data.password, admin['password']):
            token = create_access_token({"sub": str(admin['admin_id']), "role": "admin"})
            return {"user_id": admin['admin_id'], "name": admin['name'], "role": "admin", "access_token": token, "message": "Admin Login successful"}

        return {"error": "Invalid email or password"}
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_db_connection(conn)

@router.get("/profile/{user_id}")
def get_user_profile(user_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    try:
        cursor = conn.cursor(dictionary=True)
        # REMOVED created_at AND role TO PREVENT FATAL 500 CRASHES
        cursor.execute("""
            SELECT user_id, name, email, phone, address, city, pincode 
            FROM users WHERE user_id = %s
        """, (user_id,))
        user = cursor.fetchone()
        
        # THE FIX: If the logged-in user is an Admin testing the site, pull from admins table!
        if not user:
            cursor.execute("SELECT admin_id as user_id, name, email FROM admins WHERE admin_id = %s", (user_id,))
            admin = cursor.fetchone()
            if admin:
                # Provide empty defaults for fields admins don't have so the UI doesn't break
                admin['phone'] = ''
                admin['address'] = 'Admin Dashboard'
                admin['city'] = ''
                admin['pincode'] = ''
                return admin
            return {"error": "User not found"}
            
        return user
    except Exception as e:
        # This will print the exact database error to your Uvicorn terminal!
        print(f"DATABASE ERROR in get_user_profile: {e}")
        return {"error": f"Internal Server Error: {str(e)}"}
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_db_connection(conn)

@router.put("/profile/{user_id}")
def update_user_profile(user_id: int, profile_data: dict):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET name=%s, phone=%s, address=%s, city=%s, pincode=%s 
            WHERE user_id=%s
        """, (
            profile_data.get('name'), 
            profile_data.get('phone'), 
            profile_data.get('address'), 
            profile_data.get('city'), 
            profile_data.get('pincode'), 
            user_id
        ))
        
        # THE FIX: If 0 rows updated, they are an admin. Update the admin's name.
        if cursor.rowcount == 0:
            cursor.execute("UPDATE admins SET name=%s WHERE admin_id=%s", (profile_data.get('name'), user_id))

        conn.commit()
        return {"message": "Profile updated successfully"}
    except Exception as e:
        print(f"DATABASE ERROR in update_user_profile: {e}")
        return {"error": f"Internal Server Error: {str(e)}"}
    finally:
        if 'cursor' in locals():
            cursor.close()
        close_db_connection(conn)