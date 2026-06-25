from fastapi import APIRouter
from backend.database import get_db_connection, close_db_connection

router = APIRouter(prefix="/api/products", tags=["Products"])

@router.get("/")
def get_all_products():
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    close_db_connection(conn)
    return products

@router.get("/{product_id}")
def get_product(product_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    close_db_connection(conn)
    if not product:
        return {"error": "Product not found"}
    return product