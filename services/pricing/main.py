from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3, json, os

app = FastAPI(title="Pricing & Configuration Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "/data/pricing.db"

def get_db():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS car_models (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            base_price REAL NOT NULL,
            description TEXT,
            image_hint TEXT
        );

        CREATE TABLE IF NOT EXISTS options (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            compatible_models TEXT,
            description TEXT
        );

        INSERT OR IGNORE INTO car_models VALUES
            ('model-s', 'Apex S', 45000, 'Refined sports sedan with dynamic handling', 'sedan'),
            ('model-x', 'Apex X', 62000, 'Performance SUV for every terrain', 'suv'),
            ('model-r', 'Apex R', 89000, 'Track-bred hypercar for the road', 'coupe');

        INSERT OR IGNORE INTO options VALUES
            ('color-obsidian', 'color', 'Obsidian Black', 0, 'all', 'Classic deep black'),
            ('color-arctic', 'color', 'Arctic White', 500, 'all', 'Pearl white finish'),
            ('color-plasma', 'color', 'Plasma Blue', 1200, 'all', 'Metallic electric blue'),
            ('color-carbon', 'color', 'Carbon Red', 1500, 'all', 'Matte carbon red'),
            ('color-gold', 'color', 'Champagne Gold', 2000, 'all', 'Satin gold finish'),

            ('engine-base', 'engine', '2.0L Turbo (250hp)', 0, 'model-s,model-x', 'Efficient and responsive'),
            ('engine-v6', 'engine', '3.5L V6 (380hp)', 4500, 'model-s,model-x', 'Sport performance'),
            ('engine-v8', 'engine', '5.0L V8 (520hp)', 12000, 'model-r', 'Race-bred powerhouse'),
            ('engine-hybrid', 'engine', 'Hybrid AWD (430hp)', 8000, 'model-s,model-x', 'Best-in-class efficiency'),

            ('acc-sunroof', 'accessories', 'Panoramic Sunroof', 2200, 'all', 'Full-length glass roof'),
            ('acc-leather', 'accessories', 'Nappa Leather Interior', 3500, 'all', 'Hand-stitched premium leather'),
            ('acc-sound', 'accessories', '1200W Surround Sound', 1800, 'all', '16-speaker audiophile system'),
            ('acc-autopilot', 'accessories', 'Advanced Driver Assist', 4000, 'all', 'Lane keep, adaptive cruise'),
            ('acc-carbon', 'accessories', 'Carbon Fiber Trim', 2800, 'all', 'Interior & exterior carbon accents'),
            ('acc-wheels-20', 'accessories', '20" Forged Alloys', 1600, 'all', 'Lightweight forged wheels'),
            ('acc-wheels-22', 'accessories', '22" Sport Wheels', 2800, 'all', 'Aggressive staggered fitment'),
            ('acc-tint', 'accessories', 'Ceramic Window Tint', 800, 'all', 'UV/IR blocking ceramic film');
    """)
    conn.commit()
    conn.close()

init_db()

class ConfigRequest(BaseModel):
    model_id: str
    color_id: str
    engine_id: str
    accessory_ids: List[str] = []

class ConfigResponse(BaseModel):
    valid: bool
    model: dict
    color: dict
    engine: dict
    accessories: List[dict]
    base_price: float
    options_total: float
    total_price: float
    configuration_summary: str

@app.get("/models")
def get_models():
    conn = get_db()
    models = [dict(r) for r in conn.execute("SELECT * FROM car_models").fetchall()]
    conn.close()
    return models

@app.get("/options")
def get_options():
    conn = get_db()
    rows = conn.execute("SELECT * FROM options").fetchall()
    conn.close()
    result = {}
    for r in rows:
        cat = r["category"]
        result.setdefault(cat, []).append(dict(r))
    return result

@app.post("/configure", response_model=ConfigResponse)
def configure(req: ConfigRequest):
    conn = get_db()

    model = conn.execute("SELECT * FROM car_models WHERE id=?", (req.model_id,)).fetchone()
    if not model:
        raise HTTPException(400, f"Unknown model: {req.model_id}")
    model = dict(model)

    def get_option(oid):
        opt = conn.execute("SELECT * FROM options WHERE id=?", (oid,)).fetchone()
        if not opt:
            raise HTTPException(400, f"Unknown option: {oid}")
        return dict(opt)

    color = get_option(req.color_id)
    engine = get_option(req.engine_id)

    # Validate engine compatibility
    compatible = engine["compatible_models"].split(",")
    if "all" not in compatible and req.model_id not in compatible:
        raise HTTPException(400, f"Engine {req.engine_id} not compatible with {req.model_id}")

    accessories = [get_option(a) for a in req.accessory_ids]

    options_total = color["price"] + engine["price"] + sum(a["price"] for a in accessories)
    total_price = model["base_price"] + options_total

    acc_names = ", ".join(a["name"] for a in accessories) if accessories else "None"
    summary = f"{model['name']} | {color['name']} | {engine['name']} | Accessories: {acc_names}"

    conn.close()
    return ConfigResponse(
        valid=True,
        model=model,
        color=color,
        engine=engine,
        accessories=accessories,
        base_price=model["base_price"],
        options_total=options_total,
        total_price=total_price,
        configuration_summary=summary
    )

@app.get("/health")
def health():
    return {"status": "ok", "service": "pricing"}
