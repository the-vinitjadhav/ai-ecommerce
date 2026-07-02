from fastapi import APIRouter
import os
import json
import re
from groq import Groq
from backend.database import get_db_connection, close_db_connection
from backend.models import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

def get_product_recommendation(query: str) -> str:
    print(f"\n🔍 AI Tool: Searching for: {query}")
    conn = get_db_connection()
    if not conn:
        return json.dumps({"error": "Database connection failed."})
    
    cursor = conn.cursor(dictionary=True)
    price_limit = None
    match = re.search(r'under\s*(\d+)', query, re.IGNORECASE)
    if match:
        price_limit = int(match.group(1))
    
    category_map = {
        "phone": "Electronics", "laptop": "Laptops", "computer": "Laptops",
        "shoe": "Clothing", "shoes": "Clothing", "jeans": "Clothing",
        "book": "Books", "books": "Books", "electronic": "Electronics",
        "clothing": "Clothing", "watch": "Electronics", "bag": "Clothing",
        "camera": "Electronics"
    }
    
    detected_category = None
    for keyword, db_category in category_map.items():
        if keyword in query.lower():
            detected_category = db_category
            break
            
    is_generic = query.lower().strip() in ["", "featured", "all", "random", "explore", "products", "recommend"]

    if price_limit and detected_category:
        sql = "SELECT product_id, product_name, price, rating, category_name FROM products WHERE price <= %s AND category_name = %s LIMIT 5"
        params = (price_limit, detected_category)
    elif price_limit:
        sql = "SELECT product_id, product_name, price, rating, category_name FROM products WHERE price <= %s LIMIT 5"
        params = (price_limit,)
    elif detected_category:
        sql = "SELECT product_id, product_name, price, rating, category_name FROM products WHERE category_name = %s LIMIT 5"
        params = (detected_category,)
    elif is_generic:
        sql = "SELECT product_id, product_name, price, rating, category_name FROM products ORDER BY RAND() LIMIT 4"
        params = ()
    else:
        sql = "SELECT product_id, product_name, price, rating, category_name FROM products WHERE product_name LIKE %s OR description LIKE %s LIMIT 5"
        params = (f"%{query}%", f"%{query}%")
    
    try:
        cursor.execute(sql, params)
        products = cursor.fetchall()
        cursor.close()
        close_db_connection(conn)
    except Exception as e:
        return json.dumps({"error": f"Database error: {str(e)}"})
    
    if not products:
        return json.dumps({"message": f"No products found for '{query}'."})
        
    for p in products:
        if 'price' in p and p['price'] is not None:
            p['price'] = float(p['price'])
        if 'rating' in p and p['rating'] is not None:
            p['rating'] = float(p['rating'])
            
    return json.dumps(products)

def place_order(user_id: int, product_name: str, quantity: int) -> str:
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
        return f"Insufficient stock for {product_name}."
    total = product['price'] * quantity
    cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
    order_id = cursor.lastrowid
    cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (%s, %s, %s, %s, %s)", (order_id, product['product_id'], product_name, product['price'], quantity))
    cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, product['product_id']))
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    return f"Order #{order_id} placed successfully for {quantity} x {product_name}. Total: ₹{total}"

def check_order_status(user_id: int, order_id: int) -> str:
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
    return f"Order #{order['order_id']} (₹{order['total_amount']}) - Status: {order['status']}"

def cancel_order(user_id: int, order_id: int) -> str:
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
    if result['status'] in ('cancelled', 'shipped', 'delivered'):
        cursor.close()
        close_db_connection(conn)
        return f"Order #{order_id} is already {result['status']}."
    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (order_id,))
    cursor.execute("UPDATE products p JOIN order_items oi ON p.product_id = oi.product_id SET p.stock = p.stock + oi.quantity WHERE oi.order_id = %s", (order_id,))
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    return f"Order #{order_id} cancelled successfully."

@router.post("")
async def process_chat(request: ChatRequest):
    if not client:
        return {"response": "AI features not configured. Missing GROQ_API_KEY."}
    try:
        current_page = request.context.page if request.context else "Unknown"
        cart_count = request.context.cart_items if request.context else "Unknown"

        dynamic_system_prompt = f"""You are a professional AI shopping assistant for AI Store.
        USER CONTEXT: Looking at page: {current_page} | Items in cart: {cart_count}.
        
        RICH UI CAPABILITY:
        When recommending products, you MUST format EACH product using this exact HTML template:
        <div class="ai-product-card">
            <a href="product.html?id=[Product ID]" style="text-decoration: none; color: inherit;">
                <h6 class="ai-card-title hover-underline">[Product Name]</h6>
            </a>
            <div class="ai-card-price">₹[Price]</div>
            <button class="ai-card-btn" onclick="apiAddToCart({request.user_id}, [Product ID]).then(() => {{ showToast('Added to Cart!', 'success'); if(typeof updateCartCount === 'function') updateCartCount(); }}).catch(e => showToast(e.message || 'Error', 'error'))">
                Add to Cart
            </button>
        </div>
        
        GENERAL EXPLORATION:
        If user asks for general recommendations or "explore", pass "featured" as the query to get_product_recommendation.
        """

        tools = [
            {"type": "function", "function": {"name": "get_product_recommendation", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "place_order", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "product_name": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["user_id", "product_name", "quantity"]}}},
            {"type": "function", "function": {"name": "check_order_status", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "order_id": {"type": "integer"}}, "required": ["user_id", "order_id"]}}},
            {"type": "function", "function": {"name": "cancel_order", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "order_id": {"type": "integer"}}, "required": ["user_id", "order_id"]}}}
        ]

        messages = [{"role": "system", "content": dynamic_system_prompt}, {"role": "user", "content": request.message}]
        response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.2, tools=tools)
        response_message = response.choices[0].message

        if response_message.tool_calls:
            messages.append({"role": "assistant", "content": response_message.content, "tool_calls": [{"id": t.id, "type": t.type, "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in response_message.tool_calls]})
            tool_call = response_message.tool_calls[0]
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if func_name == "get_product_recommendation": result = get_product_recommendation(args["query"])
            elif func_name == "place_order": result = place_order(args["user_id"], args["product_name"], args["quantity"])
            elif func_name == "check_order_status": result = check_order_status(args["user_id"], args["order_id"])
            elif func_name == "cancel_order": result = cancel_order(args["user_id"], args["order_id"])
            else: result = json.dumps({"error": "Unknown function"})
            
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": func_name, "content": str(result)})
            second_response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.2)
            return {"response": second_response.choices[0].message.content}
        else:
            return {"response": response_message.content}
            
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}"}