from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import os
import json
import urllib.parse
from typing import Optional, Literal, TypedDict, Annotated

# --- LangChain & LangGraph Imports ---
from langchain_groq import ChatGroq
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
# 1. DYNAMIC DATABASE RAG & CONTEXT ENGINE
# =====================================================================

def get_store_metadata() -> dict:
    """Dynamically fetches active categories and sample inventory to ground the LLM's brain."""
    conn = get_db_connection()
    if not conn:
        return {"categories": [], "brands": []}
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT DISTINCT category_name FROM products WHERE category_name IS NOT NULL")
        categories = [r['category_name'] for r in cursor.fetchall() if r.get('category_name')]
        return {"categories": categories}
    except Exception:
        return {"categories": []}
    finally:
        cursor.close(); close_db_connection(conn)

@tool
def search_knowledge_base(query: str) -> str:
    """Searches company policies, shipping rules, warranties, and FAQs."""
    conn = get_db_connection()
    if not conn: 
        return "Store policies are temporarily offline."
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT topic, content FROM store_policies")
        policies = cursor.fetchall()
        
        if not policies: 
            return "No store policies found."

        # Lexical scoring with synonym tolerance
        query_words = set(query.lower().split())
        scored = []
        for p in policies:
            doc_text = f"{p['topic']} Policy: {p['content']}"
            score = sum(1 for w in query_words if w in doc_text.lower())
            scored.append((score, doc_text))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        best_docs = [doc for score, doc in scored if score > 0][:2]
        return "\n\n".join(best_docs) if best_docs else "\n\n".join([f"{p['topic']}: {p['content']}" for p in policies[:2]])
    except Exception as e:
        return f"Error reading policies: {str(e)}"
    finally:
        cursor.close(); close_db_connection(conn)

def db_get_user_context(user_id: int) -> str:
    if user_id == 0: 
        return "User Profile: Guest Visitor (Not logged in)."
    
    conn = get_db_connection()
    if not conn: return ""
    cursor = conn.cursor(dictionary=True)
    
    context_str = f"User Profile: Logged-in Customer #{user_id}\n"
    
    # Active Cart
    cursor.execute("SELECT p.product_name, c.quantity, p.price FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s", (user_id,))
    cart_items = cursor.fetchall()
    if cart_items:
        context_str += "ACTIVE CART: " + ", ".join([f"{item['quantity']}x {item['product_name']} (₹{item['price']})" for item in cart_items]) + "\n"
    else:
        context_str += "ACTIVE CART: Empty\n"
        
    # Last Order
    cursor.execute("SELECT order_id, total_amount, status FROM orders WHERE user_id = %s ORDER BY order_date DESC LIMIT 1", (user_id,))
    last_order = cursor.fetchone()
    if last_order:
        context_str += f"RECENT ORDER: #{last_order['order_id']} | Status: {last_order['status']} | Total: ₹{last_order['total_amount']}\n"
        
    cursor.close(); close_db_connection(conn)
    return context_str

# =====================================================================
# 2. INTELLIGENT SEARCH & DETERMINISTIC TRANSACTION TOOLS
# =====================================================================

