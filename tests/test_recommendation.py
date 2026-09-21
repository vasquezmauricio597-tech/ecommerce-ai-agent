from app.catalog.catalog_service import CatalogService
from app.recommendation.recommendation_engine import RecommendationEngine


catalog = CatalogService()
engine = RecommendationEngine()


distances = {
    "PROD-001": 1.4007,
    "PROD-002": 1.3600,
    "PROD-003": 1.4238,
    "PROD-004": 1.3998,
    "PROD-005": 1.2996,
}


products = []

for product in catalog.get_all_products():

    products.append(
        {
            "product": product,
            "semantic_distance": distances[product["id"]],
        }
    )


ranked = engine.rank_products(
    "¿Qué me recomiendas para trabajar desde casa?",
    products,
)


print()
print("=== RANKING LOCAL ===")
print()

for index, item in enumerate(ranked, start=1):

    product = item["product"]

    print(
        f"{index}. {product['name']} "
        f"| Score: {item['score']} "
        f"| Distancia: {item['semantic_distance']}"
    )