from fastapi import HTTPException, status
from decimal import Decimal

class Queries:
    def __init__(self, db):
        self.cursor = db.cursor
        self.conn = db.conn
        
    #RESPONSE LIST/INDIV
    def response(self, current_user, unpack, user_response, admin_response):
        if current_user.role == "user":
            return user_response(**unpack)
        else:
            return admin_response(**unpack)
        
    def response_list(self, current_user, unpack, user_response, admin_response):
        if current_user.role == "user":
            return [user_response(**i) for i in unpack]
        else:
            return [admin_response(**i) for i in unpack]
    

    #PATCH
    def dynamic_patch_query(self, table: str, data: dict, table_id: int, updated_by: int, customer_id: int = None, balance_id: int = None):
        data["updated_by"] = updated_by

        set_clause = ", ".join(f"{k} = %s" for k in data.keys())    # Sanitize column names (basic safeguard against SQL injection)
        set_clause += ", updated_at = CURRENT_TIMESTAMP"

        sql = f"UPDATE {table} SET {set_clause}"        # Build base SQL
        
        if table == "transactions" and customer_id is not None and balance_id is not None:
            sql += " WHERE id =  %s AND customer_id = %s AND balance_id = %s AND deleted_at IS NULL"
            values = tuple(data.values()) + (table_id, customer_id, balance_id)
        else:
            sql += " WHERE id = %s AND deleted_at IS NULL"
            values = tuple(data.values()) + (table_id,)

        self.cursor.execute(sql, values)

        # if table == "admissions" and patient_id is not None and doctor_id is not None:          # Add WHERE clause based on table and optional IDs
        #     sql += " WHERE id = %s AND patient_id = %s AND doctor_id = %s"
        #     values = tuple(data.values()) + (table_id, patient_id, doctor_id)
        # else:
        #     sql += " WHERE id = %s"
        #     values = tuple(data.values()) + (table_id,)

        # self.cursor.execute(sql, values)


    #GET ALL/BY_ID
    def get_request(self, table: str, table_id: int = None):
        if table_id:
            self.cursor.execute(f"SELECT * FROM {table} WHERE id = %s AND deleted_at IS NULL", (table_id,))
            return self.cursor.fetchone()
        else:
            self.cursor.execute(f"SELECT * FROM {table} WHERE deleted_at IS NULL")
            return self.cursor.fetchall()

    def get_transactions(self, table_id: int = None, customer_id: int = None, balance_id: int = None):
        if table_id:
            self.cursor.execute(f"SELECT * FROM transactions WHERE id = %s AND customer_id = %s AND balance_id = %s AND deleted_at IS NULL", (
                table_id, customer_id, balance_id)
            )
            return self.cursor.fetchone()
        else:
            self.cursor.execute(f"SELECT * FROM transactions WHERE customer_id = %s AND balance_id = %s AND deleted_at IS NULL", (customer_id, balance_id))
            return self.cursor.fetchall()
        

    #POST/CREATE REQUEST
    def created_request(self, table: str):
        self.cursor.execute(f"SELECT * FROM {table} WHERE id = LAST_INSERT_ID()")
        return self.cursor.fetchone()
    
    #PUT REQUEST
    def update_balance_total(self, balance_id: int, customer_id: int, new_total: float, updated_by: int):
        self.cursor.execute("""
            UPDATE balances SET total = %s, updated_by = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE id = %s AND customer_id = %s AND deleted_at IS NULL
        """, (new_total, updated_by, balance_id, customer_id))
        self.conn.commit()

    #Transaction balance
    def adjust_balance_total(self, existing_balance: dict, existing_transaction: dict, values: dict) -> float:
        # Get new type and amount from values or fallback to existing ones
        new_type = values.get("type", existing_transaction["type"])
        new_amount = Decimal(str(values.get("amount", existing_transaction["amount"])))


        # Undo the original transaction
        if existing_transaction["type"] == "withdraw":
            existing_balance["total"] += existing_transaction["amount"]
        else:
            existing_balance["total"] -= existing_transaction["amount"]

        # Apply the new transaction
        if new_type == "withdraw":
            if existing_balance["total"] - new_amount < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Insufficient balance"
                )
            existing_balance["total"] -= new_amount
        else:
            existing_balance["total"] += new_amount

        return existing_balance["total"]

    #HARD/SOFT DELETE
    def hard_delete(self, table: str, table_id: int, customer_id: int = None, balance_id: int = None):
        if customer_id and balance_id:
            self.cursor.execute(f"DELETE FROM {table} WHERE id = %s AND customer_id = %s AND balance_id = %s", (
                table_id, customer_id, balance_id
                )
            )
        else:    
            self.cursor.execute(f"DELETE FROM {table} WHERE id = %s", (table_id,))
    
    def soft_delete(self, table: str, user_id: int, table_id: int, customer_id: int = None, balance_id: int = None):
        if customer_id and balance_id:
            self.cursor.execute(f"UPDATE {table} SET deleted_at = CURRENT_TIMESTAMP, deleted_by = %s WHERE id = %s AND customer_id = %s AND balance_id = %s AND deleted_at IS NULL", (
                user_id, table_id, customer_id, balance_id
                )
            )
        else:
            self.cursor.execute(f"UPDATE {table} SET deleted_at = CURRENT_TIMESTAMP, deleted_by = %s WHERE id = %s AND deleted_at IS NULL", (user_id, table_id))


