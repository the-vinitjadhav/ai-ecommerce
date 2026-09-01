from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import os
import json
import urllib.parse
from typing import Optional, Literal, TypedDict, Annotated

# --- LangChain & LangGraph Imports ---
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from backend.database import get_db_connection, close_db_connection
from backend.models import ChatRequest

# Architecture by Vinit Jadhav | AI E-Commerce Portfolio
router = APIRouter(prefix="/api/chat", tags=["AI Agent"])

# =====================================================================
# 1. RAG INITIALIZATION & PROACTIVE PERSONALIZATION
# =====================================================================
print("Loading RAG Embeddings & Vector DB...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

KNOWLEDGE_DOCS = [
    "Shipping Policy: Standard shipping takes 3-5 business days. Expedited takes 1-2 days. Shipping is free for orders over ₹10,000.",
    "Return Policy: We offer a 30-day no-questions-asked return policy. Refunds are processed within 48 hours.",
    "Lenovo V15 Warranty: Comes with a 1-year brand warranty covering hardware defects. Does not cover water damage.",
    "Apple Return Exception: Opened Apple products can only be returned within 14 days and are subject to a 15% restocking fee.",
    "Customer Support: You can reach our 24/7 support team by emailing support@aistore.com.",
    "Store Location: Our primary warehouse is located in Pune, Maharashtra, India."
]
vector_db = FAISS.from_texts(KNOWLEDGE_DOCS, embeddings)
rag_tool = create_retriever_tool(
    vector_db.as_retriever(search_kwargs={"k": 2}),
    "search_knowledge_base",
    "Searches company policies, shipping rules, warranties, and FAQs."
)

def db_get_user_context(user_id: int) -> str:
    """Proactively fetches user history to inject into the AI's brain before they even ask."""
    if user_id == 0: return "Guest User. No active cart or history."
    
    conn = get_db_connection()
    if not conn: return ""
    cursor = conn.cursor(dictionary=True)
    
    context_str = f"User ID: {user_id}\n"
    
    # Check Active Cart
    cursor.execute("SELECT p.product_name, c.quantity FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s", (user_id,))
    cart_items = cursor.fetchall()
    if cart_items:
        context_str += "ACTIVE CART STATE: " + ", ".join([f"{item['quantity']}x {item['product_name']}" for item in cart_items]) + ".\n"
    else:
        context_str += "ACTIVE CART STATE: Empty.\n"
        
    # Check Last Order
    cursor.execute("SELECT order_id, status FROM orders WHERE user_id = %s ORDER BY order_date DESC LIMIT 1", (user_id,))
    last_order = cursor.fetchone()
    if last_order:
        context_str += f"LAST ORDER: #{last_order['order_id']} (Status: {last_order['status']}).\n"
        
    cursor.close(); close_db_connection(conn)
    return context_str

# =====================================================================
<<<<<<< HEAD
# 2. DETERMINISTIC UI FUNCTIONS (The 14 Core Tools)
=======
# 1. DETERMINISTIC UI & DATABASE TOOLS
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
# =====================================================================

def db_get_product_recommendation(search_term: str, max_price: int, category: str, user_id: int) -> str:
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
<<<<<<< HEAD
=======
            
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
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

def db_compare_products(product_a: str, product_b: str, user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        results = []
        for term in [product_a, product_b]:
            if not term: continue
            cursor.execute("SELECT * FROM products WHERE product_name LIKE %s OR description LIKE %s LIMIT 1", (f"%{term}%", f"%{term}%"))
            p = cursor.fetchone()
            if p: results.append(p)
                
<<<<<<< HEAD
        if len(results) < 2: return "I couldn't find exact matches to compare both items."
=======
        if len(results) < 2: return f"I couldn't find exact matches to compare both items."
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec

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

def db_get_product_details(product_name: str, user_id: int) -> str:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    p = cursor.fetchone()
    cursor.close(); close_db_connection(conn)
    if not p: return f"I couldn't find a product matching '{product_name}'."
    
<<<<<<< HEAD
    img = p.get('image_url') or f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(p.get('product_name')))}&background=random"
