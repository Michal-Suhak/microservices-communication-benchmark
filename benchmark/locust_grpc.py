import sys
import time
from pathlib import Path

import grpc
from locust import User, between, task
from locust.exception import LocustError

# Add the protocols/grpc and generated directories to Python path
grpc_path = Path(__file__).parent.parent / "protocols" / "grpc"
generated_path = grpc_path / "generated"
sys.path.insert(0, str(grpc_path))
sys.path.insert(0, str(generated_path))

from generated import common_pb2, order_pb2, order_pb2_grpc  # noqa: E402

from benchmark.test_data import (  # noqa: E402
    generate_large_order,
    generate_multiple_items_order,
    generate_single_item_order,
    get_test_products,
)


class GrpcClient:
    """
    Custom gRPC client for Locust.
    """

    def __init__(self, host):
        self.host = host
        self._channel = None
        self._stub = None

    def connect(self):
        self._channel = grpc.insecure_channel(
            self.host,
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ("grpc.keepalive_time_ms", 10000),
                ("grpc.keepalive_timeout_ms", 5000),
            ],
        )
        self._stub = order_pb2_grpc.OrderServiceStub(self._channel)

    def close(self):
        if self._channel:
            self._channel.close()

    def create_order(self, customer_id, items, shipping_address):
        if not self._stub:
            self.connect()

        order_items = []
        for item in items:
            order_item = common_pb2.OrderItem(
                product_id=item["product_id"],
                product_name=item["product_name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
            )
            order_items.append(order_item)

        request = order_pb2.CreateOrderRequest(
            customer_id=customer_id,
            items=order_items,
            shipping_address=shipping_address,
        )

        try:
            response = self._stub.CreateOrder(request)
            return response
        except grpc.RpcError as e:
            raise LocustError(f"gRPC error: {e.code()} - {e.details()}") from e


class GrpcOrderUser(User):
    """
    Custom user for gRPC testing. We have to implement custom user which will handle gRPC client.
    """

    wait_time = between(1, 3)
    host = "localhost:8021"
    abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = GrpcClient(self.host)
        self.products = get_test_products()

    def on_start(self):
        self.client.connect()

    def on_stop(self):
        self.client.close()


class GrpcLocustUser(GrpcOrderUser):
    @task(10)
    def create_order_single_item(self):
        order_data = generate_single_item_order(self.products)

        start_time = time.time()
        try:
            response = self.client.create_order(
                customer_id=order_data["customer_id"],
                items=order_data["items"],
                shipping_address=order_data["shipping_address"],
            )

            total_time = int((time.time() - start_time) * 1000)

            if response.success:
                self.environment.events.request.fire(
                    request_type="grpc",
                    name="[gRPC] CreateOrder (single item)",
                    response_time=total_time,
                    response_length=response.ByteSize(),
                    exception=None,
                    context={},
                )
            else:
                self.environment.events.request.fire(
                    request_type="grpc",
                    name="[gRPC] CreateOrder (single item)",
                    response_time=total_time,
                    response_length=0,
                    exception=LocustError("Order creation failed"),
                    context={},
                )
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="grpc",
                name="[gRPC] CreateOrder (single item)",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={},
            )

    @task(5)
    def create_order_multiple_items(self):
        order_data = generate_multiple_items_order(self.products)

        start_time = time.time()
        try:
            response = self.client.create_order(
                customer_id=order_data["customer_id"],
                items=order_data["items"],
                shipping_address=order_data["shipping_address"],
            )

            total_time = int((time.time() - start_time) * 1000)

            if response.success:
                self.environment.events.request.fire(
                    request_type="grpc",
                    name="[gRPC] CreateOrder (multiple items)",
                    response_time=total_time,
                    response_length=response.ByteSize(),
                    exception=None,
                    context={},
                )
            else:
                self.environment.events.request.fire(
                    request_type="grpc",
                    name="[gRPC] CreateOrder (multiple items)",
                    response_time=total_time,
                    response_length=0,
                    exception=LocustError("Order creation failed"),
                    context={},
                )
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="grpc",
                name="[gRPC] CreateOrder (multiple items)",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={},
            )

    @task(2)
    def create_order_large(self):
        order_data = generate_large_order(self.products)

        start_time = time.time()
        try:
            response = self.client.create_order(
                customer_id=order_data["customer_id"],
                items=order_data["items"],
                shipping_address=order_data["shipping_address"],
            )

            total_time = int((time.time() - start_time) * 1000)

            if response.success:
                self.environment.events.request.fire(
                    request_type="grpc",
                    name="[gRPC] CreateOrder (large order)",
                    response_time=total_time,
                    response_length=response.ByteSize(),
                    exception=None,
                    context={},
                )
            else:
                self.environment.events.request.fire(
                    request_type="grpc",
                    name="[gRPC] CreateOrder (large order)",
                    response_time=total_time,
                    response_length=0,
                    exception=LocustError("Order creation failed"),
                    context={},
                )
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            self.environment.events.request.fire(
                request_type="grpc",
                name="[gRPC] CreateOrder (large order)",
                response_time=total_time,
                response_length=0,
                exception=e,
                context={},
            )
