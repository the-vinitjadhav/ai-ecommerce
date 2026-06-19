from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import mysql.connector
from mysql.connector import Error
import os
from pathlib import Path

# ============================================================
# DATABASE CONNECTION
# ============================================================
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Vinit.j@532",  # CHANGE THIS TO YOUR ACTUAL MYSQL PASSWORD
            database="ecommerce_db"
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def close_db_connection(connection):
    if connection:
        connection.close()

# ============================================================
# PYDANTIC MODELS
# ============================================================
class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class CartItem(BaseModel):
    product_id: int
    quantity: int = 1

class Order(BaseModel):
    user_id: int
    total_amount: float
    status: str = "pending"

class Product(BaseModel):
    product_name: str
    description: Optional[str] = None
    price: float
    stock: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    image_url: Optional[str] = None

class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None

# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(
    title="AI Ecommerce API",
    description="Monolithic API for AI Ecommerce",
    version="1.0.0"
)

# CORS (Allows frontend from any port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ ABSOLUTE PATH TO FRONTEND (No more relative path errors)
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")



# ============================================================
# AUTH ROUTES
# ============================================================
@app.post("/api/auth/register")
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
    
    cursor.execute("""
        INSERT INTO users (name, email, password, phone, address, city, pincode)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user.name, user.email, user.password, user.phone, user.address, user.city, user.pincode))
    
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    
    return {"message": "User registered successfully"}

@app.post("/api/auth/login")
def login(login_data: UserLogin):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT user_id, name, 'customer' as role 
        FROM users 
        WHERE email = %s AND password = %s
    """, (login_data.email, login_data.password))
    user = cursor.fetchone()
    
    if user:
        cursor.close()
        close_db_connection(conn)
        return {
            "user_id": user[0],
            "name": user[1],
            "role": user[2],
            "message": "Login successful"
        }
    
    cursor.execute("""
        SELECT admin_id, name, 'admin' as role 
        FROM admins 
        WHERE email = %s AND password = %s
    """, (login_data.email, login_data.password))
    admin = cursor.fetchone()
    
    if admin:
        cursor.close()
        close_db_connection(conn)
        return {
            "user_id": admin[0],
            "name": admin[1],
            "role": admin[2],
            "message": "Login successful"
        }
    
    cursor.close()
    close_db_connection(conn)
    return {"error": "Invalid email or password"}

# ============================================================
# PRODUCTS ROUTES
# ============================================================
@app.get("/api/products/")
def get_all_products():
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    
    cursor.close()
    close_db_connection(conn)
    
    return products

@app.get("/api/products/{product_id}")
def get_product(product_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()
    
    cursor.close()
    close_db_connection(conn)
    
    if not product:
        return {"error": "Product not found"}
    
    return product

@app.get("/api/products/search/")
def search_products(keyword: str):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM products 
        WHERE product_name LIKE %s OR description LIKE %s
    """, (f"%{keyword}%", f"%{keyword}%"))
    products = cursor.fetchall()
    
    cursor.close()
    close_db_connection(conn)
    
    return products

# ============================================================
# CART ROUTES
# ============================================================
@app.get("/api/cart/{user_id}")
def get_cart(user_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.cart_id, c.product_id, p.product_name, p.price, c.quantity, 
               (p.price * c.quantity) AS total_price
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    """, (user_id,))
    items = cursor.fetchall()
    
    cursor.close()
    close_db_connection(conn)
    
    return items

@app.post("/api/cart/{user_id}")
def add_to_cart(user_id: int, item: CartItem):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor()
    
    cursor.execute("SELECT quantity FROM cart WHERE user_id = %s AND product_id = %s", 
                   (user_id, item.product_id))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("""
            UPDATE cart SET quantity = quantity + %s 
            WHERE user_id = %s AND product_id = %s
        """, (item.quantity, user_id, item.product_id))
    else:
        cursor.execute("""
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES (%s, %s, %s)
        """, (user_id, item.product_id, item.quantity))
    
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    
    return {"message": "Item added to cart"}

@app.delete("/api/cart/{user_id}/{product_id}")
def remove_from_cart(user_id: int, product_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = %s AND product_id = %s", 
                   (user_id, product_id))
    conn.commit()
    
    cursor.close()
    close_db_connection(conn)
    
    return {"message": "Item removed from cart"}

