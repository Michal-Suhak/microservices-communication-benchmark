from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from common.models import OrderItem


@pytest.fixture
def order_service_client():
    from protocols.rest.order_service import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def payment_service_client():
    from protocols.rest.payment_service import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def notification_service_client():
    from protocols.rest.notification_service import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_http_response():
    def _create_response(json_data, status_code=200):
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.json.return_value = json_data
        return response

    return _create_response


@pytest.fixture
def mock_async_client(mock_http_response):
    def _create_client(post_response_data, status_code=200):
        client = AsyncMock(spec=httpx.AsyncClient)
        client.post.return_value = mock_http_response(post_response_data, status_code)
        return client

    return _create_client


@pytest.fixture
def sample_order_items():
    return [
        OrderItem(
            product_id="prod_001",
            product_name="Laptop",
            quantity=1,
            unit_price=999.99,
        ),
        OrderItem(
            product_id="prod_002",
            product_name="Mouse",
            quantity=2,
            unit_price=29.99,
        ),
    ]
