from fastapi import APIRouter, status, HTTPException, Depends
from ..body import Transaction, TransactionPatch, TokenData
from ..response import TransactionAdminResponse, TransactionResponse, TransactionBalanceAdminResponse, TransactionBalanceResponse
from ..status_codes import Validator
from ..queries import Queries
from ..database import Database
from ..oauth2 import get_current_user
from typing import List, Union
from decimal import Decimal

router = APIRouter(
    prefix="/customers/{customer_id}/balances/{balance_id}/transactions",
    tags=["Transactions"]
)

db = Database()
validate = Validator()
query = Queries(db)


@router.get("/", response_model=List[Union[TransactionResponse, TransactionAdminResponse]])
def get_transactions(customer_id: int, balance_id: int, current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["user", "admin"])
    if current_user.role == "user":
        validate.logged_in_user(current_user.id, customer_id)

    existing_customer = query.get_request("customers", customer_id)
    validate.customer_exists(existing_customer, customer_id)

    existing_balance = query.get_request("balances", balance_id)
    validate.balance_exists(existing_balance, balance_id)

    existing_transactions = query.get_transactions(customer_id=customer_id, balance_id=balance_id)
    
    return query.response_list(current_user, existing_transactions, TransactionResponse, TransactionAdminResponse)

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TransactionBalanceResponse)
def create_transaction(customer_id: int, balance_id: int, transaction: Transaction, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["user"])
        validate.logged_in_user(current_user.id, customer_id)

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_balance = query.get_request("balances", balance_id)
        validate.balance_exists(existing_balance, balance_id)

        db.cursor.execute("INSERT INTO transactions (customer_id, balance_id, type, amount) VALUES (%s, %s, %s, %s)", (
                customer_id,
                balance_id,
                transaction.type,
                transaction.amount
            )
        )
        db.conn.commit()

        created_transaction = query.created_request("transactions")

        total_balance = existing_balance["total"]
        transaction_amount = Decimal(str(transaction.amount))

        if transaction.type == "deposit":
            new_balance =  total_balance + transaction_amount
        else:
            if total_balance - transaction_amount < 0:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Total balance not sufficient")
            else:
                new_balance = total_balance - transaction_amount

        db.cursor.execute("UPDATE balances SET total = %s WHERE id = %s", (new_balance, customer_id))    
        db.conn.commit()

        updated_balance = query.get_request("balances", customer_id)
        
        return {
            "transaction": created_transaction,
            "balance": updated_balance
        }

    except HTTPException:
        raise 

    except Exception as e:
        print(f"{e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")


@router.get("/{transaction_id}", response_model=Union[TransactionResponse, TransactionAdminResponse])
def get_transactions(customer_id: int, balance_id: int, transaction_id: int, current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["user", "admin"])
    if current_user.role == "user":
        validate.logged_in_user(current_user.id, customer_id)
    
    existing_customer = query.get_request("customers", customer_id)
    validate.customer_exists(existing_customer, customer_id)

    existing_balance = query.get_request("balances", balance_id)
    validate.balance_exists(existing_balance, balance_id)

    existing_transaction = query.get_transactions(transaction_id, customer_id, balance_id)
    validate.transaction_exists(existing_transaction, transaction_id)

    return query.response(current_user, existing_transaction, TransactionResponse, TransactionAdminResponse)


@router.put("/{transaction_id}", response_model=TransactionBalanceAdminResponse)
def put_transaction(customer_id: int, balance_id: int, transaction_id: int, transaction: Transaction, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_balance = query.get_request("balances", balance_id)
        validate.balance_exists(existing_balance, balance_id)

        existing_transaction = query.get_transactions(transaction_id, customer_id, balance_id)
        validate.transaction_exists(existing_transaction, transaction_id)

        #reset balance before the transaction
        existing_balance["total"] = query.adjust_balance_total(existing_balance, existing_transaction, transaction.dict())

        db.cursor.execute("UPDATE transactions SET type = %s, amount = %s, updated_by = %s WHERE id = %s AND customer_id = %s AND balance_id = %s", (
                transaction.type, transaction.amount, current_user.id, transaction_id, customer_id, balance_id
            )
        )
        db.conn.commit()
        updated_transaction = query.get_transactions(transaction_id, customer_id, balance_id)

        query.update_balance_total(balance_id, customer_id, existing_balance["total"], current_user.id)
        updated_balance = query.get_request("balances", balance_id)

        return {
            "transaction": updated_transaction,
            "balance": updated_balance
        }
    
    except HTTPException:
        raise 

    except Exception as e:
        print(f"{e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")


@router.patch("/{transaction_id}", response_model=TransactionBalanceAdminResponse)
def patch_transaction(customer_id: int, balance_id: int, transaction_id: int, transaction: TransactionPatch, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_balance = query.get_request("balances", balance_id)
        validate.balance_exists(existing_balance, balance_id)

        existing_transaction = query.get_transactions(transaction_id, customer_id, balance_id)
        validate.transaction_exists(existing_transaction, transaction_id)

        excluded_values = transaction.dict(exclude_unset=True)
        validate.excluded_values(excluded_values)

        existing_balance["total"] = query.adjust_balance_total(existing_balance, existing_transaction, excluded_values)

        query.dynamic_patch_query("transactions", excluded_values, transaction_id, current_user.id, customer_id, balance_id)
        updated_transaction = query.get_transactions(transaction_id, customer_id, balance_id)

        query.update_balance_total(balance_id, customer_id, existing_balance["total"], current_user.id)
        updated_balance = query.get_request("balances", balance_id)

        return {
            "transaction": updated_transaction,
            "balance": updated_balance
        }
    
    except HTTPException:
        raise 

    except Exception as e:
        print(f"{e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete_transaction(customer_id: int, balance_id: int, transaction_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_balance = query.get_request("balances", balance_id)
        validate.balance_exists(existing_balance, balance_id)

        existing_transaction = query.get_transactions(transaction_id, customer_id, balance_id)
        validate.transaction_exists(existing_transaction, transaction_id)

        query.hard_delete("transactions", transaction_id, customer_id, balance_id)

        return 

    except HTTPException:
        raise 

    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.delete("/{transaction_id}/delete", status_code=status.HTTP_200_OK)
def soft_delete_transaction(customer_id: int, balance_id: int, transaction_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["user", "admin"])
        if current_user.role == "user":
            validate.logged_in_user(current_user.id, customer_id)
        
        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        existing_balance = query.get_request("balances", balance_id)
        validate.balance_exists(existing_balance, balance_id)

        existing_transaction = query.get_transactions(transaction_id, customer_id, balance_id)
        validate.transaction_exists(existing_transaction, transaction_id)

        query.soft_delete("transactions", current_user.id, transaction_id, customer_id, balance_id)

        return {"detail": "Transaction soft deleted successfully"}

    except HTTPException:
        raise 

    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
