import pytest

from app.cart.cart_service import CartService
from app.database import Database


@pytest.fixture
def cart(tmp_path):
    db = Database(
        db_path=str(
            tmp_path / "test_cart.db"
        )
    )

    return CartService(db=db)


def test_add_item(cart):
    result = cart.add_item(
        "session-1",
        "PROD-005",
        2,
    )

    assert result["item_count"] == 2
    assert len(result["items"]) == 1
    assert result["items"][0]["product_id"] == "PROD-005"


def test_add_same_item_accumulates(cart):
    cart.add_item(
        "session-1",
        "PROD-005",
        2,
    )

    result = cart.add_item(
        "session-1",
        "PROD-005",
        3,
    )

    assert result["item_count"] == 5


def test_update_item(cart):
    cart.add_item(
        "session-1",
        "PROD-005",
        2,
    )

    result = cart.update_item(
        "session-1",
        "PROD-005",
        5,
    )

    assert result["item_count"] == 5


def test_remove_item(cart):
    cart.add_item(
        "session-1",
        "PROD-005",
        1,
    )

    removed = cart.remove_item(
        "session-1",
        "PROD-005",
    )

    assert removed is True
    assert cart.get_items("session-1") == []


def test_remove_missing_item(cart):
    removed = cart.remove_item(
        "session-1",
        "PROD-005",
    )

    assert removed is False


def test_clear_cart(cart):
    cart.add_item(
        "session-1",
        "PROD-005",
        2,
    )

    cart.clear_cart(
        "session-1"
    )

    assert cart.get_items(
        "session-1"
    ) == []


def test_summary(cart):
    result = cart.add_item(
        "session-1",
        "PROD-005",
        2,
    )

    assert result["item_count"] == 2
    assert result["subtotal"] == 260.0


def test_unknown_product(cart):
    with pytest.raises(ValueError):
        cart.add_item(
            "session-1",
            "PROD-999",
            1,
        )


def test_more_than_stock(cart):
    with pytest.raises(ValueError):
        cart.add_item(
            "session-1",
            "PROD-005",
            999,
        )


def test_invalid_quantity(cart):
    with pytest.raises(ValueError):
        cart.add_item(
            "session-1",
            "PROD-005",
            0,
        )


def test_cart_survives_service_recreation(tmp_path):
    db_path = str(
        tmp_path / "persistent_cart.db"
    )

    db = Database(
        db_path=db_path
    )

    cart_one = CartService(
        db=db
    )

    cart_one.add_item(
        "persistent-session",
        "PROD-005",
        3,
    )

    db_two = Database(
        db_path=db_path
    )

    cart_two = CartService(
        db=db_two
    )

    result = cart_two.get_summary(
        "persistent-session"
    )

    assert result["item_count"] == 3
    assert result["items"][0]["product_id"] == "PROD-005"