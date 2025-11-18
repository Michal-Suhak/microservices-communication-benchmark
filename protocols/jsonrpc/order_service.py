import json
import logging
import time

import aiohttp
from aiohttp import web
from jsonrpcclient import parse, request
from jsonrpcclient.responses import Ok
from jsonrpcserver import Error, Result, Success, async_dispatch, method
from prometheus_client import generate_latest

from common.config import settings
from common.metrics import ERROR_COUNT, PAYLOAD_SIZE, REQUEST_COUNT, REQUEST_LATENCY
from common.models import Order, OrderCreate, OrderItem, PaymentMethod

logger = logging.getLogger(__name__)

session: aiohttp.ClientSession | None = None


async def init_session(app: web.Application):
    global session
    session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        connector=aiohttp.TCPConnector(limit=200, keepalive_timeout=30),
    )
    logger.info("Order Service (JSON-RPC) starting up...")


async def close_session(app: web.Application):
    global session
    if session:
        await session.close()
    logger.info("Order Service (JSON-RPC) shut down")


@method
async def create_order(customer_id: str, items: list, shipping_address: str) -> Result:
    """
    JSON-RPC method to create an order.

    Args:
        customer_id: Customer identifier
        items: List of order items
        shipping_address: Delivery address

    Returns:
        Result with order details
    """
    start_time = time.perf_counter()

    REQUEST_COUNT.labels(
        protocol="jsonrpc", service="order", method="create_order"
    ).inc()

    try:
        order_items = [
            OrderItem(
                product_id=item["product_id"],
                product_name=item["product_name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
            )
            for item in items
        ]

        order_create = OrderCreate(
            customer_id=customer_id,
            items=order_items,
            shipping_address=shipping_address,
        )

        order = Order.from_create(order_create)
        logger.info(f"Created order: {order.order_id}")

        payment_request = request(
            "process_payment",
            params={
                "order_id": order.order_id,
                "amount": order.total_amount,
                "currency": "USD",
                "payment_method": PaymentMethod.CREDIT_CARD.value,
            },
        )

        async with session.post(
            settings.PAYMENT_SERVICE_JSONRPC_URL,
            json=payment_request,
            headers={"Content-Type": "application/json"},
        ) as response:
            response_text = await response.text()
            parsed = parse(json.loads(response_text))

            if isinstance(parsed, Ok):
                payment_result = parsed.result
            else:
                ERROR_COUNT.labels(
                    protocol="jsonrpc", service="order", error_type="payment_failed"
                ).inc()
                return Error(code=-32000, message="Payment failed")

        end_time = time.perf_counter()
        processing_time = (end_time - start_time) * 1000

        REQUEST_LATENCY.labels(
            protocol="jsonrpc", service="order", method="create_order"
        ).observe(processing_time / 1000)

        return Success(
            {
                "order": order.model_dump(mode="json"),
                "payment": payment_result.get("payment"),
                "notification": payment_result.get("notification"),
                "processing_time_ms": processing_time,
            }
        )

    except Exception as e:
        ERROR_COUNT.labels(
            protocol="jsonrpc", service="order", error_type="internal_error"
        ).inc()
        logger.error(f"Internal error: {e}")
        return Error(code=-32000, message=str(e))


async def handle_jsonrpc(request: web.Request) -> web.Response:
    """Handle JSON-RPC requests."""
    body = await request.text()

    PAYLOAD_SIZE.labels(
        protocol="jsonrpc", service="order", direction="request"
    ).observe(len(body))

    response = await async_dispatch(body)

    PAYLOAD_SIZE.labels(
        protocol="jsonrpc", service="order", direction="response"
    ).observe(len(response))

    return web.Response(text=response, content_type="application/json")


async def health_check(request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy", "service": "order-jsonrpc"})


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