=======
    if not p: return f"I couldn't find a product matching '{product_name}' in our catalog."
    
    img = p.get('image_url', '')
    if not img or not str(img).startswith('http'):
        img = f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(p.get('product_name', 'Item')))}&background=random&color=fff&size=200"
    
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
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

def db_find_cheaper_alternative(product_name: str, user_id: int) -> str:
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
<<<<<<< HEAD
=======
    
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
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

<<<<<<< HEAD
def db_get_user_order_history(user_id: int) -> str:
=======
def get_user_order_history(user_id: int) -> str:
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
    if user_id == 0: return "Please log in to view your order history."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.total_amount, o.status, DATE_FORMAT(o.order_date, '%M %d, %Y') as formatted_date,
               GROUP_CONCAT(oi.product_name SEPARATOR ', ') as items_summary
<<<<<<< HEAD
        FROM orders o LEFT JOIN order_items oi ON o.order_id = oi.order_id
=======
        FROM orders o
        LEFT JOIN order_items oi ON o.order_id = oi.order_id
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
        WHERE o.user_id = %s GROUP BY o.order_id ORDER BY o.order_date DESC LIMIT 3
    """, (user_id,))
    orders = cursor.fetchall()
    cursor.close(); close_db_connection(conn)
    if not orders: return "You have no recent orders on this account."
    
<<<<<<< HEAD
=======
    if not orders: return "You have no recent orders on this account."
    
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
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

<<<<<<< HEAD
def db_view_user_cart(user_id: int) -> str:
=======
def view_user_cart(user_id: int) -> str:
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
    if user_id == 0: return "Please log in to view your cart."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT c.quantity, p.product_name, p.price, p.image_url FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s", (user_id,))
    items = cursor.fetchall()
    cursor.close(); close_db_connection(conn)
    if not items: return "Your cart is currently empty. Ask me to recommend some products!"
    
<<<<<<< HEAD
    total_cart_value = sum((item['price'] * item['quantity']) for item in items)
=======
    if not items: return "Your cart is currently empty. Ask me to recommend some products!"
    total_cart_value = sum((item['price'] * item['quantity']) for item in items)
    
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
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
<<<<<<< HEAD
        <a href="cart.html" style="display: block; text-align: center; background: linear-gradient(135deg, #6366f1, #a855f7); color: white; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px;">Proceed to Checkout</a>
=======
        <a href="cart.html" style="display: block; text-align: center; background: linear-gradient(135deg, #6366f1, #a855f7); color: white; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px; box-shadow: 0 4px 10px rgba(99,102,241,0.2);">Proceed to Checkout</a>
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
    </div>
    """
    return html

<<<<<<< HEAD
def db_add_item_to_cart(user_id: int, product_name: str, quantity: int = 1) -> str:
    if user_id == 0: return "Please log in to add items."
=======
def add_item_to_cart(user_id: int, product_name: str, quantity: int = 1) -> str:
    if user_id == 0: return "Please log in to add items to your cart."
    if not product_name: return "I didn't catch the name of the product you want to add."
    
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
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
<<<<<<< HEAD

