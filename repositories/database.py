from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from domain.models import ConversationState, Product


BRANDS = {
    "laptop": ["联想", "华为", "小米", "Apple", "华硕", "惠普"],
    "phone": ["小米", "华为", "OPPO", "vivo", "Apple", "荣耀"],
    "headphone": ["索尼", "Bose", "漫步者", "小米", "华为", "JBL"],
}


def build_demo_products() -> list[Product]:
    products: list[Product] = []
    now = datetime.now(timezone.utc).isoformat()
    for category, brands in BRANDS.items():
        for i in range(40):
            brand = brands[i % len(brands)]
            n = i + 1
            if category == "laptop":
                price = 3299 + (i % 10) * 430
                attrs: dict[str, Any] = {
                    "memory_gb": [8, 16, 16, 32][i % 4], "storage_gb": [512, 1024][i % 2],
                    "weight_kg": round(1.18 + (i % 8) * .11, 2), "screen_inches": [13.3, 14, 15.6][i % 3],
                    "battery_hours": 8 + i % 8, "product_type": "gaming_laptop" if i % 9 == 0 else "thin_laptop",
                }
                tags = ["编程", "办公", "便携" if attrs["weight_kg"] <= 1.5 else "性能", "剪视频" if attrs["memory_gb"] >= 16 else "日常"]
                desc = f"{attrs['memory_gb']}GB 内存，{attrs['weight_kg']}kg，适合{','.join(tags)}"
            elif category == "phone":
                price = 1499 + (i % 10) * 650
                attrs = {
                    "memory_gb": [8, 12, 16][i % 3], "storage_gb": [128, 256, 512][i % 3],
                    "screen_inches": [6.1, 6.5, 6.7][i % 3], "battery_mah": 4200 + (i % 5) * 250,
                    "camera_mp": [50, 64, 108][i % 3], "waterproof": "IP68" if i % 3 == 0 else "IP54",
                }
                tags = ["拍照" if attrs["camera_mp"] >= 64 else "日常", "操作简单", "长续航" if attrs["battery_mah"] >= 4700 else "轻巧"]
                desc = f"{attrs['camera_mp']}MP 相机，{attrs['battery_mah']}mAh 电池，{','.join(tags)}"
            else:
                price = 169 + (i % 10) * 140
                attrs = {
                    "form": "入耳式" if i % 2 else "头戴式", "noise_cancelling": i % 3 != 0,
                    "battery_hours": 20 + (i % 7) * 8, "weight_g": 45 if i % 2 else 245,
                }
                tags = ["降噪" if attrs["noise_cancelling"] else "开放聆听", "长续航" if attrs["battery_hours"] >= 36 else "便携", attrs["form"]]
                desc = f"{attrs['form']}，续航 {attrs['battery_hours']} 小时，{','.join(tags)}"
            pid = f"{category[:2].upper()}-{n:03d}"
            products.append(Product(
                id=pid, sku_id=f"{pid}-01", title=f"{brand} {category.title()} {n}", category=category,
                brand=brand, description=desc, price=price, list_price=price + 300, stock=(i * 7) % 51,
                rating=round(4.0 + (i % 10) * .09, 1), review_count=80 + i * 137,
                attributes=attrs, tags=tags, updated_at=now,
            ))
    return products


class Database:
    def __init__(self, path: str | Path = "shopguide.db") -> None:
        self.path = str(path)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def initialize(self) -> None:
        with self.connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                  id TEXT PRIMARY KEY, data TEXT NOT NULL, category TEXT NOT NULL,
                  brand TEXT NOT NULL, price REAL NOT NULL, stock INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active'
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(id UNINDEXED, title, description, tags, tokenize='unicode61');
                CREATE TABLE IF NOT EXISTS conversations (session_id TEXT PRIMARY KEY, state TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS user_events (request_id TEXT PRIMARY KEY, user_id TEXT, session_id TEXT, event_type TEXT, product_id TEXT, created_at TEXT);
                CREATE TABLE IF NOT EXISTS user_preferences (user_id TEXT, name TEXT, value TEXT, weight REAL, scope TEXT, updated_at TEXT, PRIMARY KEY(user_id, name, scope));
                CREATE TABLE IF NOT EXISTS knowledge_documents (id TEXT PRIMARY KEY, content TEXT NOT NULL, source_type TEXT NOT NULL, product_id TEXT, version TEXT, active INTEGER NOT NULL DEFAULT 1);
            """)
            if con.execute("SELECT count(*) FROM products").fetchone()[0] == 0:
                self.import_products(build_demo_products(), con)

    def import_products(self, products: list[Product], con: sqlite3.Connection | None = None) -> int:
        owned = con is None
        con = con or self.connect()
        try:
            for p in products:
                con.execute("INSERT OR REPLACE INTO products(id,data,category,brand,price,stock,status) VALUES(?,?,?,?,?,?,'active')",
                            (p.id, p.model_dump_json(), p.category, p.brand, p.price, p.stock))
                con.execute("DELETE FROM products_fts WHERE id=?", (p.id,))
                con.execute("INSERT INTO products_fts(id,title,description,tags) VALUES(?,?,?,?)",
                            (p.id, p.title, p.description, " ".join(p.tags)))
            con.commit()
            return len(products)
        finally:
            if owned:
                con.close()

    def all_products(self) -> list[Product]:
        with self.connect() as con:
            return [Product.model_validate_json(r[0]) for r in con.execute("SELECT data FROM products WHERE status='active'")]

    def get_products(self, ids: list[str]) -> list[Product]:
        if not ids:
            return []
        with self.connect() as con:
            rows = con.execute(f"SELECT data FROM products WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall()
        found = {json.loads(r[0])["id"]: Product.model_validate_json(r[0]) for r in rows}
        return [found[i] for i in ids if i in found]

    def lexical_scores(self, query: str) -> dict[str, float]:
        terms = [t for t in query.replace("，", " ").replace(",", " ").split() if t]
        if not terms:
            return {}
        expression = " OR ".join(f'"{t.replace(chr(34), "")}"' for t in terms)
        try:
            with self.connect() as con:
                rows = con.execute("SELECT id, bm25(products_fts) score FROM products_fts WHERE products_fts MATCH ? LIMIT 50", (expression,)).fetchall()
            return {r["id"]: 1 / (1 + abs(r["score"])) for r in rows}
        except sqlite3.OperationalError:
            return {}

    def load_state(self, session_id: str) -> ConversationState | None:
        with self.connect() as con:
            row = con.execute("SELECT state FROM conversations WHERE session_id=?", (session_id,)).fetchone()
        return ConversationState.model_validate_json(row[0]) if row else None

    def save_state(self, state: ConversationState) -> None:
        state.version += 1
        with self.connect() as con:
            con.execute("INSERT INTO conversations(session_id,state,version) VALUES(?,?,?) ON CONFLICT(session_id) DO UPDATE SET state=excluded.state,version=excluded.version",
                        (state.session_id, state.model_dump_json(), state.version))

    def delete_state(self, session_id: str) -> bool:
        with self.connect() as con:
            return con.execute("DELETE FROM conversations WHERE session_id=?", (session_id,)).rowcount > 0

    def record_event(self, request_id: str, event_type: str, product_id: str, session_id: str | None, user_id: str | None) -> bool:
        with self.connect() as con:
            return con.execute("INSERT OR IGNORE INTO user_events VALUES(?,?,?,?,?,datetime('now'))", (request_id, user_id, session_id, event_type, product_id)).rowcount > 0
