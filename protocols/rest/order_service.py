import logging
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from common.config import settings
from common.metrics import ERROR_COUNT, PAYLOAD_SIZE, REQUEST_COUNT, REQUEST_LATENCY
from common.models import (
    Order,
    OrderCreate,
    OrderResponse,
    PaymentMethod,
    PaymentRequest,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Order Service (REST) starting up...")
    app.state.http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_keepalive_connections=100, max_connections=200),
    )
    yield
    await app.state.http_client.aclose()
    logger.info("Order Service (REST) shut down")


app = FastAPI(
    title="Order Service - REST",
    description="Order management service using REST API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "order-rest"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/orders", response_model=OrderResponse)
async def create_order(order_request: OrderCreate, request: Request):
    """
    Create a new order and process payment.

    Flow:
    1. Validate and create order
    2. Call Payment Service
    3. Return complete response
    """
    start_time = time.perf_counter()

    REQUEST_COUNT.labels(protocol="rest", service="order", method="create_order").inc()

    try:
        order = Order.from_create(order_request)
        logger.info(f"Created order: {order.order_id}")

        request_body = await request.body()
        PAYLOAD_SIZE.labels(
            protocol="rest", service="order", direction="request"
        ).observe(len(request_body))

        payment_request = PaymentRequest(
            order_id=order.order_id,
            amount=order.total_amount,
            currency="USD",
            payment_method=PaymentMethod.CREDIT_CARD,
        )

        payment_response = await request.app.state.http_client.post(
            f"{settings.PAYMENT_SERVICE_URL}/payments",
            json=payment_request.model_dump(mode="json"),
        )

        if payment_response.status_code != 200:
            raise HTTPException(
                status_code=payment_response.status_code,
                detail="Payment processing failed",
            )

        payment_data = payment_response.json()

        end_time = time.perf_counter()
        processing_time = (end_time - start_time) * 1000

        REQUEST_LATENCY.labels(
            protocol="rest", service="order", method="create_order"
        ).observe(processing_time / 1000)

        response = OrderResponse(
            success=True,
            order=order,
            payment=payment_data.get("payment"),
            notification=payment_data.get("notification"),
            total_processing_time_ms=processing_time,
        )

        response_json = response.model_dump_json()
        PAYLOAD_SIZE.labels(
            protocol="rest", service="order", direction="response"
        ).observe(len(response_json))

        return response

    except httpx.RequestError as e:
        ERROR_COUNT.labels(
            protocol="rest", service="order", error_type="connection_error"
        ).inc()
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}") from e

    except HTTPException:
        raise

    except Exception as e:
        ERROR_COUNT.labels(
            protocol="rest", service="order", error_type="internal_error"
        ).inc()
        logger.error(f"Internal error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "order_service:app",
        host="0.0.0.0",
        port=8001,
        workers=4,
        log_level="info",
    )