def db_smart_product_search(search_keywords: str = "", category: str = "", max_price: int = None, min_price: int = None, user_id: int = 0) -> str:
    """
    Intelligent fuzzy product search that handles synonyms, multi-word matching,
    and category inferences without breaking on exact phrasing.
    """
    conn = get_db_connection()
    if not conn: return "Database connection unavailable."
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Fetch candidate products within price and optional category filters
        sql = "SELECT * FROM products WHERE 1=1"
        params = []

        if max_price:
            sql += " AND price <= %s"
            params.append(max_price)
        if min_price:
            sql += " AND price >= %s"
            params.append(min_price)
        if category and category.lower() not in ["all", "any"]:
            sql += " AND category_name LIKE %s"
            params.append(f"%{category}%")

        cursor.execute(sql, tuple(params))
        candidates = cursor.fetchall()

        if not candidates:
            # Broaden search if price constraints were too strict
            cursor.execute("SELECT * FROM products LIMIT 15")
            candidates = cursor.fetchall()

        if not candidates:
            return "Our catalog is currently empty."

        # 2. Semantic token scoring (Title: 4pts, Category: 3pts, Description: 1pt)
        stop_words = {"suggest", "recommend", "show", "give", "find", "best", "good", "cheap", "expensive", "buy", "product", "products", "item", "items", "for", "the", "with", "and", "me", "some", "a", "an"}
        raw_words = search_keywords.replace(",", " ").replace("/", " ").lower().split()
        target_tokens = [w.strip() for w in raw_words if w.strip() and w.strip() not in stop_words]

        scored_products = []
        for p in candidates:
            name = p.get('product_name', '').lower()
            cat = p.get('category_name', '').lower()
            desc = p.get('description', '').lower()
            score = 0

            if not target_tokens:
                score = 1
            else:
                for token in target_tokens:
                    if token in name:
                        score += 4
                    elif token in cat:
                        score += 3
                    elif token in desc:
                        score += 1

            if score > 0 or not target_tokens:
                scored_products.append((score, p))

        scored_products.sort(key=lambda x: x[0], reverse=True)
        results = [item[1] for item in scored_products[:4]]

        if not results:
            results = candidates[:4]

        # 3. Generate Modern UI Cards
        html = "<div style='display:flex; flex-direction:column; gap:10px; margin-top:8px;'>"
        for p in results:
            img = p.get('image_url') or f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(p.get('product_name')))}&background=random"
            html += f"""
            <div style="display: flex; gap: 12px; padding: 12px; background: rgba(255,255,255,0.7); border: 1px solid rgba(0,0,0,0.06); border-radius: 14px; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
                <img src="{img}" style="width: 65px; height: 65px; object-fit: cover; border-radius: 10px; flex-shrink: 0;">
                <div style="flex: 1; min-width: 0;">
                    <div style="font-size: 0.75rem; color: #6366f1; font-weight: bold; text-transform: uppercase;">{p.get('category_name', 'Featured')}</div>
                    <h6 style="margin: 2px 0 4px 0; font-size: 0.95rem; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{p['product_name']}</h6>
                    <div style="font-weight: 800; color: #0f172a; font-size: 1.1rem; margin-bottom: 6px;">₹{p['price']}</div>
                    <button style="background: linear-gradient(135deg, #0f172a, #334155); color: white; border: none; padding: 6px 14px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer;" onclick="widgetAddToCart({p['product_id']})">Add to Cart</button>
                </div>
            </div>
            """
        html += "</div>"
        return html
    except Exception as e:
        return f"Error querying products: {str(e)}"
    finally:
        cursor.close(); close_db_connection(conn)

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
                
        if len(results) < 2: 
            return "I couldn't locate both products in the catalog to draw a direct comparison."

        html = "<div style='display: flex; gap: 10px; overflow-x: auto; padding: 5px 0; margin-top: 5px;'>"
        for p in results:
            img = p.get('image_url') or f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(p.get('product_name')))}&background=random"
            html += f"""
            <div style="flex: 1; min-width: 140px; background: rgba(255,255,255,0.7); border: 1px solid rgba(0,0,0,0.05); border-radius: 12px; padding: 12px; text-align: center;">
                <img src="{img}" style="width: 70px; height: 70px; object-fit: cover; border-radius: 8px; margin-bottom: 8px;">
                <h6 style="font-size: 0.85rem; font-weight: bold; margin: 0 0 5px 0; height: 32px; overflow: hidden;">{p['product_name']}</h6>
                <p style="color: #6366f1; font-weight: 800; font-size: 1.1rem; margin: 0 0 8px 0;">₹{p['price']}</p>
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 10px;">{p.get('category_name', 'General')}</div>
                <button style="background: #0f172a; color: white; border: none; padding: 6px 10px; border-radius: 6px; width: 100%; font-size: 0.8rem; cursor: pointer;" onclick="widgetAddToCart({p['product_id']})">Add to Cart</button>
            </div>
            """
        html += "</div>"
        return html
    except Exception as e: return f"Comparison error: {str(e)}"
    finally: cursor.close(); close_db_connection(conn)

