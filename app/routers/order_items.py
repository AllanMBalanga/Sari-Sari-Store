#TODO if payment_method = "balance"
#check if balance.total > subtotal
#deduct balance

#TODO item.quantity
#check if quantity == 0
#check if order_item.quantity - item.quantity < 0

#TODO update
#update orders.store_notes (customer balance not sufficient)
#update orders.total

from fastapi import status, HTTPException, Depends, APIRouter
from ..body import OrderItem, OrderItemPatch, TokenData
from ..response import OrderItemAdminResponse, OrderItemResponse
from ..database import Database
from ..queries import Queries
from ..status_codes import Validator
from ..oauth2 import get_current_user
from typing import List, Union

router = APIRouter(
    prefix="/customers/{customer_id}/orders/{order_id}/order_items",
    tags=["Order Items"]
)

db = Database()
validate = Validator()
query = Queries(db)

@router.get("/", response_model=List[Union[OrderItemAdminResponse, OrderItemResponse]])
def get_order_items(customer_id: int, order_id: int, current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["admin", "user"])
    if current_user.role == "user":
        validate.logged_in_user(current_user.id, customer_id)

    existing_customer = query.get_request("customers", customer_id)
    validate.customer_exists(existing_customer, customer_id)

    existing_order = query.get_orders(order_id, customer_id)
    validate.order_exists(existing_order, order_id)

    order_items = query.get_order_items(order_id=order_id)

    return query.response_list(current_user, order_items, OrderItemResponse, OrderItemAdminResponse)

