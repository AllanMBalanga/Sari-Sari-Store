from fastapi import FastAPI
from .database import Database
from .routers import customers, login

app = FastAPI()

app.include_router(login.router)
app.include_router(customers.router)

@app.on_event("startup")
def startup():
    db = Database()
    db.create_tables()