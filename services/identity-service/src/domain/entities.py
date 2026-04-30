"""
Domain entities for Identity Service.
Defines the core business entities: User, Patient, Doctor.
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from sqlalchemy import (
    Column, String, Date, DateTime, Boolean, Enum as SQLEnum,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
import enum

from common.database import BaseModel


class UserRole(str, enum.Enum):
    """User roles in the system."""
    PATIENT = "patient"
    MEDIC = "medic"
    ADMIN = "admin"
    STAFF = "staff"


class Gender(str, enum.Enum):
    """Gender options."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


# SQLAlchemy Models
class User(BaseModel):
    """User authentication model."""
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.PATIENT)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="user", uselist=False)
    doctor = relationship("Doctor", back_populates="user", uselist=False)

    __table_args__ = (
        Index("ix_users_email_role", "email", "role"),
    )


class Patient(BaseModel):
    """Patient profile model."""
    __tablename__ = "patients"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    dni = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(SQLEnum(Gender), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    emergency_phone = Column(String(20), nullable=True)
    blood_type = Column(String(10), nullable=True)
    allergies = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="patient")
    medical_record = relationship("MedicalRecord", back_populates="patient", uselist=False)

    __table_args__ = (
        Index("ix_patients_dni", "dni"),
    )


class Doctor(BaseModel):
    """Doctor/Medical professional model."""
    __tablename__ = "doctors"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    dni = Column(String(20), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False, index=True)
    specialty = Column(String(100), nullable=False)
    sub_specialty = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    consultation_fee = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="doctor")
    availability = relationship("DoctorAvailability", back_populates="doctor")

    __table_args__ = (
        Index("ix_doctors_license", "license_number"),
        Index("ix_doctors_specialty", "specialty"),
    )


class DoctorAvailability(BaseModel):
    """Doctor availability schedule model."""
    __tablename__ = "doctor_availability"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    doctor_id = Column(PGUUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    day_of_week = Column(String(10), nullable=False)  # monday, tuesday, etc.
    start_time = Column(String(10), nullable=False)  # HH:MM format
    end_time = Column(String(10), nullable=False)  # HH:MM format
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    doctor = relationship("Doctor", back_populates="availability")


class MedicalRecord(BaseModel):
    """Medical record reference (linked to Medical Record Service)."""
    __tablename__ = "medical_records"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id = Column(PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, unique=True)
    record_number = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="medical_record")


# Pydantic Schemas for API
class UserBase:
    """Base user schema."""
    username: str
    email: str


class PatientBase:
    """Base patient schema."""
    dni: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Optional[Gender] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class DoctorBase:
    """Base doctor schema."""
    dni: str
    first_name: str
    last_name: str
    license_number: str
    specialty: str
    sub_specialty: Optional[str] = None
    phone: Optional[str] = None
    consultation_fee: Optional[str] = None
