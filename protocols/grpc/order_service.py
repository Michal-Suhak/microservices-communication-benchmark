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
    order_pb2,
    order_pb2_grpc,
    payment_pb2,
    payment_pb2_grpc,
)

from common.config import settings
from common.metrics import ERROR_COUNT, REQUEST_COUNT, REQUEST_LATENCY

logger = logging.getLogger(__name__)


def datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to protobuf Timestamp."""
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


class OrderServicer(order_pb2_grpc.OrderServiceServicer):
    def __init__(self):
        self.payment_channel = None
        self.payment_stub = None

    async def initialize(self):
        """Initialize gRPC client for Payment Service."""
        self.payment_channel = grpc.aio.insecure_channel(
            settings.PAYMENT_SERVICE_GRPC_URL,
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ("grpc.keepalive_time_ms", 10000),
                ("grpc.keepalive_timeout_ms", 5000),
            ],
        )
        self.payment_stub = payment_pb2_grpc.PaymentServiceStub(self.payment_channel)
        logger.info(
            f"Connected to Payment Service at {settings.PAYMENT_SERVICE_GRPC_URL}"
        )

    async def shutdown(self):
        """Close gRPC channel."""
        if self.payment_channel:
            await self.payment_channel.close()

    async def CreateOrder(
        self, request: order_pb2.CreateOrderRequest, context
    ) -> order_pb2.CreateOrderResponse:
        """
        Create a new order and process payment.

        Flow:
        1. Validate and create order
        2. Call Payment Service
        3. Return complete response
        """
        start_time = time.perf_counter()

        REQUEST_COUNT.labels(
            protocol="grpc", service="order", method="create_order"
        ).inc()

        try:
            total_amount = sum(
                item.quantity * item.unit_price for item in request.items
            )

            order = common_pb2.Order(
                order_id=str(uuid.uuid4()),
                customer_id=request.customer_id,
                shipping_address=request.shipping_address,
                total_amount=total_amount,
                status=common_pb2.PENDING,
            )

            for item in request.items:
                order.items.append(item)

            order.created_at.CopyFrom(datetime_to_timestamp(datetime.utcnow()))

            logger.info(f"Created order: {order.order_id}")

            payment_request = payment_pb2.ProcessPaymentRequest(
                order_id=order.order_id,
                amount=order.total_amount,
                currency="USD",
                payment_method=common_pb2.CREDIT_CARD,
            )

            payment_response = await self.payment_stub.ProcessPayment(payment_request)

            if not payment_response.success:
                ERROR_COUNT.labels(
                    protocol="grpc", service="order", error_type="payment_failed"
                ).inc()
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Payment processing failed")
                return order_pb2.CreateOrderResponse(success=False)

            end_time = time.perf_counter()
            processing_time = (end_time - start_time) * 1000

            REQUEST_LATENCY.labels(
                protocol="grpc", service="order", method="create_order"
            ).observe(processing_time / 1000)

            return order_pb2.CreateOrderResponse(
                success=True,
                order=order,
                payment=payment_response.payment,
                notification=payment_response.notification,
                total_processing_time_ms=processing_time,
            )

        except grpc.RpcError as e:
            ERROR_COUNT.labels(
                protocol="grpc", service="order", error_type="connection_error"
            ).inc()
            logger.error(f"gRPC error: {e}")
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details(f"Service unavailable: {e}")
            return order_pb2.CreateOrderResponse(success=False)

        except Exception as e:
            ERROR_COUNT.labels(
                protocol="grpc", service="order", error_type="internal_error"
            ).inc()
            logger.error(f"Internal error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return order_pb2.CreateOrderResponse(success=False)


async def serve():
    servicer = OrderServicer()
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

    order_pb2_grpc.add_OrderServiceServicer_to_server(servicer, server)

    listen_addr = "[::]:8021"
    server.add_insecure_port(listen_addr)

    logger.info(f"Order Service (gRPC) starting on {listen_addr}...")
    await server.start()

    start_http_server(9021)
    logger.info("Prometheus metrics server started on port 9021")

    try:
        await server.wait_for_termination()
    finally:
        await servicer.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
