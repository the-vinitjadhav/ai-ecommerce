from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import mysql.connector
from mysql.connector import Error
import os
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

# ============================================================
# DATABASE CONNECTION
# ============================================================
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        FROM users WHERE email = %s AND password = %s
    """, (login_data.email, login_data.password))
    user = cursor.fetchone()
    if user:
        cursor.close()
        close_db_connection(conn)
        return {"user_id": user[0], "name": user[1], "role": user[2], "message": "Login successful"}
    cursor.execute("""
        SELECT admin_id, name, 'admin' as role 
        FROM admins WHERE email = %s AND password = %s
    """, (login_data.email, login_data.password))
    admin = cursor.fetchone()
    if admin:
        cursor.close()
        close_db_connection(conn)
        return {"user_id": admin[0], "name": admin[1], "role": admin[2], "message": "Login successful"}
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
        FROM cart c JOIN products p ON c.product_id = p.product_id
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
    cursor.execute("SELECT quantity FROM cart WHERE user_id = %s AND product_id = %s", (user_id, item.product_id))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE cart SET quantity = quantity + %s WHERE user_id = %s AND product_id = %s", (item.quantity, user_id, item.product_id))
    else:
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)", (user_id, item.product_id, item.quantity))
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    return {"message": "Item added to cart"}

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
        SELECT o.order_id, o.total_amount, o.status, o.order_date, COUNT(oi.item_id) AS item_count
        FROM orders o LEFT JOIN order_items oi ON o.order_id = oi.order_id
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
        FROM cart c JOIN products p ON c.product_id = p.product_id
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
    cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, %s)", (user_id, total, order_data.status))
    order_id = cursor.lastrowid
    for item in cart_items:
        product_id, quantity, price, stock, product_name = item
        cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (%s, %s, %s, %s, %s)", (order_id, product_id, product_name, price, quantity))
        cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, product_id))
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
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        close_db_connection(conn)
        return {"error": "Order not found"}
    status = result[0]
    if status == 'cancelled' or status in ('shipped', 'delivered'):
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
    """, (product.product_name, product.description, product.price, product.stock, product.category_id, product.category_name, product.image_url))
    conn.commit()
    product_id = cursor.lastrowid
    cursor.close()
    close_db_connection(conn)
    return {"product_id": product_id, "message": "Product added successfully"}

@app.get("/api/admin/orders")
def get_all_orders():
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.user_id, o.total_amount, o.status, o.order_date, u.name
        FROM orders o JOIN users u ON o.user_id = u.user_id
        ORDER BY o.order_date DESC
    """)
    orders = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    return orders

# ============================================================
# TEST ROUTE
# ============================================================
@app.get("/api/test/ping")
def ping():
    return {"status": "pong", "message": "Monolithic API is working!"}

# ============================================================
# GROQ NATIVE SDK (NO LANGCHAIN, 100% WORKING)
# ============================================================
load_dotenv()

class ChatRequest(BaseModel):
    user_id: int
    message: str

# ============================================================
# AI TOOLS (Native Python functions)
# ============================================================
def get_product_recommendation(query: str) -> str:
    """Get product recommendations based on a search query (supports category + price)."""
    print(f"\n🔍 AI Tool: Searching for: {query}")
    
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    
    cursor = conn.cursor(dictionary=True)
    
    # 1. Extract price limit from query (e.g., "under 50000" → 50000)
    price_limit = None
    import re
    match = re.search(r'under\s*(\d+)', query, re.IGNORECASE)
    if match:
        price_limit = int(match.group(1))
        print(f"💰 Extracted price limit: {price_limit}")
    
    # 2. Extract category keyword (e.g., "phones", "laptops", "shoes")
    # Map user-friendly keywords to actual database category_names
    category_map = {
        "phone": "Electronics",
        "laptop": "Laptops",
        "computer": "Laptops",
        "shoe": "Clothing",
        "shoes": "Clothing",
        "jeans": "Clothing",
        "book": "Books",
        "books": "Books",
        "electronic": "Electronics",
        "clothing": "Clothing",
        "watch": "Electronics",
        "bag": "Clothing",
        "camera": "Electronics"
    }
    # 2. Extract category keyword and map it to actual database category_name
    detected_category = None
    for keyword, db_category in category_map.items():
        if keyword in query.lower():
            detected_category = db_category
            print(f"📂 Detected keyword: '{keyword}' → Mapped to category: '{detected_category}'")
            break
    
    # 3. Build the SQL query dynamically
    if price_limit and detected_category:
        # Filter by BOTH price AND category_name
        sql = """
            SELECT product_name, price, rating, category_name 
            FROM products 
            WHERE price <= %s 
            AND category_name = %s
            LIMIT 5
        """
        params = (price_limit, detected_category)
        print(f"📝 Executing SQL (Price + Category): {sql}")

    elif price_limit:
        # Filter by price ONLY
        sql = """
            SELECT product_name, price, rating, category_name 
            FROM products 
            WHERE price <= %s
            LIMIT 5
        """
        params = (price_limit,)
        print(f"📝 Executing SQL (Price Only): {sql}")

    elif detected_category:
        # Filter by category_name ONLY
        sql = """
            SELECT product_name, price, rating, category_name 
            FROM products 
            WHERE category_name = %s
            LIMIT 5
        """
        params = (detected_category,)
        print(f"📝 Executing SQL (Category Only): {sql}")

    else:
        # Full text search (fallback)
        sql = """
            SELECT product_name, price, rating, category_name 
            FROM products 
            WHERE product_name LIKE %s 
            OR description LIKE %s
            LIMIT 5
        """
        params = (f"%{query}%", f"%{query}%")
        print(f"📝 Executing SQL (Full Text): {sql}")
    
    try:
        cursor.execute(sql, params)
        products = cursor.fetchall()
        cursor.close()
        close_db_connection(conn)
    except Exception as e:
        print(f"❌ SQL Error: {e}")
        return f"Database error: {str(e)}"
    
    if not products:
        return f"No products found for '{query}'."
    
    result = "Recommended products:\n"
    for p in products:
        result += f"- {p['product_name']} (₹{p['price']}, Rating: {p['rating']}/5, Category: {p['category_name']})\n"
    return result

def place_order(user_id: int, product_name: str, quantity: int) -> str:
    """Place an order for a specific product by name."""
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, price, stock FROM products WHERE product_name LIKE %s", (f"%{product_name}%",))
    product = cursor.fetchone()
    if not product:
        cursor.close()
        close_db_connection(conn)
        return f"Product '{product_name}' not found."
    if product['stock'] < quantity:
        cursor.close()
        close_db_connection(conn)
        return f"Insufficient stock for {product_name}. Available: {product['stock']}"
    total = product['price'] * quantity
    cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
    order_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
        VALUES (%s, %s, %s, %s, %s)
    """, (order_id, product['product_id'], product_name, product['price'], quantity))
    cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, product['product_id']))
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    return f"Order #{order_id} placed successfully for {quantity} x {product_name}. Total: ₹{total}"

