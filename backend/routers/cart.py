from fastapi import APIRouter
from backend.database import get_db_connection, close_db_connection
from backend.models import CartItem

router = APIRouter(prefix="/api/cart", tags=["Cart"])

@router.get("/{user_id}")
def get_cart(user_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.cart_id, c.product_id, p.product_name, p.price, c.quantity, 
               (p.price * c.quantity) AS total_price
        FROM cart c JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    """, (user_id,))
    items = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    return items

@router.post("/{user_id}")
def add_to_cart(user_id: int, item: CartItem):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM cart WHERE user_id = %s AND product_id = %s", (user_id, item.product_id))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("UPDATE cart SET quantity = quantity + %s WHERE user_id = %s AND product_id = %s", (item.quantity, user_id, item.product_id))
    else:
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)", (user_id, item.product_id, item.quantity))
    conn.commit()
    cursor.close()
    close_db_connection(conn)
    return {"message": "Item added to cart"}

@router.delete("/{user_id}/{product_id}")
def remove_item_from_cart(user_id: int, product_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
        conn.commit()
        return {"message": "Item successfully removed"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        close_db_connection(conn)