from __future__ import annotations

from typing import Any

from app.cart.cart_service import CartService
from app.catalog.catalog_service import CatalogService
from app.database import Database
from app.database.repositories import (
    CartRepository,
    OrderRepository,
    ProductRepository,
)


class CheckoutService:
    """
    Procesa checkout de forma transaccional.

    Una orden:
    1. valida carrito
    2. valida stock
    3. crea orden
    4. descuenta stock
    5. crea líneas históricas
    6. vacía carrito
    7. confirma todo

    Si cualquier paso falla, todo vuelve atrás.
    """

    def __init__(
        self,
        cart_service: CartService | None = None,
        db: Database | None = None,
        db_path: str | None = None,
    ):
        if cart_service is not None:
            # Reutilizamos el CartService existente
            # y, por tanto, su misma base de datos.
            self.cart_service = cart_service
            self.db = cart_service.database

        elif db is not None:
            # Creamos un CatalogService sobre la misma
            # instancia de Database.
            catalog_service = CatalogService(
                db=db
            )

            self.cart_service = CartService(
                catalog_service=catalog_service
            )

            self.db = db

        elif db_path is not None:
            self.cart_service = CartService(
                db_path=db_path
            )

            self.db = self.cart_service.database

        else:
            self.cart_service = CartService()

            self.db = self.cart_service.database

    def create_order(
        self,
        session_id: str,
    ) -> dict[str, Any]:

        if not session_id or not session_id.strip():
            raise ValueError(
                "El session_id es obligatorio."
            )

        with self.db.transaction() as connection:

            cart_repository = CartRepository(
                connection
            )

            product_repository = ProductRepository(
                connection
            )

            order_repository = OrderRepository(
                connection
            )

            items = cart_repository.get_items(
                session_id
            )

            if not items:
                raise ValueError(
                    "No se puede completar el checkout "
                    "con un carrito vacío."
                )

            total = 0.0

            # -------------------------------------------------
            # 1. Validar productos y stock
            # -------------------------------------------------

            for item in items:

                product = product_repository.get_by_id(
                    item["product_id"]
                )

                if product is None:
                    raise ValueError(
                        f"Producto '{item['product_id']}' "
                        "no encontrado."
                    )

                quantity = int(
                    item["quantity"]
                )

                if product["stock"] < quantity:
                    raise ValueError(
                        f"Stock insuficiente para "
                        f"'{product['name']}'. "
                        f"Disponible: {product['stock']}."
                    )

                total += (
                    float(product["price"])
                    * quantity
                )

            # -------------------------------------------------
            # 2. Crear orden
            # -------------------------------------------------

            order_id = order_repository.create_order(
                session_id,
                total,
            )

            # -------------------------------------------------
            # 3. Descontar stock y crear líneas históricas
            # -------------------------------------------------

            for item in items:

                product = product_repository.get_by_id(
                    item["product_id"]
                )

                if product is None:
                    raise ValueError(
                        f"Producto '{item['product_id']}' "
                        "no encontrado."
                    )

                quantity = int(
                    item["quantity"]
                )

                success = product_repository.decrease_stock(
                    product["id"],
                    quantity,
                )

                if not success:
                    raise ValueError(
                        f"No fue posible reservar "
                        f"el stock de '{product['name']}'."
                    )

                order_repository.add_item(
                    order_id=order_id,
                    product_id=product["id"],
                    product_name=product["name"],
                    unit_price=float(
                        product["price"]
                    ),
                    quantity=quantity,
                )

            # -------------------------------------------------
            # 4. Vaciar carrito
            # -------------------------------------------------

            cart_repository.clear(
                session_id
            )

        # -----------------------------------------------------
        # 5. Recuperar orden creada
        # -----------------------------------------------------

        result = self.get_order(
            order_id
        )

        if result is None:
            raise RuntimeError(
                "La orden fue creada pero no pudo recuperarse."
            )

        return result

    def get_order(
        self,
        order_id: int,
    ) -> dict[str, Any] | None:

        connection = self.db.get_connection()

        try:
            repository = OrderRepository(
                connection
            )

            return repository.get_by_id(
                order_id
            )

        finally:
            connection.close()

    def get_orders_by_session(
        self,
        session_id: str,
    ) -> list[dict[str, Any]]:

        connection = self.db.get_connection()

        try:
            repository = OrderRepository(
                connection
            )

            return repository.get_by_session(
                session_id
            )

        finally:
            connection.close()