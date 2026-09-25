from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.core.logging import logger
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, Token, UserOut


class AuthService:
    @staticmethod
    def register_user(db: Session, user_in: UserCreate) -> User:
        """Registers a new user, ensuring email uniqueness"""
        existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
        if existing_user:
            logger.warning(f"Registration failed: Email {user_in.email} is already registered")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists",
            )

        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            email=user_in.email.lower(),
            hashed_password=hashed_password,
            full_name=user_in.full_name.strip(),
            phone_number=user_in.phone_number.strip() if user_in.phone_number else None,
            role=user_in.role,
            is_active=True,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Successfully registered new user: {db_user.email} (ID: {db_user.id})")
        return db_user

    @staticmethod
    def authenticate(db: Session, credentials: UserLogin) -> Token:
        """Validates credentials and issues a JWT bearer token"""
        user = db.query(User).filter(User.email == credentials.email.lower()).first()
        if not user or not verify_password(credentials.password, user.hashed_password):
            logger.warning(f"Login failed: Invalid credentials for email {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.warning(f"Login failed: User account {user.email} is deactivated")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )

        access_token = create_access_token(
            subject=user.id,
            role=user.role.value,
        )
        logger.info(f"User authenticated successfully: {user.email} (ID: {user.id})")
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user=UserOut.model_validate(user),
        )
