from __future__ import annotations

import os
import re
from typing import Any

from dotenv import load_dotenv

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from langchain_google_genai import ChatGoogleGenerativeAI

from app.recommendation.recommendation_engine import RecommendationEngine

from app.tools.tools import (
    add_product_to_cart,
    check_product_stock,
    checkout_cart,
    get_cart,
    remove_product_from_cart,
    search_products_catalog,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

load_dotenv()

MAX_GEMINI_CALLS = 2
MAX_HISTORY_MESSAGES = 6
DEFAULT_SESSION_ID = "cli-session-001"


# ============================================================
# EXCEPCIONES
# ============================================================

class GoogleAPIUnavailableError(Exception):
    """Gemini no está disponible temporalmente."""


# ============================================================
# MÉTRICAS
# ============================================================

_metrics = {
    "gemini_calls": 0,
    "tool_calls": 0,
    "gemini_rounds": 0,
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
}


def reset_metrics() -> None:
    """Reinicia las métricas."""

    _metrics["gemini_calls"] = 0
    _metrics["tool_calls"] = 0
    _metrics["gemini_rounds"] = 0
    _metrics["input_tokens"] = 0
    _metrics["output_tokens"] = 0
    _metrics["total_tokens"] = 0


def record_tool_call() -> None:
    """Registra una llamada de herramienta."""

    _metrics["tool_calls"] += 1


def record_gemini_usage(response: Any) -> None:
    """Registra los tokens devueltos por Gemini."""

    usage = getattr(response, "usage_metadata", None)

    if not usage:
        return

    input_tokens = usage.get(
        "input_tokens",
        usage.get("prompt_token_count", 0),
    )

    output_tokens = usage.get(
        "output_tokens",
        usage.get("candidates_token_count", 0),
    )

    total_tokens = usage.get(
        "total_tokens",
        input_tokens + output_tokens,
    )

    _metrics["input_tokens"] += int(
        input_tokens or 0
    )

    _metrics["output_tokens"] += int(
        output_tokens or 0
    )

    _metrics["total_tokens"] += int(
        total_tokens or 0
    )


def print_metrics() -> None:
    """Muestra las métricas."""

    print("\n[Métricas]")

    print(
        f"  Gemini: {_metrics['gemini_calls']} llamada(s)"
    )

    print(
        f"  Herramientas: {_metrics['tool_calls']} llamada(s)"
    )

    print(
        f"  Rondas Gemini: {_metrics['gemini_rounds']}"
    )

    print(
        f"  Tokens entrada: {_metrics['input_tokens']}"
    )

    print(
        f"  Tokens salida: {_metrics['output_tokens']}"
    )

    print(
        f"  Tokens total: {_metrics['total_tokens']}"
    )


# ============================================================
# MODELO
# ============================================================

def create_agent():
    """
    Crea Gemini y las herramientas del agente.
    """

    api_key = (
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
    )

    if not api_key:
        raise RuntimeError(
            "No se encontró GOOGLE_API_KEY ni GEMINI_API_KEY "
            "en las variables de entorno o en el archivo .env."
        )

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0,
        retries=0,
        api_key=api_key,
    )

    tools = [
        search_products_catalog,
        check_product_stock,
        add_product_to_cart,
        get_cart,
        remove_product_from_cart,
        checkout_cart,
    ]

    llm_with_tools = llm.bind_tools(tools)

    tool_map = {
        tool.name: tool
        for tool in tools
    }

    return llm, llm_with_tools, tool_map


# ============================================================
# GEMINI
# ============================================================

def invoke_with_retry(
    model: Any,
    messages: list,
) -> Any:
    """
    Ejecuta Gemini sin reintentos automáticos.

    Maneja 429 y 503 sin depender de google.api_core.
    """

    try:

        response = model.invoke(messages)

        record_gemini_usage(response)

        return response

    except Exception as exc:

        message = str(exc).lower()

        if (
            "429" in message
            or "resource exhausted" in message
            or "quota" in message
            or "rate limit" in message
            or "too many requests" in message
        ):

            raise GoogleAPIUnavailableError(
                "Se agotó la cuota disponible de Gemini."
            ) from exc

        if (
            "503" in message
            or "service unavailable" in message
            or "unavailable" in message
            or "high demand" in message
        ):

            raise GoogleAPIUnavailableError(
                "Gemini no está disponible temporalmente."
            ) from exc

        raise


