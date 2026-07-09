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
# 1. RECOMMENDATIONS (Python Native Rendering)
# ==========================================
def get_product_recommendation(query: str, user_id: int) -> str:
    conn = get_db_connection()
    if not conn: return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    
    price_limit = None
    match = re.search(r'under\s*(\d+)', query, re.IGNORECASE)
    if match: price_limit = int(match.group(1))
    
    category_map = {"phone": "Electronics", "laptop": "Laptops", "computer": "Laptops", "shoe": "Clothing", "book": "Books"}
    detected_category = next((v for k, v in category_map.items() if k in query.lower()), None)
            
    if any(word in query.lower() for word in ["latest", "new"]): sql = "SELECT * FROM products ORDER BY product_id DESC LIMIT 5"; params = ()
    elif price_limit and detected_category: sql = "SELECT * FROM products WHERE price <= %s AND category_name = %s LIMIT 5"; params = (price_limit, detected_category)
    elif price_limit: sql = "SELECT * FROM products WHERE price <= %s LIMIT 5"; params = (price_limit,)
    elif detected_category: sql = "SELECT * FROM products WHERE category_name = %s LIMIT 5"; params = (detected_category,)
    elif any(word in query.lower() for word in ["recommend", "explore", "products", "all", "show", "featured"]): sql = "SELECT * FROM products ORDER BY RAND() LIMIT 4"; params = ()
    else: sql = "SELECT * FROM products WHERE product_name LIKE %s OR description LIKE %s LIMIT 5"; params = (f"%{query}%", f"%{query}%")
    
    try:
        cursor.execute(sql, params)
        products = cursor.fetchall()
        
        # SMART FALLBACK: If nothing matches exactly, just grab 4 random items so the chat never feels empty
        if not products:
            cursor.execute("SELECT * FROM products ORDER BY RAND() LIMIT 4")
            products = cursor.fetchall()

        if not products: return "Sorry, the store is currently empty!"

        # PYTHON BUILDS THE HTML (AI CANNOT MESS THIS UP)
        html = "<p style='margin-bottom: 10px; color: #475569;'>Here are some excellent choices I found for you:</p>"
        html += "<div style='display:flex; flex-direction:column; gap:10px;'>"
        for p in products:
            img = p.get('image_url', '')
            if not img or not str(img).startswith('http'):
                img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(p.get('product_name', 'P'))}&background=random&color=fff&size=200&bold=true"
            
            html += f"""
            <div style="display: flex; gap: 15px; background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); max-width: 400px; align-items: center;">
                <img src="{img}" style="width: 70px; height: 70px; object-fit: cover; border-radius: 12px; flex-shrink: 0;">
                <div style="flex: 1;">
                    <h6 style="font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 4px; line-height: 1.2;">{p['product_name']}</h6>
                    <div style="font-weight: 800; color: #6366f1; font-size: 1.1rem; margin-bottom: 8px;">₹{p['price']}</div>
                    <button style="background: #0f172a; color: white; border: none; padding: 6px 14px; border-radius: 8px; font-size: 0.8rem; cursor: pointer;" onclick="apiAddToCart({user_id}, {p['product_id']}).then(() => {{ if(typeof showToast === 'function') showToast('Added to Cart!', 'success'); if(typeof updateCartCount === 'function') updateCartCount(); }})">Add to Cart</button>
                </div>
            </div>
            """
        html += "</div>"
        return html
    except Exception as e: return f"Error retrieving products: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)

# ==========================================
# 2. COMPARISONS (Python Native Rendering)
# ==========================================
def compare_products(product_a: str, product_b: str, user_id: int) -> str:
    conn = get_db_connection()
    if not conn: return "Database connection failed."
    try:
        cursor = conn.cursor(dictionary=True)
        results = []
        for term in [product_a, product_b]:
            cursor.execute("SELECT * FROM products WHERE product_name LIKE %s OR description LIKE %s LIMIT 1", (f"%{term}%", f"%{term}%"))
            p = cursor.fetchone()
            if p: results.append(p)
                
        if not results: return f"Could not find exact matches for '{product_a}' and '{product_b}' to compare."

        html = "<p style='margin-bottom: 10px; color: #475569;'>Here is the side-by-side comparison:</p>"
        html += "<div style='display: flex; gap: 15px; overflow-x: auto; padding: 10px 0; max-width: 100%;'>"
        for p in results:
            img = p.get('image_url', '')
            if not img or not str(img).startswith('http'):
                img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(p.get('product_name', 'P'))}&background=random&color=fff&size=200&bold=true"
            html += f"""
            <div style="flex: 1; min-width: 180px; background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                <img src="{img}" style="width: 90px; height: 90px; object-fit: cover; border-radius: 12px; margin-bottom: 12px;">
                <h6 style="font-size: 0.9rem; font-weight: bold; color: #0f172a; margin-bottom: 5px; height: 35px; overflow: hidden;">{p['product_name']}</h6>
                <p style="color: #6366f1; font-weight: 800; font-size: 1.2rem; margin-bottom: 10px;">₹{p['price']}</p>
                <div style="font-size: 0.8rem; color: #64748b; margin-bottom: 15px; text-align: left; background: #f8fafc; padding: 10px; border-radius: 8px;">
                    <b>Category:</b> {p.get('category_name', 'Unknown')}
                </div>
                <button style="background: linear-gradient(135deg, #6366f1, #a855f7); color: white; border: none; padding: 10px 15px; border-radius: 10px; width: 100%; cursor: pointer;" onclick="apiAddToCart({user_id}, {p['product_id']}).then(() => {{ if(typeof showToast === 'function') showToast('Added to Cart!', 'success'); if(typeof updateCartCount === 'function') updateCartCount(); }})">Add to Cart</button>
            </div>
            """
        html += "</div>"
        return html
    except Exception as e: return f"Error during comparison: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)

