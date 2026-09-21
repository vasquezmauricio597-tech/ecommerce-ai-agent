import app.agent.agent as agent_module


def setup_function():
    """
    Reinicia las métricas antes de cada test.
    """
    agent_module.reset_metrics()


def create_test_agent():
    """
    Crea los componentes utilizados por el agente real.
    """

    llm = agent_module.create_agent()

    tool_map = {
        tool.name: tool
        for tool in [
            agent_module.search_products_catalog,
            agent_module.check_product_stock,
            agent_module.add_product_to_cart,
            agent_module.get_cart,
            agent_module.remove_product_from_cart,
            agent_module.checkout_cart,
        ]
    }

    return llm, tool_map


def test_local_recommendation_does_not_need_gemini():
    """
    Una consulta que puede resolverse localmente
    no debería llamar a Gemini.
    """

    llm, tool_map = create_test_agent()

    messages = []

    result = agent_module.process_message(
        "Quiero una laptop para desarrollo",
        llm,
        llm,
        tool_map,
        messages,
    )

    assert result is not None
    assert "Laptop ProX 15" in result
    assert agent_module._metrics["gemini_calls"] == 0


def test_show_empty_cart_does_not_need_gemini():
    """
    Consultar el carrito es una operación determinística.
    """

    llm, tool_map = create_test_agent()

    messages = []

    result = agent_module.process_message(
        "muéstrame mi carrito",
        llm,
        llm,
        tool_map,
        messages,
    )

    assert result is not None
    assert "carrito" in result.lower()
    assert agent_module._metrics["gemini_calls"] == 0


def test_checkout_empty_cart_does_not_need_gemini():
    """
    Checkout de un carrito vacío debe resolverse localmente
    y no consumir una llamada a Gemini.
    """

    llm, tool_map = create_test_agent()

    messages = []

    result = agent_module.process_message(
        "checkout",
        llm,
        llm,
        tool_map,
        messages,
    )

    assert result is not None
    assert agent_module._metrics["gemini_calls"] == 0


def test_add_to_cart_from_previous_recommendation():
    """
    Verifica que el agente pueda agregar al carrito un producto
    mencionado en una recomendación anterior.
    """

    # ---------------------------------------------------------
    # 1. Crear agente de prueba
    # ---------------------------------------------------------

    llm, tool_map = create_test_agent()

    messages = []

    # ---------------------------------------------------------
    # 2. Generar recomendación
    # ---------------------------------------------------------

    recommendation = agent_module.process_message(
        "Quiero una laptop para desarrollo",
        llm,
        llm,
        tool_map,
        messages,
    )

    print("\n")
    print("=" * 70)
    print("DEBUG: RECOMENDACIÓN GENERADA")
    print("=" * 70)
    print(recommendation)
    print("=" * 70)

    # La recomendación debe mencionar el producto esperado.
    assert "Laptop ProX 15" in recommendation

    # ---------------------------------------------------------
    # 3. Guardar recomendación en memoria
    # ---------------------------------------------------------

    agent_module.save_assistant_message(
        messages,
        recommendation,
    )

    # ---------------------------------------------------------
    # 4. Inspeccionar memoria
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("DEBUG: MESSAGES DESPUÉS DE GUARDAR")
    print("=" * 70)

    print(f"Cantidad de mensajes: {len(messages)}")

    for index, message in enumerate(messages):
        print()
        print(f"--- MENSAJE {index} ---")
        print(f"Tipo: {type(message)}")
        print(
            "Contenido:",
            getattr(message, "content", None),
        )

    print("=" * 70)

    # ---------------------------------------------------------
    # 5. Intentar agregar usando la memoria
    # ---------------------------------------------------------

    result = agent_module.process_message(
        "agregala",
        llm,
        llm,
        tool_map,
        messages,
    )

    # ---------------------------------------------------------
    # 6. Mostrar resultado
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("DEBUG: RESULTADO DE 'AGREGALA'")
    print("=" * 70)
    print(result)
    print("=" * 70)

    # ---------------------------------------------------------
    # 7. Validación
    # ---------------------------------------------------------

    assert "Producto agregado correctamente" in result