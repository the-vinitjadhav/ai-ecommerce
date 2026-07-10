from fastapi import APIRouter
import os
import json
import re
import urllib.parse
from groq import Groq
from backend.database import get_db_connection, close_db_connection
from backend.models import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["AI Chat"])

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

# ==========================================
# 1. RECOMMENDATIONS
# ==========================================
def get_product_recommendation(query: str, user_id: int) -> str:
    conn = get_db_connection()
    if not conn: 
        return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    
    price_limit = None
    match = re.search(r'under\s*(\d+)', query, re.IGNORECASE)
    if match: 
        price_limit = int(match.group(1))
    
    category_map = {"phone": "Electronics", "laptop": "Laptops", "computer": "Laptops", "shoe": "Clothing", "book": "Books"}
    detected_category = next((v for k, v in category_map.items() if k in query.lower()), None)
            
    if any(word in query.lower() for word in ["latest", "new"]): 
        sql = "SELECT * FROM products ORDER BY product_id DESC LIMIT 5"
        params = ()
    elif price_limit and detected_category: 
        sql = "SELECT * FROM products WHERE price <= %s AND category_name = %s LIMIT 5"
        params = (price_limit, detected_category)
    elif price_limit: 
        sql = "SELECT * FROM products WHERE price <= %s LIMIT 5"
        params = (price_limit,)
    elif detected_category: 
        sql = "SELECT * FROM products WHERE category_name = %s LIMIT 5"
        params = (detected_category,)
    elif any(word in query.lower() for word in ["recommend", "explore", "products", "all", "show", "featured"]): 
        sql = "SELECT * FROM products ORDER BY RAND() LIMIT 4"
        params = ()
    else: 
        sql = "SELECT * FROM products WHERE product_name LIKE %s OR description LIKE %s LIMIT 5"
        params = (f"%{query}%", f"%{query}%")
    
    try:
        cursor.execute(sql, params)
        products = cursor.fetchall()
        
        if not products:
            cursor.execute("SELECT * FROM products ORDER BY RAND() LIMIT 4")
            products = cursor.fetchall()
            
        if not products: 
            return "Sorry, our store catalog is currently empty!"

        html = "<div style='display:flex; flex-direction:column; gap:10px; margin-top:5px;'>"
        for p in products:
            img = p.get('image_url', '')
            if not img or not str(img).startswith('http'):
                safe_name = urllib.parse.quote(str(p.get('product_name', 'Item')))
                img = f"https://ui-avatars.com/api/?name={safe_name}&background=random&color=fff&size=200"

            html += f"""
            <div style="display: flex; gap: 12px; padding: 10px; background: rgba(255,255,255,0.5); border: 1px solid rgba(0,0,0,0.05); border-radius: 12px; align-items: center;">
                <img src="{img}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 8px;">
                <div style="flex: 1;">
                    <h6 style="margin: 0 0 4px 0; font-size: 0.9rem; font-weight: bold; color: inherit; line-height: 1.2;">{p['product_name']}</h6>
                    <div style="font-weight: 800; color: #6366f1; font-size: 1.05rem; margin-bottom: 6px;">₹{p['price']}</div>
                    <button style="background: #0f172a; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;" onclick="widgetAddToCart({p['product_id']})">Add to Cart</button>
                </div>
            </div>
            """
        html += "</div>"
        return html
    except Exception as e: 
        return f"Error retrieving products: {str(e)}"
    finally: 
        cursor.close()
        close_db_connection(conn)

