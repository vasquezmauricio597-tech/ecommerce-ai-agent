import json
import os
import chromadb

def setup_vector_db():
    file_path = os.path.join("data", "products.json")
    
    if not os.path.exists(file_path):
        print("❌ Error: El archivo products.json no existe.")
        return

    # 1. Cargar el catálogo limpio
    with open(file_path, "r", encoding="utf-8-sig") as f:
        products = json.load(f)
        
    print(f"📦 Cargados {len(products)} productos desde el JSON.")

    # 2. Inicializar ChromaDB en modo persistente (guarda los datos localmente en una carpeta)
    client = chromadb.PersistentClient(path="./chroma_db")
    
    collection_name = "ecommerce_products"
    
    # Limpiamos la colección si ya existe para evitar duplicados al re-ejecutar
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass
        
    collection = client.create_collection(name=collection_name)

    # 3. Preparar los datos para indexación semántica
    ids = []
    documents = []
    metadatas = []

    for prod in products:
        ids.append(prod["id"])
        
        # Combinamos la información clave en un texto enriquecido para que el embedding sea ultra preciso
        doc_text = f"Producto: {prod['name']}. Categoría: {prod['category']}. Descripción: {prod['description']}. Tags: {', '.join(prod['tags'])}."
        documents.append(doc_text)
        
        # Metadatas estructuradas para filtros posteriores (precio, stock, etc.)
        metadatas.append({
            "name": prod["name"],
            "category": prod["category"],
            "price": float(prod["price"]),
            "stock": int(prod["stock"])
        })

    # 4. Insertar en ChromaDB (genera los embeddings por defecto localmente)
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print(f"✅ ¡Base de datos ChromaDB inicializada con éxito! Se indexaron {len(ids)} productos.")

if __name__ == "__main__":
    setup_vector_db()