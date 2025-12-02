import random


def get_test_products():
    """Get consistent product catalog for testing."""
    return [
        {
            "id": f"prod_{i}",
            "name": f"Product {i}",
            "price": round(random.uniform(10, 500), 2),
        }
        for i in range(1, 101)
    ]


def generate_single_item_order(products):
    """Generate order with a single item."""
    product = random.choice(products)
    return {
        "customer_id": f"cust_{random.randint(1000, 9999)}",
        "items": [
            {
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": random.randint(1, 5),
                "unit_price": product["price"],
            }
        ],
        "shipping_address": f"{random.randint(100, 999)} Main St, City, Country",
    }


def generate_multiple_items_order(products, num_items=None):
    """Generate order with multiple items."""
    if num_items is None:
        num_items = random.randint(2, 5)

    items = []
    for _ in range(num_items):
        product = random.choice(products)
        items.append(
            {
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": random.randint(1, 3),
                "unit_price": product["price"],
            }
        )

    return {
        "customer_id": f"cust_{random.randint(1000, 9999)}",
        "items": items,
        "shipping_address": f"{random.randint(100, 999)} Main St, City, Country",
    }


def generate_large_order(products):
    """Generate order with many items (stress test)."""
    return generate_multiple_items_order(products, num_items=random.randint(10, 20))
