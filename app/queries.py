from httpx import delete


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
    def dynamic_patch_query(self, table: str, data: dict, table_id: int, updated_by: int):
        data["updated_by"] = updated_by

        set_clause = ", ".join(f"{k} = %s" for k in data.keys())    # Sanitize column names (basic safeguard against SQL injection)

        sql = f"UPDATE {table} SET {set_clause} WHERE id = %s AND deleted_at IS NULL"        # Build base SQL
        
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
    def get_customers(self, customer_id: int = None):
        if customer_id:
            self.cursor.execute("SELECT * FROM customers WHERE id = %s AND deleted_at IS NULL", (customer_id,))
            return self.cursor.fetchone()
        else:
            self.cursor.execute("SELECT * FROM customers WHERE deleted_at IS NULL")
            return self.cursor.fetchall()


    #POST/CREATE REQUEST
    def created_customer(self):
        self.cursor.execute("SELECT * FROM customers WHERE id = LAST_INSERT_ID()")
        return self.cursor.fetchone()
    
    def created_balance(self):
        self.cursor.execute("SELECT * FROM balances WHERE id = LAST_INSERT_ID()")
        return self.cursor.fetchone()
    
    def created_transaction(self):
        self.cursor.execute("SELECT * FROM transactions WHERE id = LAST_INSERT_ID()")
        return self.cursor.fetchone()

    def created_items(self):
        self.cursor.execute("SELECT * FROM items WHERE id = LAST_INSERT_ID()")
        return self.cursor.fetchone()
    
    def created_orders(self):
        self.cursor.execute("SELECT * FROM orders WHERE id = LAST_INSERT_ID()")
        return self.cursor.fetchone()
    
    def created_order_items(self):
        self.cursor.execute("SELECT * FROM order_items WHERE id = LAST_INSERT_ID()")
        return self.cursor.fetchone()

    #HARD/SOFT DELETE
    def hard_delete_customers(self, customer_id: int):
        self.cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
        self.conn.commit()
    
    def soft_delete_customers(self, user_id: int, delete_id: int):
        self.cursor.execute("UPDATE customers SET deleted_at = CURRENT_TIMESTAMP, deleted_by = %s WHERE id = %s", (user_id, delete_id))
        self.conn.commit()

