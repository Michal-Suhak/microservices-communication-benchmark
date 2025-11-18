from datetime import datetime

import pytest

from common.models import (
    BenchmarkMetrics,
    Notification,
    NotificationRequest,
    NotificationStatus,
    NotificationType,
    Order,
    OrderCreate,
    OrderItem,
    OrderResponse,
    OrderStatus,
    Payment,
    PaymentMethod,
    PaymentRequest,
    PaymentStatus,
)


class TestOrderItem:
    def test_create_order_item(self):
        item = OrderItem(
            product_id="prod_001",
            product_name="Test Product",
            quantity=2,
            unit_price=49.99,
        )

        assert item.product_id == "prod_001"
        assert item.product_name == "Test Product"
        assert item.quantity == 2
        assert item.unit_price == 49.99

    def test_total_price_property(self):
        item = OrderItem(
            product_id="prod_001",
            product_name="Test",
            quantity=3,
            unit_price=10.0,
        )

        assert item.total_price == 30.0

    @pytest.mark.parametrize(
        "quantity,unit_price,expected",
        [
            (1, 100.0, 100.0),
            (5, 20.0, 100.0),
            (10, 0.5, 5.0),
            (1, 0.01, 0.01),
        ],
        ids=["single", "multiple", "decimal_price", "penny"],
    )
    def test_total_price_calculations(self, quantity, unit_price, expected):
        item = OrderItem(
            product_id="prod",
            product_name="Test",
            quantity=quantity,
            unit_price=unit_price,
        )

        assert item.total_price == expected

    def test_quantity_minimum_validation(self):
        with pytest.raises(ValueError):
            OrderItem(
                product_id="prod",
                product_name="Test",
                quantity=0,
                unit_price=10.0,
            )

    def test_unit_price_minimum_validation(self):
        with pytest.raises(ValueError):
            OrderItem(
                product_id="prod",
                product_name="Test",
                quantity=1,
                unit_price=-10.0,
            )


class TestOrderCreate:
    """Tests for OrderCreate model."""

    def test_create_order_create(self):
        items = [
            OrderItem(
                product_id="prod_001",
                product_name="Test",
                quantity=1,
                unit_price=10.0,
            )
        ]
        order_create = OrderCreate(
            customer_id="cust_123",
            items=items,
            shipping_address="123 Main St",
        )

        assert order_create.customer_id == "cust_123"
        assert len(order_create.items) == 1
        assert order_create.shipping_address == "123 Main St"

    def test_items_minimum_length_validation(self):
        with pytest.raises(ValueError):
            OrderCreate(
                customer_id="cust_123",
                items=[],
                shipping_address="123 Main St",
            )


class TestOrder:
    """Tests for Order model."""

    def test_from_create_single_item(self):
        items = [
            OrderItem(
                product_id="prod_001",
                product_name="Test",
                quantity=1,
                unit_price=99.99,
            )
        ]
        order_create = OrderCreate(
            customer_id="cust_123",
            items=items,
            shipping_address="123 Main St",
        )

        order = Order.from_create(order_create)

        assert order.customer_id == "cust_123"
        assert order.items == items
        assert order.shipping_address == "123 Main St"
        assert order.total_amount == 99.99
        assert order.status == OrderStatus.PENDING
        assert order.order_id is not None
        assert order.created_at is not None

    def test_from_create_multiple_items(self):
        items = [
            OrderItem(
                product_id="prod_001",
                product_name="Item A",
                quantity=2,
                unit_price=50.0,
            ),
            OrderItem(
                product_id="prod_002",
                product_name="Item B",
                quantity=3,
                unit_price=30.0,
            ),
        ]
        order_create = OrderCreate(
            customer_id="cust_456",
            items=items,
            shipping_address="456 Oak Ave",
        )

        order = Order.from_create(order_create)

        assert order.total_amount == 190.0

    def test_order_id_is_uuid(self):
        items = [
            OrderItem(
                product_id="prod",
                product_name="Test",
                quantity=1,
                unit_price=10.0,
            )
        ]
        order_create = OrderCreate(
            customer_id="cust",
            items=items,
            shipping_address="Address",
        )

        order = Order.from_create(order_create)

        import uuid

        uuid.UUID(order.order_id)

    def test_default_status_is_pending(self):
        items = [
            OrderItem(
                product_id="prod",
                product_name="Test",
                quantity=1,
                unit_price=10.0,
            )
        ]
        order_create = OrderCreate(
            customer_id="cust",
            items=items,
            shipping_address="Address",
        )

        order = Order.from_create(order_create)

        assert order.status == OrderStatus.PENDING


