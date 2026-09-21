import json
import os

def load_products():
    file_path = os.path.join("data", "products.json")
    
    if not os.path.exists(file_path):
        print("❌ Error: El archivo data/products.json no existe.")
        return
    
    with open(file_path, "r", encoding="utf-8") as f:
        products = json.load(f)
    
    print(f"✅ Se cargaron exitosamente {len(products)} productos.\n")
    
    for prod in products:
        print(f"• [{prod['id']}] {prod['name']} - ${prod['price']} ({prod['category']})")

if __name__ == "__main__":
    load_products()