from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime
 
#Customer's Responses
class CustomerResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    created_at: datetime

class BalanceResponse(BaseModel):
    id: int
    customer_id: int
    total: float
    created_at: datetime

class CustomerBalanceResponse(BaseModel):
    customer: CustomerResponse
    balance: BalanceResponse

class TransactionResponse(BaseModel):
    id: int
    customer_id: int
    balance_id: int
    type: Literal["withdraw", "deposit"]
    amount: int
    created_at: datetime

#TRANSACTIONS POST
class TransactionBalanceResponse(BaseModel):
    transaction: TransactionResponse
    balance: BalanceResponse


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    payment_method: Literal["cash", "balance"]
    total: float
    store_notes: str
    created_at: datetime

class ItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    selling_price: float

class OrderItemResponse(BaseModel):
    id: int
    order_id: int
    item_id: int
    quantity: int
    unit_price: float
    subtotal: float


#Admin's Responses
class CustomerAdminResponse(CustomerResponse):
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None

class BalanceAdminResponse(BalanceResponse):
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None

class CustomerBalanceAdminResponse(BaseModel):
    customer: CustomerAdminResponse
    balance: BalanceAdminResponse

class TransactionAdminResponse(TransactionResponse):
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None

class TransactionBalanceAdminResponse(BaseModel):
    transaction: TransactionAdminResponse
    balance: BalanceAdminResponse

class OrderAdminResponse(OrderResponse):
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None

class ItemAdminResponse(BaseModel):
    id: int
    name: str
    quantity: int
    sold: int
    orig_price: float
    total_orig_price: float
    selling_price: float
    total_selling_price: float
    profit: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None

class OrderItemAdminResponse(OrderItemResponse):
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
