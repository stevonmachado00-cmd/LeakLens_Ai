from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core import security
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import RegistrationRequest, LoginRequest
from app.schemas.token import TokenResponse

class AuthService:
    @staticmethod
    def register_user(db: Session, request: RegistrationRequest) -> User:
        email = request.email.lower()
        # Check if email is already registered
        existing_user = UserRepository.get_by_email(db, email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = security.hash_password(request.password)
        
        # Create user
        try:
            return UserRepository.create(
                db,
                full_name=request.full_name,
                email=email,
                hashed_password=hashed_password,
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    @staticmethod
    def authenticate_user(db: Session, request: LoginRequest) -> User:
        user = UserRepository.get_by_email(db, request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not security.verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user

    @staticmethod
    def create_user_token(user: User) -> TokenResponse:
        access_token = security.create_access_token(subject=user.id)
        return TokenResponse(
            access_token=access_token,
            token_type="bearer"
        )