# ============================================================
# HISTORIAL
# ============================================================

def trim_history(messages: list) -> None:
    """Mantiene limitado el historial."""

    if len(messages) <= MAX_HISTORY_MESSAGES:
        return

    system_messages = [
        message
        for message in messages
        if isinstance(message, SystemMessage)
    ]

    other_messages = [
        message
        for message in messages
        if not isinstance(message, SystemMessage)
    ]

    other_messages = other_messages[
        -MAX_HISTORY_MESSAGES:
    ]

    messages.clear()

    messages.extend(
        system_messages + other_messages
    )


def save_assistant_message(
    messages: list,
    content: str,
) -> None:
    """Guarda solamente la respuesta final."""

    messages.append(
        AIMessage(content=str(content))
    )

    trim_history(messages)


# ============================================================
# BÚSQUEDA LOCAL
# ============================================================

def try_local_tool(
    query: str,
) -> str | None:
    """Consulta stock localmente."""

    match = re.search(
        r"\bPROD-\d{3}\b",
        query,
        re.IGNORECASE,
    )

    if not match:
        return None

    product_id = match.group(0).upper()

    normalized = query.lower()

    stock_keywords = (
        "stock",
        "existencia",
        "disponible",
        "disponibilidad",
        "cuántos",
        "cuantos",
        "unidades",
    )

    if not any(
        keyword in normalized
        for keyword in stock_keywords
    ):
        return None

    try:

        result = check_product_stock.invoke(
            {
                "product_id": product_id,
            }
        )

        record_tool_call()

        return str(result)

    except Exception as exc:

        return (
            "No pude consultar el stock. "
            f"Detalle: {exc}"
        )


def try_local_product_search(
    query: str,
) -> str | None:
    """Busca productos localmente."""

    normalized = query.lower()

    search_keywords = (
        "busco",
        "buscar",
        "necesito",
        "quiero",
        "tienes",
        "tiene",
        "hay",
        "audífonos",
        "audifonos",
        "laptop",
        "monitor",
        "teclado",
        "silla",
        "mouse",
        "producto",
    )

    excluded_keywords = (
        "para desarrollo",
        "para trabajar",
        "para trabajar desde casa",
        "recomiéndame",
        "recomiendame",
        "qué me recomiendas",
        "que me recomiendas",
        "recomendar",
    )

    if not any(
        keyword in normalized
        for keyword in search_keywords
    ):
        return None

    if any(
        keyword in normalized
        for keyword in excluded_keywords
    ):
        return None

    try:

        result = search_products_catalog.invoke(
            {
                "query": query,
            }
        )

        record_tool_call()

        result_text = str(result)

        if (
            not result_text
            or "no se encontraron"
            in result_text.lower()
        ):
            return None

        return result_text

    except Exception as exc:

        print(
            "\n[Búsqueda local] "
            f"{type(exc).__name__}: {exc}"
        )

        return None


# ============================================================
# RECOMENDACIONES
# ============================================================

recommendation_engine = RecommendationEngine()


def build_local_recommendation(
    query: str,
) -> str | None:
    """Genera recomendaciones localmente."""

    try:

        result = (
            recommendation_engine
            .format_recommendations(query)
        )

        if not result:
            return None

        return str(result).strip()

    except Exception as exc:

        print(
            "\n[Recomendación local] "
            f"{type(exc).__name__}: {exc}"
        )

        return None


# ============================================================
# INTENCIONES
# ============================================================

def is_add_to_cart_intent(
    query: str,
) -> bool:

    normalized = query.lower()

    keywords = (
        "agrega",
        "agregar",
        "añade",
        "añadir",
        "mete",
        "meter",
        "ponlo",
        "ponla",
        "al carrito",
        "en el carrito",
    )

    return any(
        keyword in normalized
        for keyword in keywords
    )


def is_show_cart_intent(
    query: str,
) -> bool:

    normalized = query.lower()

    if "carrito" not in normalized:
        return False

    keywords = (
        "muestra",
        "mostrar",
        "ver",
        "enséñame",
        "enseñame",
        "qué tengo",
        "que tengo",
        "contenido",
        "mi carrito",
    )

    return any(
        keyword in normalized
        for keyword in keywords
    )


