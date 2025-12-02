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

from generated import common_pb2, notification_pb2, notification_pb2_grpc

from common.metrics import ERROR_COUNT, REQUEST_COUNT, REQUEST_LATENCY

logger = logging.getLogger(__name__)


async def simulate_notification_sending():
    """Simulate sending email/SMS."""
    await asyncio.sleep(0.005)


def datetime_to_timestamp(dt: datetime) -> Timestamp:
    """Convert datetime to protobuf Timestamp."""
    ts = Timestamp()
    ts.FromDatetime(dt)
    return ts


class NotificationServicer(notification_pb2_grpc.NotificationServiceServicer):
    async def SendNotification(
        self, request: notification_pb2.SendNotificationRequest, context
    ) -> notification_pb2.SendNotificationResponse:
        """Send notification to customer."""
        start_time = time.perf_counter()

        REQUEST_COUNT.labels(
            protocol="grpc", service="notification", method="send_notification"
        ).inc()

        try:
            notification = common_pb2.Notification(
                notification_id=str(uuid.uuid4()),
                order_id=request.order_id,
                payment_id=request.payment_id,
                recipient=request.recipient,
                notification_type=request.notification_type,
                message=(
                    f"Your order {request.order_id} has been confirmed. "
                    f"Payment {request.payment_id} processed successfully."
                ),
                status=common_pb2.NOTIFICATION_PENDING,
            )

            notification.created_at.CopyFrom(datetime_to_timestamp(datetime.utcnow()))

            await simulate_notification_sending()

            notification.status = common_pb2.SENT
            notification.sent_at.CopyFrom(datetime_to_timestamp(datetime.utcnow()))

            end_time = time.perf_counter()
            processing_time = (end_time - start_time) * 1000

            REQUEST_LATENCY.labels(
                protocol="grpc", service="notification", method="send_notification"
            ).observe(processing_time / 1000)

            return notification_pb2.SendNotificationResponse(
                success=True,
                notification=notification,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            ERROR_COUNT.labels(
                protocol="grpc", service="notification", error_type="internal_error"
            ).inc()
            logger.error(f"Internal error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return notification_pb2.SendNotificationResponse(success=False)


async def serve():
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 10000),
            ("grpc.keepalive_timeout_ms", 5000),
        ],
    )

    notification_pb2_grpc.add_NotificationServiceServicer_to_server(
        NotificationServicer(), server
    )

    listen_addr = "[::]:8023"
    server.add_insecure_port(listen_addr)

    logger.info(f"Notification Service (gRPC) starting on {listen_addr}...")
    await server.start()

    start_http_server(9023)
    logger.info("Prometheus metrics server started on port 9023")

    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
