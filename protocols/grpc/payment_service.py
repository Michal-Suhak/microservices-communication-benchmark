import asyncio
import logging
import sys
import time
import uuid
from concurrent import futures
from datetime import datetime

from google.protobuf.timestamp_pb2 import Timestamp
from prometheus_client import start_http_server

import grpc

sys.path.append("protocols/grpc/generated")

from generated import (
    common_pb2,
    notification_pb2,
    notification_pb2_grpc,
    payment_pb2,
    payment_pb2_grpc,
)

from common.config import settings
from common.metrics import ERROR_COUNT, REQUEST_COUNT, REQUEST_LATENCY

logger = logging.getLogger(__name__)


async def simulate_payment_processing():
    """Simulate payment gateway processing time."""
    await asyncio.sleep(0.01)


def datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to protobuf Timestamp."""
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


class PaymentServicer(payment_pb2_grpc.PaymentServiceServicer):
    def __init__(self):
        self.notification_channel = None
        self.notification_stub = None

    async def initialize(self):
        """Initialize gRPC client for Notification Service."""
        self.notification_channel = grpc.aio.insecure_channel(
            settings.NOTIFICATION_SERVICE_GRPC_URL,
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ("grpc.keepalive_time_ms", 10000),
                ("grpc.keepalive_timeout_ms", 5000),
            ],
        )
        self.notification_stub = notification_pb2_grpc.NotificationServiceStub(
            self.notification_channel
        )
        logger.info(
            f"Connected to Notification Service at {settings.NOTIFICATION_SERVICE_GRPC_URL}"
        )

    async def shutdown(self):
        """Close gRPC channel."""
        if self.notification_channel:
            await self.notification_channel.close()

    async def ProcessPayment(
        self, request: payment_pb2.ProcessPaymentRequest, context
    ) -> payment_pb2.ProcessPaymentResponse:
        """Process payment and trigger notification."""
        start_time = time.perf_counter()

        REQUEST_COUNT.labels(
            protocol="grpc", service="payment", method="process_payment"
        ).inc()

        try:
            payment = common_pb2.Payment(
                payment_id=str(uuid.uuid4()),
                order_id=request.order_id,
                amount=request.amount,
                currency=request.currency,
                payment_method=request.payment_method,
                status=common_pb2.PAYMENT_PROCESSING,
                transaction_id=f"txn_{uuid.uuid4().hex[:12]}",
            )

            payment.created_at.CopyFrom(datetime_to_timestamp(datetime.utcnow()))

            await simulate_payment_processing()

            payment.status = common_pb2.PAYMENT_COMPLETED
            payment.processed_at.CopyFrom(datetime_to_timestamp(datetime.utcnow()))

            notification_request = notification_pb2.SendNotificationRequest(
                order_id=payment.order_id,
                payment_id=payment.payment_id,
                recipient="customer@example.com",
                notification_type=common_pb2.EMAIL,
            )

            notification_response = None
            try:
                notification_response = await self.notification_stub.SendNotification(
                    notification_request
                )
            except grpc.RpcError as e:
                logger.error(f"Notification service error: {e}")
                ERROR_COUNT.labels(
                    protocol="grpc", service="payment", error_type="notification_failed"
                ).inc()

            end_time = time.perf_counter()
            processing_time = (end_time - start_time) * 1000

            REQUEST_LATENCY.labels(
                protocol="grpc", service="payment", method="process_payment"
            ).observe(processing_time / 1000)

            return payment_pb2.ProcessPaymentResponse(
                success=True,
                payment=payment,
                notification=(
                    notification_response.notification
                    if notification_response and notification_response.success
                    else None
                ),
                processing_time_ms=processing_time,
            )

        except Exception as e:
            ERROR_COUNT.labels(
                protocol="grpc", service="payment", error_type="internal_error"
            ).inc()
            logger.error(f"Internal error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return payment_pb2.ProcessPaymentResponse(success=False)


async def serve():
    servicer = PaymentServicer()
    await servicer.initialize()

    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 10000),
            ("grpc.keepalive_timeout_ms", 5000),
        ],
    )

    payment_pb2_grpc.add_PaymentServiceServicer_to_server(servicer, server)

    listen_addr = "[::]:8022"
    server.add_insecure_port(listen_addr)

    logger.info(f"Payment Service (gRPC) starting on {listen_addr}...")
    await server.start()

    start_http_server(9022)
    logger.info("Prometheus metrics server started on port 9022")

    try:
        await server.wait_for_termination()
    finally:
        await servicer.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
