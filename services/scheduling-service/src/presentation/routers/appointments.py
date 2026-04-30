"""
Appointment routers.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from common.database import get_db
from common.security import decode_token
from common.exceptions import UnauthorizedException

from src.domain.services import AppointmentService
from src.domain.entities import AppointmentStatus


router = APIRouter()


class TokenData(BaseModel):
    user_id: str
    role: str


async def get_current_user(authorization: str = Query(...)):
    """Extract current user from JWT token."""
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise UnauthorizedException("Invalid scheme")
    except ValueError:
        raise UnauthorizedException("Invalid header")

    payload = decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid token")

    return TokenData(user_id=payload.user_id, role=payload.role)


# Request/Response schemas
class CreateAppointmentRequest(BaseModel):
    patient_id: str
    doctor_id: str
    scheduled_date: datetime
    duration_minutes: int = 30
    reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    scheduled_date: datetime
    duration_minutes: int
    status: str
    reason: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppointmentListResponse(BaseModel):
    items: list[AppointmentResponse]
    total: int
    page: int
    page_size: int


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    request: CreateAppointmentRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Create a new appointment."""
    service = AppointmentService(db)
    appointment = await service.create_appointment(
        patient_id=UUID(request.patient_id),
        doctor_id=UUID(request.doctor_id),
        scheduled_date=request.scheduled_date,
        duration_minutes=request.duration_minutes,
        reason=request.reason,
        notes=request.notes,
        created_by=UUID(current_user.user_id)
    )
    return AppointmentResponse(
        id=str(appointment.id),
        patient_id=str(appointment.patient_id),
        doctor_id=str(appointment.doctor_id),
        scheduled_date=appointment.scheduled_date,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status.value,
        reason=appointment.reason,
        notes=appointment.notes,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get appointment by ID."""
    service = AppointmentService(db)
    appointment = await service.get_appointment(appointment_id)
    if not appointment:
        from common.exceptions import NotFoundException
        raise NotFoundException("Appointment", appointment_id)
    return AppointmentResponse(
        id=str(appointment.id),
        patient_id=str(appointment.patient_id),
        doctor_id=str(appointment.doctor_id),
        scheduled_date=appointment.scheduled_date,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status.value,
        reason=appointment.reason,
        notes=appointment.notes,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )


@router.get("/patient/{patient_id}", response_model=AppointmentListResponse)
async def get_patient_appointments(
    patient_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get appointments for a patient."""
    service = AppointmentService(db)
    status_enum = AppointmentStatus(status_filter) if status_filter else None
    appointments, total = await service.get_patient_appointments(patient_id, status_enum, page, page_size)

    return AppointmentListResponse(
        items=[
            AppointmentResponse(
                id=str(a.id),
                patient_id=str(a.patient_id),
                doctor_id=str(a.doctor_id),
                scheduled_date=a.scheduled_date,
                duration_minutes=a.duration_minutes,
                status=a.status.value,
                reason=a.reason,
                notes=a.notes,
                created_at=a.created_at,
                updated_at=a.updated_at
            )
            for a in appointments
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/doctor/{doctor_id}", response_model=AppointmentListResponse)
async def get_doctor_appointments(
    doctor_id: UUID,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Get appointments for a doctor."""
    service = AppointmentService(db)
    status_enum = AppointmentStatus(status_filter) if status_filter else None
    appointments, total = await service.get_doctor_appointments(doctor_id, date_from, date_to, status_enum, page, page_size)

    return AppointmentListResponse(
        items=[
            AppointmentResponse(
                id=str(a.id),
                patient_id=str(a.patient_id),
                doctor_id=str(a.doctor_id),
                scheduled_date=a.scheduled_date,
                duration_minutes=a.duration_minutes,
                status=a.status.value,
                reason=a.reason,
                notes=a.notes,
                created_at=a.created_at,
                updated_at=a.updated_at
            )
            for a in appointments
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
async def confirm_appointment(
    appointment_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Confirm an appointment."""
    service = AppointmentService(db)
    appointment = await service.confirm_appointment(appointment_id, UUID(current_user.user_id))
    return AppointmentResponse(
        id=str(appointment.id),
        patient_id=str(appointment.patient_id),
        doctor_id=str(appointment.doctor_id),
        scheduled_date=appointment.scheduled_date,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status.value,
        reason=appointment.reason,
        notes=appointment.notes,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: UUID,
    reason: Optional[str] = Query(None),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Cancel an appointment."""
    service = AppointmentService(db)
    appointment = await service.cancel_appointment(appointment_id, UUID(current_user.user_id), reason)
    return AppointmentResponse(
        id=str(appointment.id),
        patient_id=str(appointment.patient_id),
        doctor_id=str(appointment.doctor_id),
        scheduled_date=appointment.scheduled_date,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status.value,
        reason=appointment.reason,
        notes=appointment.notes,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: UUID,
    new_date: datetime = Query(..., alias="newDate"),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Reschedule an appointment."""
    service = AppointmentService(db)
    appointment = await service.reschedule_appointment(appointment_id, new_date, UUID(current_user.user_id))
    return AppointmentResponse(
        id=str(appointment.id),
        patient_id=str(appointment.patient_id),
        doctor_id=str(appointment.doctor_id),
        scheduled_date=appointment.scheduled_date,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status.value,
        reason=appointment.reason,
        notes=appointment.notes,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )


@router.post("/{appointment_id}/start", response_model=AppointmentResponse)
async def start_appointment(
    appointment_id: UUID,
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Start (mark as in progress) an appointment."""
    service = AppointmentService(db)
    appointment = await service.start_appointment(appointment_id, UUID(current_user.user_id))
    return AppointmentResponse(
        id=str(appointment.id),
        patient_id=str(appointment.patient_id),
        doctor_id=str(appointment.doctor_id),
        scheduled_date=appointment.scheduled_date,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status.value,
        reason=appointment.reason,
        notes=appointment.notes,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: UUID,
    notes: Optional[str] = Query(None),
    db=Depends(get_db),
    current_user=Depends(get_current_user)
):
    """Complete an appointment."""
    service = AppointmentService(db)
    appointment = await service.complete_appointment(appointment_id, UUID(current_user.user_id), notes)
    return AppointmentResponse(
        id=str(appointment.id),
        patient_id=str(appointment.patient_id),
        doctor_id=str(appointment.doctor_id),
        scheduled_date=appointment.scheduled_date,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status.value,
        reason=appointment.reason,
        notes=appointment.notes,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )
