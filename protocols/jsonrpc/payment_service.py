import asyncio
import json
import logging
import time
import uuid
from datetime import datetime

import aiohttp
from aiohttp import web
from jsonrpcclient import parse, request
from jsonrpcclient.responses import Ok
from jsonrpcserver import Error, Result, Success, async_dispatch, method
from prometheus_client import generate_latest

from common.config import settings
from common.metrics import ERROR_COUNT, PAYLOAD_SIZE, REQUEST_COUNT, REQUEST_LATENCY
from common.models import NotificationType, Payment, PaymentMethod, PaymentStatus

logger = logging.getLogger(__name__)

session: aiohttp.ClientSession | None = None


async def init_session(app: web.Application):
    global session
    session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        connector=aiohttp.TCPConnector(limit=200, keepalive_timeout=30),
    )
    logger.info("Payment Service (JSON-RPC) starting up...")


async def close_session(app: web.Application):
    global session
    if session:
        await session.close()
    logger.info("Payment Service (JSON-RPC) shut down")


@method
async def process_payment(
    order_id: str, amount: float, currency: str, payment_method: str
) -> Result:
    """
    Process payment via JSON-RPC.

    Args:
        order_id: Associated order ID
        amount: Payment amount
        currency: Currency code
        payment_method: Payment method

    Returns:
        Result with payment details
    """
    start_time = time.perf_counter()

    REQUEST_COUNT.labels(
        protocol="jsonrpc", service="payment", method="process_payment"
    ).inc()

    try:
        payment = Payment(
            order_id=order_id,
            amount=amount,
            currency=currency,
            payment_method=PaymentMethod(payment_method),
            status=PaymentStatus.PROCESSING,
            transaction_id=f"txn_{uuid.uuid4().hex[:12]}",
        )

        # Simulate payment processing
        await asyncio.sleep(0.01)

        payment.status = PaymentStatus.COMPLETED
        payment.processed_at = datetime.utcnow()

        notification_request = request(
            "send_notification",
            params={
                "order_id": order_id,
                "payment_id": payment.payment_id,
                "recipient": "customer@example.com",
                "notification_type": NotificationType.EMAIL.value,
            },
        )

        async with session.post(
            settings.NOTIFICATION_SERVICE_JSONRPC_URL,
            json=notification_request,
            headers={"Content-Type": "application/json"},
        ) as response:
            response_text = await response.text()
            parsed = parse(json.loads(response_text))
            notification_result = parsed.result if isinstance(parsed, Ok) else None

        end_time = time.perf_counter()
        processing_time = (end_time - start_time) * 1000

        REQUEST_LATENCY.labels(
            protocol="jsonrpc", service="payment", method="process_payment"
        ).observe(processing_time / 1000)

        return Success(
            {
                "payment": payment.model_dump(mode="json"),
                "notification": (
                    notification_result.get("notification")
                    if notification_result
                    else None
                ),
                "processing_time_ms": processing_time,
            }
        )

    except Exception as e:
        ERROR_COUNT.labels(
            protocol="jsonrpc", service="payment", error_type="internal_error"
        ).inc()
        logger.error(f"Internal error: {e}")
        return Error(code=-32000, message=str(e))


async def handle_jsonrpc(request: web.Request) -> web.Response:
    """Handle JSON-RPC requests."""
    body = await request.text()

    PAYLOAD_SIZE.labels(
        protocol="jsonrpc", service="payment", direction="request"
    ).observe(len(body))

    response = await async_dispatch(body)

    PAYLOAD_SIZE.labels(
        protocol="jsonrpc", service="payment", direction="response"
    ).observe(len(response))

    return web.Response(text=response, content_type="application/json")


async def health_check(request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy", "service": "payment-jsonrpc"})


async def metrics(request: web.Request) -> web.Response:
    return web.Response(body=generate_latest(), content_type="text/plain")


def create_app() -> web.Application:
    app = web.Application()
    app.on_startup.append(init_session)
    app.on_cleanup.append(close_session)

    app.router.add_post("/", handle_jsonrpc)
    app.router.add_get("/health", health_check)
    app.router.add_get("/metrics", metrics)

    return app