def db_remove_item_from_cart(user_id: int, product_name: str) -> str:
    if user_id == 0: return "Please log in to modify your cart."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, product_name FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    product = cursor.fetchone()
    if not product:
        cursor.close(); close_db_connection(conn)
        return f"I couldn't find '{product_name}' in our catalog."
        
    cursor.execute("DELETE FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product['product_id']))
    affected = cursor.rowcount
    conn.commit(); cursor.close(); close_db_connection(conn)
    
    if affected == 0: return f"**{product['product_name']}** was not in your cart."
    return f"✅ Successfully removed **{product['product_name']}** from your cart.<br><br><a href='cart.html' style='color: #ef4444; font-weight: bold; text-decoration: none;'>🛒 Click here to view Cart</a>"

def db_checkout_cart(user_id: int) -> str:
    if user_id == 0: return "Please log in to checkout."
=======

def remove_item_from_cart(user_id: int, product_name: str) -> str:
    if user_id == 0: return "Please log in to modify your cart."
    if not product_name: return "I didn't catch the name of the product you want to remove."
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, product_name FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    product = cursor.fetchone()
    if not product:
        cursor.close(); close_db_connection(conn)
        return f"I couldn't find '{product_name}' in our catalog."
        
    cursor.execute("DELETE FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product['product_id']))
    affected = cursor.rowcount
    conn.commit(); cursor.close(); close_db_connection(conn)
    
    if affected == 0:
        return f"**{product['product_name']}** was not currently in your cart."
        
    return f"✅ Successfully removed **{product['product_name']}** from your cart.<br><br><a href='cart.html' style='color: #ef4444; font-weight: bold; text-decoration: none;'>🛒 Click here to view Cart</a>"

def checkout_cart(user_id: int) -> str:
    if user_id == 0: return "Please log in to checkout your cart."
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT c.product_id, c.quantity, p.price, p.stock, p.product_name FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s", (user_id,))
        cart_items = cursor.fetchall()
<<<<<<< HEAD
        if not cart_items: return "Your cart is currently empty."
            
        for item in cart_items:
            if item['stock'] < item['quantity']:
                return f"Insufficient stock for {item['product_name']}."
=======
        if not cart_items: return "Your cart is currently empty. There is nothing to order!"
            
        for item in cart_items:
            if item['stock'] < item['quantity']:
                return f"Insufficient stock for {item['product_name']}. Only {item['stock']} left in warehouse."
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
                
        total = sum(item['quantity'] * item['price'] for item in cart_items)
        cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
        order_id = cursor.lastrowid
        
        for item in cart_items:
            cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (%s, %s, %s, %s, %s)", (order_id, item['product_id'], item['product_name'], item['price'], item['quantity']))
            cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (item['quantity'], item['product_id']))
            
        cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
        conn.commit()
<<<<<<< HEAD
        return f"✅ Success! Your cart has been checked out. **Order #{order_id}** placed for ₹{total}."
    except Exception as e: return f"Error during checkout: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)

def db_place_order(user_id: int, product_name: str, quantity: int = 1) -> str:
    if user_id == 0: return "You must be logged in to place an order."
=======
        return f"✅ Success! Your cart has been checked out. **Order #{order_id}** has been placed for a total of ₹{total}."
    except Exception as e: return f"Error during checkout: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)

def place_order(user_id: int, product_name: str, quantity: int = 1) -> str:
    if user_id == 0: return "You must be logged in to place an order."
    if not product_name: return "I didn't catch the name of the product you want to order."
    
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, price, stock FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    product = cursor.fetchone()
<<<<<<< HEAD
    if not product: return f"Sorry, I couldn't find '{product_name}'."
=======
    if not product: return f"Sorry, I couldn't find '{product_name}' to order."
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
    if product['stock'] < quantity: return "Insufficient stock."
        
    total = product['price'] * quantity
    cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')", (user_id, total))
    order_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (%s, %s, %s, %s, %s)", (order_id, product['product_id'], product_name, product['price'], quantity))
    cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (quantity, product['product_id']))
    cursor.execute("DELETE FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product['product_id']))
    
    conn.commit(); cursor.close(); close_db_connection(conn)
    return f"Success! Express Order #{order_id} has been placed for ₹{total}."

def db_check_order_status(user_id: int, order_id: int) -> str:
    if user_id == 0: return "Please log in."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    order = cursor.fetchone()
    cursor.close(); close_db_connection(conn)
<<<<<<< HEAD
    return f"Order #{order_id} is currently **{order['status'].upper()}**." if order else "Order not found."

def db_modify_order(user_id: int, order_id: int, product_name: str, new_quantity: int) -> str:
    if user_id == 0: return "Please log in."
    if new_quantity < 0: return "Quantity cannot be negative."
=======
    return f"Order #{order_id} is currently **{order['status'].upper()}**." if order else "I couldn't find an order with that ID."

def modify_order(user_id: int, order_id: int, product_name: str, new_quantity: int) -> str:
    if user_id == 0: return "Please log in to modify orders."
    if new_quantity < 0: return "Quantity cannot be less than zero."
    if not product_name: return "I need the name of the product you want to modify."
    
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
        order = cursor.fetchone()
<<<<<<< HEAD
        if not order: return f"Order #{order_id} not found."
        if order['status'] != 'pending': return f"Cannot modify Order #{order_id} (already {order['status']})."
            
        cursor.execute("SELECT * FROM order_items WHERE order_id = %s AND product_name LIKE %s", (order_id, f"%{product_name}%"))
        item = cursor.fetchone()
        if not item: return f"'{product_name}' not in Order #{order_id}."
=======
        if not order: return f"Order #{order_id} not found on your account."
        if order['status'] != 'pending': return f"Cannot modify Order #{order_id} because it is already {order['status']}."
            
        cursor.execute("SELECT * FROM order_items WHERE order_id = %s AND product_name LIKE %s", (order_id, f"%{product_name}%"))
        item = cursor.fetchone()
        if not item: return f"I couldn't find '{product_name}' in Order #{order_id}."
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
            
        old_quantity = item['quantity']
        qty_diff = new_quantity - old_quantity
        
        if new_quantity == 0:
            cursor.execute("DELETE FROM order_items WHERE order_id = %s AND product_id = %s", (order_id, item['product_id']))
        else:
            cursor.execute("SELECT stock FROM products WHERE product_id = %s", (item['product_id'],))
            product_data = cursor.fetchone()
<<<<<<< HEAD
            if qty_diff > 0 and product_data['stock'] < qty_diff: return f"Not enough stock."
=======
            if qty_diff > 0 and product_data['stock'] < qty_diff:
                return f"Not enough stock to increase. Only {product_data['stock']} left."
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
            cursor.execute("UPDATE order_items SET quantity = %s WHERE order_id = %s AND product_id = %s", (new_quantity, order_id, item['product_id']))
            
        cursor.execute("UPDATE products SET stock = stock - %s WHERE product_id = %s", (qty_diff, item['product_id']))
        cursor.execute("SELECT SUM(price * quantity) as new_total FROM order_items WHERE order_id = %s", (order_id,))
        new_total_data = cursor.fetchone()
        new_total = new_total_data['new_total'] if new_total_data['new_total'] else 0
        
        if new_total == 0:
            cursor.execute("UPDATE orders SET status = 'cancelled', total_amount = 0 WHERE order_id = %s", (order_id,))
            conn.commit()
<<<<<<< HEAD
            return f"Order #{order_id} is now empty and has been cancelled."
            
        cursor.execute("UPDATE orders SET total_amount = %s WHERE order_id = %s", (new_total, order_id))
        conn.commit()
        return f"Order #{order_id} updated. New Total: ₹{new_total}."
    except Exception as e: return f"Error: {str(e)}"
=======
            return f"Item removed. Since the order is now empty, Order #{order_id} has been automatically cancelled."
            
        cursor.execute("UPDATE orders SET total_amount = %s WHERE order_id = %s", (new_total, order_id))
        conn.commit()
        return f"Success! Order #{order_id} updated. {product_name} quantity is now {new_quantity}. New Total: ₹{new_total}."
    except Exception as e: return f"Error modifying order: {str(e)}"
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
    finally: cursor.close(); close_db_connection(conn)

def db_cancel_order(user_id: int, order_id: int) -> str:
    if user_id == 0: return "Please log in."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    result = cursor.fetchone()
<<<<<<< HEAD
    if not result: return "Order not found."
=======
    if not result: return "I couldn't find an order with that ID."
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
    if result['status'] == 'cancelled': return f"Order #{order_id} is already cancelled."
        
    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (order_id,))
    cursor.execute("UPDATE products p JOIN order_items oi ON p.product_id = oi.product_id SET p.stock = p.stock + oi.quantity WHERE oi.order_id = %s", (order_id,))
    conn.commit(); cursor.close(); close_db_connection(conn)
