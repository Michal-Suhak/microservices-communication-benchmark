import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from common.config import settings
from common.metrics import ERROR_COUNT, PAYLOAD_SIZE, REQUEST_COUNT, REQUEST_LATENCY
from common.models import (
    NotificationRequest,
    NotificationType,
    Payment,
    PaymentRequest,
    PaymentStatus,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Payment Service (REST) starting up...")
    app.state.http_client = httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_keepalive_connections=100, max_connections=200),
    )
    yield
    await app.state.http_client.aclose()
    logger.info("Payment Service (REST) shut down")


app = FastAPI(
    title="Payment Service - REST",
    description="Payment processing service using REST API",
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
    return {"status": "healthy", "service": "payment-rest"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


async def simulate_payment_processing():
    """Simulate payment gateway processing time."""
    await asyncio.sleep(0.01)


@app.post("/payments")
async def process_payment(payment_request: PaymentRequest, request: Request):
    """
    Process payment and trigger notification.

    Flow:
    1. Validate payment request
    2. Process payment (simulate)
    3. Call Notification Service
    4. Return payment result
    """
    start_time = time.perf_counter()

    REQUEST_COUNT.labels(
        protocol="rest", service="payment", method="process_payment"
    ).inc()

    try:
        request_body = await request.body()
        PAYLOAD_SIZE.labels(
            protocol="rest", service="payment", direction="request"
        ).observe(len(request_body))

        payment = Payment(
            order_id=payment_request.order_id,
            amount=payment_request.amount,
            currency=payment_request.currency,
            payment_method=payment_request.payment_method,
            status=PaymentStatus.PROCESSING,
            transaction_id=f"txn_{uuid.uuid4().hex[:12]}",
        )

        await simulate_payment_processing()

        payment.status = PaymentStatus.COMPLETED
        payment.processed_at = datetime.utcnow()

        notification_request = NotificationRequest(
            order_id=payment.order_id,
            payment_id=payment.payment_id,
            recipient="customer@example.com",
            notification_type=NotificationType.EMAIL,
        )

        notification_response = await request.app.state.http_client.post(
            f"{settings.NOTIFICATION_SERVICE_URL}/notifications",
            json=notification_request.model_dump(mode="json"),
        )

        notification_data = None
        if notification_response.status_code == 200:
            notification_data = notification_response.json().get("notification")

        end_time = time.perf_counter()
        processing_time = (end_time - start_time) * 1000

        REQUEST_LATENCY.labels(
            protocol="rest", service="payment", method="process_payment"
        ).observe(processing_time / 1000)

        return {
            "success": True,
            "payment": payment.model_dump(mode="json"),
            "notification": notification_data,
            "processing_time_ms": processing_time,
        }

    except httpx.RequestError as e:
        ERROR_COUNT.labels(
            protocol="rest", service="payment", error_type="connection_error"
        ).inc()
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}") from e

    except Exception as e:
        ERROR_COUNT.labels(
            protocol="rest", service="payment", error_type="internal_error"
        ).inc()
        logger.error(f"Internal error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "payment_service:app",
        host="0.0.0.0",
        port=8002,
        workers=4,
        log_level="info",
    )
