from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserOut, Token
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new patient or admin user with email and secure password.",
)
def signup(
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> UserOut:
    return AuthService.register_user(db=db, user_in=user_in)


@router.post(
    "/login",
    response_model=Token,
    summary="User login and JWT acquisition",
    description="Authenticates credentials and returns a JWT access token for authorization headers.",
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> Token:
    return AuthService.authenticate(db=db, credentials=credentials)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user profile",
    description="Returns profile details of the currently authenticated user.",
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserOut:
    return current_user
