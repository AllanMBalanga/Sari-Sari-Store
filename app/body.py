from pydantic import BaseModel, EmailStr
from typing import Literal, Optional

#POST/PUT
class Customer(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class Balance(BaseModel):
    total: float

class Transaction(BaseModel):
    type: Literal["withdraw", "deposit"] = "deposit"
    amount: float

class Order(BaseModel):
    payment_method: Literal["cash", "balance"] = "cash"
    note: str

class Item(BaseModel):
    name: str
    quantity: int
    orig_price: float
    selling_price: float

class OrderItem(BaseModel):
    quantity: int

#PATCH
class CustomerPatch(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class BalancePatch(BaseModel):
    total: Optional[float] = None

class TransactionPatch(BaseModel):
    type: Optional[Literal["withdraw", "deposit"]] = "deposit"
    amount: Optional[float] = None

class OrderPatch(BaseModel):
    payment_method: Optional[Literal["cash", "balance"]] = "cash"
    note: Optional[str] = None

class ItemPatch(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    orig_price: Optional[float] = None
    selling_price: Optional[float] = None

class OrderItemPatch(BaseModel):
    quantity: Optional[int] = None



#Token
class LoggedInToken(BaseModel):
    user_id: int
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    id: Optional[int] = None
    role: Optional[Literal["user", "admin"]] = None