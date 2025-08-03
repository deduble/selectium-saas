"""
Authentication system with Google OAuth, JWT tokens, and API key support.
"""
import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User, APIKey, UserSubscription, SubscriptionPlan
from schemas import TokenData, UserResponse


# Environment variables - use standardized names with legacy fallbacks
SECRET_KEY = os.getenv("SELEXTRACT_API_SECRET_KEY", os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production"))
JWT_SECRET_KEY = os.getenv("SELEXTRACT_JWT_SECRET_KEY", os.getenv("JWT_SECRET_KEY", SECRET_KEY))
ALGORITHM = os.getenv("SELEXTRACT_JWT_ALGORITHM", os.getenv("JWT_ALGORITHM", "HS256"))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("SELEXTRACT_ACCESS_TOKEN_EXPIRE_MINUTES", os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")))

GOOGLE_CLIENT_ID = os.getenv("SELEXTRACT_GOOGLE_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID", ""))
GOOGLE_CLIENT_SECRET = os.getenv("SELEXTRACT_GOOGLE_CLIENT_SECRET", os.getenv("GOOGLE_CLIENT_SECRET", ""))
GOOGLE_REDIRECT_URI = os.getenv("SELEXTRACT_GOOGLE_REDIRECT_URI", os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/google/callback"))

# OAuth URLs
GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Password context for API key hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error."""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error."""
    def __init__(self, detail: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Token payload data
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access_token"
    })
    
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Token data if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != "access_token":
            return None
            
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
            
        # Create timezone-aware datetime from timestamp
        exp_timestamp = payload.get("exp", 0)
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            
        return TokenData(
            user_id=user_id,
            exp=exp_datetime
        )
    except JWTError:
        return None


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage."""
    return pwd_context.hash(api_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return pwd_context.verify(plain_key, hashed_key)


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key and its preview.
    
    Returns:
        Tuple of (full_api_key, preview)
    """
    # Generate a secure random API key
    api_key = f"sk_{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(32))}"
    preview = f"{api_key[:8]}{'*' * 24}"
    
    return api_key, preview


async def get_user_from_google(access_token: str) -> Dict[str, Any]:
    """
    Fetch user information from Google using access token.
    
    Args:
        access_token: Google OAuth access token
        
    Returns:
        User information from Google
        
    Raises:
        HTTPException: If unable to fetch user info
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user information from Google"
            )
        
        return response.json()


def get_google_auth_url(state: Optional[str] = None) -> str:
    """
    Generate Google OAuth authorization URL.
    
    Args:
        state: Optional state parameter for CSRF protection
        
    Returns:
        Google OAuth authorization URL
    """
    if not state:
        state = secrets.token_urlsafe(32)
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "response_type": "code",
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    return f"{GOOGLE_AUTHORIZATION_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """
    Exchange authorization code for access token.
    
    Args:
        code: Authorization code from Google
        
    Returns:
        Token response from Google
        
    Raises:
        HTTPException: If token exchange fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token"
            )
        
        return response.json()


def get_or_create_user(db, google_user_info: Dict[str, Any]) -> User:
    """
    Get existing user or create new user from Google user info.
    
    Args:
        db: Database session
        google_user_info: User info from Google
        
    Returns:
        User instance
    """
    google_id = google_user_info["id"]
    email = google_user_info["email"]
    
    # Try to find existing user by Google ID
    user = db.query(User).filter(User.google_id == google_id).first()
    
    if not user:
        # Try to find by email (in case of account linking)
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Link Google account to existing user
            user.google_id = google_id
        else:
            # Create new user
            user = User(
                email=email,
                google_id=google_id,
                full_name=google_user_info.get("name"),
                subscription_tier="free",
                compute_units_remaining=100  # Free tier allowance
            )
            db.add(user)
            db.flush()  # Get the user ID
            
            # Create free subscription
            free_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == "free").first()
            if free_plan:
                subscription = UserSubscription(
                    user_id=user.id,
                    plan_id=free_plan.id,
                    status="active"
                )
                db.add(subscription)
    
    # Update user info from Google
    user.full_name = google_user_info.get("name") or user.full_name
    user.is_active = True
    
    db.commit()
    db.refresh(user)
    
    return user


