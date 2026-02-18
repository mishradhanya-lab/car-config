from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, uuid, random
from datetime import datetime

app = FastAPI(title="Payment Gateway (Mock)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/data/payments.db"

def get_db():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            amount REAL NOT NULL,
            card_last4 TEXT,
            card_holder TEXT,
            status TEXT NOT NULL,
            transaction_ref TEXT,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

init_db()

class PaymentRequest(BaseModel):
    order_id: str
    amount: float
    card_number: str  # Mock - we only store last 4
    card_holder: str
    expiry: str
    cvv: str
    # Force a specific outcome for testing; omit for random simulation
    force_result: Optional[str] = None  # "success" | "fail"

class PaymentResponse(BaseModel):
    payment_id: str
    order_id: str
    amount: float
    status: str
    transaction_ref: Optional[str]
    message: str
    timestamp: str

@app.post("/pay", response_model=PaymentResponse)
def process_payment(req: PaymentRequest):
    payment_id = f"PAY-{uuid.uuid4().hex[:10].upper()}"
    now = datetime.utcnow().isoformat()
    last4 = req.card_number.replace(" ", "")[-4:]

    # Simulate payment: 90% success unless forced
    if req.force_result == "fail":
        success = False
    elif req.force_result == "success":
        success = True
    else:
        success = random.random() > 0.1  # 90% success rate

    status = "success" if success else "failed"
    transaction_ref = f"TXN-{uuid.uuid4().hex[:12].upper()}" if success else None
    message = (
        f"Payment of ${req.amount:,.2f} processed successfully."
        if success else
        "Payment declined. Please check your card details and try again."
    )

    conn = get_db()
    conn.execute(
        "INSERT INTO payments VALUES (?,?,?,?,?,?,?,?)",
        (payment_id, req.order_id, req.amount, last4,
         req.card_holder, status, transaction_ref, now)
    )
    conn.commit()
    conn.close()

    if not success:
        # Return 200 with failed status (not an HTTP error, a business logic failure)
        return PaymentResponse(
            payment_id=payment_id, order_id=req.order_id,
            amount=req.amount, status="failed",
            transaction_ref=None, message=message, timestamp=now
        )

    return PaymentResponse(
        payment_id=payment_id, order_id=req.order_id,
        amount=req.amount, status="success",
        transaction_ref=transaction_ref, message=message, timestamp=now
    )

@app.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: str):
    conn = get_db()
    p = conn.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    conn.close()
    if not p:
        raise HTTPException(404, "Payment not found")
    return PaymentResponse(
        payment_id=p["id"], order_id=p["order_id"],
        amount=p["amount"], status=p["status"],
        transaction_ref=p["transaction_ref"],
        message="Payment record retrieved.", timestamp=p["created_at"]
    )

@app.get("/health")
def health():
    return {"status": "ok", "service": "payment"}
