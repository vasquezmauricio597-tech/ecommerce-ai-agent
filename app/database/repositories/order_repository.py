from __future__ import annotations

import sqlite3
from typing import Any


class OrderRepository:
    """
    Persistencia de órdenes y sus líneas.
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
        subtotal = unit_price * quantity

        self.connection.execute(
            """
            INSERT INTO order_items (
                order_id,
                product_id,
                product_name,
                unit_price,
                quantity,
                subtotal
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                product_id,
                product_name,
                unit_price,
                quantity,
                subtotal,
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
                id,
                product_id,
                product_name,
                unit_price,
                quantity,
                subtotal
            FROM order_items
            WHERE order_id = ?
            ORDER BY id
            """,
            (order_id,),
        ).fetchall()

        result = dict(order)

        result["total"] = float(
            result["total"]
        )

        result["items"] = [
            {
                **dict(item),
                "unit_price": float(
                    item["unit_price"]
                ),
                "subtotal": float(
                    item["subtotal"]
                ),
                "quantity": int(
                    item["quantity"]
                ),
            }
            for item in items
        ]

        return result

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
            {
                **dict(row),
                "total": float(row["total"]),
            }
            for row in rows
        ]