<<<<<<< HEAD
    return f"✅ Order #{order_id} cancelled."
=======
    return f"✅ Order #{order_id} has been successfully cancelled and items restocked."
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec

def db_cancel_all_orders(user_id: int) -> str:
    if user_id == 0: return "Please log in."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT order_id FROM orders WHERE user_id = %s AND status = 'pending'", (user_id,))
<<<<<<< HEAD
        pending = cursor.fetchall()
        if not pending: return "No pending orders."
=======
        pending_orders = cursor.fetchall()
        if not pending_orders: return "You have no pending orders to cancel right now."
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
            
        count = 0
        for order in pending_orders:
            o_id = order['order_id']
            cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (o_id,))
            cursor.execute("UPDATE products pr JOIN order_items oi ON pr.product_id = oi.product_id SET pr.stock = pr.stock + oi.quantity WHERE oi.order_id = %s", (o_id,))
            count += 1
            
        conn.commit()
<<<<<<< HEAD
        return f"✅ Cancelled {len(pending)} order(s)."
    except Exception as e: return f"Error: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)


# =====================================================================
# 3. THE MULTI-AGENT SUPERVISOR GRAPH
# =====================================================================

def get_sales_tools(safe_user_id: int):
    """Generates the 14 SQL UI tools bound to the active user."""
    @tool
    def get_product_recommendation(search_term: Optional[str] = None, max_price: Optional[int] = None, category: Optional[str] = None) -> str:
        """Search products dynamically in the database."""
        return db_get_product_recommendation(search_term, max_price, category, safe_user_id)
    @tool
    def compare_products(product_a: str, product_b: str) -> str:
        """Compare two products side-by-side."""
        return db_compare_products(product_a, product_b, safe_user_id)
    @tool
    def get_product_details(product_name: str) -> str:
        """Get deep product specs for a single item."""
        return db_get_product_details(product_name, safe_user_id)
    @tool
    def find_cheaper_alternative(product_name: str) -> str:
        """Find cheaper alternatives to a product."""
        return db_find_cheaper_alternative(product_name, safe_user_id)
    @tool
    def get_user_order_history() -> str:
        """Get recent orders for the user."""
        return db_get_user_order_history(safe_user_id)
    @tool
    def view_user_cart() -> str:
        """View the current contents of the user's shopping cart."""
        return db_view_user_cart(safe_user_id)
    @tool
    def add_item_to_cart(product_name: str, quantity: int = 1) -> str:
        """Add an item to the shopping cart."""
        return db_add_item_to_cart(safe_user_id, product_name, quantity)
    @tool
    def remove_item_from_cart(product_name: str) -> str:
        """Remove an item completely from the shopping cart."""
        return db_remove_item_from_cart(safe_user_id, product_name)
    @tool
    def place_order(product_name: str, quantity: int = 1) -> str:
        """Express checkout immediately."""
        return db_place_order(safe_user_id, product_name, quantity)
    @tool
    def checkout_cart() -> str:
        """Process the entire shopping cart."""
        return db_checkout_cart(safe_user_id)
    @tool
    def check_order_status(order_id: int) -> str:
        """Check status by integer order ID."""
        return db_check_order_status(safe_user_id, order_id)
    @tool
    def modify_order(order_id: int, product_name: str, new_quantity: int) -> str:
        """Modify an existing pending order."""
        return db_modify_order(safe_user_id, order_id, product_name, new_quantity)
    @tool
    def cancel_order(order_id: int) -> str:
        """Cancel a specific order using its integer ID."""
        return db_cancel_order(safe_user_id, order_id)
    @tool
    def cancel_all_orders() -> str:
        """Cancel all pending orders."""
        return db_cancel_all_orders(safe_user_id)

    return [get_product_recommendation, compare_products, get_product_details, find_cheaper_alternative, get_user_order_history, view_user_cart, add_item_to_cart, remove_item_from_cart, place_order, checkout_cart, check_order_status, modify_order, cancel_order, cancel_all_orders]