def db_view_user_cart(user_id: int) -> str:
    if user_id == 0: return "Please log in to inspect your cart."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT c.quantity, p.product_name, p.price, p.image_url FROM cart c JOIN products p ON c.product_id = p.product_id WHERE c.user_id = %s", (user_id,))
    items = cursor.fetchall()
    cursor.close(); close_db_connection(conn)
    if not items: return "Your cart is currently empty."
    
    total = sum(item['price'] * item['quantity'] for item in items)
    html = "<div style='display:flex; flex-direction:column; gap:8px; margin-top:5px;'>"
    for item in items:
        img = item.get('image_url') or f"https://ui-avatars.com/api/?name={urllib.parse.quote(str(item.get('product_name')))}&background=random"
        html += f"""
        <div style="display: flex; gap: 10px; padding: 8px; background: rgba(255,255,255,0.7); border-radius: 10px; align-items: center;">
            <img src="{img}" style="width: 45px; height: 45px; object-fit: cover; border-radius: 6px;">
            <div style="flex: 1;">
                <b style="font-size: 0.85rem;">{item['product_name']}</b>
                <div style="font-size: 0.75rem; color: #64748b;">Qty: {item['quantity']} × ₹{item['price']}</div>
            </div>
            <div style="font-weight: bold; color: #6366f1;">₹{item['price'] * item['quantity']}</div>
        </div>
        """
    html += f"""
        <div style="margin-top: 6px; padding-top: 8px; border-top: 1px dashed #cbd5e1; display: flex; justify-content: space-between;">
            <b>Total:</b> <span style="font-weight: 800; color: #0f172a;">₹{total}</span>
        </div>
        <a href="cart.html" style="display: block; text-align: center; background: #6366f1; color: white; padding: 8px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 8px;">Go to Checkout</a>
    </div>
    """
    return html

def db_add_item_to_cart(user_id: int, product_name: str, quantity: int = 1) -> str:
    if user_id == 0: return "Please log in to add products to your cart."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT product_id, product_name FROM products WHERE product_name LIKE %s LIMIT 1", (f"%{product_name}%",))
    product = cursor.fetchone()
    if not product:
        cursor.close(); close_db_connection(conn)
        return f"Could not find '{product_name}' in the store."
        
    cursor.execute("SELECT quantity FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product['product_id']))
    if cursor.fetchone():
        cursor.execute("UPDATE cart SET quantity = quantity + %s WHERE user_id = %s AND product_id = %s", (quantity, user_id, product['product_id']))
    else:
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)", (user_id, product['product_id'], quantity))
        
    conn.commit(); cursor.close(); close_db_connection(conn)
    return f"✅ Added {quantity}x **{product['product_name']}** to your cart! <a href='cart.html' style='color:#6366f1; font-weight:bold;'>View Cart</a>"

