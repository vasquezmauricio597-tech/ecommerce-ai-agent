from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator


DEFAULT_DB_PATH = "data/ecommerce.db"
DEFAULT_CATALOG_PATH = "data/products.json"


class Database:
    """
    Capa de acceso a SQLite.

    Responsabilidades:
    - crear la base de datos
    - crear el esquema
    - cargar el catálogo inicial
    - proporcionar conexiones
    - proporcionar transacciones
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        catalog_path: str = DEFAULT_CATALOG_PATH,
    ):
        self.db_path = db_path
        self.catalog_path = catalog_path

        self._ensure_directory()
        self.initialize()

    def _ensure_directory(self) -> None:
        directory = os.path.dirname(self.db_path)

        if directory:
            os.makedirs(directory, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=10,
        )

        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.execute(
            "PRAGMA busy_timeout = 10000"
        )

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.get_connection()

        try:
            connection.execute("BEGIN")
            yield connection
            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def initialize(self) -> None:
        connection = self.get_connection()

        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price REAL NOT NULL CHECK(price >= 0),
                    stock INTEGER NOT NULL CHECK(stock >= 0),
                    description TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS carts (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS cart_items (
                    session_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK(quantity > 0),

                    PRIMARY KEY(session_id, product_id),

                    FOREIGN KEY(session_id)
                        REFERENCES carts(session_id)
                        ON DELETE CASCADE,

                    FOREIGN KEY(product_id)
                        REFERENCES products(id)
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    total REAL NOT NULL CHECK(total >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    product_id TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    unit_price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    subtotal REAL NOT NULL,

                    FOREIGN KEY(order_id)
                        REFERENCES orders(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_orders_session
                    ON orders(session_id);

                CREATE INDEX IF NOT EXISTS idx_order_items_order
                    ON order_items(order_id);
                """
            )

            self._seed_products(connection)

            connection.commit()

        finally:
            connection.close()

    def _seed_products(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        count = connection.execute(
            "SELECT COUNT(*) AS count FROM products"
        ).fetchone()["count"]

        if count > 0:
            return

        if not os.path.exists(self.catalog_path):
            return

        with open(
            self.catalog_path,
            "r",
            encoding="utf-8-sig",
        ) as file:
            products = json.load(file)

        for product in products:
            tags = product.get("tags", [])

            connection.execute(
                """
                INSERT INTO products (
                    id,
                    name,
                    category,
                    price,
                    stock,
                    description,
                    tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product["id"],
                    product["name"],
                    product["category"],
                    float(product["price"]),
                    int(product["stock"]),
                    product["description"],
                    json.dumps(
                        tags,
                        ensure_ascii=False,
                    ),
                ),
            )

    def reset(self) -> None:
        connection = self.get_connection()

        try:
            connection.executescript(
                """
                DROP TABLE IF EXISTS order_items;
                DROP TABLE IF EXISTS orders;
                DROP TABLE IF EXISTS cart_items;
                DROP TABLE IF EXISTS carts;
                DROP TABLE IF EXISTS products;
                """
            )

            connection.commit()

        finally:
            connection.close()

        self.initialize()