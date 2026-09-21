import re
from typing import Any

import chromadb

from app.catalog.catalog_service import CatalogService


class RecommendationEngine:
    """
    Motor local de recomendaciones.

    No utiliza Gemini.

    Combina:
    - búsqueda semántica mediante ChromaDB
    - coincidencias directas
    - intención detectada
    - tags
    - categoría
    - disponibilidad
    """

    MAX_DISTANCE = 1.50
    MAX_RESULTS = 5

    def __init__(self):
        self.catalog = CatalogService()

        self.chroma_client = chromadb.PersistentClient(
            path="./chroma_db"
        )

        self.collection = self.chroma_client.get_collection(
            name="ecommerce_products"
        )

        self.intent_keywords = {
            "trabajo_desde_casa": {
                "trabajar",
                "trabajo",
                "casa",
                "remoto",
                "oficina",
                "teletrabajo",
                "productividad",
            },
            "audio": {
                "audio",
                "audífonos",
                "auriculares",
                "ruido",
                "cancelación",
                "cancelacion",
                "inalámbricos",
                "inalambricos",
            },
            "teclado": {
                "teclado",
                "mecánico",
                "mecanico",
                "silencioso",
                "escribir",
                "escritura",
            },
            "pantalla": {
                "monitor",
                "pantalla",
                "ultrawide",
                "qhd",
                "144hz",
                "multitarea",
            },
            "ergonomia": {
                "silla",
                "ergonómica",
                "ergonomica",
                "lumbar",
                "comodidad",
                "postura",
            },
            "computacion": {
                "laptop",
                "portátil",
                "portatil",
                "computadora",
                "ordenador",
                "desarrollo",
                "programación",
                "programacion",
                "diseño",
            },
        }

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Normaliza texto para facilitar coincidencias.
        """

        text = text.lower()

        replacements = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ü": "u",
        }

        for source, target in replacements.items():
            text = text.replace(source, target)

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        return text

    def detect_intents(
        self,
        query: str
    ) -> set[str]:
        """
        Detecta intenciones locales mediante palabras clave.
        """

        normalized_query = self._normalize(query)

        detected = set()

        for intent, keywords in self.intent_keywords.items():

            for keyword in keywords:

                normalized_keyword = self._normalize(
                    keyword
                )

                if normalized_keyword in normalized_query:
                    detected.add(intent)
                    break

        return detected

    def search_candidates(
        self,
        query: str
    ) -> list[dict[str, Any]]:
        """
        Recupera candidatos desde ChromaDB y los convierte
        en productos estructurados.

        No genera texto para el usuario.
        """

        results = self.collection.query(
            query_texts=[query],
            n_results=self.MAX_RESULTS
        )

        ids = results["ids"][0]
        distances = results["distances"][0]

        candidates = []

        for product_id, distance in zip(
            ids,
            distances
        ):

            if distance > self.MAX_DISTANCE:
                continue

            product = self.catalog.get_product_by_id(
                product_id
            )

            if product is None:
                continue

            candidates.append(
                {
                    "product": product,
                    "semantic_distance": distance,
                }
            )

        return candidates

    def calculate_score(
        self,
        query: str,
        product: dict[str, Any],
        semantic_distance: float
    ) -> float:
        """
        Calcula la puntuación final del producto.
        """

        normalized_query = self._normalize(query)

        product_text = " ".join(
            [
                str(product.get("name", "")),
                str(product.get("category", "")),
                str(product.get("description", "")),
                " ".join(
                    str(tag)
                    for tag in product.get("tags", [])
                ),
            ]
        )

        normalized_product = self._normalize(
            product_text
        )

        score = 0.0

        # -------------------------------
        # 1. RELEVANCIA SEMÁNTICA
        # -------------------------------

        semantic_score = max(
            0.0,
            1.0 - (
                semantic_distance
                / self.MAX_DISTANCE
            )
        )

        score += semantic_score * 50

        # -------------------------------
        # 2. COINCIDENCIAS DIRECTAS
        # -------------------------------

        query_words = set(
            normalized_query.split()
        )

        product_words = set(
            normalized_product.split()
        )

        direct_matches = (
            query_words & product_words
        )

        score += min(
            len(direct_matches) * 4,
            16
        )

        # -------------------------------
        # 3. INTENCIONES
        # -------------------------------

        intents = self.detect_intents(
            query
        )

        category = self._normalize(
            str(product.get("category", ""))
        )

        tags = {
            self._normalize(str(tag))
            for tag in product.get("tags", [])
        }

        intent_matches = 0

        if "trabajo_desde_casa" in intents:

            if (
                "mobiliario" in category
                or "oficina" in tags
                or "ergonomia" in tags
                or "remoto" in tags
                or "multitarea" in tags
            ):
                intent_matches += 1

        if "audio" in intents:

            if (
                "audio" in category
                or "audio" in tags
            ):
                intent_matches += 1

        if "teclado" in intents:

            if (
                "perifericos" in category
                or "teclado" in tags
                or "silencioso" in tags
            ):
                intent_matches += 1

        if "pantalla" in intents:

            if (
                "monitores" in category
                or "pantalla" in tags
                or "multitarea" in tags
            ):
                intent_matches += 1

        if "ergonomia" in intents:

            if (
                "mobiliario" in category
                or "ergonomia" in tags
            ):
                intent_matches += 1

        if "computacion" in intents:

            if (
                "laptops" in category
                or "desarrollo" in tags
                or "diseño" in tags
            ):
                intent_matches += 1

        score += intent_matches * 20

        # -------------------------------
        # 4. STOCK
        # -------------------------------

        stock = product.get(
            "stock",
            0
        )

        if stock <= 0:
            score -= 30

        elif stock <= 3:
            score -= 5

        elif stock >= 10:
            score += 3

        return round(
            max(score, 0.0),
            2
        )

    def rank_products(
        self,
        query: str,
        products: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Ordena productos por puntuación.
        """

        ranked = []

        for item in products:

            product = item["product"]

            score = self.calculate_score(
                query=query,
                product=product,
                semantic_distance=item[
                    "semantic_distance"
                ]
            )

            ranked.append(
                {
                    "product": product,
                    "semantic_distance": item[
                        "semantic_distance"
                    ],
                    "score": score,
                }
            )

        ranked.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return ranked

    def recommend(
        self,
        query: str,
        max_results: int = 3
    ) -> list[dict[str, Any]]:
        """
        Ejecuta la recomendación completa:

        consulta
            ↓
        ChromaDB
            ↓
        candidatos
            ↓
        ranking
            ↓
        mejores productos
        """

        candidates = self.search_candidates(
            query
        )

        if not candidates:
            return []

        ranked = self.rank_products(
            query=query,
            products=candidates
        )

        return ranked[:max_results]

    def format_recommendations(
        self,
        query: str,
        max_results: int = 3
    ) -> str:
        """
        Convierte las recomendaciones estructuradas
        en una respuesta legible.
        """

        recommendations = self.recommend(
            query=query,
            max_results=max_results
        )

        if not recommendations:
            return (
                "No encontré productos suficientemente "
                "relevantes para tu consulta."
            )

        lines = [
            "Basándome en tu necesidad, estas son "
            "las opciones más relacionadas:",
            ""
        ]

        for index, item in enumerate(
            recommendations,
            start=1
        ):

            product = item["product"]

            lines.append(
                f"{index}. {product['name']}"
            )

            lines.append(
                f"   Categoría: {product['category']}"
            )

            lines.append(
                f"   Precio: ${product['price']}"
            )

            lines.append(
                f"   Stock: {product['stock']}"
            )

            lines.append(
                f"   Motivo: relevancia semántica "
                f"+ coincidencia con tu necesidad."
            )

            lines.append("")

        return "\n".join(lines)