# ==========================================
# 2. COMPARISONS
# ==========================================
def compare_products(product_a: str, product_b: str, user_id: int) -> str:
    conn = get_db_connection()
    if not conn: 
        return "Database connection failed."
    try:
        cursor = conn.cursor(dictionary=True)
        results = []
        for term in [product_a, product_b]:
            cursor.execute("SELECT * FROM products WHERE product_name LIKE %s OR description LIKE %s LIMIT 1", (f"%{term}%", f"%{term}%"))
            p = cursor.fetchone()
            if p: 
                results.append(p)
                
        if len(results) < 2: 
            return f"I couldn't find exact matches to compare '{product_a}' and '{product_b}'."

        html = "<div style='display: flex; gap: 10px; overflow-x: auto; padding: 5px 0; margin-top: 5px;'>"
        for p in results:
            img = p.get('image_url', '')
            if not img or not str(img).startswith('http'):
                img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(p.get('product_name', 'Item')))}&background=random&color=fff&size=200"
            html += f"""
            <div style="flex: 1; min-width: 140px; background: rgba(255,255,255,0.5); border: 1px solid rgba(0,0,0,0.05); border-radius: 12px; padding: 10px; text-align: center;">
                <img src="{img}" style="width: 70px; height: 70px; object-fit: cover; border-radius: 8px; margin-bottom: 8px;">
                <h6 style="font-size: 0.85rem; font-weight: bold; margin: 0 0 5px 0; height: 32px; overflow: hidden;">{p['product_name']}</h6>
                <p style="color: #6366f1; font-weight: 800; font-size: 1.1rem; margin: 0 0 8px 0;">₹{p['price']}</p>
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 10px;">{p.get('category_name', 'Unknown')}</div>
                <button style="background: #0f172a; color: white; border: none; padding: 6px 10px; border-radius: 6px; width: 100%; font-size: 0.8rem; cursor: pointer;" onclick="widgetAddToCart({p['product_id']})">Add to Cart</button>
            </div>
            """
        html += "</div>"
        return html
    except Exception as e: 
        return f"Error during comparison: {str(e)}"
    finally: 
        cursor.close()
        close_db_connection(conn)

# ==========================================
# 3. DEEP PRODUCT DETAILS
# ==========================================
def get_product_details(product_name: str, user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    p = cursor.fetchone()
    cursor.close()
    close_db_connection(conn)
    
    if not p: 
        return f"I couldn't find a product matching '{product_name}' in our catalog."
    
    img = p.get('image_url', '')
    if not img or not str(img).startswith('http'):
        img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(p.get('product_name', 'Item')))}&background=random&color=fff&size=200"
    
    html = f"""
    <div style="background: rgba(255,255,255,0.5); border: 1px solid rgba(0,0,0,0.05); border-radius: 12px; padding: 12px; margin-top: 5px;">
        <img src="{img}" style="width: 100%; height: 160px; object-fit: cover; border-radius: 8px; margin-bottom: 12px;">
        <span style="background: #e0e7ff; color: #4338ca; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold;">{p.get('category_name', 'General')}</span>
        <h5 style="font-weight: 800; margin: 10px 0 8px 0; font-size: 1rem;">{p['product_name']}</h5>
        <p style="font-size: 0.85rem; opacity: 0.8; margin-bottom: 12px; line-height: 1.4;">{p.get('description', 'A premium product from AI Store.')}</p>
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(0,0,0,0.05); padding-top: 12px;">
            <span style="font-weight: 900; color: #6366f1; font-size: 1.2rem;">₹{p['price']}</span>
            <button style="background: linear-gradient(135deg, #6366f1, #a855f7); color: white; border: none; padding: 8px 16px; border-radius: 8px; font-weight: bold; cursor: pointer;" onclick="widgetAddToCart({p['product_id']})">Buy Now</button>
        </div>
    </div>
    """
    return html

# ==========================================
# 4. FIND CHEAPER ALTERNATIVES 
# ==========================================
def find_cheaper_alternative(product_name: str, user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT price, category_name FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    target = cursor.fetchone()
    
    if not target: 
        cursor.close()
        close_db_connection(conn)
        return "I couldn't find the original product to compare against."

    cursor.execute("SELECT * FROM products WHERE category_name = %s AND price < %s ORDER BY price DESC LIMIT 3", (target['category_name'], target['price']))
    alts = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    
    if not alts: 
        return f"There are no cheaper alternatives in the {target['category_name']} category right now."
    
    html = "<p style='margin-bottom: 10px; font-size: 0.9rem;'>Here are some budget-friendly alternatives:</p><div style='display:flex; flex-direction:column; gap:10px;'>"
    for p in alts:
        img = p.get('image_url', '')
        if not img or not str(img).startswith('http'):
            img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(p.get('product_name', 'Item')))}&background=random&color=fff&size=200"
        html += f"""
        <div style="display: flex; gap: 12px; padding: 10px; background: rgba(255,255,255,0.5); border: 1px solid rgba(0,0,0,0.05); border-radius: 12px; align-items: center;">
            <img src="{img}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 8px; flex-shrink: 0;">
            <div style="flex: 1;">
                <h6 style="font-weight: 700; font-size: 0.9rem; margin: 0 0 4px 0;">{p['product_name']}</h6>
                <div style="font-weight: 800; color: #16a34a; font-size: 1.05rem; margin-bottom: 6px;">₹{p['price']}</div>
                <button style="background: #0f172a; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;" onclick="widgetAddToCart({p['product_id']})">Add to Cart</button>
            </div>
        </div>
        """
    html += "</div>"
    return html

