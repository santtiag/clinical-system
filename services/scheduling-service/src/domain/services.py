"""
Scheduling Service domain services.
"""

from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import NotFoundException, ValidationException, ConflictException
from common.logging import get_logger
from common.messaging import get_message_publisher

from src.domain.entities import Appointment, AppointmentStatus, AppointmentHistory


logger = get_logger(__name__)


class AppointmentService:
    """Service for managing appointments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_appointment(
        self,
        patient_id: UUID,
        doctor_id: UUID,
        scheduled_date: datetime,
        duration_minutes: int = 30,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> Appointment:
        """Create a new appointment."""
        # Check for conflicts
        conflict = await self._check_conflict(doctor_id, scheduled_date, duration_minutes)
        if conflict:
            raise ConflictException(
                f"Time slot not available. Doctor has an appointment from "
                f"{conflict.scheduled_date} to {conflict.scheduled_date}"
            )

        # Create appointment
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            scheduled_date=scheduled_date,
            duration_minutes=duration_minutes,
            status=AppointmentStatus.SCHEDULED,
            reason=reason,
            notes=notes
        )
        self.db.add(appointment)
        await self.db.flush()
        await self.db.refresh(appointment)

        # Record history
        await self._record_history(
            appointment.id,
            created_by or patient_id,
            "created",
            None,
            {"status": AppointmentStatus.SCHEDULED.value, "scheduled_date": str(scheduled_date)}
        )

        # Publish event
        try:
            publisher = await get_message_publisher()
            await publisher.publish_appointment_scheduled(
                appointment_id=str(appointment.id),
                patient_id=str(patient_id),
                doctor_id=str(doctor_id),
                scheduled_time=scheduled_date.isoformat()
            )
        except Exception as e:
            logger.warning(f"Failed to publish appointment event: {e}")

        logger.info(f"Appointment created: {appointment.id}")
        return appointment

    async def _check_conflict(
        self,
        doctor_id: UUID,
        scheduled_date: datetime,
        duration_minutes: int
    ) -> Optional[Appointment]:
        """Check if there's a scheduling conflict."""
        from datetime import timedelta
        end_time = scheduled_date + timedelta(minutes=duration_minutes)

        result = await self.db.execute(
            select(Appointment).where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
                    or_(
                        # New appointment starts during existing
                        and_(
                            Appointment.scheduled_date <= scheduled_date,
                            func.datetime(Appointment.scheduled_date) + func.interval(f'{Appointment.duration_minutes} minutes') > scheduled_date
                        ),
                        # Existing appointment starts during new
                        and_(
                            Appointment.scheduled_date < end_time,
                            Appointment.scheduled_date + func.interval(f'{Appointment.duration_minutes} minutes') > end_time
                        )
                    )
                )
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_appointment(self, appointment_id: UUID) -> Optional[Appointment]:
        """Get appointment by ID."""
        result = await self.db.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        return result.scalar_one_or_none()

    async def get_patient_appointments(
        self,
        patient_id: UUID,
        status: Optional[AppointmentStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Appointment], int]:
        """Get appointments for a patient."""
        offset = (page - 1) * page_size

        query = select(Appointment).where(Appointment.patient_id == patient_id)
        if status:
            query = query.where(Appointment.status == status)

        count_result = await self.db.execute(select(func.count(Appointment.id)).where(Appointment.patient_id == patient_id))
        total = count_result.scalar()

        result = await self.db.execute(
            query.order_by(Appointment.scheduled_date.desc())
            .offset(offset).limit(page_size)
        )
        appointments = list(result.scalars().all())

        return appointments, total

    async def get_doctor_appointments(
        self,
        doctor_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[AppointmentStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Appointment], int]:
        """Get appointments for a doctor."""
        offset = (page - 1) * page_size

        query = select(Appointment).where(Appointment.doctor_id == doctor_id)

        if date_from:
            query = query.where(Appointment.scheduled_date >= date_from)
        if date_to:
            query = query.where(Appointment.scheduled_date <= date_to)
        if status:
            query = query.where(Appointment.status == status)

        count_result = await self.db.execute(select(func.count(Appointment.id)).where(Appointment.doctor_id == doctor_id))
        total = count_result.scalar()

        result = await self.db.execute(
            query.order_by(Appointment.scheduled_date)
            .offset(offset).limit(page_size)
        )
        appointments = list(result.scalars().all())

        return appointments, total

    async def confirm_appointment(self, appointment_id: UUID, confirmed_by: UUID) -> Appointment:
        """Confirm an appointment."""
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            raise NotFoundException("Appointment", appointment_id)

        if appointment.status != AppointmentStatus.SCHEDULED:
            raise ValidationException(f"Cannot confirm appointment with status '{appointment.status.value}'")

        old_status = appointment.status
        appointment.status = AppointmentStatus.CONFIRMED
        appointment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self._record_history(
            appointment_id, confirmed_by, "status_change",
            {"status": old_status.value},
            {"status": AppointmentStatus.CONFIRMED.value}
        )

        logger.info(f"Appointment confirmed: {appointment_id}")
        return appointment

    async def cancel_appointment(
        self,
        appointment_id: UUID,
        cancelled_by: UUID,
        reason: Optional[str] = None
    ) -> Appointment:
        """Cancel an appointment."""
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            raise NotFoundException("Appointment", appointment_id)

        if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
            raise ValidationException(f"Cannot cancel appointment with status '{appointment.status.value}'")

        old_status = appointment.status
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_at = datetime.now(timezone.utc)
        appointment.cancelled_by = cancelled_by
        appointment.cancellation_reason = reason
        appointment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self._record_history(
            appointment_id, cancelled_by, "cancelled",
            {"status": old_status.value},
            {"status": AppointmentStatus.CANCELLED.value, "reason": reason}
        )

        # Publish event
        try:
            publisher = await get_message_publisher()
            await publisher.publish(
                EventType=type("EventType", (), {"value": "appointment.cancelled"})(),
                data={"appointment_id": str(appointment_id), "patient_id": str(appointment.patient_id)}
            )
        except Exception as e:
            logger.warning(f"Failed to publish cancellation event: {e}")

        logger.info(f"Appointment cancelled: {appointment_id}")
        return appointment

    async def reschedule_appointment(
        self,
        appointment_id: UUID,
        new_scheduled_date: datetime,
        rescheduled_by: UUID
    ) -> Appointment:
        """Reschedule an appointment."""
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            raise NotFoundException("Appointment", appointment_id)

        if appointment.status not in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]:
            raise ValidationException(f"Cannot reschedule appointment with status '{appointment.status.value}'")

        # Check for conflicts at new time
        conflict = await self._check_conflict(appointment.doctor_id, new_scheduled_date, appointment.duration_minutes)
        if conflict and conflict.id != appointment_id:
            raise ConflictException("New time slot is not available")

        old_date = appointment.scheduled_date
        appointment.scheduled_date = new_scheduled_date
        appointment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self._record_history(
            appointment_id, rescheduled_by, "rescheduled",
            {"scheduled_date": str(old_date)},
            {"scheduled_date": str(new_scheduled_date)}
        )

        logger.info(f"Appointment rescheduled: {appointment_id} from {old_date} to {new_scheduled_date}")
        return appointment

    async def complete_appointment(self, appointment_id: UUID, completed_by: UUID, notes: Optional[str] = None) -> Appointment:
        """Mark appointment as completed."""
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            raise NotFoundException("Appointment", appointment_id)

        if appointment.status != AppointmentStatus.IN_PROGRESS:
            raise ValidationException(f"Cannot complete appointment with status '{appointment.status.value}'")

        old_status = appointment.status
        appointment.status = AppointmentStatus.COMPLETED
        if notes:
            appointment.notes = notes
        appointment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self._record_history(
            appointment_id, completed_by, "completed",
            {"status": old_status.value},
            {"status": AppointmentStatus.COMPLETED.value}
        )

        # Publish event for billing
        try:
            publisher = await get_message_publisher()
            from common.messaging import EventType
            await publisher.publish(
                EventType.APPOINTMENT_COMPLETED,
                {
                    "appointment_id": str(appointment_id),
                    "patient_id": str(appointment.patient_id),
                    "doctor_id": str(appointment.doctor_id)
                }
            )
        except Exception as e:
            logger.warning(f"Failed to publish completion event: {e}")

        logger.info(f"Appointment completed: {appointment_id}")
        return appointment

    async def start_appointment(self, appointment_id: UUID, started_by: UUID) -> Appointment:
        """Mark appointment as in progress."""
        appointment = await self.get_appointment(appointment_id)
        if not appointment:
            raise NotFoundException("Appointment", appointment_id)

        if appointment.status != AppointmentStatus.CONFIRMED:
            raise ValidationException(f"Cannot start appointment with status '{appointment.status.value}'")

        old_status = appointment.status
        appointment.status = AppointmentStatus.IN_PROGRESS
        appointment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        await self._record_history(
            appointment_id, started_by, "status_change",
            {"status": old_status.value},
            {"status": AppointmentStatus.IN_PROGRESS.value}
        )

        logger.info(f"Appointment started: {appointment_id}")
        return appointment

    async def _record_history(
        self,
        appointment_id: UUID,
        changed_by: UUID,
        change_type: str,
        old_values: Optional[dict],
        new_values: Optional[dict]
    ):
        """Record appointment history."""
        import json
        history = AppointmentHistory(
            appointment_id=appointment_id,
            changed_by=changed_by,
            change_type=change_type,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None
        )
        self.db.add(history)
        await self.db.flush()
