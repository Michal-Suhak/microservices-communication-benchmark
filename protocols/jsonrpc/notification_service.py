import asyncio
import logging
import time
from datetime import datetime

from aiohttp import web
from jsonrpcserver import Error, Result, Success, async_dispatch, method
from prometheus_client import generate_latest

from common.metrics import ERROR_COUNT, PAYLOAD_SIZE, REQUEST_COUNT, REQUEST_LATENCY
from common.models import Notification, NotificationStatus, NotificationType

logger = logging.getLogger(__name__)


@method
async def send_notification(
    order_id: str, payment_id: str, recipient: str, notification_type: str
) -> Result:
    """
    Send notification via JSON-RPC.

    Args:
        order_id: Associated order ID
        payment_id: Associated payment ID
        recipient: Recipient email/phone
        notification_type: Type of notification

    Returns:
        Result with notification details
    """
    start_time = time.perf_counter()

    REQUEST_COUNT.labels(
        protocol="jsonrpc", service="notification", method="send_notification"
    ).inc()

    try:
        notification = Notification(
            order_id=order_id,
            payment_id=payment_id,
            recipient=recipient,
            notification_type=NotificationType(notification_type),
            message=(
                f"Your order {order_id} has been confirmed. "
                f"Payment {payment_id} processed successfully."
            ),
            status=NotificationStatus.PENDING,
        )

        # Simulate notification sending
        await asyncio.sleep(0.005)

        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()

        end_time = time.perf_counter()
        processing_time = (end_time - start_time) * 1000

        REQUEST_LATENCY.labels(
            protocol="jsonrpc", service="notification", method="send_notification"
        ).observe(processing_time / 1000)

        return Success(
            {
                "notification": notification.model_dump(mode="json"),
                "processing_time_ms": processing_time,
            }
        )

    except Exception as e:
        ERROR_COUNT.labels(
            protocol="jsonrpc", service="notification", error_type="internal_error"
        ).inc()
        logger.error(f"Internal error: {e}")
        return Error(code=-32000, message=str(e))


async def handle_jsonrpc(request: web.Request) -> web.Response:
    """Handle JSON-RPC requests."""
    body = await request.text()

    PAYLOAD_SIZE.labels(
        protocol="jsonrpc", service="notification", direction="request"
    ).observe(len(body))

    response = await async_dispatch(body)

    PAYLOAD_SIZE.labels(
        protocol="jsonrpc", service="notification", direction="response"
    ).observe(len(response))

    return web.Response(text=response, content_type="application/json")


async def health_check(request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy", "service": "notification-jsonrpc"})


async def metrics(request: web.Request) -> web.Response:
    return web.Response(body=generate_latest(), content_type="text/plain")


def create_app() -> web.Application:
    app = web.Application()

    app.router.add_post("/", handle_jsonrpc)
    app.router.add_get("/health", health_check)
    app.router.add_get("/metrics", metrics)

    logger.info("Notification Service (JSON-RPC) started")
    return app
