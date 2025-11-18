import json
import logging
from typing import Any

import aiohttp
from jsonrpcclient import parse, request
from jsonrpcclient.responses import Ok

logger = logging.getLogger(__name__)


class JsonRpcClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        """
        Initialize JSON-RPC client.

        Args:
            base_url: Base URL for the JSON-RPC server
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=aiohttp.TCPConnector(limit=100, keepalive_timeout=30),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def call(self, method: str, **params) -> Any:
        """
        Make a JSON-RPC call.

        Args:
            method: RPC method name
            **params: Method parameters

        Returns:
            Result from the RPC call

        Raises:
            JsonRpcError: If the RPC call fails
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Use async with context.")

        rpc_request = request(method, params=params)

        async with self._session.post(
            self.base_url,
            json=rpc_request,
            headers={"Content-Type": "application/json"},
        ) as response:
            response_text = await response.text()
            parsed = parse(json.loads(response_text))

            if isinstance(parsed, Ok):
                return parsed.result
            else:
                error_msg = getattr(parsed, "message", "Unknown error")
                error_code = getattr(parsed, "code", -1)
                raise JsonRpcError(code=error_code, message=error_msg)


class JsonRpcError(Exception):
    """Exception raised when JSON-RPC call fails."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"JSON-RPC Error {code}: {message}")


async def create_order(
    client: JsonRpcClient,
    customer_id: str,
    items: list[dict],
    shipping_address: str,
) -> dict:
    """
    Create an order via JSON-RPC.

    Args:
        client: JSON-RPC client
        customer_id: Customer identifier
        items: List of order items
        shipping_address: Delivery address

    Returns:
        Order response with payment and notification details
    """
    return await client.call(
        "create_order",
        customer_id=customer_id,
        items=items,
        shipping_address=shipping_address,
    )


async def process_payment(
    client: JsonRpcClient,
    order_id: str,
    amount: float,
    currency: str = "USD",
    payment_method: str = "credit_card",
) -> dict:
    """
    Process a payment via JSON-RPC.

    Args:
        client: JSON-RPC client
        order_id: Order ID
        amount: Payment amount
        currency: Currency code
        payment_method: Payment method

    Returns:
        Payment response with notification details
    """
    return await client.call(
        "process_payment",
        order_id=order_id,
        amount=amount,
        currency=currency,
        payment_method=payment_method,
    )


async def send_notification(
    client: JsonRpcClient,
    order_id: str,
    payment_id: str,
    recipient: str,
    notification_type: str = "email",
) -> dict:
    """
    Send a notification via JSON-RPC.

    Args:
        client: JSON-RPC client
        order_id: Order ID
        payment_id: Payment ID
        recipient: Recipient email/phone
        notification_type: Type of notification

    Returns:
        Notification response
    """
    return await client.call(
        "send_notification",
        order_id=order_id,
        payment_id=payment_id,
        recipient=recipient,
        notification_type=notification_type,
    )
