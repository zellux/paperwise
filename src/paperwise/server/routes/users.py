from fastapi import APIRouter, Depends, HTTPException, Response, status

from paperwise.server.dependencies import (
    SESSION_COOKIE_NAME,
    current_user_dependency,
    document_repository_dependency,
    settings_dependency,
)
from paperwise.application.interfaces import PreferenceRepository, UserRepository
from paperwise.application.services.session_tokens import create_session_token
from paperwise.application.services.llm_preferences import validate_llm_preference_api_keys
from paperwise.application.services.user_preferences import (
    load_normalized_user_preferences,
    load_user_preferences,
    normalized_user_preferences,
)
from paperwise.application.services.users import (
    CreateUserCommand,
    authenticate_user,
    change_user_password,
    create_user,
)
from paperwise.domain.models import User
from paperwise.domain.models import UserPreference
from paperwise.infrastructure.config import Settings
from paperwise.server.user_schemas import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    UserPreferenceRequest,
    UserPreferenceResponse,
    UserResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


def _session_cookie_secure(settings: Settings) -> bool:
    if settings.session_cookie_secure is not None:
        return settings.session_cookie_secure
    return settings.env.lower() not in {"local", "dev", "development", "test", "docker"}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def create_user_endpoint(
    payload: CreateUserRequest,
    repository: UserRepository = Depends(document_repository_dependency),
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
    return UserResponse.from_domain(user)


@router.get("", response_model=list[UserResponse])
def list_users_endpoint(
    limit: int = 100,
    repository: UserRepository = Depends(document_repository_dependency),
) -> list[UserResponse]:
    users = repository.list_users(limit=limit)
    return [UserResponse.from_domain(user) for user in users]


@router.get("/me", response_model=UserResponse)
def get_me_endpoint(
    current_user: User = Depends(current_user_dependency),
) -> UserResponse:
    return UserResponse.from_domain(current_user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user_endpoint(
    user_id: str,
    repository: UserRepository = Depends(document_repository_dependency),
) -> UserResponse:
    user = repository.get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserResponse.from_domain(user)


@router.post("/login", response_model=LoginResponse)
def login_user_endpoint(
    payload: LoginRequest,
    response: Response,
    repository: UserRepository = Depends(document_repository_dependency),
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
    token = create_session_token(
        user_id=user.id,
        secret=settings.auth_secret,
        ttl_seconds=settings.session_ttl_seconds,
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=max(settings.session_ttl_seconds, 60),
        httponly=True,
        samesite="lax",
        secure=_session_cookie_secure(settings),
        path="/",
    )
    return LoginResponse(user=UserResponse.from_domain(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user_endpoint(response: Response) -> Response:
    response.status_code = status.HTTP_204_NO_CONTENT
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/", httponly=True, samesite="lax")
    return response


@router.get("/me/preferences", response_model=UserPreferenceResponse)
def get_me_preferences_endpoint(
    repository: PreferenceRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> UserPreferenceResponse:
    return UserPreferenceResponse(
        preferences=load_normalized_user_preferences(repository=repository, user_id=current_user.id)
    )


@router.put("/me/preferences", response_model=UserPreferenceResponse)
def put_me_preferences_endpoint(
    payload: UserPreferenceRequest,
    repository: PreferenceRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> UserPreferenceResponse:
    merged_preferences = load_user_preferences(repository=repository, user_id=current_user.id)
    merged_preferences.update(dict(payload.preferences))
    if error := validate_llm_preference_api_keys(merged_preferences):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )
    preference = UserPreference(user_id=current_user.id, preferences=merged_preferences)
    repository.save_user_preference(preference)
    return UserPreferenceResponse(preferences=normalized_user_preferences(preference.preferences))


@router.post("/me/password", response_model=ChangePasswordResponse)
def change_password_endpoint(
    payload: ChangePasswordRequest,
    repository: UserRepository = Depends(document_repository_dependency),
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
