import json
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer

from common.models import OrderItem


@pytest_asyncio.fixture
async def order_service_client():
    from protocols.jsonrpc.order_service import create_app

    app = create_app()
    async with TestClient(TestServer(app)) as client:
        yield client


@pytest_asyncio.fixture
async def payment_service_client():
    from protocols.jsonrpc.payment_service import create_app

    app = create_app()
    async with TestClient(TestServer(app)) as client:
        yield client


@pytest_asyncio.fixture
async def notification_service_client():
    from protocols.jsonrpc.notification_service import create_app

    app = create_app()
    async with TestClient(TestServer(app)) as client:
        yield client


@pytest.fixture
def jsonrpc_request():
    def _create_request(method: str, params: dict, request_id: int = 1):
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id,
        }

    return _create_request


@pytest.fixture
def mock_aiohttp_response():
    def _create_response(json_data, status=200):
        response = AsyncMock()
        response.status = status
        response.text = AsyncMock(return_value=json.dumps(json_data))
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=None)
        return response

    return _create_response


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
