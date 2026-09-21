import pytest

from app.cart.cart_service import CartService
from app.checkout.checkout_service import CheckoutService
from app.database import Database


@pytest.fixture
def services(tmp_path):
    db = Database(
        db_path=str(
            tmp_path / "test_checkout.db"
        )
    )

    cart = CartService(
        db=db
    )

    checkout = CheckoutService(
        cart_service=cart
    )

    return db, cart, checkout


def test_checkout_creates_order(services):
    _, cart, checkout = services

    cart.add_item(
        "session-1",
        "PROD-005",
        2,
    )

    order = checkout.create_order(
        "session-1"
    )

    assert order["id"] > 0
    assert order["session_id"] == "session-1"
    assert order["total"] == 260.0


def test_checkout_contains_items(services):
    _, cart, checkout = services

    cart.add_item(
        "session-1",
        "PROD-005",
        2,
    )

    order = checkout.create_order(
        "session-1"
    )

    assert len(order["items"]) == 1

    item = order["items"][0]

    assert item["product_id"] == "PROD-005"
    assert item["product_name"] == (
        "Teclado Mecánico Silent"
    )
    assert item["quantity"] == 2
    assert item["unit_price"] == 130.0
    assert item["subtotal"] == 260.0


def test_checkout_clears_cart(services):
    _, cart, checkout = services

    cart.add_item(
        "session-1",
        "PROD-005",
        1,
    )

    checkout.create_order(
        "session-1"
    )

    assert cart.get_items(
        "session-1"
    ) == []


def test_checkout_decreases_stock(services):
    db, cart, checkout = services

    before = db.get_connection()

    try:
        stock_before = before.execute(
            """
            SELECT stock
            FROM products
            WHERE id = 'PROD-005'
            """
        ).fetchone()["stock"]

    finally:
        before.close()

    cart.add_item(
        "session-1",
        "PROD-005",
        4,
    )

    checkout.create_order(
        "session-1"
    )

    after = db.get_connection()

    try:
        stock_after = after.execute(
            """
            SELECT stock
            FROM products
            WHERE id = 'PROD-005'
            """
        ).fetchone()["stock"]

    finally:
        after.close()

    assert stock_after == stock_before - 4


def test_empty_cart_fails(services):
    _, _, checkout = services

    with pytest.raises(ValueError):
        checkout.create_order(
            "empty-session"
        )


def test_insufficient_stock_rolls_back(services):
    db, cart, checkout = services

    # El carrito registra 30 unidades.
    cart.add_item(
        "session-1",
        "PROD-005",
        30,
    )

    # Simulamos que otro comprador consume
    # una unidad antes del checkout.
    connection = db.get_connection()

    try:
        connection.execute(
            """
            UPDATE products
            SET stock = 29
            WHERE id = 'PROD-005'
            """
        )

        # IMPORTANTE:
        # confirmar el cambio para que el checkout,
        # usando otra conexión, pueda verlo.
        connection.commit()

    finally:
        connection.close()

    # El carrito pide 30, pero ahora solo existen 29.
    with pytest.raises(ValueError):
        checkout.create_order(
            "session-1"
        )

    # El carrito debe permanecer intacto.
    cart_after = cart.get_items(
        "session-1"
    )

    assert len(cart_after) == 1
    assert cart_after[0]["quantity"] == 30

    # No debe haberse creado ninguna orden.
    connection = db.get_connection()

    try:
        orders = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM orders
            """
        ).fetchone()["count"]

    finally:
        connection.close()

    assert orders == 0


def test_order_persists(services):
    _, cart, checkout = services

    cart.add_item(
        "session-1",
        "PROD-005",
        1,
    )

    created = checkout.create_order(
        "session-1"
    )

    order = checkout.get_order(
        created["id"]
    )

    assert order is not None
    assert order["id"] == created["id"]
    assert order["total"] == 130.0


def test_session_order_history(services):
    _, cart, checkout = services

    cart.add_item(
        "session-1",
        "PROD-005",
        1,
    )

    first = checkout.create_order(
        "session-1"
    )

    cart.add_item(
        "session-1",
        "PROD-003",
        1,
    )

    second = checkout.create_order(
        "session-1"
    )

    orders = checkout.get_orders_by_session(
        "session-1"
    )

    ids = {
        order["id"]
        for order in orders
    }

    assert first["id"] in ids
    assert second["id"] in ids
    assert len(orders) == 2