# ==========================================
# 5. FULL ORDER HISTORY
# ==========================================
def get_user_order_history(user_id: int) -> str:
    if user_id == 0: 
        return "Please log in to view your order history."
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT order_id, total_amount, status, DATE_FORMAT(order_date, '%M %d, %Y') as formatted_date 
        FROM orders WHERE user_id = %s ORDER BY order_date DESC LIMIT 3
    """, (user_id,))
    orders = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    
    if not orders: 
        return "You have no recent orders on this account."
    
    html = "<div style='display:flex; flex-direction:column; gap:8px; margin-top:5px;'>"
    for o in orders:
        html += f"""
        <div style="background: rgba(255,255,255,0.6); border-left: 4px solid #6366f1; padding: 10px 12px; border-radius: 0 8px 8px 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <b style="font-size: 0.95rem;">Order #{o['order_id']}</b>
                <span style="background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 6px; font-size: 0.7rem; font-weight: bold; text-transform: uppercase;">{o['status']}</span>
            </div>
            <div style="opacity: 0.8; font-size: 0.8rem;">{o.get('formatted_date', '')}</div>
            <div style="color: #6366f1; font-weight: bold; font-size: 0.95rem; margin-top: 4px;">₹{o['total_amount']}</div>
        </div>
        """
    html += "</div>"
    return html

# ==========================================
# 6. NEW: VIEW CART CONTENTS
# ==========================================
def view_user_cart(user_id: int) -> str:
    if user_id == 0: 
        return "Please log in to view your cart."
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.quantity, p.product_name, p.price, p.image_url
        FROM cart c 
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    """, (user_id,))
    items = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    
    if not items: 
        return "Your cart is currently empty. Ask me to recommend some products!"
        
    total_cart_value = 0
    html = "<p style='margin-bottom: 10px; font-size: 0.95rem;'>Here is what's currently in your cart:</p>"
    html += "<div style='display:flex; flex-direction:column; gap:8px; margin-top:5px;'>"
    
    for item in items:
        img = item.get('image_url', '')
        if not img or not str(img).startswith('http'):
            img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(item.get('product_name', 'Item')))}&background=random&color=fff&size=200"

        item_total = item['price'] * item['quantity']
        total_cart_value += item_total

        html += f"""
        <div style="display: flex; gap: 12px; padding: 10px; background: rgba(255,255,255,0.6); border: 1px solid rgba(0,0,0,0.05); border-radius: 12px; align-items: center;">
            <img src="{img}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;">
            <div style="flex: 1;">
                <h6 style="margin: 0 0 2px 0; font-size: 0.85rem; font-weight: bold;">{item['product_name']}</h6>
                <div style="font-size: 0.8rem; color: #64748b;">Qty: {item['quantity']} × ₹{item['price']}</div>
            </div>
            <div style="font-weight: bold; color: #6366f1; font-size: 0.95rem;">₹{item_total}</div>
        </div>
        """
        
    html += f"""
        <div style="margin-top: 8px; padding-top: 12px; border-top: 2px dashed rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center;">
            <span style="font-weight: bold; color: #475569;">Cart Total:</span>
            <span style="font-weight: 900; font-size: 1.15rem; color: #0f172a;">₹{total_cart_value}</span>
        </div>
        <a href="cart.html" style="display: block; text-align: center; background: linear-gradient(135deg, #6366f1, #a855f7); color: white; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px; box-shadow: 0 4px 10px rgba(99,102,241,0.2);">Proceed to Checkout</a>
    </div>
    """
    return html

# ==========================================
# 7. ADD ITEM TO CART 
# ==========================================
def add_item_to_cart(user_id: int, product_name: str, quantity: int) -> str:
    if user_id == 0: 
        return "Please log in to add items to your cart."
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT product_id, product_name, price FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    product = cursor.fetchone()
    
    if not product:
        cursor.close()
        close_db_connection(conn)
        return f"I couldn't find '{product_name}' in our catalog."
        
    cursor.execute("SELECT quantity FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product['product_id']))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("UPDATE cart SET quantity = quantity + %s WHERE user_id = %s AND product_id = %s", (quantity, user_id, product['product_id']))
    else:
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)", (user_id, product['product_id'], quantity))
        
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    return f"✅ Successfully added **{quantity}x {product['product_name']}** to your cart!<br><br><a href='cart.html' style='color: #6366f1; font-weight: bold; text-decoration: none;'>🛒 Click here to view Cart</a>"

