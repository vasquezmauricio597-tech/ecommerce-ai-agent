from fastapi.testclient import TestClient

from app.api.main import (
    app,
    chat_sessions,
    cart_service,
)


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "E-commerce AI Agent API is running"
    )


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_chat_local_stock():
    session_id = "api-stock-test"

    response = client.post(
        "/chat",
        json={
            "session_id": session_id,
            "message": "¿Cuánto stock tiene PROD-003?",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["session_id"] == session_id
    assert data["gemini_calls"] == 0
    assert data["tool_calls"] == 1
    assert "PROD-003" in data["response"]


def test_chat_local_search():
    session_id = "api-search-test"

    response = client.post(
        "/chat",
        json={
            "session_id": session_id,
            "message": (
                "busco audífonos inalámbricos "
                "con cancelación de ruido"
            ),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["gemini_calls"] == 0
    assert data["tool_calls"] == 1
    assert "PROD-003" in data["response"]


def test_chat_local_recommendation():
    session_id = "api-recommendation-test"

    response = client.post(
        "/chat",
        json={
            "session_id": session_id,
            "message": (
                "¿Qué me recomiendas "
                "para trabajar desde casa?"
            ),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["gemini_calls"] == 0


def test_chat_session_reuse():
    session_id = "api-session-reuse"

    first = client.post(
        "/chat",
        json={
            "session_id": session_id,
            "message": "busco un teclado mecánico",
        },
    )

    second = client.post(
        "/chat",
        json={
            "session_id": session_id,
            "message": "también necesito algo para audio",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert session_id in chat_sessions


def test_chat_session_isolation():
    session_a = "api-session-a"
    session_b = "api-session-b"

    client.post(
        "/chat",
        json={
            "session_id": session_a,
            "message": "busco un teclado",
        },
    )

    client.post(
        "/chat",
        json={
            "session_id": session_b,
            "message": "busco una laptop",
        },
    )

    assert session_a in chat_sessions
    assert session_b in chat_sessions
    assert chat_sessions[session_a] is not chat_sessions[session_b]


def test_chat_missing_message():
    response = client.post(
        "/chat",
        json={
            "session_id": "invalid-message"
        },
    )

    assert response.status_code == 422


def test_chat_empty_message():
    response = client.post(
        "/chat",
        json={
            "session_id": "invalid-message",
            "message": "",
        },
    )

    assert response.status_code == 422


def test_chat_invalid_json():
    response = client.post(
        "/chat",
        content="esto no es json",
        headers={
            "Content-Type": "application/json"
        },
    )

    assert response.status_code == 422


def test_cart_add():
    session_id = "api-cart-add"

    response = client.post(
        f"/cart/{session_id}/items",
        json={
            "product_id": "PROD-005",
            "quantity": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["session_id"] == session_id
    assert data["item_count"] == 2


def test_cart_get():
    session_id = "api-cart-get"

    client.post(
        f"/cart/{session_id}/items",
        json={
            "product_id": "PROD-005",
            "quantity": 1,
        },
    )

    response = client.get(
        f"/cart/{session_id}"
    )

    assert response.status_code == 200
    assert response.json()["item_count"] == 1


def test_cart_update():
    session_id = "api-cart-update"

    client.post(
        f"/cart/{session_id}/items",
        json={
            "product_id": "PROD-005",
            "quantity": 1,
        },
    )

    response = client.put(
        f"/cart/{session_id}/items/PROD-005",
        json={
            "quantity": 3,
        },
    )

    assert response.status_code == 200
    assert response.json()["item_count"] == 3


def test_cart_remove():
    session_id = "api-cart-remove"

    client.post(
        f"/cart/{session_id}/items",
        json={
            "product_id": "PROD-005",
            "quantity": 1,
        },
    )

    response = client.delete(
        f"/cart/{session_id}/items/PROD-005"
    )

    assert response.status_code == 200


def test_cart_clear():
    session_id = "api-cart-clear"

    client.post(
        f"/cart/{session_id}/items",
        json={
            "product_id": "PROD-005",
            "quantity": 1,
        },
    )

    response = client.delete(
        f"/cart/{session_id}"
    )

    assert response.status_code == 200

    cart = client.get(
        f"/cart/{session_id}"
    )

    assert cart.status_code == 200
    assert cart.json()["item_count"] == 0


def test_checkout_api():
    session_id = "api-checkout"

    client.post(
        f"/cart/{session_id}/items",
        json={
            "product_id": "PROD-005",
            "quantity": 1,
        },
    )

    response = client.post(
        f"/checkout/{session_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["session_id"] == session_id
    assert data["total"] > 0
    assert len(data["items"]) == 1


def test_checkout_empty_cart():
    session_id = "api-empty-checkout"

    response = client.post(
        f"/checkout/{session_id}"
    )

    assert response.status_code == 400


def test_order_not_found():
    response = client.get(
        "/orders/999999999"
    )

    assert response.status_code == 404