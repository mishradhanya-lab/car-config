from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
import sqlite3, json, os, uuid
from datetime import datetime

app = FastAPI(title="Cart & Order Management", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/data/orders.db"

def get_db():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            customer_name TEXT,
            customer_email TEXT,
            configuration TEXT NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

init_db()

class CreateOrderRequest(BaseModel):
    customer_name: str
    customer_email: str
    configuration: dict
    total_price: float

class PlaceOrderRequest(BaseModel):
    order_id: str

class OrderResponse(BaseModel):
    order_id: str
    customer_name: str
    customer_email: str
    configuration: dict
    total_price: float
    status: str
    created_at: str

@app.post("/orders", response_model=OrderResponse)
def create_order(req: CreateOrderRequest):
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)",
        (order_id, req.customer_name, req.customer_email,
         json.dumps(req.configuration), req.total_price,
         "pending", now, now)
    )
    conn.commit()
    conn.close()
    return OrderResponse(
        order_id=order_id,
        customer_name=req.customer_name,
        customer_email=req.customer_email,
        configuration=req.configuration,
        total_price=req.total_price,
        status="pending",
        created_at=now
    )

@app.post("/orders/{order_id}/place")
def place_order(order_id: str):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] != "pending":
        raise HTTPException(400, f"Order already in status: {order['status']}")
    now = datetime.utcnow().isoformat()
    conn.execute("UPDATE orders SET status='confirmed', updated_at=? WHERE id=?", (now, order_id))
    conn.commit()
    conn.close()
    return {"order_id": order_id, "status": "confirmed", "message": "Order placed successfully"}

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    if not order:
        raise HTTPException(404, "Order not found")
    return OrderResponse(
        order_id=order["id"],
        customer_name=order["customer_name"],
        customer_email=order["customer_email"],
        configuration=json.loads(order["configuration"]),
        total_price=order["total_price"],
        status=order["status"],
        created_at=order["created_at"]
    )

@app.patch("/orders/{order_id}/status")
def update_order_status(order_id: str, status: str):
    allowed = ["pending", "confirmed", "paid", "cancelled"]
    if status not in allowed:
        raise HTTPException(400, f"Invalid status. Must be one of: {allowed}")
    conn = get_db()
    now = datetime.utcnow().isoformat()
    result = conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (status, now, order_id))
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        raise HTTPException(404, "Order not found")
    return {"order_id": order_id, "status": status}

@app.get("/health")
def health():
    return {"status": "ok", "service": "orders"}
