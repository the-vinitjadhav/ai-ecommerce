from fastapi import APIRouter, UploadFile, File
from backend.database import get_db_connection, close_db_connection
from backend.models import Product
import os
import shutil

router = APIRouter(prefix="/api/admin", tags=["Admin"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
IMAGE_DIR = os.path.join(BASE_DIR, "frontend", "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    file_location = os.path.join(IMAGE_DIR, file.filename)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    return {"url": f"images/{file.filename}"}

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

@router.put("/products/{product_id}")
def update_product(product_id: int, product: Product):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products 
            SET product_name = %s, price = %s, stock = %s, category_name = %s, image_url = %s
            WHERE product_id = %s
        """, (product.product_name, product.price, product.stock, product.category_name, product.image_url, product_id))
        conn.commit()
        return {"message": "Product updated successfully"}
    except Exception as e:
        return {"error": f"Failed to update product: {str(e)}"}
    finally:
        cursor.close()
        close_db_connection(conn)

@router.delete("/products/{product_id}")
def delete_product(product_id: int):
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE product_id = %s", (product_id,))
        cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))
        conn.commit()
        return {"message": "Product deleted successfully"}
    except Exception as e:
        return {"error": f"Failed to delete product: {str(e)}"}
    finally:
        cursor.close()
        close_db_connection(conn)