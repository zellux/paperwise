from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    settings_dependency,
)
from paperwise.application.interfaces import DocumentRepository
from paperwise.application.services.auth_tokens import create_access_token
from paperwise.application.services.users import (
    CreateUserCommand,
    authenticate_user,
    change_user_password,
    create_user,
)
from paperwise.domain.models import User
from paperwise.domain.models import UserPreference
from paperwise.infrastructure.config import Settings

router = APIRouter(prefix="/users", tags=["users"])


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=8, max_length=256)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserPreferenceRequest(BaseModel):
    preferences: dict[str, Any]


class UserPreferenceResponse(BaseModel):
    preferences: dict[str, Any]


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class ChangePasswordResponse(BaseModel):
    message: str


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def create_user_endpoint(
    payload: CreateUserRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> UserResponse:
    try:
        user = create_user(
            CreateUserCommand(
                email=payload.email,
                full_name=payload.full_name,
                password=payload.password,
            ),
            repository=repository,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return _to_user_response(user)


@router.get("", response_model=list[UserResponse])
def list_users_endpoint(
    limit: int = 100,
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> list[UserResponse]:
    users = repository.list_users(limit=limit)
    return [_to_user_response(user) for user in users]


@router.get("/me", response_model=UserResponse)
def get_me_endpoint(
    current_user: User = Depends(current_user_dependency),
) -> UserResponse:
    return _to_user_response(current_user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user_endpoint(
    user_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> UserResponse:
    user = repository.get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return _to_user_response(user)


@router.post("/login", response_model=LoginResponse)
def login_user_endpoint(
    payload: LoginRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    settings: Settings = Depends(settings_dependency),
) -> LoginResponse:
    user = authenticate_user(
        email=payload.email,
        password=payload.password,
        repository=repository,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(
        user_id=user.id,
        secret=settings.auth_secret,
        ttl_seconds=settings.auth_token_ttl_seconds,
    )
    return LoginResponse(access_token=token, user=_to_user_response(user))


@router.get("/me/preferences", response_model=UserPreferenceResponse)
def get_me_preferences_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> UserPreferenceResponse:
    preference = repository.get_user_preference(current_user.id)
    return UserPreferenceResponse(preferences=dict(preference.preferences) if preference else {})


@router.put("/me/preferences", response_model=UserPreferenceResponse)
def put_me_preferences_endpoint(
    payload: UserPreferenceRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> UserPreferenceResponse:
    existing = repository.get_user_preference(current_user.id)
    merged_preferences = dict(existing.preferences) if existing is not None else {}
    merged_preferences.update(dict(payload.preferences))
    preference = UserPreference(user_id=current_user.id, preferences=merged_preferences)
    repository.save_user_preference(preference)
    return UserPreferenceResponse(preferences=dict(preference.preferences))


@router.post("/me/password", response_model=ChangePasswordResponse)
def change_password_endpoint(
    payload: ChangePasswordRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> ChangePasswordResponse:
    try:
        change_user_password(
            user=current_user,
            current_password=payload.current_password,
            new_password=payload.new_password,
            repository=repository,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ChangePasswordResponse(message="Password updated successfully.")
