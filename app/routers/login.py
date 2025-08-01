from fastapi import APIRouter, status, HTTPException, Depends
from ..database import Database
from ..body import LoggedInToken
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from ..utils import verify
from ..oauth2 import create_token

router = APIRouter(
    prefix="/login",
    tags=["Login"]
)

db = Database()

@router.post("/", response_model=LoggedInToken)
def user_login(credentials: OAuth2PasswordRequestForm = Depends()):
    db.cursor.execute("SELECT * FROM customers WHERE email = %s", (credentials.username,))
    user = db.cursor.fetchone()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Invalid credentials.")
    
    if not verify(credentials.password, user["password"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Invalid credentials.")
    
    access_token = create_token(data={"user_id": user["id"], "role": user["role"]})

    return {"access_token": access_token, "token_type": "bearer", "user_id": user["id"], "role": user["role"]}