def is_remove_from_cart_intent(
    query: str,
) -> bool:

    normalized = query.lower()

    keywords = (
        "quitar del carrito",
        "quita del carrito",
        "eliminar del carrito",
        "elimina del carrito",
        "borrar del carrito",
        "borra del carrito",
    )

    return any(
        keyword in normalized
        for keyword in keywords
    )


def is_checkout_intent(
    query: str,
) -> bool:

    normalized = query.lower()

    keywords = (
        "checkout",
        "finalizar compra",
        "finaliza la compra",
        "completar compra",
        "completa la compra",
    )

    return any(
        keyword in normalized
        for keyword in keywords
    )


# ============================================================
# MEMORIA DE PRODUCTO
# ============================================================

def resolve_product_from_history(messages):
    """
    Recupera el producto de una recomendación anterior.

    Está pensada para resolver mensajes como:

        "agregala"
        "agrégala"
        "agregalo"
        "añádelo"
        "quiero ese"

    La estrategia principal es:

    1. Buscar un PROD-XXX directamente en el historial.
    2. Buscar el primer producto de una recomendación numerada.
    3. Resolver ese nombre directamente contra CatalogService.
    4. Buscar nombres de productos mencionados en el texto.
    5. Como último recurso, utilizar la búsqueda semántica.
    """

    if not messages:
        return None

    from app.catalog.catalog_service import CatalogService

    catalog_service = CatalogService()

    # Recorremos desde el mensaje más reciente hacia atrás.
    for message in reversed(messages):

        content = getattr(message, "content", None)

        if not content:
            continue

        # Algunos mensajes pueden tener contenido estructurado.
        if isinstance(content, list):
            parts = []

            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")

                    if text:
                        parts.append(str(text))
                else:
                    parts.append(str(item))

            content = "\n".join(parts)

        content = str(content).strip()

        if not content:
            continue

        # =========================================================
        # 1. Buscar directamente un ID de producto
        # =========================================================

        product_id_match = re.search(
            r"\bPROD-\d{3}\b",
            content,
            re.IGNORECASE,
        )

        if product_id_match:
            product_id = product_id_match.group(0).upper()

            product = catalog_service.get_product_by_id(
                product_id
            )

            if product is not None:
                print(
                    f"[Memoria] Producto encontrado por ID: {product_id}"
                )

                return product_id

        # =========================================================
        # 2. Buscar el primer producto de una recomendación
        # =========================================================

        first_product_match = re.search(
            r"(?m)^\s*1[\.\):\-]\s*(.+?)\s*$",
            content,
        )

        if first_product_match:

            product_name = first_product_match.group(1).strip()

            print(
                "[Memoria] Producto detectado en recomendación: "
                f"{product_name}"
            )

            # -----------------------------------------------------
            # 2A. Buscar directamente por nombre en el catálogo
            # -----------------------------------------------------

            try:
                product = catalog_service.get_product_by_name(
                    product_name
                )

            except Exception as exc:
                print(
                    "[Memoria] Error buscando producto por nombre: "
                    f"{exc}"
                )

                product = None

            if product is not None:

                product_id = product.get("id")

                if product_id:
                    print(
                        "[Memoria] Producto recuperado por nombre: "
                        f"{product_id}"
                    )

                    return product_id

        # =========================================================
        # 3. Buscar nombres de productos mencionados en el texto
        # =========================================================

        lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip()
        ]

        for line in lines:

            clean_line = re.sub(
                r"^[\s>*\-•\d\.\):]+",
                "",
                line,
            ).strip()

            if not clean_line:
                continue

            # Evitamos consultar frases genéricas demasiado largas.
            if len(clean_line) > 120:
                continue

            try:
                product = catalog_service.get_product_by_name(
                    clean_line
                )

            except Exception:
                product = None

            if product is not None:

                product_id = product.get("id")

                if product_id:
                    print(
                        "[Memoria] Producto recuperado desde "
                        f"la línea: {product_id}"
                    )

                    return product_id

        # =========================================================
        # 4. Último recurso: búsqueda semántica existente
        # =========================================================

        try:

            result = search_products_catalog.invoke(
                {
                    "query": content
                }
            )

            result_text = str(result)

            result_product_id = re.search(
                r"\bPROD-\d{3}\b",
                result_text,
                re.IGNORECASE,
            )

            if result_product_id:

                product_id = (
                    result_product_id.group(0).upper()
                )

                print(
                    "[Memoria] Producto recuperado mediante "
                    f"búsqueda semántica: {product_id}"
                )

                return product_id

        except Exception as exc:

            print(
                "[Memoria] Error en búsqueda semántica: "
                f"{exc}"
            )

    print(
        "[Memoria] No se pudo identificar un producto "
        "en el historial."
    )

    return None


