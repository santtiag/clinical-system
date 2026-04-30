"""
Authentication and registration routes.
"""

from fastapi import APIRouter, Depends, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from common.database import get_db
from common.security import decode_token
from common.exceptions import UnauthorizedException
from common.config import settings

from src.domain.services import AuthService
from src.presentation.schemas import (
    RegisterPatientRequest,
    RegisterDoctorRequest,
    LoginRequest,
    TokenResponse,
    RegisterResponse
)


router = APIRouter()


async def get_current_user(
    authorization: str = Header(default=None)
):
    """Dependency to get current authenticated user from JWT token."""
    if not authorization:
        raise UnauthorizedException("Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise UnauthorizedException("Invalid authentication scheme")
    except ValueError:
        raise UnauthorizedException("Invalid authorization header format")

    payload = decode_token(token)
    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    return payload


@router.post(
    "/register/patient",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new patient",
    description="Register a new patient account with profile information"
)
async def register_patient(
    request: RegisterPatientRequest,
    db=Depends(get_db)
):
    """
    Register a new patient.

    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (8-100 characters)
    - **dni**: Document ID number
    - **first_name**: First name
    - **last_name**: Last name
    - **date_of_birth**: Date of birth
    """
    auth_service = AuthService(db)

    user, patient, token = await auth_service.register_patient(
        username=request.username,
        email=request.email,
        password=request.password,
        dni=request.dni,
        first_name=request.first_name,
        last_name=request.last_name,
        date_of_birth=request.date_of_birth,
        phone=request.phone,
        address=request.address
    )

    return RegisterResponse(
        userId=str(user.id),
        patientId=str(patient.id),
        role=user.role.value,
        access_token=token,
        tokenType="bearer"
    )


@router.post(
    "/register/medic",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new doctor",
    description="Register a new medical professional account"
)
async def register_medic(
    request: RegisterDoctorRequest,
    db=Depends(get_db)
):
    """
    Register a new doctor.

    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (8-100 characters)
    - **dni**: Document ID number
    - **first_name**: First name
    - **last_name**: Last name
    - **license_number**: Medical license number
    - **specialty**: Medical specialty
    """
    auth_service = AuthService(db)

    user, doctor, token = await auth_service.register_doctor(
        username=request.username,
        email=request.email,
        password=request.password,
        dni=request.dni,
        first_name=request.first_name,
        last_name=request.last_name,
        license_number=request.license_number,
        specialty=request.specialty,
        phone=request.phone,
        consultation_fee=request.consultation_fee
    )

    return RegisterResponse(
        userId=str(user.id),
        doctorId=str(doctor.id),
        role=user.role.value,
        access_token=token,
        tokenType="bearer"
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate user and return JWT token"
)
async def login(
    request: LoginRequest,
    db=Depends(get_db)
):
    """
    Login with username and password.

    Returns a JWT token for authenticating subsequent requests.
    """
    auth_service = AuthService(db)

    user, token = await auth_service.login(
        username=request.username,
        password=request.password
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_MINUTES * 60,
        userId=str(user.id),
        role=user.role.value
    )


@router.post(
    "/token",
    response_model=TokenResponse,
    include_in_schema=False,
    summary="OAuth2 token endpoint",
    description="OAuth2 compatible token endpoint"
)
async def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db)
):
    """
    OAuth2 compatible token endpoint for password grant.
    """
    auth_service = AuthService(db)

    user, token = await auth_service.login(
        username=form_data.username,
        password=form_data.password
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRATION_MINUTES * 60,
        userId=str(user.id),
        role=user.role.value
    )
