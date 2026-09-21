from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.agent import agent as agent_module
from app.agent.agent import create_agent, process_message
from app.cart.cart_service import CartService
from app.checkout.checkout_service import CheckoutService


app = FastAPI(
    title="E-commerce AI Agent API",
    description=(
        "API para un agente de e-commerce "
        "con catálogo, carrito y checkout."
    ),
    version="1.0.0",
)


# -------------------------------------------------------------------
# Servicios
# -------------------------------------------------------------------

cart_service = CartService()

checkout_service = CheckoutService(
    cart_service=cart_service
)

llm, llm_with_tools, tool_map = create_agent()


# -------------------------------------------------------------------
# Sesiones de conversación
# -------------------------------------------------------------------

chat_sessions: dict[str, list] = {}


# -------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
    )


class ChatResponse(BaseModel):
    session_id: str
    response: str
    gemini_calls: int
    tool_calls: int


class CartItemRequest(BaseModel):
    product_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    quantity: int = Field(
        ...,
        gt=0,
    )


class CartUpdateRequest(BaseModel):
    quantity: int = Field(
        ...,
        gt=0,
    )


# -------------------------------------------------------------------
# Health
# -------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "E-commerce AI Agent API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


# -------------------------------------------------------------------
# Chat
# -------------------------------------------------------------------

@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest):
    if request.session_id not in chat_sessions:
        chat_sessions[request.session_id] = []

    messages = chat_sessions[request.session_id]

    # Cada request empieza con métricas independientes.
    agent_module.reset_metrics()

    response = process_message(
        request.message,
        llm,
        llm_with_tools,
        tool_map,
        messages,
        request.session_id,
    )

    return {
        "session_id": request.session_id,
        "response": response,
        "gemini_calls": agent_module._metrics[
            "gemini_calls"
        ],
        "tool_calls": agent_module._metrics[
            "tool_calls"
        ],
    }


# -------------------------------------------------------------------
# Cart
# -------------------------------------------------------------------

@app.get("/cart/{session_id}")
def get_cart(session_id: str):
    try:
        return cart_service.get_summary(
            session_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.post("/cart/{session_id}/items")
def add_cart_item(
    session_id: str,
    request: CartItemRequest,
):
    try:
        # CartService devuelve el ítem agregado.
        cart_service.add_item(
            session_id=session_id,
            product_id=request.product_id,
            quantity=request.quantity,
        )

        # La API mantiene su contrato de devolver
        # el resumen completo del carrito.
        return cart_service.get_summary(
            session_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.put(
    "/cart/{session_id}/items/{product_id}"
)
def update_cart_item(
    session_id: str,
    product_id: str,
    request: CartUpdateRequest,
):
    try:
        # CartService devuelve el ítem actualizado.
        cart_service.update_item(
            session_id=session_id,
            product_id=product_id,
            quantity=request.quantity,
        )

        # La API mantiene el contrato de devolver
        # el resumen completo del carrito.
        return cart_service.get_summary(
            session_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.delete(
    "/cart/{session_id}/items/{product_id}"
)
def remove_cart_item(
    session_id: str,
    product_id: str,
):
    try:
        removed = cart_service.remove_item(
            session_id,
            product_id,
        )

        if not removed:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Producto no encontrado "
                    "en el carrito."
                ),
            )

        return {
            "message": (
                "Producto eliminado "
                "del carrito."
            ),
            "session_id": session_id,
            "product_id": product_id.upper(),
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@app.delete("/cart/{session_id}")
def clear_cart(session_id: str):
    try:
        cart_service.clear_cart(
            session_id
        )

        return {
            "message": "Carrito vaciado.",
            "session_id": session_id,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# -------------------------------------------------------------------
# Checkout
# -------------------------------------------------------------------

@app.post("/checkout/{session_id}")
def checkout(session_id: str):
    try:
        return checkout_service.create_order(
            session_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


# -------------------------------------------------------------------
# Orders
# -------------------------------------------------------------------

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    order = checkout_service.get_order(
        order_id
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    return order


@app.get(
    "/orders/session/{session_id}"
)
def get_session_orders(session_id: str):
    return checkout_service.get_orders_by_session(
        session_id
    )