from pathlib import Path

import pytest

from app.cart.cart_service import CartService
from app.catalog.catalog_service import CatalogService
from app.checkout.checkout_service import CheckoutService
from app.database.database import Database


@pytest.fixture
def services(tmp_path):
    """
    Crea una base de datos SQLite aislada para cada test.
    Así los tests no modifican data/ecommerce.db.
    """

    db_path = str(tmp_path / "test_ecommerce.db")

    db = Database(db_path=db_path)

    catalog_service = CatalogService(db=db)
    cart_service = CartService(catalog_service=catalog_service)
    checkout_service = CheckoutService(cart_service=cart_service)

    # Insertamos un producto controlado para los tests.
    with db.get_connection() as connection:
        connection.execute(
            """
            INSERT INTO products (
                id,
                name,
                category,
                price,
                stock,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "TEST-001",
                "Producto de prueba",
                "Testing",
                100.0,
                10,
                "Producto utilizado para pruebas automatizadas.",
            ),
        )

    return {
        "db": db,
        "catalog": catalog_service,
        "cart": cart_service,
        "checkout": checkout_service,
    }


def test_add_product_to_cart(services):
    cart = services["cart"]

    item = cart.add_item(
        session_id="test-session",
        product_id="TEST-001",
        quantity=2,
    )

    assert item["product_id"] == "TEST-001"
    assert item["name"] == "Producto de prueba"
    assert item["quantity"] == 2
    assert item["price"] == 100.0
    assert item["subtotal"] == 200.0


def test_cart_summary(services):
    cart = services["cart"]

    cart.add_item(
        session_id="test-session",
        product_id="TEST-001",
        quantity=3,
    )

    summary = cart.get_summary("test-session")

    assert summary["session_id"] == "test-session"
    assert summary["item_count"] == 3
    assert summary["subtotal"] == 300.0
    assert len(summary["items"]) == 1


def test_update_cart_quantity(services):
    cart = services["cart"]

    cart.add_item(
        session_id="test-session",
        product_id="TEST-001",
        quantity=1,
    )

    updated = cart.update_item(
        session_id="test-session",
        product_id="TEST-001",
        quantity=4,
    )

    assert updated["quantity"] == 4
    assert updated["subtotal"] == 400.0


def test_remove_product_from_cart(services):
    cart = services["cart"]

    cart.add_item(
        session_id="test-session",
        product_id="TEST-001",
        quantity=2,
    )

    removed = cart.remove_item(
        session_id="test-session",
        product_id="TEST-001",
    )

    assert removed is True
    assert cart.get_items("test-session") == []


def test_checkout_creates_order_and_clears_cart(services):
    cart = services["cart"]
    checkout = services["checkout"]

    cart.add_item(
        session_id="test-session",
        product_id="TEST-001",
        quantity=2,
    )

    order = checkout.create_order("test-session")

    assert order["id"] is not None
    assert order["session_id"] == "test-session"
    assert order["total"] == 200.0

    # El carrito debe quedar vacío.
    assert cart.get_items("test-session") == []

    # El stock debe disminuir de 10 a 8.
    product = services["catalog"].get_product_by_id("TEST-001")

    assert product["stock"] == 8


def test_checkout_empty_cart_fails(services):
    checkout = services["checkout"]

    with pytest.raises(ValueError, match="carrito vacío"):
        checkout.create_order("test-session")


def test_cannot_add_more_than_available_stock(services):
    cart = services["cart"]

    with pytest.raises(ValueError, match="suficiente stock"):
        cart.add_item(
            session_id="test-session",
            product_id="TEST-001",
            quantity=11,
        )


def test_cannot_use_invalid_product(services):
    cart = services["cart"]

    with pytest.raises(ValueError, match="No existe el producto"):
        cart.add_item(
            session_id="test-session",
            product_id="DOES-NOT-EXIST",
            quantity=1,
        )


def test_invalid_quantity_fails(services):
    cart = services["cart"]

    with pytest.raises(ValueError, match="mayor que cero"):
        cart.add_item(
            session_id="test-session",
            product_id="TEST-001",
            quantity=0,
        )