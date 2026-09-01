from fastapi import APIRouter
import os
import json
import urllib.parse
from groq import Groq
from backend.database import get_db_connection, close_db_connection
from backend.models import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["AI Agent"])

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

# =====================================================================
# 1. DETERMINISTIC UI & DATABASE TOOLS (Consistent HTML Locked In)
# =====================================================================

def get_product_recommendation(search_term: str = None, max_price: int = None, category: str = None, user_id: int = 0) -> str:
    conn = get_db_connection()
    if not conn: return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    
    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if search_term and search_term.lower() not in ["recommend", "explore", "products", "all", "show", "featured"]:
        sql += " AND (product_name LIKE %s OR description LIKE %s)"
        params.extend([f"%{search_term}%", f"%{search_term}%"])
    if max_price:
        sql += " AND price <= %s"
        params.append(max_price)
    if category:
        sql += " AND category_name = %s"
        params.append(category)
        
    sql += " LIMIT 5" if params else " ORDER BY RAND() LIMIT 4"
    
    try:
        cursor.execute(sql, tuple(params))
        products = cursor.fetchall()
        
        if not products:
            cursor.execute("SELECT * FROM products ORDER BY RAND() LIMIT 4")
            products = cursor.fetchall()
            
        if not products: return "Sorry, our store catalog is currently empty!"

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
    except Exception as e: return f"Error retrieving products: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)

def compare_products(product_a: str, product_b: str, user_id: int = 0) -> str:
    conn = get_db_connection()
    if not conn: return "Database connection failed."
    cursor = conn.cursor(dictionary=True)
    try:
        results = []
        for term in [product_a, product_b]:
            if not term: continue
            cursor.execute("SELECT * FROM products WHERE product_name LIKE %s OR description LIKE %s LIMIT 1", (f"%{term}%", f"%{term}%"))
            p = cursor.fetchone()
            if p: results.append(p)
                
        if len(results) < 2: return f"I couldn't find exact matches to compare both items."

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
    except Exception as e: return f"Error during comparison: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)

def get_product_details(product_name: str, user_id: int = 0) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    p = cursor.fetchone()
    cursor.close(); close_db_connection(conn)
    
    if not p: return f"I couldn't find a product matching '{product_name}' in our catalog."
    
    img = p.get('image_url', '')
    if not img or not str(img).startswith('http'):
        img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(p.get('product_name', 'Item')))}&background=random&color=fff&size=200"
    
    return f"""
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

def find_cheaper_alternative(product_name: str, user_id: int = 0) -> str:
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
    
    if not alts: return f"There are no cheaper alternatives in the {target['category_name']} category right now."
    
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

def get_user_order_history(user_id: int) -> str:
    if user_id == 0: return "Please log in to view your order history."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.total_amount, o.status, DATE_FORMAT(o.order_date, '%M %d, %Y') as formatted_date,
               GROUP_CONCAT(oi.product_name SEPARATOR ', ') as items_summary
        FROM orders o
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.user_id = %s GROUP BY o.order_id ORDER BY o.order_date DESC LIMIT 3
    """, (user_id,))
    orders = cursor.fetchall()
    cursor.close(); close_db_connection(conn)
    
    if not orders: return "You have no recent orders on this account."
    
    html = "<div style='display:flex; flex-direction:column; gap:8px; margin-top:5px;'>"
    for o in orders:
        html += f"""
        <div style="background: rgba(255,255,255,0.6); border-left: 4px solid #6366f1; padding: 10px 12px; border-radius: 0 8px 8px 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <b style="font-size: 0.95rem;">Order #{o['order_id']}</b>
                <span style="background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 6px; font-size: 0.7rem; font-weight: bold; text-transform: uppercase;">{o['status']}</span>
            </div>
            <div style="font-size: 0.8rem; color: #475569; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">Items: {o.get('items_summary', 'Standard items')}</div>
            <div style="opacity: 0.8; font-size: 0.8rem; margin-top: 2px;">{o.get('formatted_date', '')}</div>
            <div style="color: #6366f1; font-weight: bold; font-size: 0.95rem; margin-top: 4px;">₹{o['total_amount']}</div>
        </div>
        """
    html += "</div>"
    return html