# ==========================================
# 8, 9, 10, 11. ORDER ACTIONS
# ==========================================
def place_order(user_id: int, product_name: str, quantity: int) -> str:
    if user_id == 0: 
        return "You must be logged in to place an order."
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, price, stock FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    product = cursor.fetchone()
    
    if not product: 
        return "Sorry, I couldn't find that product to order."
        
    total = product['price'] * quantity
    cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
    order_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (%s, %s, %s, %s, %s)", (order_id, product['product_id'], product_name, product['price'], quantity))
    cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, product['product_id']))
    
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    return f"Success! Order #{order_id} has been placed."

def check_order_status(user_id: int, order_id: int) -> str:
    if user_id == 0: 
        return "Please log in to track orders."
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT order_id, total_amount, status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    order = cursor.fetchone()
    
    cursor.close()
    close_db_connection(conn)
    
    if order:
        return f"Order #{order_id} is currently **{order['status'].upper()}**." 
    else:
        return "I couldn't find an order with that ID."

def modify_order(user_id: int, order_id: int, product_name: str, new_quantity: int) -> str:
    if user_id == 0: 
        return "Please log in to modify orders."
    if new_quantity < 0: 
        return "Quantity cannot be less than zero."
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
        order = cursor.fetchone()
        
        if not order: 
            return f"Order #{order_id} not found on your account."
        if order['status'] != 'pending': 
            return f"Cannot modify Order #{order_id} because it is already {order['status']}."
            
        cursor.execute("SELECT * FROM order_items WHERE order_id = %s AND product_name LIKE %s", (order_id, f"%{product_name}%"))
        item = cursor.fetchone()
        
        if not item: 
            return f"I couldn't find '{product_name}' in Order #{order_id}."
            
        old_quantity = item['quantity']
        qty_diff = new_quantity - old_quantity
        
        if new_quantity == 0:
            cursor.execute("DELETE FROM order_items WHERE order_id = %s AND product_id = %s", (order_id, item['product_id']))
        else:
            cursor.execute("SELECT stock FROM products WHERE product_id = %s", (item['product_id'],))
            product_data = cursor.fetchone()
            
            if qty_diff > 0 and product_data['stock'] < qty_diff:
                return f"Not enough stock to increase. Only {product_data['stock']} left in warehouse."
            
            cursor.execute("UPDATE order_items SET quantity = %s WHERE order_id = %s AND product_id = %s", (new_quantity, order_id, item['product_id']))
            
        cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (qty_diff, item['product_id']))
        cursor.execute("SELECT SUM(price * quantity) as new_total FROM order_items WHERE order_id = %s", (order_id,))
        new_total_data = cursor.fetchone()
        new_total = new_total_data['new_total'] if new_total_data['new_total'] else 0
        
        if new_total == 0:
            cursor.execute("UPDATE orders SET status = 'cancelled', total_amount = 0 WHERE order_id = %s", (order_id,))
            conn.commit()
            return f"Item removed. Since the order is now empty, Order #{order_id} has been automatically cancelled."
            
        cursor.execute("UPDATE orders SET total_amount = %s WHERE order_id = %s", (new_total, order_id))
        conn.commit()
        return f"Success! Order #{order_id} updated. {product_name} quantity is now {new_quantity}. New Total: ₹{new_total}."
    
    except Exception as e:
        return f"Error modifying order: {str(e)}"
    finally:
        cursor.close()
        close_db_connection(conn)

def cancel_order(user_id: int, order_id: int) -> str:
    if user_id == 0: 
        return "Please log in to cancel orders."
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    result = cursor.fetchone()
    
    if not result: 
        return "I couldn't find an order with that ID."
        
    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (order_id,))
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    return f"Order #{order_id} has been successfully cancelled."