# ============================================================
# FORMATEADORES DE RESULTADOS
# ============================================================

def format_cart_add_result(
    result: Any,
) -> str:
    """
    Convierte la respuesta de add_product_to_cart
    en una respuesta estable para el usuario.

    Soporta tanto dict como texto para evitar que
    un cambio interno de la herramienta rompa el agente.
    """

    if not isinstance(result, dict):
        return str(result)

    name = result.get(
        "name",
        result.get(
            "product_name",
            "Producto",
        ),
    )

    product_id = result.get(
        "product_id",
        "N/A",
    )

    quantity = result.get(
        "quantity",
        1,
    )

    price = result.get(
        "price",
        result.get(
            "unit_price",
            0,
        ),
    )

    subtotal = result.get(
        "subtotal",
        result.get(
            "item_subtotal",
            0,
        ),
    )

    cart_subtotal = result.get(
        "cart_subtotal",
        result.get(
            "total",
            subtotal,
        ),
    )

    return (
        "Producto agregado correctamente.\n"
        f"• Producto: {name}\n"
        f"• ID: {product_id}\n"
        f"• Cantidad: {quantity}\n"
        f"• Precio unitario: ${price}\n"
        f"• Subtotal: ${subtotal}\n"
        f"• Total del carrito: ${cart_subtotal}"
    )


def format_cart_result(
    result: Any,
) -> str:
    """
    Formatea el carrito para una respuesta legible.
    """

    if not isinstance(result, dict):
        return str(result)

    items = result.get(
        "items",
        [],
    )

    if not items:
        return "El carrito está vacío."

    lines = [
        "🛒 Carrito actual:"
    ]

    for item in items:

        name = item.get(
            "name",
            "Producto",
        )

        product_id = item.get(
            "product_id",
            "N/A",
        )

        quantity = item.get(
            "quantity",
            0,
        )

        subtotal = item.get(
            "subtotal",
            0,
        )

        lines.append(
            f"• {name} "
            f"(ID: {product_id}) "
            f"x{quantity} = ${subtotal}"
        )

    item_count = result.get(
        "item_count",
        0,
    )

    subtotal = result.get(
        "subtotal",
        0,
    )

    lines.append(
        f"Total de unidades: {item_count}"
    )

    lines.append(
        f"Subtotal: ${subtotal}"
    )

    return "\n".join(lines)


def format_checkout_result(
    result: Any,
) -> str:
    """
    Formatea el resultado del checkout.
    """

    if not isinstance(result, dict):
        return str(result)

    order_id = result.get(
        "id",
        result.get(
            "order_id",
            "N/A",
        ),
    )

    total = result.get(
        "total",
        0,
    )

    return (
        "✅ Compra completada correctamente.\n"
        f"• Orden: #{order_id}\n"
        f"• Total: ${total}\n"
        "• El carrito fue vaciado.\n"
        "• El stock fue actualizado."
    )


def format_remove_result(
    result: Any,
) -> str:
    """
    Formatea el resultado de eliminar un producto.
    """

    if not isinstance(result, dict):
        return str(result)

    if result.get("success") is False:
        return result.get(
            "message",
            "El producto no estaba en el carrito.",
        )

    return result.get(
        "message",
        "Producto eliminado correctamente.",
    )


# ============================================================
# FALLBACK
# ============================================================

def build_fallback(
    query: str,
) -> str:

    stock_result = try_local_tool(query)

    if stock_result is not None:
        return stock_result

    search_result = try_local_product_search(query)

    if search_result is not None:
        return search_result

    recommendation = build_local_recommendation(query)

    if recommendation is not None:
        return recommendation

    return (
        "Puedo ayudarte a buscar productos, consultar stock, "
        "gestionar el carrito y completar compras."
    )


# ============================================================
# PROCESS MESSAGE
# ============================================================