def get_or_create_dev_user(db: Session, email: str) -> User:
    """
    Get or create a development user with elevated privileges.
    This function is intended for development/testing purposes only.
    """
    user = db.query(User).filter(User.email == email).first()

    if user:
        # Ensure the dev user always has enterprise privileges for testing
        if user.subscription_tier != "enterprise" or user.compute_units_remaining < 500000:
            user.subscription_tier = "enterprise"
            user.compute_units_remaining = 999999
            user.is_active = True # Ensure user is active
            
            # Check for active subscription and update if necessary
            active_sub = user.get_active_subscription()
            if not active_sub or active_sub.plan_id != "enterprise":
                # Deactivate other subscriptions
                for sub in user.subscriptions:
                    sub.status = "inactive"
                
                # Create or activate enterprise subscription
                enterprise_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == "enterprise").first()
                if enterprise_plan:
                    enterprise_sub = db.query(UserSubscription).filter(UserSubscription.user_id == user.id, UserSubscription.plan_id == "enterprise").first()
                    if enterprise_sub:
                        enterprise_sub.status = "active"
                    else:
                         db.add(UserSubscription(user_id=user.id, plan_id="enterprise", status="active"))

        db.commit()
        db.refresh(user)
        return user

    # If user does not exist, create a new one
    new_user = User(
        email=email,
        full_name="Dev User",
        subscription_tier="enterprise",
        compute_units_remaining=999999,
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    # Ensure enterprise plan exists and create subscription
    enterprise_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == "enterprise").first()
    if enterprise_plan:
        subscription = UserSubscription(
            user_id=new_user.id,
            plan_id=enterprise_plan.id,
            status="active"
        )
        db.add(subscription)

    db.commit()
    db.refresh(new_user)
    return new_user


async def get_current_user_from_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token.
    
    Args:
        credentials: Bearer token credentials
        db: Database session
        
    Returns:
        User if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    token_data = verify_token(credentials.credentials)
    if not token_data:
        return None
    
    # Check if token is expired
    if token_data.exp and datetime.now(timezone.utc) > token_data.exp:
        return None
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user or not user.is_active:
        return None
    
    return user


