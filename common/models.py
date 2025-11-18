import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    COMPLETED = "completed"
    FAILED = "failed"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"


class NotificationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class OrderItem(BaseModel):
    product_id: str = Field(..., description="Product identifier")
    product_name: str = Field(..., description="Product name")
    quantity: int = Field(..., ge=1, description="Quantity ordered")
    unit_price: float = Field(..., ge=0, description="Price per unit")

    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price


class OrderCreate(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    items: list[OrderItem] = Field(..., min_length=1, description="Order items")
    shipping_address: str = Field(..., description="Delivery address")


class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    items: list[OrderItem]
    shipping_address: str
    total_amount: float = Field(..., ge=0)
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    @classmethod
    def from_create(cls, order_create: OrderCreate) -> "Order":
        """Create Order from OrderCreate request."""
        total = sum(item.quantity * item.unit_price for item in order_create.items)
        return cls(
            customer_id=order_create.customer_id,
            items=order_create.items,
            shipping_address=order_create.shipping_address,
            total_amount=total,
        )


class PaymentRequest(BaseModel):
    order_id: str = Field(..., description="Associated order ID")
    amount: float = Field(..., ge=0, description="Payment amount")
    currency: str = Field(default="USD", description="Currency code")
    payment_method: PaymentMethod = Field(..., description="Payment method")


class Payment(BaseModel):
    payment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    amount: float
    currency: str = "USD"
    payment_method: PaymentMethod
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None
    error_message: str | None = None


class NotificationRequest(BaseModel):
    order_id: str = Field(..., description="Associated order ID")
    payment_id: str = Field(..., description="Associated payment ID")
    recipient: str = Field(..., description="Recipient (email/phone)")
    notification_type: NotificationType = Field(..., description="Notification type")


class Notification(BaseModel):
    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    payment_id: str
    recipient: str
    notification_type: NotificationType
    message: str
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    error_message: str | None = None


class OrderResponse(BaseModel):
    success: bool
    order: Order
    payment: Payment | None = None
    notification: Notification | None = None
    total_processing_time_ms: float


class BenchmarkMetrics(BaseModel):
    protocol: str
    operation: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    payload_size_bytes: int
    success: bool
    error_message: str | None = None