@app.delete("/api/cart/clear/{user_id}")
def clear_cart(user_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
    conn.commit()
    
    cursor.close()
    close_db_connection(conn)
    
    return {"message": "Cart cleared"}

# ============================================================
# ORDERS ROUTES
# ============================================================
@app.get("/api/orders/{user_id}")
def get_user_orders(user_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.total_amount, o.status, o.order_date,
               COUNT(oi.item_id) AS item_count
        FROM orders o
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.user_id = %s
        GROUP BY o.order_id, o.total_amount, o.status, o.order_date
        ORDER BY o.order_date DESC
    """, (user_id,))
    orders = cursor.fetchall()
    
    cursor.close()
    close_db_connection(conn)
    
    return orders

@app.post("/api/orders/{user_id}")
def place_order(user_id: int, order_data: Order):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.product_id, c.quantity, p.price, p.stock, p.product_name
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    """, (user_id,))
    cart_items = cursor.fetchall()
    
    if not cart_items:
        cursor.close()
        close_db_connection(conn)
        return {"error": "Cart is empty"}
    
    for item in cart_items:
        if item[3] < item[1]:
            cursor.close()
            close_db_connection(conn)
            return {"error": f"Insufficient stock for {item[4]}"}
    
    total = sum(item[1] * item[2] for item in cart_items)
    
    cursor.execute("""
        INSERT INTO orders (user_id, total_amount, status)
        VALUES (%s, %s, %s)
    """, (user_id, total, order_data.status))
    order_id = cursor.lastrowid
    
    for item in cart_items:
        product_id, quantity, price, stock, product_name = item
        
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
            VALUES (%s, %s, %s, %s, %s)
        """, (order_id, product_id, product_name, price, quantity))
        
        cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", 
                       (quantity, product_id))
    
    cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
    
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    
    return {"order_id": order_id, "total_amount": total, "message": "Order placed successfully"}

@app.put("/api/orders/cancel/{user_id}/{order_id}")
def cancel_order(user_id: int, order_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor()
    
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", 
                   (order_id, user_id))
    result = cursor.fetchone()
    
    if not result:
        cursor.close()
        close_db_connection(conn)
        return {"error": "Order not found"}
    
    status = result[0]
    if status == 'cancelled':
        cursor.close()
        close_db_connection(conn)
        return {"error": "Order already cancelled"}
    
    if status in ('shipped', 'delivered'):
        cursor.close()
        close_db_connection(conn)
        return {"error": f"Cannot cancel {status} order"}
    
    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (order_id,))
    
    cursor.execute("""
        UPDATE products p
        JOIN order_items oi ON p.product_id = oi.product_id
        SET p.stock = p.stock + oi.quantity
        WHERE oi.order_id = %s
    """, (order_id,))
    
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    
    return {"message": "Order cancelled successfully"}

# ============================================================
# ADMIN ROUTES
# ============================================================
@app.post("/api/admin/products")
def add_product(product: Product):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (product_name, description, price, stock, category_id, category_name, image_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (product.product_name, product.description, product.price, product.stock, 
          product.category_id, product.category_name, product.image_url))
    
    conn.commit()
    product_id = cursor.lastrowid
    
    cursor.close()
    close_db_connection(conn)
    
    return {"product_id": product_id, "message": "Product added successfully"}

@app.put("/api/admin/products/{product_id}")
def update_product(product_id: int, product: ProductUpdate):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor()
    
    updates = []
    values = []
    
    if product.product_name:
        updates.append("product_name = %s")
        values.append(product.product_name)
    if product.price:
        updates.append("price = %s")
        values.append(product.price)
    if product.stock:
        updates.append("stock = %s")
        values.append(product.stock)
    
    if not updates:
        cursor.close()
        close_db_connection(conn)
        return {"error": "No fields to update"}
    
    values.append(product_id)
    query = f"UPDATE products SET {', '.join(updates)} WHERE product_id = %s"
    cursor.execute(query, values)
    conn.commit()
    
    cursor.close()
    close_db_connection(conn)
    
    return {"message": "Product updated successfully"}

@app.delete("/api/admin/products/{product_id}")
def delete_product(product_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
    conn.commit()
    
    cursor.close()
    close_db_connection(conn)
    
    return {"message": "Product deleted successfully"}

@app.get("/api/admin/orders")
def get_all_orders():
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.user_id, o.total_amount, o.status, o.order_date, u.name
        FROM orders o
        JOIN users u ON o.user_id = u.user_id
        ORDER BY o.order_date DESC
    """)
    orders = cursor.fetchall()
    
    cursor.close()
    close_db_connection(conn)
    
    return orders

@app.put("/api/admin/orders/{order_id}")
def update_order_status(order_id: int, status: str):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = %s WHERE order_id = %s", (status, order_id))
    conn.commit()
    
    cursor.close()
    close_db_connection(conn)
    
    return {"message": f"Order status updated to {status}"}

# ============================================================
# TEST ROUTE
# ============================================================
@app.get("/api/test/ping")
def ping():
    return {"status": "pong", "message": "Monolithic API is working!"}

@app.get("/")
def root():
    return {"message": "AI Ecommerce API is running!"}

# Serve frontend files
# Serve frontend files
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")