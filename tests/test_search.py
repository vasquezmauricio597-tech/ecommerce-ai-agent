import chromadb


def run_semantic_search(query: str):
    """
    Ejecuta una búsqueda semántica manual sobre ChromaDB
    y muestra los resultados en consola.
    """

    client = chromadb.PersistentClient(
        path="./chroma_db"
    )

    collection = client.get_collection(
        name="ecommerce_products"
    )

    results = collection.query(
        query_texts=[query],
        n_results=2
    )

    print(
        f"\n🔍 Búsqueda: '{query}'"
    )

    print(
        "=" * 50
    )

    for i, (
        prod_id,
        doc,
        metadata,
        distance
    ) in enumerate(
        zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )
    ):

        print(
            f"Resultado {i + 1}:"
        )

        print(
            f"  • ID: {prod_id}"
        )

        print(
            f"  • Producto: {metadata['name']}"
        )

        print(
            f"  • Categoría: {metadata['category']}"
        )

        print(
            f"  • Precio: ${metadata['price']}"
        )

        print(
            f"  • Distancia: "
            f"{distance:.4f} "
            f"(menor es mejor)"
        )

        print(
            f"  • Doc indexado: {doc}"
        )

        print(
            "-" * 50
        )


if __name__ == "__main__":

    run_semantic_search(
        "necesito algo para trabajar concentrado sin ruido"
    )

    run_semantic_search(
        "computadora potente para programar y desarrollo"
    )