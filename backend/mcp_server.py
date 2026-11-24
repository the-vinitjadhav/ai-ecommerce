import json
import os
from contextvars import ContextVar
from typing import Optional

import jwt
from fastmcp import FastMCP

try:
    from fastmcp.tools import ToolResult
except ImportError:
    from fastmcp.tools.tool import ToolResult

try:
    from fastmcp.server.dependencies import get_http_headers
except ImportError:
    def get_http_headers() -> dict:
        return {}

from backend.database import get_db_connection, close_db_connection

mcp = FastMCP("AI Store")

# In-process request context set by backend/routers/chat.py
current_user_id: ContextVar[int] = ContextVar("current_user_id", default=0)


def _resolve_user_id() -> int:
    """Resolve user_id from in-process ContextVar or HTTP Bearer JWT (never from LLM args)."""
    uid = current_user_id.get()
    if uid:
        return uid

    headers = get_http_headers() or {}
    auth_header = headers.get("authorization") or headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        secret = os.getenv("SECRET_KEY", "")
        algo = os.getenv("ALGORITHM", "HS256")
        if secret:
            try:
                payload = jwt.decode(token, secret, algorithms=[algo])
                return int(payload.get("user_id") or payload.get("sub") or 0)
            except Exception:
                return 0
    return 0


def _serialize_product(p: dict) -> dict:
    return {
        "product_id": int(p["product_id"]),
        "product_name": str(p.get("product_name", "")),
        "price": float(p.get("price", 0)),
        "category_name": str(p.get("category_name") or "Featured"),
        "image_url": p.get("image_url") or "",
    }


# =====================================================================
# MCP RESOURCE: LIVE STORE POLICIES
# =====================================================================

@mcp.resource("store://policies")
def list_store_policies() -> str:
    """Exposes all live store policies from MySQL as a readable MCP resource."""
    conn = get_db_connection()
    if not conn:
        return json.dumps({"error": "Policy database unavailable."})
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT topic, content FROM store_policies")
        return json.dumps(cursor.fetchall())
    finally:
        cursor.close()
        close_db_connection(conn)


# =====================================================================
# SUPPORT TOOL: ZERO-RAM LEXICAL RAG
# =====================================================================

@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """Search live store policies, shipping rules, returns, warranties, and FAQs."""
    conn = get_db_connection()
    if not conn:
        return "Store policies are temporarily offline."
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT topic, content FROM store_policies")
        policies = cursor.fetchall()
        if not policies:
            return "No store policies found."

        query_words = set(query.lower().split())
        scored = []
        for p in policies:
            doc_text = f"{p['topic']} Policy: {p['content']}"
            score = sum(1 for w in query_words if w in doc_text.lower())
            scored.append((score, doc_text))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_docs = [doc for score, doc in scored if score > 0][:2]
        if not best_docs:
            return "\n\n".join(f"{p['topic']}: {p['content']}" for p in policies[:2])
        return "\n\n".join(best_docs)
    except Exception as e:
        return f"Error reading policies: {str(e)}"
    finally:
        cursor.close()
        close_db_connection(conn)


# =====================================================================
# SALES TOOLS: CATALOG, CART & ORDERS
# =====================================================================

