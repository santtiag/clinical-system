"""
RabbitMQ message publisher and consumer utilities.
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Callable, Any
from enum import Enum

import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType

from common.config import settings
from common.logging import get_logger


logger = get_logger(__name__)


class EventType(str, Enum):
    """Domain events types."""
    # Appointment events
    APPOINTMENT_SCHEDULED = "appointment.scheduled"
    APPOINTMENT_CONFIRMED = "appointment.confirmed"
    APPOINTMENT_COMPLETED = "appointment.completed"
    APPOINTMENT_CANCELLED = "appointment.cancelled"
    APPOINTMENT_RESCHEDULED = "appointment.rescheduled"

    # Medical record events
    CLINICAL_NOTE_CREATED = "clinical_note.created"
    DIAGNOSIS_REGISTERED = "diagnosis.registered"
    PRESCRIPTION_CREATED = "prescription.created"
    DOCUMENT_ATTACHED = "document.attached"

    # Billing events
    INVOICE_GENERATED = "invoice.generated"
    PAYMENT_PROCESSED = "payment.processed"
    PAYMENT_REFUNDED = "payment.refunded"

    # User events
    USER_REGISTERED = "user.registered"
    USER_UPDATED = "user.updated"

    # Audit events
    AUDIT_LOG_CREATED = "audit_log.created"


class MessagePublisher:
    """
    RabbitMQ message publisher for domain events.
    Implements the publish-subscribe pattern for async service communication.
    """

    def __init__(self):
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.Channel] = None
        self._exchange: Optional[aio_pika.Exchange] = None
        self._connected = False

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        if self._connected:
            return

        try:
            self._connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                timeout=10
            )
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                ExchangeType.TOPIC,
                durable=True
            )
            self._connected = True
            logger.info("Connected to RabbitMQ", extra={"exchange": settings.RABBITMQ_EXCHANGE})
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        if self._connection:
            await self._connection.close()
            self._connected = False
            logger.info("Disconnected from RabbitMQ")

    async def publish(
        self,
        event_type: EventType,
        data: dict,
        correlation_id: Optional[str] = None
    ) -> None:
        """
        Publish a domain event.

        Args:
            event_type: Type of the event
            data: Event payload
            correlation_id: Optional correlation ID for tracing
        """
        if not self._connected:
            await self.connect()

        message_body = {
            "event_type": event_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": settings.SERVICE_NAME,
            "data": data,
            "correlation_id": correlation_id
        }

        message = Message(
            body=json.dumps(message_body).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
            correlation_id=correlation_id or ""
        )

        await self._exchange.publish(
            message,
            routing_key=event_type.value
        )

        logger.info(
            f"Published event: {event_type.value}",
            extra={"event_type": event_type.value, "data": data}
        )

    # Convenience methods for common events
    async def publish_appointment_scheduled(
        self,
        appointment_id: str,
        patient_id: str,
        doctor_id: str,
        scheduled_time: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish appointment scheduled event."""
        await self.publish(
            EventType.APPOINTMENT_SCHEDULED,
            {
                "appointment_id": appointment_id,
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "scheduled_time": scheduled_time
            },
            correlation_id
        )

    async def publish_appointment_completed(
        self,
        appointment_id: str,
        patient_id: str,
        doctor_id: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish appointment completed event."""
        await self.publish(
            EventType.APPOINTMENT_COMPLETED,
            {
                "appointment_id": appointment_id,
                "patient_id": patient_id,
                "doctor_id": doctor_id
            },
            correlation_id
        )

    async def publish_invoice_generated(
        self,
        invoice_id: str,
        patient_id: str,
        appointment_id: str,
        amount: float,
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish invoice generated event."""
        await self.publish(
            EventType.INVOICE_GENERATED,
            {
                "invoice_id": invoice_id,
                "patient_id": patient_id,
                "appointment_id": appointment_id,
                "amount": amount
            },
            correlation_id
        )

    async def publish_payment_processed(
        self,
        payment_id: str,
        invoice_id: str,
        amount: float,
        status: str,
        correlation_id: Optional[str] = None
    ) -> None:
        """Publish payment processed event."""
        await self.publish(
            EventType.PAYMENT_PROCESSED,
            {
                "payment_id": payment_id,
                "invoice_id": invoice_id,
                "amount": amount,
                "status": status
            },
            correlation_id
        )


# Global publisher instance
_publisher: Optional[MessagePublisher] = None


async def get_message_publisher() -> MessagePublisher:
    """Get or create the global message publisher."""
    global _publisher
    if _publisher is None:
        _publisher = MessagePublisher()
        await _publisher.connect()
    return _publisher


async def close_message_publisher() -> None:
    """Close the global message publisher."""
    global _publisher
    if _publisher:
        await _publisher.disconnect()
        _publisher = None