def db_get_user_order_history(user_id: int) -> str:
    if user_id == 0: return "Please log in to view orders."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.total_amount, o.status, DATE_FORMAT(o.order_date, '%M %d, %Y') as formatted_date,
               GROUP_CONCAT(oi.product_name SEPARATOR ', ') as items_summary
        FROM orders o LEFT JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.user_id = %s GROUP BY o.order_id ORDER BY o.order_date DESC LIMIT 3
    """, (user_id,))
    orders = cursor.fetchall()
    cursor.close(); close_db_connection(conn)
    if not orders: return "You have no previous orders."
    
    html = "<div style='display:flex; flex-direction:column; gap:8px; margin-top:5px;'>"
    for o in orders:
        html += f"""
        <div style="background: rgba(255,255,255,0.7); border-left: 4px solid #6366f1; padding: 8px 12px; border-radius: 0 8px 8px 0;">
            <div style="display: flex; justify-content: space-between;">
                <b>Order #{o['order_id']}</b>
                <span style="font-size: 0.75rem; font-weight: bold;">{o['status'].upper()}</span>
            </div>
            <div style="font-size: 0.8rem; color: #475569;">Items: {o.get('items_summary', 'Catalog Items')}</div>
            <div style="color: #6366f1; font-weight: bold; margin-top: 2px;">₹{o['total_amount']}</div>
        </div>
        """
    html += "</div>"
    return html

def db_cancel_order(user_id: int, order_id: int) -> str:
    if user_id == 0: return "Please log in."
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE order_id = %s AND user_id = %s", (order_id, user_id))
    result = cursor.fetchone()
    if not result: 
        cursor.close(); close_db_connection(conn)
        return f"Order #{order_id} not found."
    if result['status'] == 'cancelled': 
        cursor.close(); close_db_connection(conn)
        return f"Order #{order_id} is already cancelled."
        
    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (order_id,))
    cursor.execute("UPDATE products p JOIN order_items oi ON p.product_id = oi.product_id SET p.stock = p.stock + oi.quantity WHERE oi.order_id = %s", (order_id,))
    conn.commit(); cursor.close(); close_db_connection(conn)
    return f"✅ Order #{order_id} has been successfully cancelled."

# =====================================================================
# 3. MULTI-AGENT GRAPH ARCHITECTURE
# =====================================================================

def get_sales_tools(safe_user_id: int):
    @tool
    def search_catalog(search_keywords: str, category: Optional[str] = None, max_price: Optional[int] = None) -> str:
        """
        Search catalog with full synonym flexibility. 
        Pass multiple space-separated synonyms in `search_keywords` (e.g., 'phone mobile smartphone iphone').
        """
        return db_smart_product_search(search_keywords=search_keywords, category=category, max_price=max_price, user_id=safe_user_id)

    @tool
    def compare_products(product_a: str, product_b: str) -> str:
        """Compare two items side-by-side."""
        return db_compare_products(product_a, product_b, safe_user_id)

    @tool
    def view_cart() -> str:
        """View the current shopping cart contents and total."""
        return db_view_user_cart(safe_user_id)

    @tool
    def add_to_cart(product_name: str, quantity: int = 1) -> str:
        """Add an item into the customer's cart."""
        return db_add_item_to_cart(safe_user_id, product_name, quantity)

    @tool
    def get_order_history() -> str:
        """View the customer's recent orders and statuses."""
        return db_get_user_order_history(safe_user_id)

    @tool
    def cancel_order(order_id: int) -> str:
        """Cancel an order using its order ID."""
        return db_cancel_order(safe_user_id, order_id)

    return [search_catalog, compare_products, view_cart, add_to_cart, get_order_history, cancel_order]

class RouteDefinition(BaseModel):
    next_node: Literal["Sales", "Support"] = Field(
        description="Route to 'Sales' for any shopping, search, products, cart, or order actions. Route to 'Support' for greetings, policies, warranties, or shipping."
    )

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next_node: str
    user_id: int

