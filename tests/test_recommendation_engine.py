from app.recommendation.recommendation_engine import (
    RecommendationEngine
)


def test_detects_home_office_intent():
    engine = RecommendationEngine()

    intents = engine.detect_intents(
        "¿Qué me recomiendas para trabajar desde casa?"
    )

    assert "trabajo_desde_casa" in intents


def test_detects_keyboard_intent():
    engine = RecommendationEngine()

    intents = engine.detect_intents(
        "busco un teclado mecánico silencioso"
    )

    assert "teclado" in intents


def test_recommends_products():
    engine = RecommendationEngine()

    recommendations = engine.recommend(
        "teclado mecánico silencioso"
    )

    assert len(recommendations) > 0

    first_product = recommendations[0]["product"]

    assert first_product["id"] == "PROD-005"


def test_recommendation_contains_score():
    engine = RecommendationEngine()

    recommendations = engine.recommend(
        "audífonos inalámbricos con cancelación de ruido"
    )

    assert len(recommendations) > 0

    first_result = recommendations[0]

    assert "score" in first_result
    assert "semantic_distance" in first_result
    assert "product" in first_result


def test_unknown_query_returns_no_relevant_products():
    engine = RecommendationEngine()

    recommendations = engine.recommend(
        "refrigerador industrial para restaurante"
    )

    assert recommendations == []


def test_format_recommendations_returns_text():
    engine = RecommendationEngine()

    response = engine.format_recommendations(
        "teclado mecánico silencioso"
    )

    assert isinstance(response, str)
    assert "Teclado Mecánico Silent" in response