# ==========================================
# 3. DEEP PRODUCT DETAILS
# ==========================================
def get_product_details(product_name: str, user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    p = cursor.fetchone()
    cursor.close(); close_db_connection(conn)
    if not p: return f"I couldn't find a product matching '{product_name}' in our catalog."
    
    img = p.get('image_url', '')
    if not img or not str(img).startswith('http'):
        img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(p.get('product_name', 'P'))}&background=random&color=fff&size=200&bold=true"
    
    html = f"""
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 15px; margin-top: 5px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <img src="{img}" style="width: 100%; height: 180px; object-fit: cover; border-radius: 12px; margin-bottom: 15px;">
        <span style="background: #e0e7ff; color: #4338ca; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold;">{p.get('category_name', 'General')}</span>
        <span style="background: #dcfce7; color: #166534; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold; margin-left: 5px;">{p.get('stock', 0)} in stock</span>
        <h5 style="font-weight: 800; color: #0f172a; margin: 12px 0 8px 0;">{p['product_name']}</h5>
        <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 15px; line-height: 1.5;">{p.get('description', 'A premium product from AI Store.')}</p>
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 15px;">
            <span style="font-weight: 900; color: #6366f1; font-size: 1.3rem;">₹{p['price']}</span>
            <button style="background: linear-gradient(135deg, #6366f1, #a855f7); color: white; border: none; padding: 10px 20px; border-radius: 10px; font-weight: bold; cursor: pointer;" onclick="apiAddToCart({user_id}, {p['product_id']}).then(() => {{ if(typeof showToast === 'function') showToast('Added!', 'success'); if(typeof updateCartCount === 'function') updateCartCount(); }})">Buy Now</button>
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
        cursor.close(); close_db_connection(conn)
        return "I couldn't find the original product to compare against."

    cursor.execute("SELECT * FROM products WHERE category_name = %s AND price < %s ORDER BY price DESC LIMIT 3", (target['category_name'], target['price']))
    alts = cursor.fetchall()
    cursor.close(); close_db_connection(conn)
    
    if not alts: return f"There are currently no cheaper alternatives in the {target['category_name']} category."
    
    html = "<p style='margin-bottom: 10px; color: #475569;'>Here are some great budget-friendly alternatives:</p>"
    html += "<div style='display:flex; flex-direction:column; gap:10px;'>"
    for p in alts:
        img = p.get('image_url', '')
        if not img or not str(img).startswith('http'):
            img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(p.get('product_name', 'P'))}&background=random&color=fff&size=200&bold=true"
        html += f"""
        <div style="display: flex; gap: 15px; background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); max-width: 400px; align-items: center;">
            <img src="{img}" style="width: 70px; height: 70px; object-fit: cover; border-radius: 12px; flex-shrink: 0;">
            <div style="flex: 1;">
                <h6 style="font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 4px; line-height: 1.2;">{p['product_name']}</h6>
                <div style="font-weight: 800; color: #16a34a; font-size: 1.1rem; margin-bottom: 8px;">₹{p['price']}</div>
                <button style="background: #0f172a; color: white; border: none; padding: 6px 14px; border-radius: 8px; font-size: 0.8rem; cursor: pointer;" onclick="apiAddToCart({user_id}, {p['product_id']}).then(() => {{ if(typeof showToast === 'function') showToast('Added to Cart!', 'success'); if(typeof updateCartCount === 'function') updateCartCount(); }})">Add to Cart</button>
            </div>
        </div>
        """
    html += "</div>"
    return html

# ==========================================
# 5. FULL ORDER HISTORY
# ==========================================
def get_user_order_history(user_id: int) -> str:
    if user_id == 0: return "Please log in to view your order history."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT order_id, total_amount, status, DATE_FORMAT(order_date, '%M %d, %Y') as formatted_date 
        FROM orders WHERE user_id = %s ORDER BY order_date DESC LIMIT 3
    """, (user_id,))
    orders = cursor.fetchall()
    cursor.close(); close_db_connection(conn)
    
    if not orders: return "You have no recent orders on this account."
    
    html = "<p style='margin-bottom: 10px; color: #475569;'>Here are your most recent orders:</p>"
    for o in orders:
        html += f"""
        <div style="background: white; border-left: 4px solid #6366f1; padding: 12px 15px; margin-top: 10px; border-radius: 0 12px 12px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <b style="color: #0f172a;">Order #{o['order_id']}</b>
                <span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 8px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;">{o['status']}</span>
            </div>
            <div style="color: #64748b; font-size: 0.85rem;">Date: {o.get('formatted_date', '')}</div>
            <div style="color: #6366f1; font-weight: bold; font-size: 0.95rem; margin-top: 5px;">Total: ₹{o['total_amount']}</div>
        </div>
        """
    return html

