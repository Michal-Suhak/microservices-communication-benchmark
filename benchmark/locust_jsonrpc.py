import json

from locust import HttpUser, between, task

from benchmark.test_data import (
    generate_large_order,
    generate_multiple_items_order,
    generate_single_item_order,
    get_test_products,
)


class JsonRpcOrderUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8011"

    def on_start(self):
        """Initialize test data."""
        self.products = get_test_products()
        self.request_id = 0

    def _get_next_request_id(self):
        """Get next JSON-RPC request ID."""
        self.request_id += 1
        return self.request_id

    def _make_jsonrpc_request(self, method, params, name=None):
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._get_next_request_id(),
        }

        with self.client.post(
            "/",
            json=request_data,
            catch_response=True,
            name=name or f"JSON-RPC: {method}",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "result" in data:
                        response.success()
                        return data["result"]
                    elif "error" in data:
                        response.failure(f"JSON-RPC error: {data['error']}")
                        return None
                    else:
                        response.failure(f"Invalid JSON-RPC response: {data}")
                        return None
                except json.JSONDecodeError as e:
                    response.failure(f"Invalid JSON: {e}")
                    return None
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
                return None

    @task(10)
    def create_order_single_item(self):
        params = generate_single_item_order(self.products)
        self._make_jsonrpc_request(
            "create_order", params, name="[JSON-RPC] create_order (single item)"
        )

    @task(5)
    def create_order_multiple_items(self):
        params = generate_multiple_items_order(self.products)
        self._make_jsonrpc_request(
            "create_order", params, name="[JSON-RPC] create_order (multiple items)"
        )

    @task(2)
    def create_order_large(self):
        params = generate_large_order(self.products)
        self._make_jsonrpc_request(
            "create_order", params, name="[JSON-RPC] create_order (large order)"
        )
