from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestOrderService:
    """Tests for REST Order Service."""

    def test_health_check(self, order_service_client):
        response = order_service_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "order-rest"

    def test_metrics_endpoint(self, order_service_client):
        response = order_service_client.get("/metrics")

        assert response.status_code == 200
        assert "request_total" in response.text
        assert "request_latency_seconds" in response.text

    def test_create_order_success(self, order_service_client, sample_order_items):
        payment_response = {
            "success": True,
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
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = payment_response

        with patch.object(
            order_service_client.app.state, "http_client", new_callable=AsyncMock
        ) as mock_client:
            mock_client.post.return_value = mock_response

            order_data = {
                "customer_id": "cust_12345",
                "items": [item.model_dump() for item in sample_order_items],
                "shipping_address": "123 Main St, City, Country",
            }

            response = order_service_client.post("/orders", json=order_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "order" in data
        assert data["order"]["customer_id"] == "cust_12345"
        assert len(data["order"]["items"]) == 2
        assert data["order"]["total_amount"] == 1059.97

    def test_create_order_payment_failure(
        self, order_service_client, sample_order_items
    ):
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(
            order_service_client.app.state, "http_client", new_callable=AsyncMock
        ) as mock_client:
            mock_client.post.return_value = mock_response

            order_data = {
                "customer_id": "cust_12345",
                "items": [item.model_dump() for item in sample_order_items],
                "shipping_address": "123 Main St, City, Country",
            }

            response = order_service_client.post("/orders", json=order_data)

        assert response.status_code == 500
        assert "Payment processing failed" in response.json()["detail"]

    def test_create_order_connection_error(
        self, order_service_client, sample_order_items
    ):
        with patch.object(
            order_service_client.app.state, "http_client", new_callable=AsyncMock
        ) as mock_client:
            mock_client.post.side_effect = httpx.RequestError("Connection failed")

            order_data = {
                "customer_id": "cust_12345",
                "items": [item.model_dump() for item in sample_order_items],
                "shipping_address": "123 Main St, City, Country",
            }

            response = order_service_client.post("/orders", json=order_data)

        assert response.status_code == 503
        assert "Service unavailable" in response.json()["detail"]

    @pytest.mark.parametrize(
        "invalid_data,expected_error",
        [
            (
                {"customer_id": "", "items": [], "shipping_address": "123 Main St"},
                "items",
            ),
            (
                {
                    "customer_id": "cust_123",
                    "items": [
                        {
                            "product_id": "prod_001",
                            "product_name": "Test",
                            "quantity": 0,
                            "unit_price": 10.0,
                        }
                    ],
                    "shipping_address": "123 Main St",
                },
                "quantity",
            ),
            (
                {
                    "customer_id": "cust_123",
                    "items": [
                        {
                            "product_id": "prod_001",
                            "product_name": "Test",
                            "quantity": 1,
                            "unit_price": -10.0,
                        }
                    ],
                    "shipping_address": "123 Main St",
                },
                "unit_price",
            ),
        ],
        ids=["empty_items", "zero_quantity", "negative_price"],
    )
    def test_create_order_validation_errors(
        self, order_service_client, invalid_data, expected_error
    ):
        response = order_service_client.post("/orders", json=invalid_data)

        assert response.status_code == 422
        assert expected_error in str(response.json())


class TestPaymentService:
    """Tests for REST Payment Service."""

    def test_health_check(self, payment_service_client):
        response = payment_service_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "payment-rest"

    def test_metrics_endpoint(self, payment_service_client):
        response = payment_service_client.get("/metrics")

        assert response.status_code == 200
        assert "request_total" in response.text

    def test_process_payment_success(self, payment_service_client):
        notification_response = {
            "success": True,
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
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = notification_response

        with patch.object(
            payment_service_client.app.state, "http_client", new_callable=AsyncMock
        ) as mock_client:
            mock_client.post.return_value = mock_response

            payment_data = {
                "order_id": "ord_12345",
                "amount": 999.99,
                "currency": "USD",
                "payment_method": "credit_card",
            }

            response = payment_service_client.post("/payments", json=payment_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "payment" in data
        assert data["payment"]["order_id"] == "ord_12345"
        assert data["payment"]["amount"] == 999.99
        assert data["payment"]["status"] == "completed"
        assert data["payment"]["transaction_id"] is not None

    def test_process_payment_notification_failure(self, payment_service_client):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {}

        with patch.object(
            payment_service_client.app.state, "http_client", new_callable=AsyncMock
        ) as mock_client:
            mock_client.post.return_value = mock_response

            payment_data = {
                "order_id": "ord_12345",
                "amount": 999.99,
                "currency": "USD",
                "payment_method": "credit_card",
            }

            response = payment_service_client.post("/payments", json=payment_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["notification"] is None

    @pytest.mark.parametrize(
        "payment_method",
        [
            "credit_card",
            "debit_card",
            "bank_transfer",
            "paypal",
        ],
    )
    def test_process_payment_different_methods(
        self, payment_service_client, payment_method
    ):
        notification_response = {
            "success": True,
            "notification": None,
            "processing_time_ms": 5.0,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = notification_response

        with patch.object(
            payment_service_client.app.state, "http_client", new_callable=AsyncMock
        ) as mock_client:
            mock_client.post.return_value = mock_response

            payment_data = {
                "order_id": "ord_12345",
                "amount": 100.0,
                "currency": "USD",
                "payment_method": payment_method,
            }

            response = payment_service_client.post("/payments", json=payment_data)

        assert response.status_code == 200
        assert response.json()["payment"]["payment_method"] == payment_method

    @pytest.mark.parametrize(
        "invalid_data,expected_error",
        [
            (
                {
                    "order_id": "ord_123",
                    "amount": -100.0,
                    "currency": "USD",
                    "payment_method": "credit_card",
                },
                "amount",
            ),
            (
                {
                    "order_id": "ord_123",
                    "amount": 100.0,
                    "currency": "USD",
                    "payment_method": "invalid_method",
                },
                "payment_method",
            ),
        ],
        ids=["negative_amount", "invalid_method"],
    )
    def test_process_payment_validation_errors(
        self, payment_service_client, invalid_data, expected_error
    ):
        response = payment_service_client.post("/payments", json=invalid_data)

        assert response.status_code == 422
        assert expected_error in str(response.json())


class TestNotificationService:
    """Tests for REST Notification Service."""

    def test_health_check(self, notification_service_client):
        response = notification_service_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "notification-rest"

    def test_metrics_endpoint(self, notification_service_client):
        response = notification_service_client.get("/metrics")

        assert response.status_code == 200
        assert "request_total" in response.text

    def test_send_notification_success(self, notification_service_client):
        notification_data = {
            "order_id": "ord_12345",
            "payment_id": "pay_12345",
            "recipient": "customer@example.com",
            "notification_type": "email",
        }

        response = notification_service_client.post(
            "/notifications", json=notification_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "notification" in data
        assert data["notification"]["order_id"] == "ord_12345"
        assert data["notification"]["payment_id"] == "pay_12345"
        assert data["notification"]["recipient"] == "customer@example.com"
        assert data["notification"]["status"] == "sent"
        assert "Your order" in data["notification"]["message"]

    @pytest.mark.parametrize(
        "notification_type",
        [
            "email",
            "sms",
            "push",
        ],
    )
    def test_send_notification_different_types(
        self, notification_service_client, notification_type
    ):
        notification_data = {
            "order_id": "ord_12345",
            "payment_id": "pay_12345",
            "recipient": "customer@example.com",
            "notification_type": notification_type,
        }

        response = notification_service_client.post(
            "/notifications", json=notification_data
        )

        assert response.status_code == 200
        assert response.json()["notification"]["notification_type"] == notification_type

    @pytest.mark.parametrize(
        "invalid_data,expected_error",
        [
            (
                {
                    "order_id": "ord_123",
                    "payment_id": "pay_123",
                    "recipient": "test@example.com",
                    "notification_type": "invalid_type",
                },
                "notification_type",
            ),
        ],
        ids=["invalid_type"],
    )
    def test_send_notification_validation_errors(
        self, notification_service_client, invalid_data, expected_error
    ):
        response = notification_service_client.post("/notifications", json=invalid_data)

        assert response.status_code == 422
        assert expected_error in str(response.json())


class TestIntegration:
    """Integration tests for REST services (requires all services running)."""

    @pytest.mark.integration
    def test_full_order_flow(self):
        """Test complete order → payment → notification flow.

        This test requires all services to be running:
        - Order Service on port 8001
        - Payment Service on port 8002
        - Notification Service on port 8003
        """
        import httpx

        order_data = {
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
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "http://localhost:8001/orders",
                json=order_data,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["order"]["customer_id"] == "cust_integration_test"
        assert data["payment"]["status"] == "completed"
        assert data["notification"]["status"] == "sent"
        assert data["total_processing_time_ms"] > 0

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "service_url,service_name",
        [
            ("http://localhost:8001", "order-rest"),
            ("http://localhost:8002", "payment-rest"),
            ("http://localhost:8003", "notification-rest"),
        ],
    )
    def test_service_health_checks(self, service_url, service_name):
        """Test health checks for all services."""
        import httpx

        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{service_url}/health")

        assert response.status_code == 200
        assert response.json()["service"] == service_name