class RouteDefinition(BaseModel):
    next_node: Literal["Sales", "Support", "FINISH"] = Field(
        description="Route to 'Sales' for product searches, carts, checkouts, and orders. Route to 'Support' for policies, shipping, and FAQs. Route to 'FINISH' if answering a casual greeting like 'hello'."
    )

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next_node: str
    user_id: int

def supervisor_node(state: AgentState):
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0) # Fast router
    system_prompt = "You are the AI Supervisor. Read the user's message and determine the correct department to route to."
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    
    response = llm.with_structured_output(RouteDefinition).invoke(messages)
    return {"next_node": response.next_node}

def sales_node(state: AgentState):
    user_context = db_get_user_context(state["user_id"])
    sales_prompt = f"""You are the Sales Agent. You have strict SQL tools.
    {user_context}
    RULE 1: For order lookups missing an ID, use get_user_order_history first.
    RULE 2: Your tools generate HTML. Do not summarize their output. When a tool finishes successfully, output exactly: "DONE"."""
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
    agent = create_react_agent(llm, get_sales_tools(state["user_id"]), state_modifier=sales_prompt)
    result = agent.invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}

def support_node(state: AgentState):
    support_prompt = "You are the Support Agent. Use search_knowledge_base to read store policies. Answer conversationally in text."
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
    agent = create_react_agent(llm, [rag_tool], state_modifier=support_prompt)
    result = agent.invoke({"messages": state["messages"]})
    return {"messages": result["messages"]}

