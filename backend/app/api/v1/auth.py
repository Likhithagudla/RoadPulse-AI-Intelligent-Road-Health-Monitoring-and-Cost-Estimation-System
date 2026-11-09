"""
RoadPulse AI - Authentication & Identity Router
Handles secure user registration, bcrypt password authentication,
and JWT token distribution with strict privilege escalation prevention.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import SecurityService
from ...core.dependencies import get_current_user
from ...models.user import User
from ...schemas.user import UserRegister, UserLogin, UserResponse
from ...schemas.token import Token
from ...utils.audit import log_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Public user registration",
    description="Registers a new standard user account. Role is strictly assigned as 'user'.",
)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_db),
):
    # Check if username already exists (case-insensitive)
    existing = db.query(User).filter(User.username.ilike(user_in.username.strip())).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_in.username}' is already registered.",
        )

    # Validate password complexity
    valid_pw, pw_err = SecurityService.validate_password_strength(user_in.password)
    if not valid_pw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=pw_err,
        )

    # Hash password with bcrypt
    hashed = SecurityService.get_password_hash(user_in.password)

    # Strict role assignment: Public registration CANNOT grant worker or admin roles
    new_user = User(
        username=user_in.username.strip(),
        password_hash=hashed,
        role="user",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=Token,
    summary="User login & JWT distribution",
    description="Authenticates credentials and returns a signed JWT access token.",
)
def login(
    user_in: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username.ilike(user_in.username.strip())).first()
    if not user or not SecurityService.verify_password(user_in.password, user.password_hash, username=user.username):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated. Please contact an administrator.",
        )

    token = SecurityService.create_access_token(
        data={"sub": user.username, "role": user.role}
    )

    log_audit_event(
        db=db,
        action="LOGIN_SUCCESS",
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        details={"username": user.username, "role": user.role},
        request=request,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
    }


@router.post(
    "/token",
    response_model=Token,
    include_in_schema=False,
    summary="OAuth2 form-data login fallback",
)
def login_oauth2_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Standard OAuth2 form-data login endpoint for Swagger UI authorization."""
    user = db.query(User).filter(User.username.ilike(form_data.username.strip())).first()
    if not user or not SecurityService.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = SecurityService.create_access_token(
        data={"sub": user.username, "role": user.role}
    )

    log_audit_event(
        db=db,
        action="LOGIN_SUCCESS",
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        details={"username": user.username, "role": user.role},
        request=request,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user identity",
    description="Returns identity and role profile of the currently authenticated token owner.",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user
