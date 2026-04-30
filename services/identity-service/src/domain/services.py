"""
Domain services for Identity Service.
Business logic for user management and authentication.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.security import (
    get_password_hash,
    verify_password,
    create_access_token
)
from common.exceptions import (
    NotFoundException,
    ValidationException,
    UnauthorizedException,
    ConflictException
)
from common.logging import get_logger

from src.domain.entities import User, Patient, Doctor, UserRole
from src.domain.repositories import UserRepository, PatientRepository, DoctorRepository


logger = get_logger(__name__)


class AuthService:
    """Authentication and authorization service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register_patient(
        self,
        username: str,
        email: str,
        password: str,
        dni: str,
        first_name: str,
        last_name: str,
        date_of_birth,
        phone: Optional[str] = None,
        address: Optional[str] = None
    ) -> Tuple[User, Patient, str]:
        """
        Register a new patient and return user with token.

        Raises:
            ConflictException: If username, email, or DNI already exists
        """
        # Check for existing user
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            raise ConflictException(f"Email '{email}' is already registered")

        existing_username = await self.user_repo.get_by_username(username)
        if existing_username:
            raise ConflictException(f"Username '{username}' is already taken")

        # Create user
        password_hash = get_password_hash(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role=UserRole.PATIENT,
            is_active=True
        )
        self.db.add(user)
        await self.db.flush()

        # Create patient profile
        patient = Patient(
            user_id=user.id,
            dni=dni,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            phone=phone,
            address=address
        )
        self.db.add(patient)
        await self.db.flush()

        # Generate token
        token = create_access_token(user.id, user.role)

        logger.info(
            f"Patient registered: {patient.id}",
            extra={"user_id": user.id, "patient_id": patient.id}
        )

        return user, patient, token

    async def register_doctor(
        self,
        username: str,
        email: str,
        password: str,
        dni: str,
        first_name: str,
        last_name: str,
        license_number: str,
        specialty: str,
        phone: Optional[str] = None,
        consultation_fee: Optional[str] = None
    ) -> Tuple[User, Doctor, str]:
        """
        Register a new doctor and return user with token.

        Raises:
            ConflictException: If username, email, or license already exists
        """
        # Check for existing user
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            raise ConflictException(f"Email '{email}' is already registered")

        existing_username = await self.user_repo.get_by_username(username)
        if existing_username:
            raise ConflictException(f"Username '{username}' is already taken")

        # Create user
        password_hash = get_password_hash(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role=UserRole.MEDIC,
            is_active=True
        )
        self.db.add(user)
        await self.db.flush()

        # Create doctor profile
        doctor = Doctor(
            user_id=user.id,
            dni=dni,
            first_name=first_name,
            last_name=last_name,
            license_number=license_number,
            specialty=specialty,
            phone=phone,
            consultation_fee=consultation_fee
        )
        self.db.add(doctor)
        await self.db.flush()

        # Generate token
        token = create_access_token(user.id, user.role)

        logger.info(
            f"Doctor registered: {doctor.id}",
            extra={"user_id": user.id, "doctor_id": doctor.id}
        )

        return user, doctor, token

    async def login(self, username: str, password: str) -> Tuple[User, str]:
        """
        Authenticate user and return token.

        Raises:
            UnauthorizedException: If credentials are invalid
        """
        user = await self.user_repo.get_by_username(username)
        if not user:
            raise UnauthorizedException("Invalid username or password")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid username or password")

        if not user.is_active:
            raise UnauthorizedException("Account is deactivated")

        token = create_access_token(user.id, user.role)

        logger.info(
            f"User logged in: {user.id}",
            extra={"user_id": user.id, "role": user.role}
        )

        return user, token

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return await self.user_repo.get_by_id(user_id)


class UserService:
    """User management service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.patient_repo = PatientRepository(db)
        self.doctor_repo = DoctorRepository(db)

    async def update_patient_profile(
        self,
        user_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        emergency_contact: Optional[str] = None,
        emergency_phone: Optional[str] = None,
        blood_type: Optional[str] = None,
        allergies: Optional[str] = None
    ) -> Patient:
        """Update patient profile."""
        patient = await self.patient_repo.get_by_user_id(user_id)
        if not patient:
            raise NotFoundException("Patient", user_id)

        if first_name:
            patient.first_name = first_name
        if last_name:
            patient.last_name = last_name
        if phone:
            patient.phone = phone
        if address:
            patient.address = address
        if emergency_contact:
            patient.emergency_contact = emergency_contact
        if emergency_phone:
            patient.emergency_phone = emergency_phone
        if blood_type:
            patient.blood_type = blood_type
        if allergies:
            patient.allergies = allergies

        patient.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info(f"Patient profile updated: {patient.id}")

        return patient

    async def update_doctor_profile(
        self,
        user_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        specialty: Optional[str] = None,
        sub_specialty: Optional[str] = None,
        consultation_fee: Optional[str] = None
    ) -> Doctor:
        """Update doctor profile."""
        doctor = await self.doctor_repo.get_by_user_id(user_id)
        if not doctor:
            raise NotFoundException("Doctor", user_id)

        if first_name:
            doctor.first_name = first_name
        if last_name:
            doctor.last_name = last_name
        if phone:
            doctor.phone = phone
        if specialty:
            doctor.specialty = specialty
        if sub_specialty:
            doctor.sub_specialty = sub_specialty
        if consultation_fee:
            doctor.consultation_fee = consultation_fee

        doctor.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info(f"Doctor profile updated: {doctor.id}")

        return doctor

    async def get_patient_by_id(self, patient_id: UUID) -> Optional[Patient]:
        """Get patient by ID."""
        return await self.patient_repo.get_by_id(patient_id)

    async def get_doctor_by_id(self, doctor_id: UUID) -> Optional[Doctor]:
        """Get doctor by ID."""
        return await self.doctor_repo.get_by_id(doctor_id)

    async def get_doctors_by_specialty(self, specialty: str) -> list[Doctor]:
        """Get doctors by specialty."""
        return await self.doctor_repo.get_by_specialty(specialty)

    async def search_patients(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[list[Patient], int]:
        """Search patients by name or DNI."""
        return await self.patient_repo.search(query, page, page_size)
