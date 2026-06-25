from pydantic import BaseModel
from typing import Optional

class UserRegister(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class CartItem(BaseModel):
    product_id: int
    quantity: int = 1

class Order(BaseModel):
    user_id: int
    total_amount: float
    status: str = "pending"

class Product(BaseModel):
    product_name: str
    description: Optional[str] = None
    price: float
    stock: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    image_url: Optional[str] = None

class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None

class ChatContext(BaseModel):
    page: str
    cart_items: str

class ChatRequest(BaseModel):
    user_id: int
    message: str
    context: Optional[ChatContext] = None