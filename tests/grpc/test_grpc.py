import sys

import grpc
import pytest

sys.path.append("protocols/grpc/generated")

from protocols.grpc.generated import (
    common_pb2,
    notification_pb2,
    notification_pb2_grpc,
    order_pb2,
    order_pb2_grpc,
    payment_pb2,
    payment_pb2_grpc,
)


class TestNotificationService:
    """Tests for gRPC Notification Service."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_send_notification_success(self, grpc_notification_channel):
        async with grpc.aio.insecure_channel(grpc_notification_channel) as channel:
            stub = notification_pb2_grpc.NotificationServiceStub(channel)

            request = notification_pb2.SendNotificationRequest(
                order_id="ord_12345",
                payment_id="pay_67890",
                recipient="customer@example.com",
                notification_type=common_pb2.EMAIL,
            )

            response = await stub.SendNotification(request)

            assert response.success is True
            assert response.notification.order_id == "ord_12345"
            assert response.notification.payment_id == "pay_67890"
            assert response.notification.recipient == "customer@example.com"
            assert response.notification.notification_type == common_pb2.EMAIL
            assert response.notification.status == common_pb2.SENT
            assert response.notification.message
            assert response.processing_time_ms > 0


class TestPaymentService:
    """Tests for gRPC Payment Service."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_process_payment_success(self, grpc_payment_channel):
        async with grpc.aio.insecure_channel(grpc_payment_channel) as channel:
            stub = payment_pb2_grpc.PaymentServiceStub(channel)

            request = payment_pb2.ProcessPaymentRequest(
                order_id="ord_12345",
                amount=1059.97,
                currency="USD",
                payment_method=common_pb2.CREDIT_CARD,
            )

            response = await stub.ProcessPayment(request)

            assert response.success is True
            assert response.payment.order_id == "ord_12345"
            assert response.payment.amount == pytest.approx(1059.97, rel=0.01)
            assert response.payment.currency == "USD"
            assert response.payment.payment_method == common_pb2.CREDIT_CARD
            assert response.payment.status == common_pb2.PAYMENT_COMPLETED
            assert response.payment.transaction_id
            assert response.notification is not None
            assert response.notification.status == common_pb2.SENT
            assert response.processing_time_ms > 0


class TestOrderService:
    """Tests for gRPC Order Service."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_order_success(self, grpc_order_channel, sample_order_items):
        async with grpc.aio.insecure_channel(grpc_order_channel) as channel:
            stub = order_pb2_grpc.OrderServiceStub(channel)

            request = order_pb2.CreateOrderRequest(
                customer_id="cust_12345",
                items=sample_order_items,
                shipping_address="123 Main St, City, Country",
            )

            response = await stub.CreateOrder(request)

            assert response.success is True
            assert response.order.customer_id == "cust_12345"
            assert response.order.total_amount == pytest.approx(1059.97, rel=0.01)
            assert response.order.status == common_pb2.PENDING
            assert len(response.order.items) == 2
            assert response.order.shipping_address == "123 Main St, City, Country"

            assert response.payment is not None
            assert response.payment.payment_id
            assert response.payment.status == common_pb2.PAYMENT_COMPLETED
            assert response.payment.transaction_id

            assert response.notification is not None
            assert response.notification.notification_id
            assert response.notification.status == common_pb2.SENT

            assert response.total_processing_time_ms > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_order_with_single_item(self, grpc_order_channel):
        async with grpc.aio.insecure_channel(grpc_order_channel) as channel:
            stub = order_pb2_grpc.OrderServiceStub(channel)

            items = [
                common_pb2.OrderItem(
                    product_id="prod_003",
                    product_name="Keyboard",
                    quantity=1,
                    unit_price=149.99,
                )
            ]

            request = order_pb2.CreateOrderRequest(
                customer_id="cust_67890",
                items=items,
                shipping_address="456 Oak Ave, Town, Country",
            )

            response = await stub.CreateOrder(request)

            assert response.success is True
            assert response.order.total_amount == pytest.approx(149.99, rel=0.01)
            assert len(response.order.items) == 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_create_order_with_multiple_quantities(self, grpc_order_channel):
        async with grpc.aio.insecure_channel(grpc_order_channel) as channel:
            stub = order_pb2_grpc.OrderServiceStub(channel)

            items = [
                common_pb2.OrderItem(
                    product_id="prod_004",
                    product_name="Headphones",
                    quantity=3,
                    unit_price=79.99,
                )
            ]

            request = order_pb2.CreateOrderRequest(
                customer_id="cust_99999",
                items=items,
                shipping_address="789 Pine Rd, Village, Country",
            )

            response = await stub.CreateOrder(request)

            assert response.success is True
            assert response.order.total_amount == pytest.approx(239.97, rel=0.01)

    @pytest.mark.asyncio
    async def test_service_unavailable(self):
        """Test handling of unavailable service."""
        async with grpc.aio.insecure_channel("localhost:9999") as channel:
            stub = order_pb2_grpc.OrderServiceStub(channel)

            items = [
                common_pb2.OrderItem(
                    product_id="prod_001",
                    product_name="Test",
                    quantity=1,
                    unit_price=10.0,
                )
            ]

            request = order_pb2.CreateOrderRequest(
                customer_id="cust_test",
                items=items,
                shipping_address="Test Address",
            )

            with pytest.raises(grpc.RpcError):
                await stub.CreateOrder(request, timeout=2.0)
