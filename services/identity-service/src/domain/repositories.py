"""
Repository pattern implementations for data access.
Provides abstraction layer between domain and database.
"""

from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities import User, Patient, Doctor, DoctorAvailability, UserRole


class UserRepository:
    """Repository for User entity."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Create a new user."""
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """Update an existing user."""
        await self.db.flush()
        await self.db.refresh(user)
        return user


class PatientRepository:
    """Repository for Patient entity."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, patient_id: UUID) -> Optional[Patient]:
        """Get patient by ID with user relationship."""
        result = await self.db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.id == patient_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> Optional[Patient]:
        """Get patient by user ID."""
        result = await self.db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_dni(self, dni: str) -> Optional[Patient]:
        """Get patient by DNI."""
        result = await self.db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.dni == dni)
        )
        return result.scalar_one_or_none()

    async def create(self, patient: Patient) -> Patient:
        """Create a new patient."""
        self.db.add(patient)
        await self.db.flush()
        await self.db.refresh(patient)
        return patient

    async def update(self, patient: Patient) -> Patient:
        """Update an existing patient."""
        await self.db.flush()
        await self.db.refresh(patient)
        return patient

    async def search(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Patient], int]:
        """Search patients by name or DNI."""
        offset = (page - 1) * page_size

        # Search query
        search_filter = or_(
            Patient.dni.ilike(f"%{query}%"),
            Patient.first_name.ilike(f"%{query}%"),
            Patient.last_name.ilike(f"%{query}%")
        )

        # Count total
        count_result = await self.db.execute(
            select(func.count(Patient.id)).where(search_filter)
        )
        total = count_result.scalar()

        # Fetch page
        result = await self.db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(search_filter)
            .offset(offset)
            .limit(page_size)
        )
        patients = list(result.scalars().all())

        return patients, total


class DoctorRepository:
    """Repository for Doctor entity."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, doctor_id: UUID) -> Optional[Doctor]:
        """Get doctor by ID with user relationship."""
        result = await self.db.execute(
            select(Doctor)
            .options(selectinload(Doctor.user))
            .where(Doctor.id == doctor_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> Optional[Doctor]:
        """Get doctor by user ID."""
        result = await self.db.execute(
            select(Doctor)
            .options(selectinload(Doctor.user))
            .where(Doctor.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_license(self, license_number: str) -> Optional[Doctor]:
        """Get doctor by license number."""
        result = await self.db.execute(
            select(Doctor)
            .options(selectinload(Doctor.user))
            .where(Doctor.license_number == license_number)
        )
        return result.scalar_one_or_none()

    async def get_by_specialty(self, specialty: str) -> List[Doctor]:
        """Get doctors by specialty."""
        result = await self.db.execute(
            select(Doctor)
            .options(selectinload(Doctor.user))
            .where(Doctor.specialty == specialty)
            .where(Doctor.is_active == True)
        )
        return list(result.scalars().all())

    async def get_all_active(self) -> List[Doctor]:
        """Get all active doctors."""
        result = await self.db.execute(
            select(Doctor)
            .options(selectinload(Doctor.user))
            .where(Doctor.is_active == True)
        )
        return list(result.scalars().all())

    async def create(self, doctor: Doctor) -> Doctor:
        """Create a new doctor."""
        self.db.add(doctor)
        await self.db.flush()
        await self.db.refresh(doctor)
        return doctor

    async def update(self, doctor: Doctor) -> Doctor:
        """Update an existing doctor."""
        await self.db.flush()
        await self.db.refresh(doctor)
        return doctor


class DoctorAvailabilityRepository:
    """Repository for DoctorAvailability entity."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_doctor(self, doctor_id: UUID) -> List[DoctorAvailability]:
        """Get availability schedule for a doctor."""
        result = await self.db.execute(
            select(DoctorAvailability)
            .where(DoctorAvailability.doctor_id == doctor_id)
            .where(DoctorAvailability.is_active == True)
            .order_by(DoctorAvailability.day_of_week)
        )
        return list(result.scalars().all())

    async def create(self, availability: DoctorAvailability) -> DoctorAvailability:
        """Create new availability slot."""
        self.db.add(availability)
        await self.db.flush()
        await self.db.refresh(availability)
        return availability
