from fastapi import status, HTTPException
from .database import Database

db = Database()

class Validator:
    #Token and logged in IDs
    def logged_in_user(self, current_user: int, user_id: int):
        if current_user != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to perform this action"
            )

    def required_roles(self, current_user_role: str, allowed_roles: list[str]):
        if current_user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only {', '.join(allowed_roles)} authorized to perform this action"
            )
    
    #PATCH
    def excluded_values(self, excluded_values):
        if not excluded_values:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="No data was found for the update"
            )

    #Tables
    def customer_exists(self, customer, customer_id: int = None):
        if not customer:
            if customer_id:
                detail = f"Customer with id {customer_id} was not found"
            else:
                detail = "Customer was not found"

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail
            )


