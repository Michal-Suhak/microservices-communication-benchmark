import asyncio
import logging
import time
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from common.metrics import ERROR_COUNT, REQUEST_COUNT, REQUEST_LATENCY
from common.models import Notification, NotificationRequest, NotificationStatus

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Notification Service - REST",
    description="Notification service using REST API",
    version="1.0.0",
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
    return {"status": "healthy", "service": "notification-rest"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


async def simulate_notification_sending(notification: Notification):
    """Simulate sending email/SMS."""
    await asyncio.sleep(0.005)


@app.post("/notifications")
async def send_notification(notification_request: NotificationRequest):
    """
    Send notification to customer.

    Flow:
    1. Create notification record
    2. Send notification (simulate)
    3. Return result
    """
    start_time = time.perf_counter()

    REQUEST_COUNT.labels(
        protocol="rest", service="notification", method="send_notification"
    ).inc()

    try:
        notification = Notification(
            order_id=notification_request.order_id,
            payment_id=notification_request.payment_id,
            recipient=notification_request.recipient,
            notification_type=notification_request.notification_type,
            message=(
                f"Your order {notification_request.order_id} has been confirmed. "
                f"Payment {notification_request.payment_id} processed successfully."
            ),
            status=NotificationStatus.PENDING,
        )

        await simulate_notification_sending(notification)

        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.utcnow()

        end_time = time.perf_counter()
        processing_time = (end_time - start_time) * 1000

        REQUEST_LATENCY.labels(
            protocol="rest", service="notification", method="send_notification"
        ).observe(processing_time / 1000)

        return {
            "success": True,
            "notification": notification.model_dump(mode="json"),
            "processing_time_ms": processing_time,
        }

    except Exception as e:
        ERROR_COUNT.labels(
            protocol="rest", service="notification", error_type="internal_error"
        ).inc()
        logger.error(f"Internal error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "notification_service:app",
        host="0.0.0.0",
        port=8003,
        workers=4,
        log_level="info",
    )
