from locust import HttpUser, between, task

from benchmark.test_data import (
    generate_large_order,
    generate_multiple_items_order,
    generate_single_item_order,
    get_test_products,
)


class RestOrderUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8001"

    def on_start(self):
        self.products = get_test_products()

    @task(10)
    def create_order_single_item(self):
        order_data = generate_single_item_order(self.products)

        with self.client.post(
            "/orders",
            json=order_data,
            catch_response=True,
            name="[REST] POST /orders (single item)",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure(f"Order creation failed: {data}")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")

    @task(5)
    def create_order_multiple_items(self):
        order_data = generate_multiple_items_order(self.products)

        with self.client.post(
            "/orders",
            json=order_data,
            catch_response=True,
            name="[REST] POST /orders (multiple items)",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure(f"Order creation failed: {data}")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")

    @task(2)
    def create_order_large(self):
        order_data = generate_large_order(self.products)

        with self.client.post(
            "/orders",
            json=order_data,
            catch_response=True,
            name="[REST] POST /orders (large order)",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure(f"Order creation failed: {data}")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
