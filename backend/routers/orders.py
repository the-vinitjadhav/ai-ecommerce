from fastapi import APIRouter
from backend.database import get_db_connection, close_db_connection
from backend.models import Order

router = APIRouter(prefix="/api/orders", tags=["Orders"])

@router.get("/{user_id}")
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

@router.post("/{user_id}")
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

@router.put("/cancel/{user_id}/{order_id}")
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