"""
Security Module
JWT token creation, verification, and authentication dependencies.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Cookie, Header
from app.core.config import settings


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing user claims (user_id, email, etc.)
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
            
        return payload
        
    except JWTError:
        raise credentials_exception


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    access_token: Optional[str] = Cookie(None)
):
    """
    FastAPI dependency to get current authenticated user from JWT token.
    Accepts token from Authorization header (Bearer token) or cookie (for backward compatibility).
    """
    token = None
    
    print(f"[DEBUG] get_current_user: Authorization header: {authorization[:50] if authorization else None}...")
    print(f"[DEBUG] get_current_user: Cookie token: {access_token[:20] if access_token else None}...")
    
    # Try to get token from Authorization header first (Bearer token)
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                print(f"[DEBUG] get_current_user: Invalid scheme '{scheme}', expected 'bearer'")
                raise ValueError("Invalid authorization scheme")
            print(f"[DEBUG] get_current_user: Extracted token from Authorization header: {token[:20]}...")
        except ValueError as e:
            print(f"[DEBUG] get_current_user: Error parsing Authorization header: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Fallback to cookie if no Authorization header
    if not token and access_token:
        token = access_token
        print(f"[DEBUG] get_current_user: Using token from cookie: {token[:20]}...")
    
    if not token:
        print("[DEBUG] get_current_user: No access_token found in Authorization header or cookie")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"[DEBUG] get_current_user: Verifying token {token[:20]}...")
    try:
        payload = verify_token(token)
        print(f"[DEBUG] get_current_user: Token verified for user {payload.get('user_id')}")
        return payload
    except Exception as e:
        print(f"[DEBUG] get_current_user: Token verification failed: {e}")
        raise


async def get_current_user_optional(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    access_token: Optional[str] = Cookie(None)
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication dependency - returns None if not authenticated.
    Accepts token from Authorization header (Bearer token) or cookie (for backward compatibility).
    
    Returns:
        dict or None: User information if authenticated, None otherwise
    """
    token = None
    
    # Try to get token from Authorization header first
    if authorization:
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                return None
        except ValueError:
            return None
    
    # Fallback to cookie if no Authorization header
    if not token and access_token:
        token = access_token
    
    if not token:
        return None
    
    try:
        payload = verify_token(token)
        return payload
    except HTTPException:
        return None