# Build the Multi-Agent Graph
builder = StateGraph(AgentState)
builder.add_node("Supervisor", supervisor_node)
builder.add_node("Sales", sales_node)
builder.add_node("Support", support_node)

builder.add_edge(START, "Supervisor")
builder.add_conditional_edges("Supervisor", lambda state: state["next_node"], {"Sales": "Sales", "Support": "Support", "FINISH": END})
builder.add_edge("Sales", END)
builder.add_edge("Support", END)

memory = MemorySaver()
multi_agent_graph = builder.compile(checkpointer=memory)

# =====================================================================
# 4. SERVER-SENT EVENTS (SSE) STREAMING ENDPOINT
=======
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
        "remove_item_from_cart": lambda: remove_item_from_cart(safe_user_id, args.get("product_name")),
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
- If the user wants to search, view cart, add items, remove items, checkout, check order status, modify, or cancel orders, OUTPUT ONLY ONE WORD: "DB_ACTION".
"""

AGENTIC_SYSTEM_PROMPT = """You are an autonomous e-commerce reasoning agent for AI Store.
You have access to real-time database tools.

AUTONOMOUS EXECUTION RULES:
1. MULTI-STEP REASONING: If a user asks to cancel, track, or modify an order by item name without providing the integer order_id, DO NOT ask the user for the ID. First call 'get_user_order_history', observe the order_id associated with that product, and then automatically call 'cancel_order' or 'modify_order' in the next step.
2. CHECKOUT vs EXPRESS: If the user says "checkout" or "buy my cart", use 'checkout_cart'. If they specify a single product directly to buy now, use 'place_order'.
3. SILENT UI RENDERING: The Python backend automatically displays the HTML result of the LAST tool you called directly to the user. Because of this, after you successfully call a tool, you MUST output exactly the word "DONE" and nothing else. Do not summarize the products, do not say 'Here is your cart'. Just output "DONE".
4. REMOVING FROM CART: If a user asks to remove an item from their cart, use the 'remove_item_from_cart' tool. DO NOT use 'add_item_to_cart' with quantity 0.
"""

# =====================================================================
# 3. MULTI-TURN ENGINE
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
# =====================================================================

@router.post("")
async def process_chat(request: ChatRequest):
    safe_user_id = request.user_id if request.user_id else 0

<<<<<<< HEAD
    async def generate_stream():
        config = {"configurable": {"thread_id": str(safe_user_id)}}
        initial_state = {"messages": [HumanMessage(content=request.message)], "user_id": safe_user_id}

        # Streams internal LangGraph "Thought" events to the frontend in real-time
        async for event in multi_agent_graph.astream_events(initial_state, config, version="v2"):
            kind = event["event"]
            
            # Emit Text Tokens (When the LLM speaks naturally)
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content
                if chunk: 
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                    
            # Emit "Thought" Logging (When the Agent decides to use a Tool)
            elif kind == "on_tool_start":
                tool_name = event["name"]
                yield f"data: {json.dumps({'type': 'thought', 'content': f'Running {tool_name} transaction...'})}\n\n"
=======
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
        tools_schema = [
            {"type": "function", "function": {"name": "get_product_recommendation", "description": "Search products dynamically.", "parameters": {"type": "object", "properties": {"search_term": {"type": ["string", "null"]}, "max_price": {"type": ["integer", "null"]}, "category": {"type": ["string", "null"]}}}}},
            {"type": "function", "function": {"name": "compare_products", "description": "Compare two products.", "parameters": {"type": "object", "properties": {"product_a": {"type": "string"}, "product_b": {"type": "string"}}, "required": ["product_a", "product_b"]}}},
            {"type": "function", "function": {"name": "get_product_details", "description": "Get deep product specs.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "find_cheaper_alternative", "description": "Find cheaper alternatives in the same category.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
            {"type": "function", "function": {"name": "get_user_order_history", "description": "Get recent order records for the user.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "view_user_cart", "description": "View items in the user's cart.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "add_item_to_cart", "description": "Add an item to the shopping cart.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}, "quantity": {"type": "integer"}}, "required": ["product_name", "quantity"]}}},
            {"type": "function", "function": {"name": "remove_item_from_cart", "description": "Remove an item completely from the shopping cart.", "parameters": {"type": "object", "properties": {"product_name": {"type": "string"}}, "required": ["product_name"]}}},
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

        last_tool_output = ""
        
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
                final_text = (msg.content or "").strip()
                
                if "DONE" in final_text.upper() or (last_tool_output and len(final_text) > 150):
                    return {"response": last_tool_output}
                
                if last_tool_output and final_text:
                    return {"response": f"{final_text}<br><br>{last_tool_output}"}
                
                return {"response": final_text}

            last_tool_output = ""
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                    
                tool_output = execute_tool(func_name, args, safe_user_id)
                last_tool_output += str(tool_output)
>>>>>>> fb5b9486b228971bbbb1e4bcf8d7b3ade0d795ec
                
            # Emit Final HTML UI Blocks (Intercepted dynamically)
            elif kind == "on_tool_end":
                tool_name = event["name"]
                output = event["data"].get("output", "")
                if tool_name != "search_knowledge_base" and tool_name != "RouteDefinition":
                    yield f"data: {json.dumps({'type': 'ui_block', 'content': str(output)})}\n\n"

        # Signal completion to frontend
        yield f"data: {json.dumps({'type': 'end'})}\n\n"

    # StreamingResponse replaces standard JSON return
    return StreamingResponse(generate_stream(), media_type="text/event-stream")