@mcp.tool()
def search_catalog(
    search_keywords: str,
    category: Optional[str] = None,
    max_price: Optional[int] = None,
) -> ToolResult:
    """Search store catalog with synonyms (e.g., search_keywords='phone mobile smartphone'). Call at most once per turn."""
    conn = get_db_connection()
    if not conn:
        return ToolResult(content="Database connection unavailable.")
    cursor = conn.cursor(dictionary=True)
    try:
        sql = "SELECT * FROM products WHERE 1=1"
        params = []

        if max_price is not None:
            sql += " AND price <= %s"
            params.append(max_price)
        if category and category.lower() not in {"all", "any"}:
            sql += " AND category_name LIKE %s"
            params.append(f"%{category}%")

        cursor.execute(sql, tuple(params))
        candidates = cursor.fetchall()
        if not candidates:
            cursor.execute("SELECT * FROM products LIMIT 15")
            candidates = cursor.fetchall()
        if not candidates:
            return ToolResult(content="Catalog is currently empty.")

        stop_words = {
            "suggest", "recommend", "show", "give", "find", "best", "good",
            "cheap", "buy", "product", "products", "item", "items", "for",
            "the", "with", "and", "me", "some", "a", "an",
        }
        raw_words = search_keywords.replace(",", " ").replace("/", " ").lower().split()
        target_tokens = [w.strip() for w in raw_words if w.strip() and w.strip() not in stop_words]

        scored_products = []
        for p in candidates:
            name = (p.get("product_name") or "").lower()
            cat = (p.get("category_name") or "").lower()
            desc = (p.get("description") or "").lower()
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
        results = [item[1] for item in scored_products[:4]] or candidates[:4]

        serialized = [_serialize_product(p) for p in results]
        summary = "; ".join(f"{p['product_name']} (₹{p['price']:.0f})" for p in serialized)

        return ToolResult(
            content=f"Found {len(serialized)} items: {summary}. Cards are displayed on the user's screen.",
            structured_content={"ui_type": "products", "items": serialized},
        )
    except Exception as e:
        return ToolResult(content=f"Error querying products: {str(e)}", is_error=True)
    finally:
        cursor.close()
        close_db_connection(conn)


@mcp.tool()
def compare_products(product_a: str, product_b: str) -> ToolResult:
    """Compare two products side-by-side by name or keyword."""
    conn = get_db_connection()
    if not conn:
        return ToolResult(content="Database connection unavailable.")
    cursor = conn.cursor(dictionary=True)
    try:
        results = []
        for term in (product_a, product_b):
            if not term:
                continue
            cursor.execute(
                "SELECT * FROM products WHERE product_name LIKE %s OR description LIKE %s LIMIT 1",
                (f"%{term}%", f"%{term}%"),
            )
            p = cursor.fetchone()
            if p:
                results.append(_serialize_product(p))

        if len(results) < 2:
            return ToolResult(content="Could not find both products in the catalog to compare.")

        summary = (
            f"Comparing {results[0]['product_name']} (₹{results[0]['price']:.0f}) "
            f"vs {results[1]['product_name']} (₹{results[1]['price']:.0f}). Comparison cards displayed."
        )
        return ToolResult(
            content=summary,
            structured_content={"ui_type": "comparison", "items": results},
        )
    except Exception as e:
        return ToolResult(content=f"Comparison error: {str(e)}", is_error=True)
    finally:
        cursor.close()
        close_db_connection(conn)


@mcp.tool()
def view_cart() -> ToolResult:
    """View the logged-in customer's current shopping cart and total."""
    user_id = _resolve_user_id()
    if user_id == 0:
        return ToolResult(content="Customer is not logged in. Ask them to log in to view their cart.")

    conn = get_db_connection()
    if not conn:
        return ToolResult(content="Database connection unavailable.")
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT c.quantity, p.product_name, p.price, p.image_url
            FROM cart c JOIN products p ON c.product_id = p.product_id
            WHERE c.user_id = %s
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        if not rows:
            return ToolResult(content="The user's cart is currently empty.")

        items = [
            {
                "product_name": str(r["product_name"]),
                "quantity": int(r["quantity"]),
                "price": float(r["price"]),
                "subtotal": float(r["price"]) * int(r["quantity"]),
                "image_url": r.get("image_url") or "",
            }
            for r in rows
        ]
        total = sum(i["subtotal"] for i in items)
        summary = f"Cart has {len(items)} item(s), total ₹{total:.0f}. Cart card displayed."
        return ToolResult(
            content=summary,
            structured_content={"ui_type": "cart", "items": items, "total": total},
        )
    finally:
        cursor.close()
        close_db_connection(conn)