class TestPaymentRequest:
    """Tests for PaymentRequest model."""

    def test_create_payment_request(self):
        request = PaymentRequest(
            order_id="ord_123",
            amount=99.99,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
        )

        assert request.order_id == "ord_123"
        assert request.amount == 99.99
        assert request.currency == "USD"
        assert request.payment_method == PaymentMethod.CREDIT_CARD

    def test_default_currency(self):
        request = PaymentRequest(
            order_id="ord_123",
            amount=100.0,
            payment_method=PaymentMethod.PAYPAL,
        )

        assert request.currency == "USD"

    def test_amount_minimum_validation(self):
        with pytest.raises(ValueError):
            PaymentRequest(
                order_id="ord_123",
                amount=-100.0,
                payment_method=PaymentMethod.CREDIT_CARD,
            )


class TestPayment:
    """Tests for Payment model."""

    def test_create_payment(self):
        payment = Payment(
            order_id="ord_123",
            amount=99.99,
            payment_method=PaymentMethod.CREDIT_CARD,
        )

        assert payment.order_id == "ord_123"
        assert payment.amount == 99.99
        assert payment.payment_method == PaymentMethod.CREDIT_CARD
        assert payment.payment_id is not None
        assert payment.status == PaymentStatus.PENDING

    def test_default_values(self):
        payment = Payment(
            order_id="ord_123",
            amount=100.0,
            payment_method=PaymentMethod.DEBIT_CARD,
        )

        assert payment.currency == "USD"
        assert payment.status == PaymentStatus.PENDING
        assert payment.transaction_id is None
        assert payment.processed_at is None
        assert payment.error_message is None

    @pytest.mark.parametrize(
        "method",
        [
            PaymentMethod.CREDIT_CARD,
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.BANK_TRANSFER,
            PaymentMethod.PAYPAL,
        ],
    )
    def test_all_payment_methods(self, method):
        payment = Payment(
            order_id="ord_123",
            amount=100.0,
            payment_method=method,
        )

        assert payment.payment_method == method


class TestNotificationRequest:
    """Tests for NotificationRequest model."""

    def test_create_notification_request(self):
        request = NotificationRequest(
            order_id="ord_123",
            payment_id="pay_456",
            recipient="test@example.com",
            notification_type=NotificationType.EMAIL,
        )

        assert request.order_id == "ord_123"
        assert request.payment_id == "pay_456"
        assert request.recipient == "test@example.com"
        assert request.notification_type == NotificationType.EMAIL


