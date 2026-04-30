"""
Audit Worker.
Consumes domain events from RabbitMQ and records audit logs.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import aio_pika
from aio_pika import IncomingMessage
from sqlalchemy import select, Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from common.config import settings
from common.logging import setup_logging
from common.database import BaseModel, AsyncSessionLocal


setup_logging()
logger = logging.getLogger(__name__)


class AuditLog(BaseModel):
    """Audit log entry model."""
    __tablename__ = "audit_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    service = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    action = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AuditWorker:
    """Worker that consumes events and records audit logs."""

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
            "audit_worker",
            durable=True
        )

        # Bind to all events for audit
        await self._queue.bind(exchange, routing_key="#")

        logger.info("Audit worker connected to RabbitMQ")

    async def _save_audit_log(
        self,
        event_type: str,
        service: str,
        data: dict,
        correlation_id: Optional[str] = None
    ):
        """Save audit log entry to database."""
        async with AsyncSessionLocal() as db:
            try:
                # Extract resource info from data
                resource_id = data.get("appointment_id") or data.get("patient_id") or data.get("invoice_id")
                resource_type = "appointment" if data.get("appointment_id") else "patient" if data.get("patient_id") else "invoice" if data.get("invoice_id") else None
                user_id = data.get("doctor_id") or data.get("patient_id")

                audit_log = AuditLog(
                    event_type=event_type,
                    service=service,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=str(resource_id) if resource_id else None,
                    action=self._action_from_event(event_type),
                    details=json.dumps(data),
                    correlation_id=correlation_id
                )
                db.add(audit_log)
                await db.commit()

                logger.info(
                    f"Audit log saved: {event_type}",
                    extra={"audit_id": str(audit_log.id)}
                )
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to save audit log: {e}")

    def _action_from_event(self, event_type: str) -> str:
        """Map event type to action name."""
        mapping = {
            "appointment.scheduled": "CREATE",
            "appointment.confirmed": "UPDATE",
            "appointment.completed": "COMPLETE",
            "appointment.cancelled": "DELETE",
            "appointment.rescheduled": "UPDATE",
            "clinical_note.created": "CREATE",
            "diagnosis.registered": "CREATE",
            "prescription.created": "CREATE",
            "invoice.generated": "CREATE",
            "payment.processed": "UPDATE",
            "payment.refunded": "UPDATE",
            "user.registered": "CREATE",
            "user.updated": "UPDATE",
        }
        return mapping.get(event_type, "UNKNOWN")

    async def process_message(self, message: IncomingMessage):
        """Process a domain event message for audit."""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                event_type = body.get("event_type")
                service = body.get("service")
                data = body.get("data", {})
                correlation_id = body.get("correlation_id")

                logger.info(
                    f"Audit event: {event_type}",
                    extra={"event_type": event_type, "correlation_id": correlation_id}
                )

                # Save to audit log
                await self._save_audit_log(
                    event_type=event_type,
                    service=service,
                    data=data,
                    correlation_id=correlation_id
                )

            except Exception as e:
                logger.error(f"Error processing audit message: {e}")
                raise

    async def start(self):
        """Start consuming messages."""
        if not self._queue:
            await self.connect()

        logger.info("Starting audit worker...")
        await self._queue.consume(self.process_message)

        # Keep the worker running
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            logger.info("Audit worker stopped")

    async def stop(self):
        """Stop the worker."""
        if self._connection:
            await self._connection.close()
            logger.info("Audit worker disconnected")


async def main():
    """Main entry point."""
    worker = AuditWorker()
    await worker.connect()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
