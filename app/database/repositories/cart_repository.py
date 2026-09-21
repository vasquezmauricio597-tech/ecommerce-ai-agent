from __future__ import annotations

import sqlite3
from typing import Any


class CartRepository:
    """
    Acceso persistente a carritos y sus líneas.
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
            INSERT INTO carts (
                session_id
            )
            VALUES (?)
            ON CONFLICT(session_id)
            DO UPDATE SET
                updated_at = CURRENT_TIMESTAMP
            """,
            (session_id,),
        )

    def get_item(
        self,
        session_id: str,
        product_id: str,
    ) -> dict[str, Any] | None:
        normalized_id = product_id.strip().upper()

        row = self.connection.execute(
            """
            SELECT
                ci.session_id,
                ci.product_id,
                ci.quantity,
                p.name,
                p.category,
                p.price,
                p.stock,
                p.description
            FROM cart_items ci
            JOIN products p
                ON p.id = ci.product_id
            WHERE ci.session_id = ?
              AND UPPER(ci.product_id) = ?
            LIMIT 1
            """,
            (
                session_id,
                normalized_id,
            ),
        ).fetchone()

        if row is None:
            return None

        item = dict(row)

        item["price"] = float(item["price"])
        item["stock"] = int(item["stock"])
        item["quantity"] = int(item["quantity"])

        item["subtotal"] = (
            item["price"] * item["quantity"]
        )

        return item

    def get_items(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                ci.session_id,
                ci.product_id,
                ci.quantity,
                p.name,
                p.category,
                p.price,
                p.stock,
                p.description
            FROM cart_items ci
            JOIN products p
                ON p.id = ci.product_id
            WHERE ci.session_id = ?
            ORDER BY ci.product_id
            """,
            (session_id,),
        ).fetchall()

        items: list[dict[str, Any]] = []

        for row in rows:
            item = dict(row)

            item["price"] = float(item["price"])
            item["stock"] = int(item["stock"])
            item["quantity"] = int(item["quantity"])

            item["subtotal"] = (
                item["price"] * item["quantity"]
            )

            items.append(item)

        return items

    def add_item(
        self,
        session_id: str,
        product_id: str,
        quantity: int,
    ) -> None:
        normalized_id = product_id.strip().upper()

        self.ensure_cart(session_id)

        self.connection.execute(
            """
            INSERT INTO cart_items (
                session_id,
                product_id,
                quantity
            )
            VALUES (?, ?, ?)
            ON CONFLICT(
                session_id,
                product_id
            )
            DO UPDATE SET
                quantity =
                    quantity + excluded.quantity
            """,
            (
                session_id,
                normalized_id,
                quantity,
            ),
        )

        self.touch_cart(session_id)

    def update_item(
        self,
        session_id: str,
        product_id: str,
        quantity: int,
    ) -> None:
        normalized_id = product_id.strip().upper()

        self.ensure_cart(session_id)

        self.connection.execute(
            """
            UPDATE cart_items
            SET quantity = ?
            WHERE session_id = ?
              AND UPPER(product_id) = ?
            """,
            (
                quantity,
                session_id,
                normalized_id,
            ),
        )

        self.touch_cart(session_id)

    def remove_item(
        self,
        session_id: str,
        product_id: str,
    ) -> bool:
        normalized_id = product_id.strip().upper()

        self.ensure_cart(session_id)

        cursor = self.connection.execute(
            """
            DELETE FROM cart_items
            WHERE session_id = ?
              AND UPPER(product_id) = ?
            """,
            (
                session_id,
                normalized_id,
            ),
        )

        self.touch_cart(session_id)

        return cursor.rowcount == 1

    def clear(
        self,
        session_id: str,
    ) -> None:
        self.ensure_cart(session_id)

        self.connection.execute(
            """
            DELETE FROM cart_items
            WHERE session_id = ?
            """,
            (session_id,),
        )

        self.touch_cart(session_id)

    def touch_cart(
        self,
        session_id: str,
    ) -> None:
        self.connection.execute(
            """
            UPDATE carts
            SET updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (session_id,),
        )