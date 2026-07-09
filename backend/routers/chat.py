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
def get_product_recommendation(query: str) -> str:
    conn = get_db_connection()
    if not conn: return json.dumps({"error": "Database connection failed."})
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
        
        # SMART FALLBACK: If user types gibberish, return random items instead of returning nothing!
        if not products:
            cursor.execute("SELECT * FROM products ORDER BY RAND() LIMIT 4")
            products = cursor.fetchall()

        for p in products:
            if 'price' in p and p['price'] is not None: p['price'] = float(p['price'])
            if not p.get('image_url') or not str(p['image_url']).startswith('http'):
                p['image_url'] = f"https://ui-avatars.com/api/?name={urllib.parse.quote(p.get('product_name', 'P'))}&background=random&color=fff&size=200&bold=true"
        return json.dumps(products)
    except Exception as e: return json.dumps({"error": str(e)})
    finally: cursor.close(); close_db_connection(conn)

# ==========================================
# 2. COMPARISONS
# ==========================================
def compare_products(product_a: str, product_b: str) -> str:
    conn = get_db_connection()
    if not conn: return json.dumps({"error": "Database connection failed."})
    try:
        cursor = conn.cursor(dictionary=True)
        results = []
        for term in [product_a, product_b]:
            cursor.execute("SELECT * FROM products WHERE product_name LIKE %s OR description LIKE %s LIMIT 1", (f"%{term}%", f"%{term}%"))
            p = cursor.fetchone()
            if p:
                if 'price' in p and p['price'] is not None: p['price'] = float(p['price'])
                if not p.get('image_url') or not str(p['image_url']).startswith('http'):
                    p['image_url'] = f"https://ui-avatars.com/api/?name={urllib.parse.quote(p.get('product_name', 'P'))}&background=random&color=fff&size=200&bold=true"
                results.append(p)
                
        if not results: return json.dumps({"message": f"Could not find any items matching '{product_a}' and '{product_b}'."})
        return json.dumps(results)
    except Exception as e: return json.dumps({"error": str(e)})
    finally: cursor.close(); close_db_connection(conn)

# ==========================================
# 3. DEEP PRODUCT DETAILS
# ==========================================
def get_product_details(product_name: str) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    p = cursor.fetchone()
    cursor.close(); close_db_connection(conn)
    if not p: return json.dumps({"message": f"Could not find details for {product_name}."})
    
    if 'price' in p and p['price'] is not None: p['price'] = float(p['price'])
    if not p.get('image_url') or not str(p['image_url']).startswith('http'):
        p['image_url'] = f"https://ui-avatars.com/api/?name={urllib.parse.quote(p.get('product_name', 'P'))}&background=random&color=fff&size=200&bold=true"
    return json.dumps(p)

# ==========================================
# 4. FIND CHEAPER ALTERNATIVES
# ==========================================
def find_cheaper_alternative(product_name: str) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT price, category_name FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    target = cursor.fetchone()
    
    if not target: 
        cursor.close(); close_db_connection(conn)
        return json.dumps({"message": "Original product not found to compare."})

    cursor.execute("SELECT * FROM products WHERE category_name = %s AND price < %s ORDER BY price DESC LIMIT 3", (target['category_name'], target['price']))
    alts = cursor.fetchall()
    cursor.close(); close_db_connection(conn)
    
    if not alts: return json.dumps({"message": f"No cheaper alternatives found in {target['category_name']}."})
    
    for p in alts:
        if 'price' in p and p['price'] is not None: p['price'] = float(p['price'])
        if not p.get('image_url') or not str(p['image_url']).startswith('http'):
            p['image_url'] = f"https://ui-avatars.com/api/?name={urllib.parse.quote(p.get('product_name', 'P'))}&background=random&color=fff&size=200&bold=true"
    return json.dumps(alts)

