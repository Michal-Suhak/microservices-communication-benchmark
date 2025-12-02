import sys

import pytest

sys.path.append("protocols/grpc/generated")

from protocols.grpc.generated import common_pb2


@pytest.fixture
def sample_order_items():
    return [
        common_pb2.OrderItem(
            product_id="prod_001",
            product_name="Laptop",
            quantity=1,
            unit_price=999.99,
        ),
        common_pb2.OrderItem(
            product_id="prod_002",
            product_name="Mouse",
            quantity=2,
            unit_price=29.99,
        ),
    ]


@pytest.fixture
def grpc_order_channel():
    return "localhost:8021"


@pytest.fixture
def grpc_payment_channel():
    return "localhost:8022"


@pytest.fixture
def grpc_notification_channel():
    return "localhost:8023"