async def get_current_user_from_api_key(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from API key.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        User if authenticated, None otherwise
    """
    # Check for API key in headers
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    
    # Find API key in database
    api_key_obj = db.query(APIKey).filter(
        APIKey.key_prefix == api_key[:8],
        APIKey.is_active == True
    ).first()
    
    if not api_key_obj:
        return None
    
    # Verify the full API key
    if not verify_api_key(api_key, api_key_obj.key_hash):
        return None
    
    # Update last used timestamp
    api_key_obj.mark_as_used()
    db.commit()
    
    # Get the user
    user = api_key_obj.user
    if not user or not user.is_active:
        return None
    
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    request: Request = None,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user (JWT or API key).
    
    Args:
        credentials: Bearer token credentials
        request: FastAPI request object
        db: Database session
        
    Returns:
        Authenticated user
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    # Try JWT token first
    user = await get_current_user_from_token(credentials, db)
    
    # Try API key if JWT fails
    if not user and request:
        user = await get_current_user_from_api_key(request, db)
    
    if not user:
        raise AuthenticationError("Invalid or expired authentication credentials")
    
    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    request: Request = None,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.
    
    Args:
        credentials: Bearer token credentials
        request: FastAPI request object
        db: Database session
        
    Returns:
        User if authenticated, None otherwise
    """
    try:
        return await get_current_user(credentials, request, db)
    except AuthenticationError:
        return None


def require_subscription_tier(min_tier: str):
    """
    Dependency factory for requiring minimum subscription tier.
    
    Args:
        min_tier: Minimum required subscription tier
        
    Returns:
        Dependency function
    """
    tier_hierarchy = {"free": 0, "pro": 1, "enterprise": 2}
    min_level = tier_hierarchy.get(min_tier, 0)
    
    async def check_subscription_tier(user: User = Depends(get_current_user)) -> User:
        user_level = tier_hierarchy.get(user.subscription_tier, 0)
        if user_level < min_level:
            raise AuthorizationError(
                f"This operation requires {min_tier} subscription or higher"
            )
        return user
    
    return check_subscription_tier


def require_compute_units(required_units: int):
    """
    Dependency factory for requiring minimum compute units.
    
    Args:
        required_units: Minimum required compute units
        
    Returns:
        Dependency function
    """
    async def check_compute_units(user: User = Depends(get_current_user)) -> User:
        if user.compute_units_remaining < required_units:
            raise AuthorizationError(
                f"Insufficient compute units. Required: {required_units}, "
                f"Available: {user.compute_units_remaining}"
            )
        return user
    
    return check_compute_units


def admin_required(user: User = Depends(get_current_user)) -> User:
    """
    Require admin privileges.
    
    Args:
        user: Current authenticated user
        
    Returns:
        User if admin
        
    Raises:
        AuthorizationError: If user is not admin
    """
    # In production, you'd have an admin flag in the User model
    # For now, we'll use subscription tier as a proxy
    if user.subscription_tier != "enterprise":
        raise AuthorizationError("Admin privileges required")
    
    return user


class RateLimitAuth:
    """Rate limiting for authentication endpoints."""
    
    def __init__(self):
        self.attempts = {}
        self.lockout_duration = timedelta(minutes=15)
        self.max_attempts = 5
    
    def is_locked_out(self, identifier: str) -> bool:
        """Check if identifier is locked out."""
        if identifier not in self.attempts:
            return False
        
        attempts, last_attempt = self.attempts[identifier]
        if datetime.now(timezone.utc) - last_attempt > self.lockout_duration:
            # Reset attempts after lockout period
            del self.attempts[identifier]
            return False
        
        return attempts >= self.max_attempts
    
    def record_attempt(self, identifier: str, success: bool = False):
        """Record an authentication attempt."""
        if success:
            # Clear attempts on success
            if identifier in self.attempts:
                del self.attempts[identifier]
            return
        
        if identifier not in self.attempts:
            self.attempts[identifier] = [1, datetime.now(timezone.utc)]
        else:
            attempts, _ = self.attempts[identifier]
            self.attempts[identifier] = [attempts + 1, datetime.now(timezone.utc)]


# Global rate limiter instance
auth_rate_limiter = RateLimitAuth()


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


async def check_auth_rate_limit(request: Request):
    """Check rate limit for authentication endpoints."""
    client_ip = get_client_ip(request)
    
    if auth_rate_limiter.is_locked_out(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later."
        )


def create_state_token() -> str:
    """Create a secure state token for OAuth flows."""
    return secrets.token_urlsafe(32)


def verify_state_token(provided_state: str, expected_state: str) -> bool:
    """Verify OAuth state token."""
    return secrets.compare_digest(provided_state, expected_state)


# Export commonly used dependencies
RequireAuth = Depends(get_current_user)
OptionalAuth = Depends(get_optional_current_user)
RequireProTier = Depends(require_subscription_tier("pro"))
RequireEnterpriseTier = Depends(require_subscription_tier("enterprise"))
# Standalone function for validation compatibility
def get_user_from_token(token: str, db) -> Optional[User]:
    """Get current user from token - standalone function for validation"""
    token_data = verify_token(token)
    if not token_data:
        return None
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user or not user.is_active:
        return None
    
    return user


RequireAdmin = Depends(admin_required)