# ==========================================
# 6, 7, 8. EXISTING ORDER ACTIONS
# ==========================================
def place_order(user_id: int, product_name: str, quantity: int) -> str:
    if user_id == 0: return "You must be logged in to place an order."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, price, stock FROM products WHERE product_name LIKE %s", (f"%{product_name}%",))
    product = cursor.fetchone()
    if not product: return "Sorry, I couldn't find that product to order."
    if product['stock'] < quantity: return f"We don't have enough stock for {quantity} items."
    total = product['price'] * quantity
    cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
    order_id = cursor.lastrowid
    cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (%s, %s, %s, %s, %s)", (order_id, product['product_id'], product_name, product['price'], quantity))
    cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, product['product_id']))
    conn.commit(); cursor.close(); close_db_connection(conn)
    return f"Success! Order #{order_id} has been placed."

def check_order_status(user_id: int, order_id: int) -> str:
    if user_id == 0: return "Please log in to track orders."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT order_id, total_amount, status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    order = cursor.fetchone()
    cursor.close(); close_db_connection(conn)
    return f"Order #{order_id} is currently **{order['status'].upper()}**." if order else "I couldn't find an order with that ID."

def cancel_order(user_id: int, order_id: int) -> str:
    if user_id == 0: return "Please log in to cancel orders."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    result = cursor.fetchone()
    if not result: return "I couldn't find an order with that ID to cancel."
    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (order_id,))
    conn.commit(); cursor.close(); close_db_connection(conn)
    return f"Order #{order_id} has been successfully cancelled."


# ==========================================
# MAIN AI PROCESSING ENGINE (SINGLE-STAGE FAST EXECUTION)
# ==========================================
@router.post("")
async def process_chat(request: ChatRequest):
    if not client: return {"response": "AI configuration error. Missing API Key."}
    try:
        safe_user_id = request.user_id if request.user_id else 0

        # The AI's ONLY job is to select the tool. Python handles all UI rendering natively.
        system_prompt = """You are an elite AI shopping assistant for AI Store. 
        Determine what the user wants to do, and call the correct tool.
        DO NOT attempt to format UI or HTML. The system handles all UI automatically.
        If the user says 'hello', greets you, or asks a general non-store question, reply naturally and warmly."""

        tools = [
            {"type": "function", "function": {"name": "get_product_recommendation", "description": "Search and recommend products.", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Search keyword. Use 'featured' if general."}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "compare_products", "description": "Compare two products.", "parameters": {"type": "object", "properties": {"product_a": {"type": "string"}, "product_b": {"type": "string"}}, "required": ["product_a", "product_b"]}}},
            {"type": "function", "function": {"name": "get_product_details", "description": "Get deep specs for a single product.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "find_cheaper_alternative", "description": "Find cheaper alternatives.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "get_user_order_history", "description": "Get recent orders.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}}},
            {"type": "function", "function": {"name": "place_order", "description": "Place an order.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "product_name": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["user_id", "product_name", "quantity"]}}},
            {"type": "function", "function": {"name": "check_order_status", "description": "Check order status.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "order_id": {"type": "integer"}}, "required": ["user_id", "order_id"]}}},
            {"type": "function", "function": {"name": "cancel_order", "description": "Cancel an order.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "order_id": {"type": "integer"}}, "required": ["user_id", "order_id"]}}}
        ]

        # ONE Single Call to Groq (Lightning Fast)
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": request.message}]
        response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.1, tools=tools)
        response_message = response.choices[0].message

        # If Groq decides a Tool is needed, Python executes it and returns the HTML immediately!
        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if func_name == "get_product_recommendation": result = get_product_recommendation(args.get("query", "featured"), safe_user_id)
            elif func_name == "compare_products": result = compare_products(args["product_a"], args["product_b"], safe_user_id)
            elif func_name == "get_product_details": result = get_product_details(args["product_name"], safe_user_id)
            elif func_name == "find_cheaper_alternative": result = find_cheaper_alternative(args["product_name"], safe_user_id)
            elif func_name == "get_user_order_history": result = get_user_order_history(args.get("user_id", safe_user_id))
            elif func_name == "place_order": result = place_order(args.get("user_id", safe_user_id), args["product_name"], args.get("quantity", 1))
            elif func_name == "check_order_status": result = check_order_status(args.get("user_id", safe_user_id), args["order_id"])
            elif func_name == "cancel_order": result = cancel_order(args.get("user_id", safe_user_id), args["order_id"])
            else: result = "I'm sorry, I couldn't perform that action."
            
            # Send the perfectly formatted Python HTML straight back to the widget!
            return {"response": result}
        
        # If Groq just wants to say "Hello!", send the text back.
        else:
            return {"response": response_message.content}
            
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}"}