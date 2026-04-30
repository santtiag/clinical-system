"""
API Schemas (Pydantic models) for Identity Service.
Request and response models for the REST API.
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, ConfigDict

from common.schemas import BaseSchema


# ====================
# AUTH SCHEMAS
# ====================

class RegisterPatientRequest(BaseSchema):
    """Request to register a new patient."""
    username: str = Field(min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(description="Email address")
    password: str = Field(min_length=8, max_length=100, description="Password")
    dni: str = Field(min_length=1, max_length=20, description="Document ID")
    first_name: str = Field(min_length=1, max_length=100, description="First name")
    last_name: str = Field(min_length=1, max_length=100, description="Last name")
    date_of_birth: date = Field(description="Date of birth")
    gender: Optional[str] = Field(default=None, description="Gender: male, female, other")
    phone: Optional[str] = Field(default=None, max_length=20, description="Phone number")
    address: Optional[str] = Field(default=None, max_length=500, description="Address")


class RegisterDoctorRequest(BaseSchema):
    """Request to register a new doctor."""
    username: str = Field(min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(description="Email address")
    password: str = Field(min_length=8, max_length=100, description="Password")
    dni: str = Field(min_length=1, max_length=20, description="Document ID")
    first_name: str = Field(min_length=1, max_length=100, description="First name")
    last_name: str = Field(min_length=1, max_length=100, description="Last name")
    license_number: str = Field(min_length=1, max_length=50, description="Medical license number")
    specialty: str = Field(min_length=1, max_length=100, description="Medical specialty")
    sub_specialty: Optional[str] = Field(default=None, max_length=100, description="Sub-specialty")
    phone: Optional[str] = Field(default=None, max_length=20, description="Phone number")
    consultation_fee: Optional[str] = Field(default=None, description="Consultation fee")


class LoginRequest(BaseSchema):
    """Request to login."""
    username: str = Field(description="Username")
    password: str = Field(description="Password")


class TokenResponse(BaseSchema):
    """Authentication token response."""
    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration in seconds")
    user_id: str = Field(alias="userId", description="User ID")
    role: str = Field(description="User role")


class RegisterResponse(BaseSchema):
    """Registration response."""
    user_id: str = Field(alias="userId", description="User ID")
    patient_id: Optional[str] = Field(default=None, alias="patientId", description="Patient ID")
    doctor_id: Optional[str] = Field(default=None, alias="doctorId", description="Doctor ID")
    role: str = Field(description="User role")
    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


# ====================
# USER SCHEMAS
# ====================

class UserResponse(BaseSchema):
    """User response."""
    id: UUID
    username: str
    email: str
    role: str
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")


class PatientResponse(BaseSchema):
    """Patient response."""
    id: UUID
    user_id: UUID = Field(alias="userId")
    dni: str
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    date_of_birth: date = Field(alias="dateOfBirth")
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = Field(default=None, alias="emergencyContact")
    emergency_phone: Optional[str] = Field(default=None, alias="emergencyPhone")
    blood_type: Optional[str] = Field(default=None, alias="bloodType")
    allergies: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class DoctorResponse(BaseSchema):
    """Doctor response."""
    id: UUID
    user_id: UUID = Field(alias="userId")
    dni: str
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    license_number: str = Field(alias="licenseNumber")
    specialty: str
    sub_specialty: Optional[str] = Field(default=None, alias="subSpecialty")
    phone: Optional[str] = None
    consultation_fee: Optional[str] = Field(default=None, alias="consultationFee")
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class UpdatePatientRequest(BaseSchema):
    """Request to update patient profile."""
    first_name: Optional[str] = Field(default=None, max_length=100, alias="firstName")
    last_name: Optional[str] = Field(default=None, max_length=100, alias="lastName")
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=500)
    emergency_contact: Optional[str] = Field(default=None, max_length=100, alias="emergencyContact")
    emergency_phone: Optional[str] = Field(default=None, max_length=20, alias="emergencyPhone")
    blood_type: Optional[str] = Field(default=None, max_length=10, alias="bloodType")
    allergies: Optional[str] = Field(default=None, max_length=500)


class UpdateDoctorRequest(BaseSchema):
    """Request to update doctor profile."""
    first_name: Optional[str] = Field(default=None, max_length=100, alias="firstName")
    last_name: Optional[str] = Field(default=None, max_length=100, alias="lastName")
    phone: Optional[str] = Field(default=None, max_length=20)
    specialty: Optional[str] = Field(default=None, max_length=100)
    sub_specialty: Optional[str] = Field(default=None, max_length=100, alias="subSpecialty")
    consultation_fee: Optional[str] = Field(default=None, alias="consultationFee")


class DoctorAvailabilityResponse(BaseSchema):
    """Doctor availability response."""
    id: UUID
    doctor_id: UUID = Field(alias="doctorId")
    day_of_week: str = Field(alias="dayOfWeek")
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    is_active: bool = Field(alias="isActive")


class DoctorWithAvailability(DoctorResponse):
    """Doctor with availability schedule."""
    availability: List[DoctorAvailabilityResponse] = []


class PatientSearchResponse(BaseSchema):
    """Patient search response with pagination."""
    items: List[PatientResponse] = Field(description="List of patients")
    total: int = Field(description="Total number of patients")
    page: int = Field(description="Current page")
    page_size: int = Field(alias="pageSize", description="Items per page")
    total_pages: int = Field(alias="totalPages", description="Total pages")