def process_message(
    query: str,
    llm,
    llm_with_tools,
    tool_map: dict[str, Any],
    messages: list,
    session_id: str = DEFAULT_SESSION_ID,
) -> str:

    query = query.strip()

    if not query:
        return "Por favor, escribe una consulta."

    # ========================================================
    # 1. MOSTRAR CARRITO
    # ========================================================

    if is_show_cart_intent(query):

        try:

            result = get_cart.invoke(
                {
                    "session_id": session_id,
                }
            )

            record_tool_call()

            messages.append(
                HumanMessage(content=query)
            )

            answer = format_cart_result(result)

            save_assistant_message(
                messages,
                answer,
            )

            return answer

        except Exception as exc:

            return (
                "No pude consultar el carrito. "
                f"Detalle: {exc}"
            )

    # ========================================================
    # 2. CHECKOUT
    # ========================================================

    if is_checkout_intent(query):

        try:

            result = checkout_cart.invoke(
                {
                    "session_id": session_id,
                }
            )

            record_tool_call()

            messages.append(
                HumanMessage(content=query)
            )

            answer = format_checkout_result(
                result
            )

            save_assistant_message(
                messages,
                answer,
            )

            return answer

        except Exception as exc:

            return (
                "No pude completar el checkout. "
                f"Detalle: {exc}"
            )

    # ========================================================
    # 3. QUITAR PRODUCTO
    # ========================================================

    if is_remove_from_cart_intent(query):

        product_match = re.search(
            r"\bPROD-\d{3}\b",
            query,
            re.IGNORECASE,
        )

        if product_match:

            product_id = (
                product_match
                .group(0)
                .upper()
            )

        else:

            product_id = resolve_product_from_history(
                messages
            )

        if product_id is None:

            return (
                "Indícame qué producto quieres quitar "
                "del carrito."
            )

        try:

            result = remove_product_from_cart.invoke(
                {
                    "session_id": session_id,
                    "product_id": product_id,
                }
            )

            record_tool_call()

            messages.append(
                HumanMessage(content=query)
            )

            answer = format_remove_result(
                result
            )

            save_assistant_message(
                messages,
                answer,
            )

            return answer

        except Exception as exc:

            return (
                "No pude quitar el producto del carrito. "
                f"Detalle: {exc}"
            )

    # ========================================================
    # 4. AGREGAR PRODUCTO
    # ========================================================

    if is_add_to_cart_intent(query):

        product_match = re.search(
            r"\bPROD-\d{3}\b",
            query,
            re.IGNORECASE,
        )

        if product_match:

            product_id = (
                product_match
                .group(0)
                .upper()
            )

        else:

            product_id = resolve_product_from_history(
                messages
            )

        if product_id is None:

            return (
                "Puedo agregar el producto al carrito, "
                "pero necesito saber cuál."
            )

        try:

            result = add_product_to_cart.invoke(
                {
                    "session_id": session_id,
                    "product_id": product_id,
                    "quantity": 1,
                }
            )

            record_tool_call()

            messages.append(
                HumanMessage(content=query)
            )

            answer = format_cart_add_result(
                result
            )

            save_assistant_message(
                messages,
                answer,
            )

            return answer

        except Exception as exc:

            return (
                "No pude agregar el producto al carrito. "
                f"Detalle: {exc}"
            )

    # ========================================================
    # 5. STOCK LOCAL
    # ========================================================

    local_tool_result = try_local_tool(query)

    if local_tool_result is not None:

        messages.append(
            HumanMessage(content=query)
        )

        save_assistant_message(
            messages,
            local_tool_result,
        )

        return local_tool_result

    # ========================================================
    # 6. BÚSQUEDA LOCAL
    # ========================================================

    local_search_result = try_local_product_search(query)

    if local_search_result is not None:

        messages.append(
            HumanMessage(content=query)
        )

        save_assistant_message(
            messages,
            local_search_result,
        )

        return local_search_result

    # ========================================================
    # 7. RECOMENDACIÓN LOCAL
    # ========================================================

    local_recommendation = build_local_recommendation(
        query
    )

    if local_recommendation is not None:

        messages.append(
            HumanMessage(content=query)
        )

        save_assistant_message(
            messages,
            local_recommendation,
        )

        return local_recommendation

    # ========================================================
    # 8. GEMINI
    # ========================================================

    messages.append(
        HumanMessage(content=query)
    )

    trim_history(messages)

    gemini_calls = 0

    try:

        if gemini_calls >= MAX_GEMINI_CALLS:

            raise GoogleAPIUnavailableError(
                "Se alcanzó el límite local de Gemini."
            )

        response = invoke_with_retry(
            llm_with_tools,
            messages,
        )

        gemini_calls += 1
        _metrics["gemini_calls"] += 1
        _metrics["gemini_rounds"] += 1

        # ----------------------------------------------------
        # Herramientas
        # ----------------------------------------------------

        if response.tool_calls:

            messages.append(response)

            for tool_call in response.tool_calls:

                tool_name = tool_call["name"]

                tool_args = dict(
                    tool_call.get(
                        "args",
                        {},
                    )
                )

                tool = tool_map.get(tool_name)

                if tool is None:

                    tool_result = (
                        f"Herramienta desconocida: "
                        f"{tool_name}"
                    )

                else:

                    cart_tools = {
                        "add_product_to_cart",
                        "get_cart",
                        "remove_product_from_cart",
                        "checkout_cart",
                    }

                    if tool_name in cart_tools:

                        tool_args = {
                            **tool_args,
                            "session_id": session_id,
                        }

                    try:

                        tool_result = tool.invoke(
                            tool_args
                        )

                        record_tool_call()

                    except Exception as exc:

                        tool_result = (
                            f"Error ejecutando "
                            f"{tool_name}: {exc}"
                        )

                messages.append(
                    ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call["id"],
                    )
                )

            # ------------------------------------------------
            # Segunda llamada Gemini
            # ------------------------------------------------

            if gemini_calls >= MAX_GEMINI_CALLS:

                raise GoogleAPIUnavailableError(
                    "Se alcanzó el límite local de Gemini."
                )

            final_response = invoke_with_retry(
                llm,
                messages,
            )

            gemini_calls += 1
            _metrics["gemini_calls"] += 1
            _metrics["gemini_rounds"] += 1

        else:

            final_response = response

        answer = str(
            final_response.content
        ).strip()

        if not answer:

            raise RuntimeError(
                "Gemini devolvió una respuesta vacía."
            )

        save_assistant_message(
            messages,
            answer,
        )

        return answer

    except GoogleAPIUnavailableError as exc:

        print(
            f"\n[Gemini] {exc}"
        )

        fallback = build_fallback(query)

        save_assistant_message(
            messages,
            fallback,
        )

        return fallback

    except Exception as exc:

        print(
            "\n[Gemini] "
            f"{type(exc).__name__}: {exc}"
        )

        fallback = build_fallback(query)

        save_assistant_message(
            messages,
            fallback,
        )

        return fallback


