from app.catalog.catalog_service import CatalogService


def test_catalog_loads_products():
    catalog = CatalogService()

    assert catalog.get_product_count() == 5


def test_get_product_by_id():
    catalog = CatalogService()

    product = catalog.get_product_by_id(
        "PROD-003"
    )

    assert product is not None
    assert product["name"] == "Audífonos NoiseCancel GX"
    assert product["stock"] == 25
    assert product["price"] == 220.0


def test_get_product_by_id_is_case_insensitive():
    catalog = CatalogService()

    product = catalog.get_product_by_id(
        "prod-003"
    )

    assert product is not None
    assert product["id"] == "PROD-003"


def test_unknown_product_returns_none():
    catalog = CatalogService()

    product = catalog.get_product_by_id(
        "PROD-999"
    )

    assert product is None


def test_get_all_products():
    catalog = CatalogService()

    products = catalog.get_all_products()

    assert len(products) == 5
    assert all(
        "id" in product
        for product in products
    )