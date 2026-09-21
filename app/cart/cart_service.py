from __future__ import annotations

from typing import Any

from app.catalog.catalog_service import CatalogService
from app.database.database import Database
from app.database.repositories.cart_repository import CartRepository


class CartService:
    def __init__(
        self,
        db: Database | None = None,
        catalog_service: CatalogService | None = None,
        db_path: str = "data/ecommerce.db",
    ) -> None:

        # Si recibimos un CatalogService que ya usa una
        # Database, reutilizamos exactamente esa misma DB.
        if db is None and catalog_service is not None:
            db = catalog_service.db

        self.db = db or Database(db_path)

        # Compatibilidad con CheckoutService.
        self.database = self.db

        self.catalog_service = (
            catalog_service
            or CatalogService(db=self.db)
        )

    def _validate_session_id(
        self,
        session_id: str,
    ) -> None:
        if not session_id or not session_id.strip():
            raise ValueError(
                "El session_id es obligatorio."
            )

    def _validate_quantity(
        self,
        quantity: int,
    ) -> None:
        if not isinstance(quantity, int):
            raise ValueError(
                "La cantidad debe ser un entero."
            )

        if quantity <= 0:
            raise ValueError(
                "La cantidad debe ser mayor que cero."
            )

    def _get_repository(
        self,
    ) -> tuple[Any, CartRepository]:
        connection = self.db.get_connection()

        repository = CartRepository(
            connection
        )

        return connection, repository

    def add_item(
        self,
        session_id: str,
        product_id: str,
        quantity: int = 1,
    ) -> dict[str, Any]:
        self._validate_session_id(session_id)

        if not product_id or not product_id.strip():
            raise ValueError(
                "El product_id es obligatorio."
            )

        self._validate_quantity(quantity)

        product = self.catalog_service.get_product_by_id(
            product_id
        )

        if product is None:
            raise ValueError(
                f"No existe el producto "
                f"'{product_id}'."
            )

        stock = int(product["stock"])

        connection, repository = self._get_repository()

        try:
            current_item = repository.get_item(
                session_id,
                product_id,
            )

            current_quantity = (
                int(current_item["quantity"])
                if current_item
                else 0
            )

            new_quantity = (
                current_quantity + quantity
            )

            if new_quantity > stock:
                raise ValueError(
                    f"No hay suficiente stock para "
                    f"'{product['name']}'. "
                    f"Disponible: {stock}. "
                    f"Solicitado: {new_quantity}."
                )

            repository.add_item(
                session_id=session_id,
                product_id=product_id,
                quantity=quantity,
            )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

        summary = self.get_summary(
            session_id
        )

        item = self.get_item(
            session_id,
            product_id,
        )

        if item is not None:
            summary.update(
                {
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "category": item["category"],
                    "price": item["price"],
                    "stock": item["stock"],
                    "quantity": item["quantity"],
                    "subtotal": item["subtotal"],
                }
            )

        return summary

    def update_item(
        self,
        session_id: str,
        product_id: str,
        quantity: int,
    ) -> dict[str, Any]:
        self._validate_session_id(session_id)

        if not product_id or not product_id.strip():
            raise ValueError(
                "El product_id es obligatorio."
            )

        self._validate_quantity(quantity)

        product = self.catalog_service.get_product_by_id(
            product_id
        )

        if product is None:
            raise ValueError(
                f"No existe el producto "
                f"'{product_id}'."
            )

        stock = int(product["stock"])

        if quantity > stock:
            raise ValueError(
                f"No hay suficiente stock para "
                f"'{product['name']}'. "
                f"Disponible: {stock}. "
                f"Solicitado: {quantity}."
            )

        connection, repository = self._get_repository()

        try:
            existing_item = repository.get_item(
                session_id,
                product_id,
            )

            if existing_item is None:
                raise ValueError(
                    f"El producto {product_id} "
                    "no está en el carrito."
                )

            repository.update_item(
                session_id=session_id,
                product_id=product_id,
                quantity=quantity,
            )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

        summary = self.get_summary(
            session_id
        )

        item = self.get_item(
            session_id,
            product_id,
        )

        if item is not None:
            summary.update(
                {
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "category": item["category"],
                    "price": item["price"],
                    "stock": item["stock"],
                    "quantity": item["quantity"],
                    "subtotal": item["subtotal"],
                }
            )

        return summary

    def remove_item(
        self,
        session_id: str,
        product_id: str,
    ) -> bool:
        self._validate_session_id(session_id)

        if not product_id or not product_id.strip():
            raise ValueError(
                "El product_id es obligatorio."
            )

        connection, repository = self._get_repository()

        try:
            removed = repository.remove_item(
                session_id=session_id,
                product_id=product_id,
            )

            connection.commit()

            return removed

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def get_item(
        self,
        session_id: str,
        product_id: str,
    ) -> dict[str, Any] | None:
        self._validate_session_id(session_id)

        connection, repository = self._get_repository()

        try:
            return repository.get_item(
                session_id,
                product_id,
            )

        finally:
            connection.close()

    def get_items(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:
        self._validate_session_id(session_id)

        connection, repository = self._get_repository()

        try:
            return repository.get_items(
                session_id
            )

        finally:
            connection.close()

    def get_summary(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        self._validate_session_id(session_id)

        items = self.get_items(
            session_id
        )

        subtotal = sum(
            float(item["price"])
            * int(item["quantity"])
            for item in items
        )

        item_count = sum(
            int(item["quantity"])
            for item in items
        )

        return {
            "session_id": session_id,
            "items": items,
            "item_count": item_count,
            "subtotal": subtotal,
        }

    def clear_cart(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        self._validate_session_id(session_id)

        connection, repository = self._get_repository()

        try:
            repository.clear(
                session_id
            )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

        return self.get_summary(
            session_id
        )

    def is_empty(
        self,
        session_id: str,
    ) -> bool:
        return len(
            self.get_items(session_id)
        ) == 0