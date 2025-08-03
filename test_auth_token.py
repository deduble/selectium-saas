#!/usr/bin/env python3
"""
Generate a test JWT token for frontend/API testing.
"""
import os
from datetime import datetime, timedelta, timezone
from jose import jwt

# Set environment variables from dev config
os.environ['SELEXTRACT_JWT_SECRET_KEY'] = 'dev-jwt-secret-not-for-production'
os.environ['SELEXTRACT_API_SECRET_KEY'] = 'dev-api-secret-not-for-production'
os.environ['SELEXTRACT_DB_PASSWORD'] = 'devpassword'
os.environ['DATABASE_URL'] = 'postgresql://selextract:devpassword@localhost:5432/selextract_dev'

# JWT Configuration
JWT_SECRET_KEY = "dev-jwt-secret-not-for-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token."""
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

def generate_test_token():
    """Generate a test JWT token for the existing user."""
    
    # Use the existing user ID from database
    user_id = "a5d154eb-de07-499e-baa1-2c61ef7cf198"
    
    # Create token payload
    token_data = {
        "sub": user_id,
        "email": "yunusemremre@gmail.com",
        "subscription_tier": "free"
    }
    
    # Generate token with extended expiration for testing
    expires_delta = timedelta(hours=24)  # 24 hour token for testing
    token = create_access_token(data=token_data, expires_delta=expires_delta)
    
    print("=" * 60)
    print("TEST AUTHENTICATION TOKEN GENERATED")
    print("=" * 60)
    print(f"User ID: {user_id}")
    print(f"Email: yunusemremre@gmail.com")
    print(f"JWT Secret Key: {JWT_SECRET_KEY[:8]}...")
    print(f"Algorithm: {ALGORITHM}")
    print(f"Expires: {ACCESS_TOKEN_EXPIRE_MINUTES} minutes (extended to 24h for testing)")
    print("=" * 60)
    print("JWT TOKEN:")
    print(token)
    print("=" * 60)
    print("\nUsage:")
    print("1. For API testing:")
    print(f'   curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/auth/me')
    print("\n2. For browser testing:")
    print(f'   Set cookie: access_token={token}')
    print("=" * 60)
    
    return token

if __name__ == "__main__":
    token = generate_test_token()