# ============================================================
# CLI
# ============================================================

def run_ecommerce_chat() -> None:

    print()
    print("=" * 60)
    print("              E-COMMERCE AI AGENT")
    print("=" * 60)
    print()

    print(
        "¡Hola! Soy tu asistente virtual experto de e-commerce."
    )

    print(
        "Puedo buscar productos, consultar stock, "
        "gestionar tu carrito y completar compras."
    )

    print()
    print("Escribe 'salir' para terminar.")
    print()

    reset_metrics()

    try:

        llm, llm_with_tools, tool_map = create_agent()

        print(
            "Agente creado correctamente."
        )

        print(
            "Herramientas:",
            list(tool_map.keys()),
        )

        print()

    except Exception as exc:

        print(
            "No se pudo crear el agente:"
        )

        print(exc)

        return

    messages = [
        SystemMessage(
            content=(
                "Eres un asistente virtual de e-commerce. "
                "Ayuda al usuario a buscar productos, consultar "
                "stock, gestionar su carrito y completar compras. "
                "Responde en español. "
                "Sé claro, directo y no inventes información."
            )
        )
    ]

    session_id = DEFAULT_SESSION_ID

    while True:

        try:

            query = input("Tú: ").strip()

        except (
            EOFError,
            KeyboardInterrupt,
        ):

            print()
            print("Sesión finalizada.")
            break

        if not query:
            continue

        if query.lower() == "salir":

            print()
            print("Sesión finalizada.")
            break

        reset_metrics()

        response = process_message(
            query=query,
            llm=llm,
            llm_with_tools=llm_with_tools,
            tool_map=tool_map,
            messages=messages,
            session_id=session_id,
        )

        print()
        print(
            "Agente:",
            response,
        )

        print_metrics()
        print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_ecommerce_chat()