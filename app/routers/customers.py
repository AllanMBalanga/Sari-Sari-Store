from fastapi import APIRouter, status, HTTPException, Depends
from ..response import CustomerResponse, CustomerAdminResponse, CustomerBalanceResponse
from ..body import Customer, TokenData, CustomerPatch
from ..utils import hash
from ..oauth2 import get_current_user
from ..database import Database
from ..queries import Queries
from ..status_codes import Validator
from typing import List, Union

router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)

db = Database()
validate = Validator()
query = Queries(db)

@router.get("/", response_model=List[Union[CustomerResponse, CustomerAdminResponse]])
def get_customers(current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["admin"])

    customers = query.get_request("customers")

    return query.response_list(current_user, customers, CustomerResponse, CustomerAdminResponse)
    
@router.post("/", response_model=CustomerBalanceResponse, status_code=status.HTTP_201_CREATED)
def create_customer(customer: Customer):
    try:
        db.cursor.execute("SELECT * FROM customers WHERE email = %s", (customer.email,))
        existing_email = db.cursor.fetchone()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        
        customer.password = hash(customer.password)
        db.cursor.execute("""INSERT INTO customers (email, password, first_name, last_name, role) 
                        VALUES (%s, %s, %s, %s, %s)""", (
                        customer.email,
                        customer.password,
                        customer.first_name,
                        customer.last_name,
                        "user"
            )
        )

        customer_id = db.cursor.lastrowid

        db.cursor.execute("""INSERT INTO BALANCES (customer_id, total) 
                        VALUES (%s, %s)""", (
                        customer_id,
                        0.00
            )
        )
        db.conn.commit()

        created_customer = query.created_request("customers")
        created_balance = query.created_request("balances")

        return {
            "customer": created_customer,
            "balance": created_balance
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
    
@router.get("/{customer_id}", response_model=Union[CustomerResponse, CustomerAdminResponse])
def get_customer(customer_id: int, current_user: TokenData = Depends(get_current_user)):
    validate.required_roles(current_user.role, ["admin", "user"])
    if current_user.role == "user":
        validate.logged_in_user(current_user.id, customer_id)

    customer = query.get_request("customers", customer_id)
    validate.customer_exists(customer, customer_id)

    return query.response(current_user, customer, CustomerResponse, CustomerAdminResponse)

@router.put("/{customer_id}", response_model=Union[CustomerResponse, CustomerAdminResponse])
def put_customer(customer_id: int, customer: Customer, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin", "user"])
        if current_user.role == "user":
            validate.logged_in_user(current_user.id, customer_id)

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        customer.password = hash(customer.password)
        db.cursor.execute("UPDATE customers SET email = %s, password = %s, first_name = %s, last_name = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL", (
                customer.email,
                customer.password,
                customer.first_name,
                customer.last_name,
                current_user.id,
                customer_id
            )
        )
        db.conn.commit()

        updated_customer = query.get_request("customers", customer_id)

        return query.response(current_user, updated_customer, CustomerResponse, CustomerAdminResponse)

    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.patch("/{customer_id}", response_model=Union[CustomerResponse, CustomerAdminResponse])
def patch_customer(customer_id: int, customer: CustomerPatch, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin", "user"])
        if current_user.role == "user":
            validate.logged_in_user(current_user.id, customer_id)

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        if customer.password:
            customer.password = hash(customer.password)

        excluded_values = customer.dict(exclude_unset=True)
        validate.excluded_values(excluded_values)

        query.dynamic_patch_query("customers", excluded_values, customer_id, current_user.id)
        db.conn.commit()

        updated_customer = query.get_request("customers", customer_id)

        return query.response(current_user, updated_customer, CustomerResponse, CustomerAdminResponse)

    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete(customer_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin"])

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        query.hard_delete("customers", customer_id)
        db.conn.commit()

        return

    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
    
@router.delete("/{customer_id}/delete", status_code=status.HTTP_200_OK)
def soft_delete(customer_id: int, current_user: TokenData = Depends(get_current_user)):
    try:
        validate.required_roles(current_user.role, ["admin", "user"])
        if current_user.role == "user":
            validate.logged_in_user(current_user.id, customer_id)

        existing_customer = query.get_request("customers", customer_id)
        validate.customer_exists(existing_customer, customer_id)

        query.soft_delete("customers", current_user.id, customer_id)
        query.soft_delete("balances", current_user.id, customer_id)
        db.conn.commit()

        return {"detail": f"Customer with id {customer_id} and related resources softly deleted"}
    
    except HTTPException:
        raise

    except Exception as e:
        print(f"{e}")
        db.conn.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")
    