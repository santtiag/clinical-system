"""
Domain entities for Scheduling Service.
"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional
from enum import Enum

from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum, ForeignKey, Index, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from common.database import BaseModel


class AppointmentStatus(str, Enum):
    """Appointment status enumeration."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Appointment(BaseModel):
    """Appointment model."""
    __tablename__ = "appointments"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    doctor_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    scheduled_date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    status = Column(SQLEnum(AppointmentStatus), nullable=False, default=AppointmentStatus.SCHEDULED)
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)
    cancelled_by = Column(PGUUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_appointments_patient_doctor", "patient_id", "doctor_id"),
        Index("ix_appointments_scheduled_date", "scheduled_date"),
        Index("ix_appointments_status", "status"),
    )


class AppointmentHistory(BaseModel):
    """Audit log for appointment changes."""
    __tablename__ = "appointment_history"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    appointment_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    changed_by = Column(PGUUID(as_uuid=True), nullable=False)
    change_type = Column(String(50), nullable=False)  # created, updated, cancelled, status_change
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
