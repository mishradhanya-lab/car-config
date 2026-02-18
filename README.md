# 🚗 Apex Car Configuration & Ordering System

A full-stack microservices application for configuring and ordering luxury vehicles.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│              React Frontend  (port 3000)                │
└──────┬──────────────┬────────────────┬──────────────────┘
       │ POST /configure│ POST /orders  │ POST /pay
       ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐
│  Pricing &   │ │  Cart &      │ │ Payment Gateway      │
│  Config      │ │  Order Mgmt  │ │ (Mock)               │
│  port 8001   │ │  port 8002   │ │  port 8003           │
└──────┬───────┘ └──────┬───────┘ └──────┬───────────────┘
       │                │                │
  pricing.db       orders.db        payments.db
  (SQLite)         (SQLite)         (SQLite)
```

## Data Flow

1. **Configure** — React fetches models/options from Pricing service; user selections POST to `/configure` → returns validated config + total price
2. **Checkout** — Customer info captured in frontend; POST to `/orders` creates order, then `/orders/{id}/place` confirms it
3. **Payment** — POST to `/pay` with order ID + card details → simulated success/fail response
4. **Completion** — On success, order status updated to `paid`; confirmation screen shown

---

## Quick Start

### Option A: Docker Compose (Recommended)

```bash
# Clone and start
cd car-config
docker compose up --build

# App available at:
# Frontend:  http://localhost:3000
# Pricing:   http://localhost:8001/docs
# Orders:    http://localhost:8002/docs
# Payment:   http://localhost:8003/docs
```

### Option B: Local Development

**Backend services** (requires Python 3.11+):

```bash
# Pricing service
cd services/pricing
pip install -r requirements.txt
uvicorn main:app --port 8001 --reload

# Orders service (new terminal)
cd services/orders
pip install -r requirements.txt
uvicorn main:app --port 8002 --reload

# Payment service (new terminal)
cd services/payment
pip install -r requirements.txt
uvicorn main:app --port 8003 --reload
```

**Frontend** (requires Node 20+):

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## API Reference

### Pricing Service (port 8001)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/models` | List all car models |
| GET | `/options` | List all options by category |
| POST | `/configure` | Validate config & calculate price |
| GET | `/health` | Health check |

**POST /configure body:**
```json
{
  "model_id": "model-s",
  "color_id": "color-plasma",
  "engine_id": "engine-v6",
  "accessory_ids": ["acc-sunroof", "acc-leather"]
}
```

### Orders Service (port 8002)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orders` | Create pending order |
| POST | `/orders/{id}/place` | Confirm/place order |
| GET | `/orders/{id}` | Get order by ID |
| PATCH | `/orders/{id}/status` | Update order status |

### Payment Service (port 8003)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/pay` | Process mock payment |
| GET | `/payments/{id}` | Get payment record |

**POST /pay body:**
```json
{
  "order_id": "ORD-XXXXXXXX",
  "amount": 67200,
  "card_number": "4111111111111111",
  "card_holder": "JANE SMITH",
  "expiry": "12/26",
  "cvv": "123",
  "force_result": "success"  // optional: "success" | "fail"
}
```

---

## Database Schema

### pricing.db
```sql
car_models (id, name, base_price, description, image_hint)
options (id, category, name, price, compatible_models, description)
```

### orders.db
```sql
orders (id, customer_name, customer_email, configuration JSON,
        total_price, status, created_at, updated_at)
```

### payments.db
```sql
payments (id, order_id, amount, card_last4, card_holder,
          status, transaction_ref, created_at)
```

---

## Tech Stack
- **Frontend**: React 18 + Vite, served via Nginx
- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Database**: SQLite (swap for PostgreSQL by changing `sqlite3` → `psycopg2`)
- **Containers**: Docker + Docker Compose
- **API style**: REST / JSON

## Swapping SQLite → PostgreSQL

Replace in each `main.py`:
```python
# Before (SQLite)
conn = sqlite3.connect("/data/pricing.db")

# After (PostgreSQL)
import psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
```

Add to `docker-compose.yml`:
```yaml
postgres:
  image: postgres:16
  environment:
    POSTGRES_PASSWORD: apex
    POSTGRES_DB: apex
  volumes:
    - pg-data:/var/lib/postgresql/data
```
