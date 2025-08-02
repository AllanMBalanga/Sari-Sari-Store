from fastapi import APIRouter, status, HTTPException, Depends
from ..body import Balance, TokenData
from ..queries import Queries
from ..status_codes import Validator
from ..response import BalanceAdminResponse, BalanceResponse
from ..oauth2 import get_current_user
from ..database import Database
from typing import List, Union

router = APIRouter(
    prefix="/customers/{customer_id}/balances",
    tags=["Balances"]
)

db = Database()
validate = Validator()
query = Queries(db)

@router.get("/", response_model=Union[BalanceResponse, BalanceAdminResponse])
def get_balance(customer_id: int, current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["admin","user"])
    if current_user.role == "user":
        validate.logged_in_user(current_user.id, customer_id)

    existing_customer = query.get_request("customers", customer_id)
    validate.customer_exists(existing_customer, customer_id)

    existing_balance = query.get_request("balances", customer_id)
    validate.balance_exists(existing_balance, customer_id)

    return query.response(current_user, existing_balance, BalanceResponse, BalanceAdminResponse)

@router.put("/", response_model=BalanceAdminResponse)
def put_balance(customer_id: int, balance: Balance, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_balance = query.get_request("balances", customer_id)
        validate.balance_exists(existing_balance, customer_id)

        db.cursor.execute("UPDATE balances SET total = %s, updated_by = %s WHERE id = %s AND deleted_at IS NULL", (
            balance.total,
            current_user.id,
            customer_id,
            )
        )
        db.conn.commit()

        updated_balance = query.get_request("balances", customer_id)

        return BalanceAdminResponse(**updated_balance)

    except HTTPException:
        raise

    except Exception:
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
    

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete(customer_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer)

        existing_balance = query.get_request("balances", customer_id)
        validate.balance_exists(existing_balance, customer_id)

        query.hard_delete("balances", customer_id)

        return

    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
    
@router.delete("/delete", status_code=status.HTTP_200_OK)
def soft_delete(customer_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin", "user"])
        if current_user.role == "user":
            validate.logged_in_user(current_user.id, customer_id)

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer)

        existing_balance = query.get_request("balances", customer_id)
        validate.balance_exists(existing_balance, customer_id)
        
        query.soft_delete("balances", current_user.id, customer_id)

        return {"detail": f"Balances with id {customer_id} softly deleted"}
    
    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
    