def view_user_cart(user_id: int) -> str:
    if user_id == 0: return "Please log in to view your cart."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT c.quantity, p.product_name, p.price, p.image_url FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s", (user_id,))
    items = cursor.fetchall()
    cursor.close(); close_db_connection(conn)
    
    if not items: return "Your cart is currently empty. Ask me to recommend some products!"
    total_cart_value = sum((item['price'] * item['quantity']) for item in items)
    
    html = "<p style='margin-bottom: 10px; font-size: 0.95rem;'>Here is what's currently in your cart:</p><div style='display:flex; flex-direction:column; gap:8px; margin-top:5px;'>"
    for item in items:
        img = item.get('image_url', '')
        if not img or not str(img).startswith('http'):
            img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(item.get('product_name', 'Item')))}&background=random&color=fff&size=200"

        html += f"""
        <div style="display: flex; gap: 12px; padding: 10px; background: rgba(255,255,255,0.6); border: 1px solid rgba(0,0,0,0.05); border-radius: 12px; align-items: center;">
            <img src="{img}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 8px;">
            <div style="flex: 1;">
                <h6 style="margin: 0 0 2px 0; font-size: 0.85rem; font-weight: bold;">{item['product_name']}</h6>
                <div style="font-size: 0.8rem; color: #64748b;">Qty: {item['quantity']} × ₹{item['price']}</div>
            </div>
            <div style="font-weight: bold; color: #6366f1; font-size: 0.95rem;">₹{item['price'] * item['quantity']}</div>
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

def add_item_to_cart(user_id: int, product_name: str, quantity: int = 1) -> str:
    if user_id == 0: return "Please log in to add items to your cart."
    if not product_name: return "I didn't catch the name of the product you want to add."
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, product_name FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    product = cursor.fetchone()
    if not product:
        cursor.close(); close_db_connection(conn)
        return f"I couldn't find '{product_name}' in our catalog."
        
    cursor.execute("SELECT quantity FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product['product_id']))
    if cursor.fetchone():
        cursor.execute("UPDATE cart SET quantity = quantity + %s WHERE user_id = %s AND product_id = %s", (quantity, user_id, product['product_id']))
    else:
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)", (user_id, product['product_id'], quantity))
        
    conn.commit(); cursor.close(); close_db_connection(conn)
    return f"✅ Successfully added **{quantity}x {product['product_name']}** to your cart!<br><br><a href='cart.html' style='color: #6366f1; font-weight: bold; text-decoration: none;'>🛒 Click here to view Cart</a>"

def checkout_cart(user_id: int) -> str:
    if user_id == 0: return "Please log in to checkout your cart."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT c.product_id, c.quantity, p.price, p.stock, p.product_name FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s", (user_id,))
        cart_items = cursor.fetchall()
        if not cart_items: return "Your cart is currently empty. There is nothing to order!"
            
        for item in cart_items:
            if item['stock'] < item['quantity']:
                return f"Insufficient stock for {item['product_name']}. Only {item['stock']} left in warehouse."
                
        total = sum(item['quantity'] * item['price'] for item in cart_items)
        cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
        order_id = cursor.lastrowid
        
        for item in cart_items:
            cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (%s, %s, %s, %s, %s)", (order_id, item['product_id'], item['product_name'], item['price'], item['quantity']))
            cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (item['quantity'], item['product_id']))
            
        cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
        conn.commit()
        return f"✅ Success! Your cart has been checked out. **Order #{order_id}** has been placed for a total of ₹{total}."
    except Exception as e: return f"Error during checkout: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)

def place_order(user_id: int, product_name: str, quantity: int = 1) -> str:
    if user_id == 0: return "You must be logged in to place an order."
    if not product_name: return "I didn't catch the name of the product you want to order."
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, price, stock FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    product = cursor.fetchone()
    if not product: return f"Sorry, I couldn't find '{product_name}' to order."
    if product['stock'] < quantity: return "Insufficient stock."
        
    total = product['price'] * quantity
    cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
    order_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (%s, %s, %s, %s, %s)", (order_id, product['product_id'], product_name, product['price'], quantity))
    cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, product['product_id']))
    cursor.execute("DELETE FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product['product_id']))
    
    conn.commit(); cursor.close(); close_db_connection(conn)
    return f"Success! Express Order #{order_id} has been placed for ₹{total}."

def check_order_status(user_id: int, order_id: int) -> str:
    if user_id == 0: return "Please log in to track orders."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    order = cursor.fetchone()
    cursor.close(); close_db_connection(conn)
    return f"Order #{order_id} is currently **{order['status'].upper()}**." if order else "I couldn't find an order with that ID."

def modify_order(user_id: int, order_id: int, product_name: str, new_quantity: int) -> str:
    if user_id == 0: return "Please log in to modify orders."
    if new_quantity < 0: return "Quantity cannot be less than zero."
    if not product_name: return "I need the name of the product you want to modify."
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
        order = cursor.fetchone()
        if not order: return f"Order #{order_id} not found on your account."
        if order['status'] != 'pending': return f"Cannot modify Order #{order_id} because it is already {order['status']}."
            
        cursor.execute("SELECT * FROM order_items WHERE order_id = %s AND product_name LIKE %s", (order_id, f"%{product_name}%"))
        item = cursor.fetchone()
        if not item: return f"I couldn't find '{product_name}' in Order #{order_id}."
            
        old_quantity = item['quantity']
        qty_diff = new_quantity - old_quantity
        
        if new_quantity == 0:
            cursor.execute("DELETE FROM order_items WHERE order_id = %s AND product_id = %s", (order_id, item['product_id']))
        else:
            cursor.execute("SELECT stock FROM products WHERE product_id = %s", (item['product_id'],))
            product_data = cursor.fetchone()
            if qty_diff > 0 and product_data['stock'] < qty_diff:
                return f"Not enough stock to increase. Only {product_data['stock']} left."
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
    except Exception as e: return f"Error modifying order: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)

def cancel_order(user_id: int, order_id: int) -> str:
    if user_id == 0: return "Please log in to cancel orders."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    result = cursor.fetchone()
    if not result: return "I couldn't find an order with that ID."
    if result['status'] == 'cancelled': return f"Order #{order_id} is already cancelled."
        
    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (order_id,))
    cursor.execute("UPDATE products p JOIN order_items oi ON p.product_id = oi.product_id SET p.stock = p.stock + oi.quantity WHERE oi.order_id = %s", (order_id,))
    conn.commit(); cursor.close(); close_db_connection(conn)
    return f"Order #{order_id} has been successfully cancelled and items restocked."

def cancel_all_orders(user_id: int) -> str:
    if user_id == 0: return "Please log in to cancel orders."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT order_id FROM orders WHERE user_id = %s AND status = 'pending'", (user_id,))
        pending_orders = cursor.fetchall()
        if not pending_orders: return "You have no pending orders to cancel right now."
            
        count = 0
        for order in pending_orders:
            o_id = order['order_id']
            cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (o_id,))
            cursor.execute("UPDATE products pr JOIN order_items oi ON pr.product_id = oi.product_id SET pr.stock = pr.stock + oi.quantity WHERE oi.order_id = %s", (o_id,))
            count += 1
            
        conn.commit()
        return f"✅ Successfully cancelled {count} pending order(s) and restocked all items to the store!"
    except Exception as e: return f"Error cancelling all orders: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)

# =====================================================================
# 2. DISPATCHER & PROMPTS
# =====================================================================

def execute_tool(func_name: str, args: dict, safe_user_id: int) -> str:
    mapping = {
        "get_product_recommendation": lambda: get_product_recommendation(args.get("search_term"), args.get("max_price"), args.get("category"), safe_user_id),
        "compare_products": lambda: compare_products(args.get("product_a"), args.get("product_b"), safe_user_id),
        "get_product_details": lambda: get_product_details(args.get("product_name"), safe_user_id),
        "find_cheaper_alternative": lambda: find_cheaper_alternative(args.get("product_name"), safe_user_id),
        "get_user_order_history": lambda: get_user_order_history(safe_user_id),
        "view_user_cart": lambda: view_user_cart(safe_user_id),
        "add_item_to_cart": lambda: add_item_to_cart(safe_user_id, args.get("product_name"), args.get("quantity", 1)),
        "place_order": lambda: place_order(safe_user_id, args.get("product_name"), args.get("quantity", 1)),
        "checkout_cart": lambda: checkout_cart(safe_user_id),
        "check_order_status": lambda: check_order_status(safe_user_id, args.get("order_id")),
        "modify_order": lambda: modify_order(safe_user_id, args.get("order_id"), args.get("product_name"), args.get("new_quantity")),
        "cancel_order": lambda: cancel_order(safe_user_id, args.get("order_id")),
        "cancel_all_orders": lambda: cancel_all_orders(safe_user_id)
    }
    if func_name in mapping:
        return mapping[func_name]()
    return "Action unmapped."

STORE_KNOWLEDGE = """
You are the AI Assistant for AI Store.
- Shipping: Standard (3-5 days), Expedited (1-2 days).
- Returns: 30-day return policy; instant restock upon cancellation.
- Payments: Credit Cards, Apple Pay, Google Pay, UPI.
- Support: support@aistore.com | Location: Pune, India.
"""

GATEKEEPER_PROMPT = f"""
{STORE_KNOWLEDGE}
You are the frontline Gatekeeper for AI Store.
- If the user greeting, asking store policy, shipping, or general information, answer directly and helpfully.
- If the user wants to search, view cart, add items, checkout, check order status, modify, or cancel orders, OUTPUT ONLY ONE WORD: "DB_ACTION".
"""

AGENTIC_SYSTEM_PROMPT = """You are an autonomous e-commerce reasoning agent for AI Store.
You have access to real-time database tools.

