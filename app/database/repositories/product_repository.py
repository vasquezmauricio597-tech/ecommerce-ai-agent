from __future__ import annotations

import json
import sqlite3
from typing import Any


class ProductRepository:
    """
    Acceso persistente a productos.

    Este repositorio contiene únicamente operaciones
    de persistencia sobre la tabla products.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
    ):
        self.connection = connection

    def get_by_id(
        self,
        product_id: str,
    ) -> dict[str, Any] | None:
        normalized_id = product_id.strip().upper()

        row = self.connection.execute(
            """
            SELECT
                id,
                name,
                category,
                price,
                stock,
                description,
                tags
            FROM products
            WHERE UPPER(id) = ?
            """,
            (normalized_id,),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def get_by_name(
        self,
        product_name: str,
    ) -> dict[str, Any] | None:
        normalized_name = product_name.strip()

        if not normalized_name:
            return None

        row = self.connection.execute(
            """
            SELECT
                id,
                name,
                category,
                price,
                stock,
                description,
                tags
            FROM products
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
            LIMIT 1
            """,
            (normalized_name,),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def get_all(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                id,
                name,
                category,
                price,
                stock,
                description,
                tags
            FROM products
            ORDER BY id
            """
        ).fetchall()

        return [
            self._row_to_dict(row)
            for row in rows
        ]

    def get_stock(
        self,
        product_id: str,
    ) -> int | None:
        normalized_id = product_id.strip().upper()

        row = self.connection.execute(
            """
            SELECT stock
            FROM products
            WHERE UPPER(id) = ?
            """,
            (normalized_id,),
        ).fetchone()

        if row is None:
            return None

        return int(row["stock"])

    def decrease_stock(
        self,
        product_id: str,
        quantity: int,
    ) -> bool:
        normalized_id = product_id.strip().upper()

        cursor = self.connection.execute(
            """
            UPDATE products
            SET stock = stock - ?
            WHERE UPPER(id) = ?
              AND stock >= ?
            """,
            (
                quantity,
                normalized_id,
                quantity,
            ),
        )

        return cursor.rowcount == 1

    def increase_stock(
        self,
        product_id: str,
        quantity: int,
    ) -> bool:
        normalized_id = product_id.strip().upper()

        cursor = self.connection.execute(
            """
            UPDATE products
            SET stock = stock + ?
            WHERE UPPER(id) = ?
            """,
            (
                quantity,
                normalized_id,
            ),
        )

        return cursor.rowcount == 1

    def _row_to_dict(
        self,
        row: sqlite3.Row,
    ) -> dict[str, Any]:
        try:
            tags = json.loads(row["tags"])
        except (TypeError, json.JSONDecodeError):
            tags = []

        return {
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "price": float(row["price"]),
            "stock": int(row["stock"]),
            "description": row["description"],
            "tags": tags,
        }


class CartRepository:
    """
    Acceso persistente a carritos y sus productos.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
    ):
        self.connection = connection

    def ensure_cart(
        self,
        session_id: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO carts (
                session_id
            )
            VALUES (?)
            """,
            (session_id,),
        )

        self.connection.execute(
            """
            UPDATE carts
            SET updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (session_id,),
        )

    def get_items(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                ci.product_id,
                ci.quantity,
                p.name,
                p.category,
                p.price,
                p.stock
            FROM cart_items ci
            JOIN products p
                ON p.id = ci.product_id
            WHERE ci.session_id = ?
            ORDER BY ci.product_id
            """,
            (session_id,),
        ).fetchall()

        return [
            {
                "product_id": row["product_id"],
                "quantity": int(row["quantity"]),
                "name": row["name"],
                "category": row["category"],
                "price": float(row["price"]),
                "stock": int(row["stock"]),
            }
            for row in rows
        ]

    def add_item(
        self,
        session_id: str,
        product_id: str,
        quantity: int,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO cart_items (
                session_id,
                product_id,
                quantity
            )
            VALUES (?, ?, ?)
            ON CONFLICT(session_id, product_id)
            DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (
                session_id,
                product_id,
                quantity,
            ),
        )

    def remove_item(
        self,
        session_id: str,
        product_id: str,
    ) -> bool:
        cursor = self.connection.execute(
            """
            DELETE FROM cart_items
            WHERE session_id = ?
              AND UPPER(product_id) = UPPER(?)
            """,
            (
                session_id,
                product_id,
            ),
        )

        return cursor.rowcount > 0

    def clear(
        self,
        session_id: str,
    ) -> None:
        self.connection.execute(
            """
            DELETE FROM cart_items
            WHERE session_id = ?
            """,
            (session_id,),
        )

        self.connection.execute(
            """
            UPDATE carts
            SET updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (session_id,),
        )


class OrderRepository:
    """
    Acceso persistente a órdenes y sus productos.
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
    ):
        self.connection = connection

    def create_order(
        self,
        session_id: str,
        total: float,
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO orders (
                session_id,
                total
            )
            VALUES (?, ?)
            """,
            (
                session_id,
                total,
            ),
        )

        return int(cursor.lastrowid)

    def add_item(
        self,
        order_id: int,
        product_id: str,
        product_name: str,
        unit_price: float,
        quantity: int,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO order_items (
                order_id,
                product_id,
                product_name,
                unit_price,
                quantity
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                order_id,
                product_id,
                product_name,
                unit_price,
                quantity,
            ),
        )

    def get_by_id(
        self,
        order_id: int,
    ) -> dict[str, Any] | None:
        order = self.connection.execute(
            """
            SELECT
                id,
                session_id,
                total,
                created_at
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        ).fetchone()

        if order is None:
            return None

        items = self.connection.execute(
            """
            SELECT
                product_id,
                product_name,
                unit_price,
                quantity
            FROM order_items
            WHERE order_id = ?
            ORDER BY id
            """,
            (order_id,),
        ).fetchall()

        return {
            "id": int(order["id"]),
            "session_id": order["session_id"],
            "total": float(order["total"]),
            "created_at": order["created_at"],
            "items": [
                {
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "unit_price": float(item["unit_price"]),
                    "quantity": int(item["quantity"]),
                    "subtotal": float(item["unit_price"])
                    * int(item["quantity"]),
                }
                for item in items
            ],
        }

    def get_by_session(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                id,
                session_id,
                total,
                created_at
            FROM orders
            WHERE session_id = ?
            ORDER BY id DESC
            """,
            (session_id,),
        ).fetchall()

        return [
            self.get_by_id(int(row["id"]))
            for row in rows
        ]