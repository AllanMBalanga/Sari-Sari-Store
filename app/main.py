from fastapi import FastAPI
from .database import Database
from .routers import customers, login, balances, transactions, items, orders, order_items

app = FastAPI()

app.include_router(login.router)
app.include_router(customers.router)
app.include_router(balances.router)
app.include_router(transactions.router)
app.include_router(items.router)
app.include_router(orders.router)
app.include_router(order_items.router)

#TODO items table remove generated as
#TODO orders put/patch todo
#TODO order_items connection to balance.total with put/patch

@app.on_event("startup")
def startup():
    db = Database()
    db.create_tables()