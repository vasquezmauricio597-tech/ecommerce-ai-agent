from __future__ import annotations

from typing import Any

from app.database.database import Database
from app.database.repositories import ProductRepository


class CatalogService:
    """
    Servicio de catálogo.

    Centraliza las operaciones relacionadas con productos:
    - listar productos
    - buscar productos
    - obtener producto por ID
    - obtener producto por nombre
    - consultar stock
    - modificar stock
    """

    def __init__(
        self,
        db: Database | None = None,
        db_path: str = "data/ecommerce.db",
    ) -> None:
        self.db = db or Database(db_path)

    def get_all_products(self) -> list[dict[str, Any]]:
        connection = self.db.get_connection()

        try:
            repository = ProductRepository(connection)
            return repository.get_all()
        finally:
            connection.close()

    def get_product_by_id(
        self,
        product_id: str,
    ) -> dict[str, Any] | None:
        connection = self.db.get_connection()

        try:
            repository = ProductRepository(connection)
            return repository.get_by_id(product_id)
        finally:
            connection.close()

    def get_product_by_name(
        self,
        product_name: str,
    ) -> dict[str, Any] | None:
        connection = self.db.get_connection()

        try:
            repository = ProductRepository(connection)
            return repository.get_by_name(product_name)
        finally:
            connection.close()

    def get_product_count(self) -> int:
        return len(self.get_all_products())

    def get_stock(
        self,
        product_id: str,
    ) -> int | None:
        product = self.get_product_by_id(product_id)

        if product is None:
            return None

        return int(product["stock"])

    def decrease_stock(
        self,
        product_id: str,
        quantity: int,
    ) -> bool:
        if quantity <= 0:
            return False

        connection = self.db.get_connection()

        try:
            repository = ProductRepository(connection)

            success = repository.decrease_stock(
                product_id,
                quantity,
            )

            connection.commit()

            return success

        finally:
            connection.close()

    def increase_stock(
        self,
        product_id: str,
        quantity: int,
    ) -> bool:
        if quantity <= 0:
            return False

        connection = self.db.get_connection()

        try:
            repository = ProductRepository(connection)

            success = repository.increase_stock(
                product_id,
                quantity,
            )

            connection.commit()

            return success

        finally:
            connection.close()

    def search_products(
        self,
        query: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Busca productos localmente mediante coincidencia de términos.

        Args:
            query: Texto de búsqueda.
            limit: Número máximo de productos a devolver.

        Returns:
            Lista de productos ordenados por relevancia.
        """

        if not query or not query.strip():
            return []

        if limit <= 0:
            return []

        normalized_query = query.strip().lower()

        query_terms = [
            term
            for term in normalized_query.split()
            if len(term) > 2
        ]

        if not query_terms:
            return []

        products = self.get_all_products()

        scored_products: list[
            tuple[int, dict[str, Any]]
        ] = []

        for product in products:
            searchable_parts = [
                str(product.get("name", "")),
                str(product.get("category", "")),
                str(product.get("description", "")),
            ]

            tags = product.get("tags", [])

            if isinstance(tags, list):
                searchable_parts.extend(
                    str(tag)
                    for tag in tags
                )

            searchable_text = " ".join(
                searchable_parts
            ).lower()

            score = 0

            for term in query_terms:
                if term in searchable_text:
                    score += 1

            if score > 0:
                scored_products.append(
                    (
                        score,
                        product,
                    )
                )

        scored_products.sort(
            key=lambda item: (
                -item[0],
                item[1]["id"],
            )
        )

        return [
            product
            for _, product in scored_products[:limit]
        ]