def supervisor_node(state: AgentState):
    # Fast, structured intent routing using your authorized Groq tier model
    llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    system_prompt = (
        "You are the Supervisor for AI Store. Classify the customer query:\n"
        "- Route to 'Sales': Buying advice, looking for items (phones, laptops, accessories, etc.), cart management, orders.\n"
        "- Route to 'Support': Greetings ('hi', 'hello'), returns, warranties, delivery times, shipping costs, FAQs."
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = llm.with_structured_output(RouteDefinition).invoke(messages)
    return {"next_node": response.next_node}

def sales_node(state: AgentState):
    user_ctx = db_get_user_context(state["user_id"])
    store_meta = get_store_metadata()
    categories_str = ", ".join(store_meta["categories"]) if store_meta["categories"] else "Electronics, Laptops, Smartphones, Accessories"

    sales_prompt = f"""You are an elite, proactive AI Shopping Consultant at AI Store.
{user_ctx}
STORE DEPARTMENTS: [{categories_str}]

CRITICAL CAPABILITIES:
1. SYNONYM MASTERY: You understand natural synonyms instinctively.
   - If a customer says 'mobile', 'cell', 'phone', or 'handset', you search for smartphones.
   - If they say 'laptop', 'notebook', or 'mac', you search computers.
   - When calling `search_catalog`, always populate `search_keywords` with relevant synonyms (e.g. search_keywords="phone mobile smartphone iphone").
2. CONVERSATIONAL CONSULTANT:
   - When the search tool displays products, DO NOT stay silent. Explain why these options fit the user's request.
   - Ask clarifying questions if needed (e.g. "Are you looking for high battery life or gaming performance?").
   - Guide them smoothly to add items to their cart.
"""
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.3)
    agent = create_react_agent(llm, get_sales_tools(state["user_id"]))
    
    # Version-agnostic system prompt injection
    input_messages = [SystemMessage(content=sales_prompt)] + state["messages"]
    result = agent.invoke({"messages": input_messages})
    new_messages = result["messages"][len(input_messages):]
    return {"messages": new_messages}

def support_node(state: AgentState):
    support_prompt = """You are the Support Concierge for AI Store.
- If the customer says hello or introduces themselves, greet them warmly and invite them to explore products or check their orders.
- If they ask about policies, shipping timelines, returns, or store warehouse location, use `search_knowledge_base` and explain the answer conversationally.
- Never answer with a raw data dump; be friendly, clear, and reassuring."""

    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.2)
    agent = create_react_agent(llm, [search_knowledge_base])
    
    input_messages = [SystemMessage(content=support_prompt)] + state["messages"]
    result = agent.invoke({"messages": input_messages})
    new_messages = result["messages"][len(input_messages):]
    return {"messages": new_messages}

# Build the Graph
builder = StateGraph(AgentState)
builder.add_node("Supervisor", supervisor_node)
builder.add_node("Sales", sales_node)
builder.add_node("Support", support_node)

builder.add_edge(START, "Supervisor")
builder.add_conditional_edges("Supervisor", lambda state: state["next_node"], {"Sales": "Sales", "Support": "Support"})
builder.add_edge("Sales", END)
builder.add_edge("Support", END)

memory = MemorySaver()
multi_agent_graph = builder.compile(checkpointer=memory)

# =====================================================================
# 4. SSE REAL-TIME STREAMING ENDPOINT
# =====================================================================

@router.post("")
async def process_chat(request: ChatRequest):
    safe_user_id = request.user_id if request.user_id else 0

    async def generate_stream():
        config = {"configurable": {"thread_id": str(safe_user_id)}}
        initial_state = {"messages": [HumanMessage(content=request.message)], "user_id": safe_user_id}

        try:
            async for event in multi_agent_graph.astream_events(initial_state, config, version="v2"):
                kind = event["event"]
                
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk: 
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
                        
                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    yield f"data: {json.dumps({'type': 'thought', 'content': f'Analyzing catalog via {tool_name}...'})}\n\n"
                    
                elif kind == "on_tool_end":
                    tool_name = event["name"]
                    output = event["data"].get("output", "")
                    if tool_name not in ["search_knowledge_base", "RouteDefinition"]:
                        yield f"data: {json.dumps({'type': 'ui_block', 'content': str(output)})}\n\n"

        except Exception as e:
            print("Chat Agent Runtime Error:", str(e))
            yield f"data: {json.dumps({'type': 'text', 'content': f'Encountered an issue: {str(e)}'})}\n\n"
        finally:
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")