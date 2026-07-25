from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.user import RegistrationRequest, LoginRequest, UserResponse
from app.schemas.token import TokenResponse
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    *,
    db: Session = Depends(get_db),
    request: RegistrationRequest,
) -> UserResponse:
    """
    Register a new user.
    """
    return AuthService.register_user(db, request)

@router.post("/login", response_model=TokenResponse)
def login(
    *,
    db: Session = Depends(get_db),
    request: LoginRequest,
) -> TokenResponse:
    """
    Verify credentials and return access token.
    """
    user = AuthService.authenticate_user(db, request)
    return AuthService.create_user_token(user)

@router.post("/login/access-token", response_model=TokenResponse)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponse:
    """
    OAuth2 compatible token login, get an access token for future requests.
    Supports form data parameter authentication for Swagger UI.
    """
    login_request = LoginRequest(email=form_data.username, password=form_data.password)
    user = AuthService.authenticate_user(db, login_request)
    return AuthService.create_user_token(user)

@router.get("/me", response_model=UserResponse)
def get_user_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current logged in user.
    """
    return current_user