@router.post("/", response_model=OrderItemAdminResponse, status_code=status.HTTP_201_CREATED)
def create_order_item(customer_id: int, order_id: int, order_item: OrderItem, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_order = query.get_orders(order_id, customer_id)
        validate.order_exists(existing_order, order_id)

        existing_item = query.get_request("items", order_item.item_id)
        validate.item_exists(existing_item, order_item.item_id)

        if existing_item["quantity"] <= 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Item out of stock")
        if order_item.quantity > existing_item["quantity"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ordered quantity exceeds stock")

        subtotal = order_item.quantity * existing_item["selling_price"]

        if existing_order["payment_method"] == "balance":
            balance = query.get_request("balances", customer_id)
            validate.balance_exists(balance, customer_id)
            if balance["total"] < subtotal:
                store_notes = "Customer balance not sufficient"
                db.cursor.execute("UPDATE orders SET store_notes = %s WHERE id = %s", (store_notes, order_id))
                db.conn.commit()
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Customer balance not sufficient")
            # Deduct balance
            new_balance = balance["total"] - subtotal
            db.cursor.execute("UPDATE balances SET total = %s WHERE id = %s", (new_balance, balance["id"]))

        db.cursor.execute("""
            INSERT INTO order_items (order_id, item_id, quantity, unit_price)
            VALUES (%s, %s, %s, %s)
        """, (order_id, order_item.item_id, order_item.quantity, existing_item["selling_price"]))

        # Decrease item stock
        new_quantity = existing_item["quantity"] - order_item.quantity
        db.cursor.execute("UPDATE items SET quantity = %s WHERE id = %s", (new_quantity, order_item.item_id))

        # Update order total
        new_total = existing_order["total"] + subtotal
        db.cursor.execute("UPDATE orders SET total = %s WHERE id = %s", (new_total, order_id))

        db.conn.commit()

        created = query.created_request("order_items")
        return OrderItemAdminResponse(**created)

    except HTTPException:
        raise

    except Exception as e:
        print(e)
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.get("/{order_item_id}", response_model=Union[OrderItemAdminResponse, OrderItemResponse])
def get_order_item(customer_id: int, order_id: int, order_item_id: int, current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["admin", "user"])
    if current_user.role == "user":
        validate.logged_in_user(current_user.id, customer_id)

    existing_customer = query.get_request("customers", customer_id)
    validate.customer_exists(existing_customer, customer_id)

    existing_order = query.get_orders(order_id, customer_id)
    validate.order_exists(existing_order, order_id)
    
    existing_order_item = query.get_order_items(order_item_id, order_id)
    validate.order_item_exists(existing_order_item, order_item_id)

    return query.response(current_user, existing_order_item, OrderItemResponse, OrderItemAdminResponse)

@router.put("/{order_item_id}", response_model=OrderItemAdminResponse)
def put_order_item(customer_id: int, order_id: int, order_item_id: int, order_item: OrderItem, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_order = query.get_orders(order_id, customer_id)
        validate.order_exists(existing_order, order_id)

        existing_item = query.get_request("items", order_item.item_id)
        validate.item_exists(existing_item, order_item.item_id)

        existing_order_item = query.get_order_items(order_item_id, order_id)
        validate.order_item_exists(existing_order_item, order_item_id)

        #Item quantity changes
        restored_quantity = existing_item["quantity"] + existing_order_item["quantity"]
        if order_item.quantity > restored_quantity:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Ordered quantity exceeds available stock")
        new_quantity = restored_quantity - order_item.quantity
        db.cursor.execute("UPDATE items SET quantity = %s WHERE id = %s", (new_quantity, order_item.item_id))

        db.cursor.execute("""
            UPDATE order_items SET item_id = %s, quantity = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND order_id = %s AND deleted_at IS NULL
        """, (order_item.item_id, order_item.quantity, order_item_id, order_id))
        db.conn.commit()

        updated = query.get_order_items(order_item_id, order_id)
        return OrderItemAdminResponse(**updated)

    except HTTPException:
        raise
    except Exception as e:
        print(e)
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.patch("/{order_item_id}", response_model=OrderItemAdminResponse)
def patch_order_item(customer_id: int, order_id: int, order_item_id: int, order_item: OrderItemPatch, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)
        
        existing_order = query.get_orders(order_id, customer_id)
        validate.order_exists(existing_order, order_id)

        existing_item = query.get_request("items", order_item.item_id)
        validate.item_exists(existing_item, order_item.item_id)

        existing_order_item = query.get_order_items(order_item_id, order_id)
        validate.order_item_exists(existing_order_item, order_item_id)

        excluded_values = order_item.dict(exclude_unset=True)
        validate.excluded_values(excluded_values)

        old_quantity = existing_order_item["quantity"]
        old_item_id = existing_order_item["item_id"]

        # Determine updated quantity
        new_quantity = excluded_values.get("quantity", old_quantity)
        new_item_id = excluded_values.get("item_id", old_item_id)

        # If item_id or quantity changed, do adjustments
        if new_quantity != old_quantity or new_item_id != old_item_id:
            # Step 1: Restore stock of old item
            old_item = query.get_request("items", old_item_id)
            db.cursor.execute("UPDATE items SET quantity = quantity + %s WHERE id = %s", (old_quantity, old_item_id))

            # Step 2: Deduct stock from new item
            new_item = old_item if old_item_id == new_item_id else query.get_request("items", new_item_id)

            if new_item["quantity"] < new_quantity:
                raise HTTPException(status_code=400, detail="Ordered quantity exceeds available stock")

            db.cursor.execute("UPDATE items SET quantity = quantity - %s WHERE id = %s", (new_quantity, new_item_id))
        
        query.dynamic_patch_query("order_items", excluded_values, order_item_id, current_user.id, order_id)
        db.conn.commit()

        updated = query.get_order_items(order_item_id, order_id)
        return OrderItemAdminResponse(**updated)

    except HTTPException:
        raise
    except Exception as e:
        print(e)
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.delete("/{order_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete_order_item(customer_id: int, order_id: int, order_item_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_order = query.get_orders(order_id, customer_id)
        validate.order_exists(existing_order, order_id)

        existing_order_item = query.get_order_items(order_item_id, order_id)
        validate.order_item_exists(existing_order_item, order_item_id)

        query.hard_delete("order_items", order_item_id, order_id=order_id)
        db.conn.commit()

        return

    except Exception as e:
        print(e)
        db.conn.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.delete("/{order_item_id}/delete", status_code=status.HTTP_200_OK)
def soft_delete_order_item(customer_id: int, order_id: int, order_item_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_order = query.get_orders(order_id, customer_id)
        validate.order_exists(existing_order, order_id)

        existing_order_item = query.get_order_items(order_item_id, order_id)
        validate.order_item_exists(existing_order_item, order_item_id)

        query.soft_delete("order_items", current_user.id, order_item_id, order_id=order_id)
        db.conn.commit()

        return {"detail": f"Order item with id {order_item_id} softly deleted."}

    except Exception as e:
        print(e)
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