@mcp.tool()
def add_to_cart(product_name: str, quantity: int = 1) -> str:
    """Add a product into the logged-in customer's shopping cart."""
    user_id = _resolve_user_id()
    if user_id == 0:
        return "Customer must be logged in to add items to their cart."
    if quantity < 1:
        return "Quantity must be at least 1."

    conn = get_db_connection()
    if not conn:
        return "Database connection unavailable."
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT product_id, product_name FROM products WHERE product_name LIKE %s LIMIT 1",
            (f"%{product_name}%",),
        )
        product = cursor.fetchone()
        if not product:
            return f"Could not locate '{product_name}' in store catalog."

        cursor.execute(
            "SELECT quantity FROM cart WHERE user_id = %s AND product_id = %s",
            (user_id, product["product_id"]),
        )
        if cursor.fetchone():
            cursor.execute(
                "UPDATE cart SET quantity = quantity + %s WHERE user_id = %s AND product_id = %s",
                (quantity, user_id, product["product_id"]),
            )
        else:
            cursor.execute(
                "INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)",
                (user_id, product["product_id"], quantity),
            )
        conn.commit()
        return f"Successfully added {quantity}x {product['product_name']} to cart."
    finally:
        cursor.close()
        close_db_connection(conn)


@mcp.tool()
def get_order_history() -> ToolResult:
    """View the logged-in customer's 3 most recent orders and statuses."""
    user_id = _resolve_user_id()
    if user_id == 0:
        return ToolResult(content="Customer must log in to view orders.")

    conn = get_db_connection()
    if not conn:
        return ToolResult(content="Database connection unavailable.")
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT o.order_id, o.total_amount, o.status,
                   DATE_FORMAT(o.order_date, '%M %d, %Y') AS formatted_date,
                   GROUP_CONCAT(oi.product_name SEPARATOR ', ') AS items_summary
            FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.user_id = %s
            GROUP BY o.order_id
            ORDER BY o.order_date DESC
            LIMIT 3
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        if not rows:
            return ToolResult(content="User has no order history.")

        orders = [
            {
                "order_id": int(o["order_id"]),
                "status": str(o["status"]),
                "total_amount": float(o["total_amount"]),
                "formatted_date": str(o.get("formatted_date") or ""),
                "items_summary": str(o.get("items_summary") or "Catalog Items"),
            }
            for o in rows
        ]
        summary = "; ".join(f"Order #{o['order_id']} ({o['status']}, ₹{o['total_amount']:.0f})" for o in orders)
        return ToolResult(
            content=f"Recent orders: {summary}. Order cards displayed.",
            structured_content={"ui_type": "orders", "orders": orders},
        )
    finally:
        cursor.close()
        close_db_connection(conn)


@mcp.tool()
def cancel_order(order_id: int) -> str:
    """Cancel a customer's order using its integer order ID and restore stock."""
    user_id = _resolve_user_id()
    if user_id == 0:
        return "Customer must log in to cancel an order."

    conn = get_db_connection()
    if not conn:
        return "Database connection unavailable."
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT status FROM orders WHERE order_id = %s AND user_id = %s",
            (order_id, user_id),
        )
        result = cursor.fetchone()
        if not result:
            return f"Order #{order_id} not found."
        if result["status"] == "cancelled":
            return f"Order #{order_id} is already cancelled."

        cursor.execute("UPDATE orders SET status = 'cancelled' WHERE order_id = %s", (order_id,))
        cursor.execute(
            """
            UPDATE products p
            JOIN order_items oi ON p.product_id = oi.product_id
            SET p.stock = p.stock + oi.quantity
            WHERE oi.order_id = %s
            """,
            (order_id,),
        )
        conn.commit()
        return f"Order #{order_id} has been cancelled and stock restored."
    finally:
        cursor.close()
        close_db_connection(conn)