# ==========================================
# 5. FULL ORDER HISTORY
# ==========================================
def get_user_order_history(user_id: int) -> str:
    if user_id == 0: return json.dumps({"message": "Please log in to view orders."})
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT order_id, total_amount, status, DATE_FORMAT(order_date, '%M %d, %Y') as formatted_date 
        FROM orders WHERE user_id = %s ORDER BY order_date DESC LIMIT 3
    """, (user_id,))
    orders = cursor.fetchall()
    cursor.close(); close_db_connection(conn)
    
    if not orders: return json.dumps({"message": "You have no recent orders."})
    for o in orders:
        if 'total_amount' in o and o['total_amount'] is not None: o['total_amount'] = float(o['total_amount'])
    return json.dumps(orders)

# ==========================================
# 6, 7, 8. EXISTING ORDER ACTIONS
# ==========================================
def place_order(user_id: int, product_name: str, quantity: int) -> str:
    if user_id == 0: return json.dumps({"message": "You must log in to place an order."})
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, price, stock FROM products WHERE product_name LIKE %s", (f"%{product_name}%",))
    product = cursor.fetchone()
    if not product: return json.dumps({"message": "Product not found."})
    total = product['price'] * quantity
    cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
    order_id = cursor.lastrowid
    cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (%s, %s, %s, %s, %s)", (order_id, product['product_id'], product_name, product['price'], quantity))
    cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, product['product_id']))
    conn.commit(); cursor.close(); close_db_connection(conn)
    return json.dumps({"message": f"Order #{order_id} placed successfully."})

def check_order_status(user_id: int, order_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT order_id, total_amount, status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    order = cursor.fetchone()
    cursor.close(); close_db_connection(conn)
    if not order: return json.dumps({"message": "Order not found."})
    return json.dumps({"message": f"Order #{order_id} Status: {order['status']} (Total: ₹{order['total_amount']})"})

def cancel_order(user_id: int, order_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    result = cursor.fetchone()
    if not result: return json.dumps({"message": "Order not found."})
    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (order_id,))
    conn.commit(); cursor.close(); close_db_connection(conn)
    return json.dumps({"message": f"Order #{order_id} cancelled successfully."})


# ==========================================
# MAIN AI ENGINE (TWO-STAGE + NO GUESSING)
# ==========================================
@router.post("")
async def process_chat(request: ChatRequest):
    if not client: return {"response": "AI config error. Missing API Key."}
    try:
        safe_user_id = request.user_id if request.user_id else 0

        # STAGE 1: Determine tool to use, but NEVER GUESS names!
        stage1_prompt = """You are an AI assistant for an E-commerce store. 
        Determine the user's intent and call the correct tool.
        
        CRITICAL RULES:
        1. If the user asks to COMPARE products, but does not explicitly name TWO real products, DO NOT guess (never use "Product 1"). Ask them which products they want to compare!
        2. If the user asks for details but doesn't name a product, ask them.
        3. Do not format the output yet. Just call the tool or reply in text."""

        tools = [
            {"type": "function", "function": {"name": "get_product_recommendation", "description": "Recommend products.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "compare_products", "description": "Compare two specific products.", "parameters": {"type": "object", "properties": {"product_a": {"type": "string"}, "product_b": {"type": "string"}}, "required": ["product_a", "product_b"]}}},
            {"type": "function", "function": {"name": "get_product_details", "description": "Get specs for a specific product.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "find_cheaper_alternative", "description": "Find cheaper alternatives.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "get_user_order_history", "description": "Get recent orders.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}}},
            {"type": "function", "function": {"name": "place_order", "description": "Place an order.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "product_name": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["user_id", "product_name", "quantity"]}}},
            {"type": "function", "function": {"name": "check_order_status", "description": "Check order status.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "order_id": {"type": "integer"}}, "required": ["user_id", "order_id"]}}},
            {"type": "function", "function": {"name": "cancel_order", "description": "Cancel an order.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "order_id": {"type": "integer"}}, "required": ["user_id", "order_id"]}}}
        ]

        messages = [{"role": "system", "content": stage1_prompt}, {"role": "user", "content": request.message}]
        response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.1, tools=tools)
        response_message = response.choices[0].message

        if response_message.tool_calls:
            messages.append({"role": "assistant", "content": response_message.content, "tool_calls": [{"id": t.id, "type": t.type, "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in response_message.tool_calls]})
            
            tool_call = response_message.tool_calls[0]
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if func_name == "get_product_recommendation": result = get_product_recommendation(args.get("query", "featured"))
            elif func_name == "compare_products": result = compare_products(args["product_a"], args["product_b"])
            elif func_name == "get_product_details": result = get_product_details(args["product_name"])
            elif func_name == "find_cheaper_alternative": result = find_cheaper_alternative(args["product_name"])
            elif func_name == "get_user_order_history": result = get_user_order_history(args.get("user_id", safe_user_id))
            elif func_name == "place_order": result = place_order(args.get("user_id", safe_user_id), args["product_name"], args.get("quantity", 1))
            elif func_name == "check_order_status": result = check_order_status(args.get("user_id", safe_user_id), args["order_id"])
            elif func_name == "cancel_order": result = cancel_order(args.get("user_id", safe_user_id), args["order_id"])
            else: result = json.dumps({"error": "Unknown function"})
            
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": func_name, "content": str(result)})
            
            # STAGE 2: Format the Data. Transparent styles used so they look good INSIDE the chat bubble!
            stage2_prompt = f"""You are an elite AI shopping assistant. You just received raw data from the database.
            
            CRITICAL RULES:
            1. If the database returned an error, a plain text message, or said "Could not find matches", DO NOT USE HTML. Just apologize and explain the issue in plain text.
            2. NEVER invent fake products like "Product 1". Only output the actual JSON data provided.
            
            TEMPLATE 1 (For recommendations, alternatives, comparisons):
            <div style="display: flex; gap: 10px; margin-top: 10px; align-items: center; border-bottom: 1px solid rgba(0,0,0,0.1); padding-bottom: 10px;">
                <img src="[image_url]" style="width: 60px; height: 60px; object-fit: cover; border-radius: 8px; flex-shrink: 0;">
                <div style="flex: 1;">
                    <h6 style="font-weight: bold; font-size: 0.95rem; margin: 0 0 4px 0; color: inherit;">[product_name]</h6>
                    <div style="font-weight: 800; font-size: 1.05rem; margin-bottom: 6px;">₹[price]</div>
                    <button style="background: #0f172a; color: white; border: none; padding: 5px 14px; border-radius: 6px; font-size: 0.8rem; cursor: pointer;" onclick="apiAddToCart({safe_user_id}, [product_id]).then(() => {{ if(typeof showToast === 'function') showToast('Added!', 'success'); if(typeof updateCartCount === 'function') updateCartCount(); }})">Add to Cart</button>
                </div>
            </div>

            TEMPLATE 2 (For deep product details):
            <div style="margin-top: 10px;">
                <img src="[image_url]" style="width: 100%; height: 160px; object-fit: cover; border-radius: 10px; margin-bottom: 10px;">
                <div style="margin-bottom: 8px;">
                    <span style="background: rgba(0,0,0,0.05); padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: bold;">[category_name]</span>
                </div>
                <h5 style="font-weight: bold; margin: 0 0 5px 0;">[product_name]</h5>
                <p style="font-size: 0.85rem; opacity: 0.9; line-height: 1.4; margin-bottom: 10px;">[description]</p>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: bold; font-size: 1.2rem;">₹[price]</span>
                    <button style="background: #0f172a; color: white; border: none; padding: 6px 16px; border-radius: 8px; font-weight: bold; cursor: pointer;" onclick="apiAddToCart({safe_user_id}, [product_id]).then(() => {{ if(typeof showToast === 'function') showToast('Added!', 'success'); if(typeof updateCartCount === 'function') updateCartCount(); }})">Buy Now</button>
                </div>
            </div>
            """
            
            messages[0] = {"role": "system", "content": stage2_prompt}
            second_response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.1)
            return {"response": second_response.choices[0].message.content}
            
        else:
            return {"response": response_message.content}
            
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}"}