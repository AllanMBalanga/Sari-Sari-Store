from functools import total_ordering
from fastapi import APIRouter, status, HTTPException, Depends
from ..oauth2 import get_current_user
from ..body import Item, ItemPatch, TokenData
from ..database import Database
from ..queries import Queries
from ..response import ItemAdminResponse, ItemResponse
from ..status_codes import Validator
from typing import List, Union

router = APIRouter(
    prefix="/items",
    tags=["Items"]
)

db = Database()
validate = Validator()
query = Queries(db)

@router.get("/", response_model=List[Union[ItemResponse, ItemAdminResponse]])
def get_items(current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["admin", "user"])

    items = query.get_request("items")

    return query.response_list(current_user, items, ItemResponse, ItemAdminResponse)

 
@router.post("/", response_model=ItemAdminResponse, status_code=status.HTTP_201_CREATED)
def create_customer(item: Item, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        # total_orig_price = item.quantity * item.orig_price
        # total_selling_price = item.quantity * item.selling_price
        # profit = item.quantity * item.orig_price * -1

        db.cursor.execute(""" INSERT INTO items(name, quantity, orig_price, selling_price) 
            VALUES (%s, %s, %s, %s)""", (
                item.name,
                item.quantity,
                item.orig_price,
                item.selling_price
            )
        )
        db.conn.commit()

        created_item = query.created_request("items")

        return ItemAdminResponse(**created_item)

    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
    
@router.get("/{item_id}", response_model=Union[ItemResponse, ItemAdminResponse])
def get_customer(item_id: int, current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["admin", "user"])
    if current_user.role == "user":
        validate.logged_in_user(current_user.id, item_id)

    item = query.get_request("items", item_id)
    validate.item_exists(item, item_id)

    return query.response(current_user, item, ItemResponse, ItemAdminResponse)

@router.put("/{item_id}", response_model=ItemAdminResponse)
def put_customer(item_id: int, item: Item, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_item = query.get_request("items", item_id)
        validate.item_exists(existing_item, item_id)

        db.cursor.execute("UPDATE items SET name = %s, quantity = %s, orig_price = %s, selling_price = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL", (
                item.name,
                item.quantity,
                item.orig_price,
                item.selling_price,
                current_user.id,
                item_id
            )
        )
        db.conn.commit()

        updated_item = query.get_request("items", item_id)

        return ItemAdminResponse(**updated_item)

    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.patch("/{item_id}", response_model=ItemAdminResponse)
def patch_customer(item_id: int, item: ItemPatch, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_item = query.get_request("items", item_id)
        validate.item_exists(existing_item, item_id)

        excluded_values = item.dict(exclude_unset=True)
        validate.excluded_values(excluded_values)

        query.dynamic_patch_query("items", excluded_values, item_id, current_user.id)
        db.conn.commit()

        updated_item = query.get_request("items", item_id)

        return ItemAdminResponse(**updated_item)

    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete(item_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_item = query.get_request("items", item_id)
        validate.item_exists(existing_item, item_id)

        query.hard_delete("items", item_id)
        db.conn.commit()
        return

    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
    
@router.delete("/{item_id}/delete", status_code=status.HTTP_200_OK)
def soft_delete(item_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])
        
        existing_item = query.get_request("items", item_id)
        validate.item_exists(existing_item, item_id)

        query.soft_delete("items", current_user.id, item_id)
        db.conn.commit()

        return {"detail": f"Item with id {item_id} softly deleted"}
    
    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
    