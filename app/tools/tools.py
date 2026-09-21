from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.catalog.catalog_service import CatalogService
from app.cart.cart_service import CartService
from app.checkout.checkout_service import CheckoutService


# ============================================================
# SERVICIOS
# ============================================================

catalog_service = CatalogService()

cart_service = CartService(
    catalog_service=catalog_service
)

checkout_service = CheckoutService(
    cart_service=cart_service
)


# ============================================================
# CATÁLOGO
# ============================================================

@tool
def search_products_catalog(query: str) -> str:
    """
    Busca productos del catálogo utilizando búsqueda semántica.
    """

    from app.catalog.catalog_service import CatalogService

    service = CatalogService()

    products = service.search_products(
        query=query,
        limit=3,
    )

    if not products:
        return "No se encontraron productos suficientemente relevantes."

    lines = [
        "Productos encontrados:"
    ]

    for product in products:
        lines.append(
            f"- ID: {product['id']} | "
            f"Nombre: {product['name']} | "
            f"Categoría: {product['category']} | "
            f"Precio: ${product['price']} | "
            f"Stock: {product['stock']} | "
            f"Detalle: {product['description']}"
        )

    return "\n".join(lines)


@tool
def check_product_stock(product_id: str) -> str:
    """
    Consulta el stock actual de un producto.
    """

    product = catalog_service.get_product_by_id(
        product_id
    )

    if product is None:
        return (
            f"No existe el producto "
            f"'{product_id}'."
        )

    return (
        f"Producto: {product['name']}\n"
        f"ID: {product['id']}\n"
        f"Stock disponible: {product['stock']}"
    )


# ============================================================
# CARRITO
# ============================================================

@tool
def add_product_to_cart(
    session_id: str,
    product_id: str,
    quantity: int = 1,
) -> dict[str, Any]:
    """
    Agrega un producto al carrito.

    Devuelve los datos del producto agregado y
    el estado actual del carrito.
    """

    summary = cart_service.add_item(
        session_id=session_id,
        product_id=product_id,
        quantity=quantity,
    )

    item = cart_service.get_item(
        session_id=session_id,
        product_id=product_id,
    )

    if item is None:
        raise ValueError(
            "El producto fue agregado pero "
            "no pudo recuperarse del carrito."
        )

    return {
        "session_id": session_id,
        "product_id": item["product_id"],
        "name": item["name"],
        "category": item["category"],
        "price": item["price"],
        "stock": item["stock"],
        "quantity": item["quantity"],
        "subtotal": item["subtotal"],
        "item_count": summary["item_count"],
        "cart_subtotal": summary["subtotal"],
    }


@tool
def get_cart(
    session_id: str,
) -> dict[str, Any]:
    """
    Obtiene el carrito completo de una sesión.
    """

    return cart_service.get_summary(
        session_id
    )


@tool
def update_product_in_cart(
    session_id: str,
    product_id: str,
    quantity: int,
) -> dict[str, Any]:
    """
    Actualiza la cantidad de un producto en el carrito.
    """

    summary = cart_service.update_item(
        session_id=session_id,
        product_id=product_id,
        quantity=quantity,
    )

    item = cart_service.get_item(
        session_id=session_id,
        product_id=product_id,
    )

    if item is None:
        raise ValueError(
            "El producto fue actualizado pero "
            "no pudo recuperarse del carrito."
        )

    return {
        "session_id": session_id,
        "product_id": item["product_id"],
        "name": item["name"],
        "quantity": item["quantity"],
        "price": item["price"],
        "subtotal": item["subtotal"],
        "item_count": summary["item_count"],
        "cart_subtotal": summary["subtotal"],
    }


@tool
def remove_product_from_cart(
    session_id: str,
    product_id: str,
) -> dict[str, Any]:
    """
    Elimina un producto del carrito.
    """

    removed = cart_service.remove_item(
        session_id=session_id,
        product_id=product_id,
    )

    if not removed:
        return {
            "success": False,
            "session_id": session_id,
            "product_id": product_id.upper(),
            "message": (
                "El producto no estaba "
                "en el carrito."
            ),
        }

    return {
        "success": True,
        "session_id": session_id,
        "product_id": product_id.upper(),
        "message": (
            "Producto eliminado "
            "correctamente."
        ),
    }


# ============================================================
# CHECKOUT
# ============================================================

@tool
def checkout_cart(
    session_id: str,
) -> dict[str, Any]:
    """
    Completa la compra del carrito.
    """

    return checkout_service.create_order(
        session_id
    )