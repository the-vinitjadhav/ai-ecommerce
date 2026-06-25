from fastapi import APIRouter
from backend.database import get_db_connection, close_db_connection
from backend.models import Product

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.post("/products")
def add_product(product: Product):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO products (product_name, description, price, stock, category_id, category_name, image_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (product.product_name, product.description, product.price, product.stock, product.category_id, product.category_name, product.image_url))
    conn.commit()
    product_id = cursor.lastrowid
    cursor.close()
    close_db_connection(conn)
    return {"product_id": product_id, "message": "Product added successfully"}

@router.get("/orders")
def get_all_orders():
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.user_id, o.total_amount, o.status, o.order_date, u.name
        FROM orders o JOIN users u ON o.user_id = u.user_id
        ORDER BY o.order_date DESC
    """)
    orders = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    return orders