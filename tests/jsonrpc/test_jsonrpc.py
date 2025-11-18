import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest


class TestOrderService:
    """Tests for JSON-RPC Order Service."""

    @pytest.mark.asyncio
    async def test_health_check(self, order_service_client):
        response = await order_service_client.get("/health")

        assert response.status == 200
        data = await response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "order-jsonrpc"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, order_service_client):
        response = await order_service_client.get("/metrics")

        assert response.status == 200
        text = await response.text()
        assert "request_total" in text
        assert "request_latency_seconds" in text

    @pytest.mark.asyncio
    async def test_create_order_success(
        self, order_service_client, jsonrpc_request, sample_order_items
    ):
        payment_response = {
            "jsonrpc": "2.0",
            "result": {
                "payment": {
                    "payment_id": "pay_12345",
                    "order_id": "ord_12345",
                    "amount": 1059.97,
                    "currency": "USD",
                    "payment_method": "credit_card",
                    "status": "completed",
                    "transaction_id": "txn_abc123",
                    "created_at": datetime.utcnow().isoformat(),
                    "processed_at": datetime.utcnow().isoformat(),
                    "error_message": None,
                },
                "notification": {
                    "notification_id": "notif_12345",
                    "order_id": "ord_12345",
                    "payment_id": "pay_12345",
                    "recipient": "customer@example.com",
                    "notification_type": "email",
                    "message": "Order confirmed",
                    "status": "sent",
                    "created_at": datetime.utcnow().isoformat(),
                    "sent_at": datetime.utcnow().isoformat(),
                    "delivered_at": None,
                    "error_message": None,
                },
                "processing_time_ms": 15.5,
            },
            "id": 1,
        }

        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=json.dumps(payment_response))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        import protocols.jsonrpc.order_service as order_module

        with patch.object(order_module, "session") as mock_session:
            mock_session.post.return_value = mock_response

            request_data = jsonrpc_request(
                "create_order",
                {
                    "customer_id": "cust_12345",
                    "items": [item.model_dump() for item in sample_order_items],
                    "shipping_address": "123 Main St, City, Country",
                },
            )

            response = await order_service_client.post(
                "/",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

        assert response.status == 200
        data = await response.json()
        assert "result" in data
        assert "order" in data["result"]
        assert data["result"]["order"]["customer_id"] == "cust_12345"
        assert len(data["result"]["order"]["items"]) == 2
        assert data["result"]["order"]["total_amount"] == 1059.97

    @pytest.mark.asyncio
    async def test_create_order_payment_failure(
        self, order_service_client, jsonrpc_request, sample_order_items
    ):
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": "Payment failed"},
            "id": 1,
        }

        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=json.dumps(error_response))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        import protocols.jsonrpc.order_service as order_module

        with patch.object(order_module, "session") as mock_session:
            mock_session.post.return_value = mock_response

            request_data = jsonrpc_request(
                "create_order",
                {
                    "customer_id": "cust_12345",
                    "items": [item.model_dump() for item in sample_order_items],
                    "shipping_address": "123 Main St, City, Country",
                },
            )

            response = await order_service_client.post(
                "/",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

        assert response.status == 200
        data = await response.json()
        assert "error" in data
        assert data["error"]["message"] == "Payment failed"

    @pytest.mark.asyncio
    async def test_invalid_method(self, order_service_client, jsonrpc_request):
        request_data = jsonrpc_request("invalid_method", {})

        response = await order_service_client.post(
            "/",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        assert response.status == 200
        data = await response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found


class TestPaymentService:
    """Tests for JSON-RPC Payment Service."""

    @pytest.mark.asyncio
    async def test_health_check(self, payment_service_client):
        response = await payment_service_client.get("/health")

        assert response.status == 200
        data = await response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "payment-jsonrpc"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, payment_service_client):
        response = await payment_service_client.get("/metrics")

        assert response.status == 200
        text = await response.text()
        assert "request_total" in text

    @pytest.mark.asyncio
    async def test_process_payment_success(
        self, payment_service_client, jsonrpc_request
    ):
        notification_response = {
            "jsonrpc": "2.0",
            "result": {
                "notification": {
                    "notification_id": "notif_12345",
                    "order_id": "ord_12345",
                    "payment_id": "pay_12345",
                    "recipient": "customer@example.com",
                    "notification_type": "email",
                    "message": "Order confirmed",
                    "status": "sent",
                    "created_at": datetime.utcnow().isoformat(),
                    "sent_at": datetime.utcnow().isoformat(),
                    "delivered_at": None,
                    "error_message": None,
                },
                "processing_time_ms": 5.0,
            },
            "id": 1,
        }

        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=json.dumps(notification_response))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        import protocols.jsonrpc.payment_service as payment_module

        with patch.object(payment_module, "session") as mock_session:
            mock_session.post.return_value = mock_response

            request_data = jsonrpc_request(
                "process_payment",
                {
                    "order_id": "ord_12345",
                    "amount": 999.99,
                    "currency": "USD",
                    "payment_method": "credit_card",
                },
            )

            response = await payment_service_client.post(
                "/",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

        assert response.status == 200
        data = await response.json()
        assert "result" in data
        assert "payment" in data["result"]
        assert data["result"]["payment"]["order_id"] == "ord_12345"
        assert data["result"]["payment"]["amount"] == 999.99
        assert data["result"]["payment"]["status"] == "completed"
        assert data["result"]["payment"]["transaction_id"] is not None

    @pytest.mark.asyncio
    async def test_process_payment_notification_failure(
        self, payment_service_client, jsonrpc_request
    ):
        error_response = {
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": "Notification failed"},
            "id": 1,
        }

        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=json.dumps(error_response))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        import protocols.jsonrpc.payment_service as payment_module

        with patch.object(payment_module, "session") as mock_session:
            mock_session.post.return_value = mock_response

            request_data = jsonrpc_request(
                "process_payment",
                {
                    "order_id": "ord_12345",
                    "amount": 999.99,
                    "currency": "USD",
                    "payment_method": "credit_card",
                },
            )

            response = await payment_service_client.post(
                "/",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

        assert response.status == 200
        data = await response.json()
        assert "result" in data
        assert data["result"]["payment"]["status"] == "completed"
        assert data["result"]["notification"] is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payment_method",
        [
            "credit_card",
            "debit_card",
            "bank_transfer",
            "paypal",
        ],
    )
    async def test_process_payment_different_methods(
        self, payment_service_client, jsonrpc_request, payment_method
    ):
        notification_response = {
            "jsonrpc": "2.0",
            "result": {
                "notification": None,
                "processing_time_ms": 5.0,
            },
            "id": 1,
        }

        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=json.dumps(notification_response))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        import protocols.jsonrpc.payment_service as payment_module

        with patch.object(payment_module, "session") as mock_session:
            mock_session.post.return_value = mock_response

            request_data = jsonrpc_request(
                "process_payment",
                {
                    "order_id": "ord_12345",
                    "amount": 100.0,
                    "currency": "USD",
                    "payment_method": payment_method,
                },
            )

            response = await payment_service_client.post(
                "/",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

        assert response.status == 200
        data = await response.json()
        assert data["result"]["payment"]["payment_method"] == payment_method


class TestNotificationService:
    """Tests for JSON-RPC Notification Service."""

    @pytest.mark.asyncio
    async def test_health_check(self, notification_service_client):
        response = await notification_service_client.get("/health")

        assert response.status == 200
        data = await response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "notification-jsonrpc"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, notification_service_client):
        response = await notification_service_client.get("/metrics")

        assert response.status == 200
        text = await response.text()
        assert "request_total" in text

    @pytest.mark.asyncio
    async def test_send_notification_success(
        self, notification_service_client, jsonrpc_request
    ):
        request_data = jsonrpc_request(
            "send_notification",
            {
                "order_id": "ord_12345",
                "payment_id": "pay_12345",
                "recipient": "customer@example.com",
                "notification_type": "email",
            },
        )

        response = await notification_service_client.post(
            "/",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        assert response.status == 200
        data = await response.json()
        assert "result" in data
        assert "notification" in data["result"]
        assert data["result"]["notification"]["order_id"] == "ord_12345"
        assert data["result"]["notification"]["payment_id"] == "pay_12345"
        assert data["result"]["notification"]["recipient"] == "customer@example.com"
        assert data["result"]["notification"]["status"] == "sent"
        assert "Your order" in data["result"]["notification"]["message"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "notification_type",
        [
            "email",
            "sms",
            "push",
        ],
    )
    async def test_send_notification_different_types(
        self, notification_service_client, jsonrpc_request, notification_type
    ):
        request_data = jsonrpc_request(
            "send_notification",
            {
                "order_id": "ord_12345",
                "payment_id": "pay_12345",
                "recipient": "customer@example.com",
                "notification_type": notification_type,
            },
        )

        response = await notification_service_client.post(
            "/",
            json=request_data,
            headers={"Content-Type": "application/json"},
        )

        assert response.status == 200
        data = await response.json()
        assert data["result"]["notification"]["notification_type"] == notification_type


class TestIntegration:
    """Integration tests for JSON-RPC services (requires all services running)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_order_flow(self):
        """Test complete order → payment → notification flow.

        This test requires all services to be running:
        - Order Service on port 8011
        - Payment Service on port 8012
        - Notification Service on port 8013
        """
        import aiohttp

        request_data = {
            "jsonrpc": "2.0",
            "method": "create_order",
            "params": {
                "customer_id": "cust_integration_test",
                "items": [
                    {
                        "product_id": "prod_001",
                        "product_name": "Integration Test Product",
                        "quantity": 1,
                        "unit_price": 99.99,
                    }
                ],
                "shipping_address": "456 Test Ave, Test City",
            },
            "id": 1,
        }

        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session,
            session.post(
                "http://localhost:8011/",
                json=request_data,
                headers={"Content-Type": "application/json"},
            ) as response,
        ):
            assert response.status == 200
            data = await response.json()

        assert "result" in data
        assert data["result"]["order"]["customer_id"] == "cust_integration_test"
        assert data["result"]["payment"]["status"] == "completed"
        assert data["result"]["notification"]["status"] == "sent"
        assert data["result"]["processing_time_ms"] > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "service_url,service_name",
        [
            ("http://localhost:8011", "order-jsonrpc"),
            ("http://localhost:8012", "payment-jsonrpc"),
            ("http://localhost:8013", "notification-jsonrpc"),
        ],
    )
    async def test_service_health_checks(self, service_url, service_name):
        """Test health checks for all services."""
        import aiohttp

        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session,
            session.get(f"{service_url}/health") as response,
        ):
            assert response.status == 200
            data = await response.json()
            assert data["service"] == service_name