class TestNotification:
    """Tests for Notification model."""

    def test_create_notification(self):
        notification = Notification(
            order_id="ord_123",
            payment_id="pay_456",
            recipient="test@example.com",
            notification_type=NotificationType.EMAIL,
            message="Your order has been confirmed.",
        )

        assert notification.order_id == "ord_123"
        assert notification.payment_id == "pay_456"
        assert notification.recipient == "test@example.com"
        assert notification.notification_type == NotificationType.EMAIL
        assert notification.message == "Your order has been confirmed."
        assert notification.notification_id is not None

    def test_default_values(self):
        notification = Notification(
            order_id="ord_123",
            payment_id="pay_456",
            recipient="test@example.com",
            notification_type=NotificationType.SMS,
            message="Test",
        )

        assert notification.status == NotificationStatus.PENDING
        assert notification.sent_at is None
        assert notification.delivered_at is None
        assert notification.error_message is None

    @pytest.mark.parametrize(
        "notification_type",
        [
            NotificationType.EMAIL,
            NotificationType.SMS,
            NotificationType.PUSH,
        ],
    )
    def test_all_notification_types(self, notification_type):
        notification = Notification(
            order_id="ord_123",
            payment_id="pay_456",
            recipient="test@example.com",
            notification_type=notification_type,
            message="Test",
        )

        assert notification.notification_type == notification_type


class TestOrderResponse:
    """Tests for OrderResponse model."""

    def test_create_order_response(self):
        items = [
            OrderItem(
                product_id="prod",
                product_name="Test",
                quantity=1,
                unit_price=10.0,
            )
        ]
        order_create = OrderCreate(
            customer_id="cust",
            items=items,
            shipping_address="Address",
        )
        order = Order.from_create(order_create)

        response = OrderResponse(
            success=True,
            order=order,
            total_processing_time_ms=15.5,
        )

        assert response.success is True
        assert response.order == order
        assert response.payment is None
        assert response.notification is None
        assert response.total_processing_time_ms == 15.5


class TestBenchmarkMetrics:
    """Tests for BenchmarkMetrics model."""

    def test_create_benchmark_metrics(self):
        start = datetime.utcnow()
        end = datetime.utcnow()

        metrics = BenchmarkMetrics(
            protocol="rest",
            operation="create_order",
            start_time=start,
            end_time=end,
            duration_ms=15.5,
            payload_size_bytes=1024,
            success=True,
        )

        assert metrics.protocol == "rest"
        assert metrics.operation == "create_order"
        assert metrics.start_time == start
        assert metrics.end_time == end
        assert metrics.duration_ms == 15.5
        assert metrics.payload_size_bytes == 1024
        assert metrics.success is True
        assert metrics.error_message is None

    def test_benchmark_metrics_with_error(self):
        start = datetime.utcnow()
        end = datetime.utcnow()

        metrics = BenchmarkMetrics(
            protocol="rest",
            operation="create_order",
            start_time=start,
            end_time=end,
            duration_ms=100.0,
            payload_size_bytes=512,
            success=False,
            error_message="Connection timeout",
        )

        assert metrics.success is False
        assert metrics.error_message == "Connection timeout"


class TestEnums:
    """Tests for enum values."""

    def test_order_status_values(self):
        assert OrderStatus.PENDING == "pending"
        assert OrderStatus.PROCESSING == "processing"
        assert OrderStatus.PAID == "paid"
        assert OrderStatus.COMPLETED == "completed"
        assert OrderStatus.FAILED == "failed"

    def test_payment_status_values(self):
        assert PaymentStatus.PENDING == "pending"
        assert PaymentStatus.PROCESSING == "processing"
        assert PaymentStatus.COMPLETED == "completed"
        assert PaymentStatus.FAILED == "failed"
        assert PaymentStatus.REFUNDED == "refunded"

    def test_payment_method_values(self):
        assert PaymentMethod.CREDIT_CARD == "credit_card"
        assert PaymentMethod.DEBIT_CARD == "debit_card"
        assert PaymentMethod.BANK_TRANSFER == "bank_transfer"
        assert PaymentMethod.PAYPAL == "paypal"

    def test_notification_type_values(self):
        assert NotificationType.EMAIL == "email"
        assert NotificationType.SMS == "sms"
        assert NotificationType.PUSH == "push"

    def test_notification_status_values(self):
        assert NotificationStatus.PENDING == "pending"
        assert NotificationStatus.SENT == "sent"
        assert NotificationStatus.DELIVERED == "delivered"
        assert NotificationStatus.FAILED == "failed"
