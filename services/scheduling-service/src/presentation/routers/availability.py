"""
Availability routers - simplified placeholder.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class AvailabilityResponse(BaseModel):
    doctor_id: str
    day_of_week: str
    start_time: str
    end_time: str


@router.get("/doctor/{doctor_id}", response_model=list[AvailabilityResponse])
async def get_doctor_availability(
    doctor_id: str,
    day_of_week: Optional[str] = Query(None)
):
    """Get doctor availability (simplified - calls identity service in real impl)."""
    # In a full implementation, this would call the identity service
    # to get the doctor's configured availability
    return []


@router.get("/slots")
async def get_available_slots(
    doctor_id: str,
    date: str,
    duration: int = Query(30)
):
    """Get available time slots for a doctor on a specific date."""
    # Simplified implementation
    return {"slots": []}