AUTONOMOUS EXECUTION RULES:
1. MULTI-STEP REASONING: If a user asks to cancel, track, or modify an order by item name (e.g., "cancel my shoe order") without providing the integer order_id, DO NOT ask the user for the ID. First call 'get_user_order_history', observe the order_id associated with that product, and then automatically call 'cancel_order' or 'modify_order' in the next step.
2. CHECKOUT vs EXPRESS: If the user says "checkout" or "buy my cart", use 'checkout_cart'. If they specify a single product directly to buy now, use 'place_order'.
3. NO HTML: Never attempt to write HTML or formatting tags. The Python backend handles UI generation exclusively.
"""

# =====================================================================
# 3. MULTI-TURN ENGINE (Strict Nullable JSON Schemas)
# =====================================================================

@router.post("")
async def process_chat(request: ChatRequest):
    if not client: return {"response": "AI configuration error: API Key missing."}
    safe_user_id = request.user_id if request.user_id else 0

    try:
        # Step 1: Gatekeeper Filter using openai/gpt-oss-20b[cite: 1]
        gatekeeper_res = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": GATEKEEPER_PROMPT},
                {"role": "user", "content": request.message}
            ],
            temperature=0.1
        ).choices[0].message.content

        if "DB_ACTION" not in gatekeeper_res:
            return {"response": gatekeeper_res}

        # Step 2: Multi-Turn Orchestrator using openai/gpt-oss-120b[cite: 1]
        # Updated Schema to prevent 400 Bad Request by allowing ["string", "null"] types.
        tools_schema = [
            {"type": "function", "function": {"name": "get_product_recommendation", "description": "Search products dynamically.", "parameters": {"type": "object", "properties": {"search_term": {"type": ["string", "null"]}, "max_price": {"type": ["integer", "null"]}, "category": {"type": ["string", "null"]}}}}},
            {"type": "function", "function": {"name": "compare_products", "description": "Compare two products.", "parameters": {"type": "object", "properties": {"product_a": {"type": "string"}, "product_b": {"type": "string"}}, "required": ["product_a", "product_b"]}}},
            {"type": "function", "function": {"name": "get_product_details", "description": "Get deep product specs.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "find_cheaper_alternative", "description": "Find cheaper alternatives in the same category.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "get_user_order_history", "description": "Get recent order records for the user.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "view_user_cart", "description": "View items in the user's cart.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "add_item_to_cart", "description": "Add an item to the shopping cart.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["product_name", "quantity"]}}},
            {"type": "function", "function": {"name": "place_order", "description": "Express buy a single specific product immediately.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["product_name", "quantity"]}}},
            {"type": "function", "function": {"name": "checkout_cart", "description": "Process the entire current shopping cart into an order.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "check_order_status", "description": "Check status by integer order ID.", "parameters": {"type": "object", "properties": {"order_id": {"type": "integer"}}, "required": ["order_id"]}}},
            {"type": "function", "function": {"name": "modify_order", "description": "Modify quantity of item in an order.", "parameters": {"type": "object", "properties": {"order_id": {"type": "integer"}, "product_name": {"type": "string"}, "new_quantity": {"type": "integer"}}, "required": ["order_id", "product_name", "new_quantity"]}}},
            {"type": "function", "function": {"name": "cancel_order", "description": "Cancel an order by integer ID.", "parameters": {"type": "object", "properties": {"order_id": {"type": "integer"}}, "required": ["order_id"]}}},
            {"type": "function", "function": {"name": "cancel_all_orders", "description": "Cancel all pending orders simultaneously.", "parameters": {"type": "object", "properties": {}}}}
        ]

        messages = [
            {"role": "system", "content": AGENTIC_SYSTEM_PROMPT},
            {"role": "user", "content": request.message}
        ]

        # Max 5 chained loops to prevent infinite routing
        for _ in range(5):
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                tools=tools_schema,
                temperature=0.1
            )
            msg = response.choices[0].message
            
            assistant_msg = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} 
                    for tc in msg.tool_calls
                ]
            messages.append(assistant_msg)

            if not msg.tool_calls:
                return {"response": msg.content}

            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                
                # Safe JSON parsing fallback
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                    
                tool_output = execute_tool(func_name, args, safe_user_id)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": str(tool_output)
                })

        return {"response": "The request required too many operations. Please break it down."}

    except Exception as e:
        return {"response": f"Agent runtime error: {str(e)}"}