# ==========================================
# MAIN AI PROCESSING ENGINE
# ==========================================
@router.post("")
async def process_chat(request: ChatRequest):
    if not client: 
        return {"response": "AI configuration error. Missing API Key."}
        
    try:
        # Get the actual ID of the logged-in user from the Request
        safe_user_id = request.user_id if request.user_id else 0

        system_prompt = """You are an elite, highly knowledgeable AI shopping assistant for AI Store.
        
        CRITICAL RULES:
        1. ANSWERING QUERIES: If a user asks general questions about products, store policies, technology, or requires help deciding, answer them warmly, fully, and conversationally. Do not be robotic.
        2. ADD TO CART VS ORDER: If a user asks to "add [item] to my cart", use the 'add_item_to_cart' tool. DO NOT use 'place_order' unless they explicitly say "buy", "purchase", or "place order now".
        3. CART CONTENTS: If a user asks "what is in my cart" or "view my cart", you MUST use the 'view_user_cart' tool. Do NOT use order history for this.
        4. TRACKING: If a user asks "where is my order" but does NOT give you an Order ID, use 'get_user_order_history'.
        5. NO HTML: Never write HTML. Python handles UI rendering.
        """

        tools = [
            {"type": "function", "function": {"name": "get_product_recommendation", "description": "Search and recommend products.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "compare_products", "description": "Compare two products.", "parameters": {"type": "object", "properties": {"product_a": {"type": "string"}, "product_b": {"type": "string"}}, "required": ["product_a", "product_b"]}}},
            {"type": "function", "function": {"name": "get_product_details", "description": "Get deep specs for a single product.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "find_cheaper_alternative", "description": "Find cheaper alternatives to a product.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "get_user_order_history", "description": "Get recent orders for the user.", "parameters": {"type": "object", "properties": {}, "required": []}}},
            {"type": "function", "function": {"name": "view_user_cart", "description": "View the items currently inside the user's shopping cart.", "parameters": {"type": "object", "properties": {}, "required": []}}},
            {"type": "function", "function": {"name": "add_item_to_cart", "description": "Add an item to the shopping cart WITHOUT checking out.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["product_name", "quantity"]}}},
            {"type": "function", "function": {"name": "place_order", "description": "Instantly purchase an item.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["product_name", "quantity"]}}},
            {"type": "function", "function": {"name": "check_order_status", "description": "Check status by specific Order ID.", "parameters": {"type": "object", "properties": {"order_id": {"type": "integer"}}, "required": ["order_id"]}}},
            {"type": "function", "function": {"name": "modify_order", "description": "Modify the quantity of a product in an existing order.", "parameters": {"type": "object", "properties": {"order_id": {"type": "integer"}, "product_name": {"type": "string"}, "new_quantity": {"type": "integer"}}, "required": ["order_id", "product_name", "new_quantity"]}}},
            {"type": "function", "function": {"name": "cancel_order", "description": "Cancel a specific order.", "parameters": {"type": "object", "properties": {"order_id": {"type": "integer"}}, "required": ["order_id"]}}}
        ]

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": request.message}]
        response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.2, tools=tools)
        response_message = response.choices[0].message

        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if func_name == "get_product_recommendation": 
                result = get_product_recommendation(args.get("query", "featured"), safe_user_id)
            elif func_name == "compare_products": 
                result = compare_products(args.get("product_a", ""), args.get("product_b", ""), safe_user_id)
            elif func_name == "get_product_details": 
                result = get_product_details(args.get("product_name", ""), safe_user_id)
            elif func_name == "find_cheaper_alternative": 
                result = find_cheaper_alternative(args.get("product_name", ""), safe_user_id)
            elif func_name == "get_user_order_history": 
                result = get_user_order_history(safe_user_id)
            elif func_name == "view_user_cart": 
                result = view_user_cart(safe_user_id)
            elif func_name == "add_item_to_cart": 
                result = add_item_to_cart(safe_user_id, args.get("product_name", ""), args.get("quantity", 1))
            elif func_name == "place_order": 
                result = place_order(safe_user_id, args.get("product_name", ""), args.get("quantity", 1))
            elif func_name == "check_order_status": 
                result = check_order_status(safe_user_id, args.get("order_id", 0))
            elif func_name == "modify_order": 
                result = modify_order(safe_user_id, args.get("order_id", 0), args.get("product_name", ""), args.get("new_quantity", 1))
            elif func_name == "cancel_order": 
                result = cancel_order(safe_user_id, args.get("order_id", 0))
            else: 
                result = "I'm sorry, I couldn't perform that action."
            
            return {"response": result}
        
        else:
            return {"response": response_message.content}
            
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}"}