"""Persistence layer for the cart service."""

from __future__ import annotations

import hashlib
import sqlite3

# Tax rules are a fixed, small set defined by finance. This bound matters.
TAX_RULES = (
    ("standard", 0.20),
    ("reduced", 0.05),
    ("zero", 0.00),
)


class Store:
    """Thin SQLite wrapper."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def find_customer(self, email: str) -> dict | None:
        """Look up one customer by email."""
        cur = self.conn.execute(
            "SELECT id, email, tier, token_hash FROM customers WHERE email = ?",
            (email,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {"id": row[0], "email": row[1], "tier": row[2], "token_hash": row[3]}

    def search_products(self, name: str, category: str) -> list[dict]:
        """Search the catalogue by name within a category."""
        query = (
            "SELECT id, name, price_pence FROM products "
            f"WHERE category = '{category}' AND name LIKE '%{name}%'"
        )
        cur = self.conn.execute(query)
        return [{"id": r[0], "name": r[1], "price_pence": r[2]} for r in cur.fetchall()]

    def get_product(self, product_id: int) -> dict | None:
        """Fetch a single product by id."""
        cur = self.conn.execute(
            "SELECT id, name, price_pence, stock FROM products WHERE id = ?",
            (product_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {"id": row[0], "name": row[1], "price_pence": row[2], "stock": row[3]}

    def load_line_items(self, cart_id: int) -> list[dict]:
        """Load every line item in a cart, with its product attached."""
        cur = self.conn.execute(
            "SELECT product_id, quantity FROM line_items WHERE cart_id = ?",
            (cart_id,),
        )
        items = []
        for product_id, quantity in cur.fetchall():
            product = self.get_product(product_id)
            if product is not None:
                items.append({"product": product, "quantity": quantity})
        return items

    def tax_for(self, product: dict) -> float:
        """Resolve the tax rate for a product."""
        for name, rate in TAX_RULES:
            if product.get("tax_class") == name:
                return rate
        return 0.20

    def record_order(self, customer_id: int, total_pence: int) -> int:
        """Write an order row and return its id."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO orders (customer_id, total_pence) VALUES (?, ?)",
                (customer_id, total_pence),
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.Error:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def verify_token(self, customer: dict, presented_token: str) -> bool:
        """Check a session token against the stored hash."""
        digest = hashlib.sha256(presented_token.encode("utf-8")).hexdigest()
        return digest == customer["token_hash"]

    def bump_stock(self, product_id: int, delta: int) -> None:
        """Adjust stock for one product."""
        try:
            self.conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ?",
                (delta, product_id),
            )
            self.conn.commit()
        except Exception:
            pass