def check_order_status(user_id: int, order_id: int) -> str:
    """Check the status of a specific order."""
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT order_id, total_amount, status, order_date FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    order = cursor.fetchone()
    cursor.close()
    close_db_connection(conn)
    if not order:
        return f"Order #{order_id} not found."
    return f"Order #{order['order_id']} (₹{order['total_amount']}) - Status: {order['status']} - Date: {order['order_date']}"

def cancel_order(user_id: int, order_id: int) -> str:
    """Cancel an existing order."""
    conn = get_db_connection()
    if not conn:
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        close_db_connection(conn)
        return f"Order #{order_id} not found."
    if result['status'] == 'cancelled' or result['status'] in ('shipped', 'delivered'):
        cursor.close()
        close_db_connection(conn)
        return f"Order #{order_id} is already {result['status']}."
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
    return f"Order #{order_id} cancelled successfully."

# ============================================================
# GROQ NATIVE AGENT (NO LANGCHAIN AT ALL)
# ============================================================
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("⚠️  WARNING: GROQ_API_KEY not set in .env file.")

client = Groq(api_key=api_key)

# System prompt that teaches Groq how to use the tools
SYSTEM_PROMPT = """You are an AI shopping assistant for an ecommerce platform.
You have access to the following functions:

1. get_product_recommendation(query) - Returns a list of product recommendations based on a search query.
2. place_order(user_id, product_name, quantity) - Places an order for a product.
3. check_order_status(user_id, order_id) - Checks the status of an order.
4. cancel_order(user_id, order_id) - Cancels an existing order.

Rules:
- You MUST call a function when asked to perform an action.
- The user_id is 1 for all requests.

SMART QUERY HANDLING:
- When the user asks for products under a certain price, extract the price.
- When the user mentions a category (like "phones", "laptops", "shoes"), extract that too.
- Pass BOTH the category and the price to get_product_recommendation.

Examples:
User: "Show me products under 50000"
You: call get_product_recommendation("under 50000")

User: "Show me phones under 30000"
You: call get_product_recommendation("phones under 30000")

User: "Laptops under 40000"
You: call get_product_recommendation("laptops under 40000")

User: "Show me shoes"
You: call get_product_recommendation("shoes")

NEVER pass the full user message as the query. ALWAYS extract the category and price filter."""

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not os.getenv("GROQ_API_KEY"):
        return {"response": "AI features are not configured. Please set GROQ_API_KEY in .env file."}
    
    try:
        # Call Groq directly with the system prompt
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request.message}
            ],
            temperature=0,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_product_recommendation",
                        "description": "Get product recommendations based on a search query",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "place_order",
                        "description": "Place an order for a specific product",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "integer", "description": "The user ID"},
                                "product_name": {"type": "string", "description": "The product name"},
                                "quantity": {"type": "integer", "description": "The quantity"}
                            },
                            "required": ["user_id", "product_name", "quantity"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "check_order_status",
                        "description": "Check the status of a specific order",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "integer", "description": "The user ID"},
                                "order_id": {"type": "integer", "description": "The order ID"}
                            },
                            "required": ["user_id", "order_id"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "cancel_order",
                        "description": "Cancel an existing order",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "integer", "description": "The user ID"},
                                "order_id": {"type": "integer", "description": "The order ID"}
                            },
                            "required": ["user_id", "order_id"]
                        }
                    }
                }
            ]
        )
        
        # Check if Groq called a tool
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            function_name = tool_call.function.name
            arguments = eval(tool_call.function.arguments)
            
            # Execute the function
            if function_name == "get_product_recommendation":
                result = get_product_recommendation(arguments["query"])
            elif function_name == "place_order":
                result = place_order(arguments["user_id"], arguments["product_name"], arguments["quantity"])
            elif function_name == "check_order_status":
                result = check_order_status(arguments["user_id"], arguments["order_id"])
            elif function_name == "cancel_order":
                result = cancel_order(arguments["user_id"], arguments["order_id"])
            else:
                result = "Unknown function called."
            
            return {"response": result}
        else:
            return {"response": response.choices[0].message.content}
            
    except Exception as e:
        print(f"AI Error: {e}")
        return {"response": f"Sorry, I encountered an error: {str(e)}"}

@app.get("/api/chat-test")
async def chat_test():
    return {"message": "GET route is working!"}

@app.get("/")
def root():
    return {"message": "AI Ecommerce API is running!"}

# ============================================================
# FRONTEND MOUNT
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")