from fastapi import APIRouter, status, HTTPException, Depends
from ..oauth2 import get_current_user
from ..body import TokenData, Order, OrderPatch
from ..database import Database
from ..queries import Queries
from ..response import OrderAdminResponse, OrderResponse
from ..status_codes import Validator
from typing import List, Union

router = APIRouter(
    prefix="/customers/{customer_id}/orders",
    tags=["Orders"]
)

db = Database()
validate = Validator()
query = Queries(db)

@router.get("/", response_model=List[Union[OrderAdminResponse, OrderResponse]])
def get_orders(customer_id: int, current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["admin", "user"])
    if current_user.role == "user":
        validate.logged_in_user(current_user.id, customer_id)

    existing_customer = query.get_request("customers", customer_id)
    validate.customer_exists(existing_customer, customer_id)

    orders = query.get_orders(customer_id=customer_id)

    return query.response_list(current_user, orders, OrderResponse, OrderAdminResponse)

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(customer_id: int, order: Order, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["user"])
        validate.logged_in_user(current_user.id, customer_id)
    
        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        db.cursor.execute("INSERT INTO orders (customer_id, payment_method, note) VALUES (%s, %s, %s)", (
            customer_id, order.payment_method, order.note
            )
        )
        db.conn.commit()

        created_order= query.created_request("orders")

        return OrderResponse(**created_order)
    
    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
    
@router.get("/{order_id}", response_model=Union[OrderAdminResponse, OrderResponse])
def get_order(customer_id: int, order_id: int, current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["user", "admin"])
    if current_user.role == "user":
        validate.logged_in_user(current_user.id, customer_id)

    existing_customer = query.get_request("customers", customer_id)
    validate.customer_exists(existing_customer, customer_id)

    existing_order = query.get_orders(order_id, customer_id)
    validate.order_exists(existing_order, order_id)

    return query.response(current_user, existing_order, OrderResponse, OrderAdminResponse)

@router.put("/{order_id}", response_model=Union[OrderResponse, OrderAdminResponse])
def put_orders(customer_id: int, order_id: int, order: Order, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["user", "admin"])
        if current_user.role == "user":
            validate.logged_in_user(current_user.id, customer_id)

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_order = query.get_orders(order_id, customer_id)
        validate.order_exists(existing_order, order_id)

        #TODO if existing_order[payment_method] == "cash" and order.payment_method == "balance"
        #check if balance.total > subtotal
        #deduct balance

        db.cursor.execute("UPDATE orders SET payment_method = %s, note = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND customer_id = %s AND deleted_at IS NULL", (
            order.payment_method, order.note, order_id, customer_id
            )
        )
        db.conn.commit()

        updated_order = query.get_orders(order_id, customer_id)

        return query.response(current_user, updated_order, OrderResponse, OrderAdminResponse)
    
    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")


@router.patch("/{order_id}", response_model=Union[OrderResponse, OrderAdminResponse])
def patch_orders(customer_id: int, order_id: int, order: OrderPatch, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["user", "admin"])
        if current_user.role == "user":
            validate.logged_in_user(current_user.id, customer_id)

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_order = query.get_orders(order_id, customer_id)
        validate.order_exists(existing_order, order_id)

        excluded_values = order.dict(exclude_unset=True)
        validate.excluded_values(excluded_values)

        #TODO if order.payment_method in excluded_values
        #if existing_order[payment_method] == "cash" and order.payment_method == "balance"
        #check if balance.total > subtotal
        #deduct balance

        query.dynamic_patch_query("orders", excluded_values, order_id, current_user.id, customer_id)
        db.conn.commit()

        updated_order = query.get_orders(order_id, customer_id)

        return query.response(current_user, updated_order, OrderResponse, OrderAdminResponse)
    
    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete(customer_id: int, order_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_order = query.get_orders(order_id, customer_id)
        validate.order_exists(existing_order, order_id)

        query.hard_delete("orders", order_id, customer_id)
        db.conn.commit()
        
        return 
    
    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.delete("/{order_id}/delete", status_code=status.HTTP_200_OK)
def soft_delete(customer_id: int, order_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["user", "admin"])
        if current_user.role == "user":
            validate.logged_in_user(current_user.id, customer_id)

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_order = query.get_orders(order_id, customer_id)
        validate.order_exists(existing_order, order_id)

        query.soft_delete("orders", current_user.id, order_id, customer_id)
        db.conn.commit()
        
        return {"detail": f"Order with {order_id} softly deleted successfully"}
    
    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
