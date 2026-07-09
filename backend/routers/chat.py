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
        
        # SMART FALLBACK: If user types gibberish (e.g., "productsa"), return random items instead of crashing
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
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, price, stock FROM products WHERE product_name LIKE %s", (f"%{product_name}%",))
    product = cursor.fetchone()
    if not product: return "Product not found."
    total = product['price'] * quantity
    cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
    order_id = cursor.lastrowid
    cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (%s, %s, %s, %s, %s)", (order_id, product['product_id'], product_name, product['price'], quantity))
    cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, product['product_id']))
    conn.commit(); cursor.close(); close_db_connection(conn)
    return f"Order #{order_id} placed successfully."

def check_order_status(user_id: int, order_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT order_id, total_amount, status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    order = cursor.fetchone()
    cursor.close(); close_db_connection(conn)
    return f"Order #{order_id} Status: {order['status']} (Total: ₹{order['total_amount']})" if order else "Order not found."

def cancel_order(user_id: int, order_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    result = cursor.fetchone()
    if not result: return "Order not found."
    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (order_id,))
    conn.commit(); cursor.close(); close_db_connection(conn)
    return f"Order #{order_id} cancelled successfully."


# ==========================================
# MAIN AI PROCESSING ENGINE (TWO-STAGE FIX)
# ==========================================
@router.post("")
async def process_chat(request: ChatRequest):
    if not client: return {"response": "AI config error. Missing API Key."}
    try:
        safe_user_id = request.user_id if request.user_id else 0

        # STAGE 1 PROMPT: Extremely simple so Groq doesn't crash during tool usage.
        stage1_prompt = """You are an AI assistant for an E-commerce store. 
        Determine the user's intent and call the correct tool to search the database.
        Do NOT try to format the output yet. Just call the tool."""

        tools = [
            {"type": "function", "function": {"name": "get_product_recommendation", "description": "Recommend products. If the request is broad (like 'products' or 'stuff'), pass 'featured' as the query.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "compare_products", "description": "Compare two products.", "parameters": {"type": "object", "properties": {"product_a": {"type": "string"}, "product_b": {"type": "string"}}, "required": ["product_a", "product_b"]}}},
            {"type": "function", "function": {"name": "get_product_details", "description": "Get detailed specs for a specific product.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "find_cheaper_alternative", "description": "Find cheaper alternatives for a specific product.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "get_user_order_history", "description": "Get the user's recent orders.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]}}},
            {"type": "function", "function": {"name": "place_order", "description": "Place an order.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "product_name": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["user_id", "product_name", "quantity"]}}},
            {"type": "function", "function": {"name": "check_order_status", "description": "Check order status.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "order_id": {"type": "integer"}}, "required": ["user_id", "order_id"]}}},
            {"type": "function", "function": {"name": "cancel_order", "description": "Cancel an order.", "parameters": {"type": "object", "properties": {"user_id": {"type": "integer"}, "order_id": {"type": "integer"}}, "required": ["user_id", "order_id"]}}}
        ]

        # First request to Groq (Just to get the tool call)
        messages = [{"role": "system", "content": stage1_prompt}, {"role": "user", "content": request.message}]
        response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.1, tools=tools)
        response_message = response.choices[0].message

        if response_message.tool_calls:
            # 1. Append the tool call to the chat history
            messages.append({"role": "assistant", "content": response_message.content, "tool_calls": [{"id": t.id, "type": t.type, "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in response_message.tool_calls]})
            
            tool_call = response_message.tool_calls[0]
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            # 2. Execute the Python Function
            if func_name == "get_product_recommendation": result = get_product_recommendation(args.get("query", "featured"))
            elif func_name == "compare_products": result = compare_products(args["product_a"], args["product_b"])
            elif func_name == "get_product_details": result = get_product_details(args["product_name"])
            elif func_name == "find_cheaper_alternative": result = find_cheaper_alternative(args["product_name"])
            elif func_name == "get_user_order_history": result = get_user_order_history(args.get("user_id", safe_user_id))
            elif func_name == "place_order": result = place_order(args.get("user_id", safe_user_id), args["product_name"], args.get("quantity", 1))
            elif func_name == "check_order_status": result = check_order_status(args.get("user_id", safe_user_id), args["order_id"])
            elif func_name == "cancel_order": result = cancel_order(args.get("user_id", safe_user_id), args["order_id"])
            else: result = json.dumps({"error": "Unknown function"})
            
            # 3. Append the database result
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": func_name, "content": str(result)})
            
            # STAGE 2 PROMPT: Now that we have data, forcefully inject the UI templates!
            stage2_prompt = f"""You are an elite AI shopping assistant. You just received raw data from the database.
            You MUST format this data into a beautiful UI for the user using the HTML templates below.
            
            CRITICAL RULES:
            1. NEVER output markdown blocks (like ```html). Just output raw HTML.
            2. Replace bracketed placeholders (like [product_name]) with the real data. 
            3. If the data is empty or says 'error', apologize normally without using HTML.
            
            TEMPLATE 1 (For single recommendations, comparisons, or alternatives):
            <div style="display: flex; gap: 15px; background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 15px; margin-top: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); max-width: 400px; align-items: center;">
                <img src="[image_url]" style="width: 70px; height: 70px; object-fit: cover; border-radius: 12px; flex-shrink: 0;">
                <div style="flex: 1;">
                    <h6 style="font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 4px;">[product_name]</h6>
                    <div style="font-weight: 800; color: #6366f1; font-size: 1.1rem; margin-bottom: 8px;">₹[price]</div>
                    <button style="background: #0f172a; color: white; border: none; padding: 6px 14px; border-radius: 8px; font-size: 0.8rem; cursor: pointer;" onclick="apiAddToCart({safe_user_id}, [product_id]).then(() => showToast('Added to Cart!', 'success'))">Add to Cart</button>
                </div>
            </div>

            TEMPLATE 2 (For deep product details):
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 15px; margin-top: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
                <img src="[image_url]" style="width: 100%; height: 180px; object-fit: cover; border-radius: 12px; margin-bottom: 15px;">
                <span style="background: #e0e7ff; color: #4338ca; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: bold;">[category_name]</span>
                <h5 style="font-weight: 800; color: #0f172a; margin: 12px 0 8px 0;">[product_name]</h5>
                <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 15px; line-height: 1.5;">[description]</p>
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #f1f5f9; padding-top: 15px;">
                    <span style="font-weight: 900; color: #6366f1; font-size: 1.3rem;">₹[price]</span>
                    <button style="background: linear-gradient(135deg, #6366f1, #a855f7); color: white; border: none; padding: 10px 20px; border-radius: 10px; font-weight: bold; cursor: pointer;" onclick="apiAddToCart({safe_user_id}, [product_id]).then(() => showToast('Added!', 'success'))">Buy Now</button>
                </div>
            </div>

            TEMPLATE 3 (For Order Tracking):
            <div style="background: white; border-left: 4px solid #6366f1; padding: 12px 15px; margin-top: 10px; border-radius: 0 12px 12px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <b style="color: #0f172a;">Order #[order_id]</b>
                    <span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 8px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;">[status]</span>
                </div>
                <div style="color: #64748b; font-size: 0.85rem;">Date: [formatted_date]</div>
                <div style="color: #6366f1; font-weight: bold; font-size: 0.95rem; margin-top: 5px;">Total: ₹[total_amount]</div>
            </div>
            """
            
            # Overwrite the original system prompt so it ONLY focuses on UI generation now!
            messages[0] = {"role": "system", "content": stage2_prompt}

            # Second request to Groq (Generate final text/HTML)
            second_response = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, temperature=0.1)
            return {"response": second_response.choices[0].message.content}
            
        else:
            return {"response": response_message.content}
            
    except Exception as e:
        return {"response": f"An error occurred: {str(e)}"}