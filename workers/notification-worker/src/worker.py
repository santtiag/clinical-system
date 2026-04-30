"""
Notification Worker.
Consumes domain events from RabbitMQ and sends notifications.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import aio_pika
from aio_pika import IncomingMessage

from common.config import settings
from common.logging import setup_logging


setup_logging()
logger = logging.getLogger(__name__)


class NotificationWorker:
    """Worker that consumes events and sends notifications."""

    def __init__(self):
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._queue: Optional[aio_pika.Queue] = None

    async def connect(self):
        """Connect to RabbitMQ."""
        self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=10)

        # Declare exchange
        exchange = await self._channel.declare_exchange(
            settings.RABBITMQ_EXCHANGE,
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )

        # Declare queue
        self._queue = await self._channel.declare_queue(
            "notification_worker",
            durable=True
        )

        # Bind to relevant events
        await self._queue.bind(exchange, routing_key="appointment.*")
        await self._queue.bind(exchange, routing_key="payment.*")
        await self._queue.bind(exchange, routing_key="invoice.*")

        logger.info("Notification worker connected to RabbitMQ")

    async def process_message(self, message: IncomingMessage):
        """Process a domain event message."""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                event_type = body.get("event_type")
                data = body.get("data", {})
                timestamp = body.get("timestamp")

                logger.info(
                    f"Processing event: {event_type}",
                    extra={"event_type": event_type, "data": data}
                )

                # Handle different event types
                if event_type == "appointment.scheduled":
                    await self._send_appointment_confirmation(data)
                elif event_type == "appointment.cancelled":
                    await self._send_cancellation_notice(data)
                elif event_type == "appointment.completed":
                    await self._send_completion_notice(data)
                elif event_type == "payment.processed":
                    await self._send_payment_confirmation(data)
                elif event_type == "invoice.generated":
                    await self._send_invoice_notification(data)
                else:
                    logger.info(f"Unhandled event type: {event_type}")

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                raise

    async def _send_appointment_confirmation(self, data: dict):
        """Send appointment confirmation notification."""
        patient_id = data.get("patient_id")
        doctor_id = data.get("doctor_id")
        scheduled_time = data.get("scheduled_time")

        # In production, this would send email/SMS
        logger.info(
            f"Sending appointment confirmation to patient {patient_id}",
            extra={
                "notification_type": "appointment_confirmation",
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "scheduled_time": scheduled_time
            }
        )

    async def _send_cancellation_notice(self, data: dict):
        """Send appointment cancellation notification."""
        patient_id = data.get("patient_id")

        logger.info(
            f"Sending cancellation notice to patient {patient_id}",
            extra={"notification_type": "cancellation_notice", "patient_id": patient_id}
        )

    async def _send_completion_notice(self, data: dict):
        """Send appointment completion notification."""
        patient_id = data.get("patient_id")

        logger.info(
            f"Sending completion notice to patient {patient_id}",
            extra={"notification_type": "completion_notice", "patient_id": patient_id}
        )

    async def _send_payment_confirmation(self, data: dict):
        """Send payment confirmation notification."""
        patient_id = data.get("patient_id")
        amount = data.get("amount")

        logger.info(
            f"Sending payment confirmation to patient {patient_id}",
            extra={
                "notification_type": "payment_confirmation",
                "patient_id": patient_id,
                "amount": amount
            }
        )

    async def _send_invoice_notification(self, data: dict):
        """Send invoice notification."""
        patient_id = data.get("patient_id")
        invoice_id = data.get("invoice_id")
        amount = data.get("amount")

        logger.info(
            f"Sending invoice notification to patient {patient_id}",
            extra={
                "notification_type": "invoice_notification",
                "patient_id": patient_id,
                "invoice_id": invoice_id,
                "amount": amount
            }
        )

    async def start(self):
        """Start consuming messages."""
        if not self._queue:
            await self.connect()

        logger.info("Starting notification worker...")
        await self._queue.consume(self.process_message)

        # Keep the worker running
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            logger.info("Notification worker stopped")

    async def stop(self):
        """Stop the worker."""
        if self._connection:
            await self._connection.close()
            logger.info("Notification worker disconnected")


async def main():
    """Main entry point."""
    worker = NotificationWorker()
    await worker.connect()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
