"""
User management routes.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, status, Query, Header
from fastapi.security import OAuth2PasswordBearer

from common.database import get_db
from common.security import decode_token
from common.exceptions import UnauthorizedException, ForbiddenException

from src.domain.services import UserService, AuthService
from src.domain.repositories import DoctorRepository
from src.presentation.schemas import (
    PatientResponse,
    DoctorResponse,
    DoctorWithAvailability,
    UpdatePatientRequest,
    UpdateDoctorRequest,
    PatientSearchResponse,
    DoctorAvailabilityResponse
)


router = APIRouter()


oauth2_scheme = OAuth2PasswordBearer(auto_error=False)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Dependency to get current authenticated user."""
    if not token:
        raise UnauthorizedException("Missing authentication")

    payload = decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    return payload


async def require_role(required_role: str):
    """Dependency factory to require specific role."""
    async def check_role(current_user=Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise ForbiddenException(f"Role '{required_role}' required")
        return current_user
    return check_role


@router.get(
    "/me",
    response_model=PatientResponse | DoctorResponse,
    summary="Get current user profile",
    description="Get the profile of the currently authenticated user"
)
async def get_my_profile(
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get the profile of the currently authenticated user.
    Returns patient profile for patients, doctor profile for doctors.
    """
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(UUID(current_user.user_id))

    if not user:
        raise UnauthorizedException("User not found")

    if user.role.value == "patient":
        user_service = UserService(db)
        patient = await user_service.get_patient_by_id(UUID(current_user.user_id))
        if patient:
            return PatientResponse(
                id=patient.id,
                userId=patient.user_id,
                dni=patient.dni,
                firstName=patient.first_name,
                lastName=patient.last_name,
                dateOfBirth=patient.date_of_birth,
                gender=patient.gender.value if patient.gender else None,
                phone=patient.phone,
                address=patient.address,
                emergencyContact=patient.emergency_contact,
                emergencyPhone=patient.emergency_phone,
                bloodType=patient.blood_type,
                allergies=patient.allergies,
                createdAt=patient.created_at,
                updatedAt=patient.updated_at
            )
    elif user.role.value == "medic":
        user_service = UserService(db)
        doctor = await user_service.get_doctor_by_id(UUID(current_user.user_id))
        if doctor:
            return DoctorResponse(
                id=doctor.id,
                userId=doctor.user_id,
                dni=doctor.dni,
                firstName=doctor.first_name,
                lastName=doctor.last_name,
                licenseNumber=doctor.license_number,
                specialty=doctor.specialty,
                subSpecialty=doctor.sub_specialty,
                phone=doctor.phone,
                consultationFee=doctor.consultation_fee,
                isActive=doctor.is_active,
                createdAt=doctor.created_at,
                updatedAt=doctor.updated_at
            )

    raise UnauthorizedException("Profile not found")


@router.put(
    "/me/patient",
    response_model=PatientResponse,
    summary="Update patient profile",
    description="Update the profile of the currently authenticated patient"
)
async def update_my_profile(
    request: UpdatePatientRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    """Update patient profile."""
    user_service = UserService(db)
    patient = await user_service.update_patient_profile(
        user_id=UUID(current_user.user_id),
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        address=request.address,
        emergency_contact=request.emergency_contact,
        emergency_phone=request.emergency_phone,
        blood_type=request.blood_type,
        allergies=request.allergies
    )

    return PatientResponse(
        id=patient.id,
        userId=patient.user_id,
        dni=patient.dni,
        firstName=patient.first_name,
        lastName=patient.last_name,
        dateOfBirth=patient.date_of_birth,
        gender=patient.gender.value if patient.gender else None,
        phone=patient.phone,
        address=patient.address,
        emergencyContact=patient.emergency_contact,
        emergencyPhone=patient.emergency_phone,
        bloodType=patient.blood_type,
        allergies=patient.allergies,
        createdAt=patient.created_at,
        updatedAt=patient.updated_at
    )


@router.put(
    "/me/doctor",
    response_model=DoctorResponse,
    summary="Update doctor profile",
    description="Update the profile of the currently authenticated doctor"
)
async def update_my_doctor_profile(
    request: UpdateDoctorRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    """Update doctor profile."""
    user_service = UserService(db)
    doctor = await user_service.update_doctor_profile(
        user_id=UUID(current_user.user_id),
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        specialty=request.specialty,
        sub_specialty=request.sub_specialty,
        consultation_fee=request.consultation_fee
    )

    return DoctorResponse(
        id=doctor.id,
        userId=doctor.user_id,
        dni=doctor.dni,
        firstName=doctor.first_name,
        lastName=doctor.last_name,
        licenseNumber=doctor.license_number,
        specialty=doctor.specialty,
        subSpecialty=doctor.sub_specialty,
        phone=doctor.phone,
        consultationFee=doctor.consultation_fee,
        isActive=doctor.is_active,
        createdAt=doctor.created_at,
        updatedAt=doctor.updated_at
    )


# Admin endpoints
@router.get(
    "/patients",
    response_model=PatientSearchResponse,
    summary="Search patients",
    description="Search patients by name or DNI (admin only)"
)
async def search_patients(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    admin=Depends(require_role("admin")),
    db=Depends(get_db)
):
    """Search patients by name or DNI."""
    user_service = UserService(db)
    patients, total = await user_service.search_patients(q, page, page_size)

    items = [
        PatientResponse(
            id=p.id,
            userId=p.user_id,
            dni=p.dni,
            firstName=p.first_name,
            lastName=p.last_name,
            dateOfBirth=p.date_of_birth,
            gender=p.gender.value if p.gender else None,
            phone=p.phone,
            address=p.address,
            emergencyContact=p.emergency_contact,
            emergencyPhone=p.emergency_phone,
            bloodType=p.blood_type,
            allergies=p.allergies,
            createdAt=p.created_at,
            updatedAt=p.updated_at
        )
        for p in patients
    ]

    total_pages = (total + page_size - 1) // page_size

    return PatientSearchResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
        totalPages=total_pages
    )


@router.get(
    "/doctors",
    response_model=list[DoctorWithAvailability],
    summary="List doctors",
    description="List all doctors, optionally filtered by specialty"
)
async def list_doctors(
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    admin=Depends(require_role("admin")),
    db=Depends(get_db)
):
    """List all doctors."""
    user_service = UserService(db)

    if specialty:
        doctors = await user_service.get_doctors_by_specialty(specialty)
    else:
        doctor_repo = DoctorRepository(db)
        doctors = await doctor_repo.get_all_active()

    return [
        DoctorWithAvailability(
            id=d.id,
            userId=d.user_id,
            dni=d.dni,
            firstName=d.first_name,
            lastName=d.last_name,
            licenseNumber=d.license_number,
            specialty=d.specialty,
            subSpecialty=d.sub_specialty,
            phone=d.phone,
            consultationFee=d.consultation_fee,
            isActive=d.is_active,
            createdAt=d.created_at,
            updatedAt=d.updated_at,
            availability=[
                DoctorAvailabilityResponse(
                    id=a.id,
                    doctorId=a.doctor_id,
                    dayOfWeek=a.day_of_week,
                    startTime=a.start_time,
                    endTime=a.end_time,
                    isActive=a.is_active
                )
                for a in d.availability
            ]
        )
        for d in doctors
    ]


@router.get(
    "/doctors/{doctor_id}",
    response_model=DoctorWithAvailability,
    summary="Get doctor details",
    description="Get doctor details with availability schedule"
)
async def get_doctor(
    doctor_id: UUID,
    admin=Depends(require_role("admin")),
    db=Depends(get_db)
):
    """Get doctor by ID with availability."""
    user_service = UserService(db)
    doctor = await user_service.get_doctor_by_id(doctor_id)

    if not doctor:
        from common.exceptions import NotFoundException
        raise NotFoundException("Doctor", doctor_id)

    return DoctorWithAvailability(
        id=doctor.id,
        userId=doctor.user_id,
        dni=doctor.dni,
        firstName=doctor.first_name,
        lastName=doctor.last_name,
        licenseNumber=doctor.license_number,
        specialty=doctor.specialty,
        subSpecialty=doctor.sub_specialty,
        phone=doctor.phone,
        consultationFee=doctor.consultation_fee,
        isActive=doctor.is_active,
        createdAt=doctor.created_at,
        updatedAt=doctor.updated_at,
        availability=[
            DoctorAvailabilityResponse(
                id=a.id,
                doctorId=a.doctor_id,
                dayOfWeek=a.day_of_week,
                startTime=a.start_time,
                endTime=a.end_time,
                isActive=a.is_active
            )
            for a in doctor.availability
        ]
    )
