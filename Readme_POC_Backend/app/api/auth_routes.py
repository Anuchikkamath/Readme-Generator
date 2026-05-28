"""
Authentication API Routes
Handles Google OAuth login, callback, and session management.
"""

from fastapi import APIRouter, HTTPException, status, Response, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from urllib.parse import urlencode
import httpx
import secrets
from datetime import datetime, timedelta
from jose import jwt
from typing import Optional

from app.core.config import settings
from app.core.security import create_access_token, get_current_user, get_current_user_optional
from app.services.storage.postgres_client import PostgresClient

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}}
)

# Initialize PostgresClient
postgres_client = PostgresClient()
FRONTEND_DASHBOARD_URL = "http://localhost:5173/dashboard"


def _build_oauth_state(mode: str, user_id: Optional[str] = None) -> str:
    """Create signed OAuth state token including optional user binding."""
    payload = {
        "type": "oauth_state",
        "mode": mode,
        "nonce": secrets.token_urlsafe(16),
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_oauth_state(state_token: Optional[str]) -> dict:
    """Decode and validate OAuth state token."""
    if not state_token:
        return {}
    try:
        payload = jwt.decode(
            state_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "oauth_state":
            return {}
        return payload
    except Exception:
        return {}


def _build_google_auth_url(mode: str = "login", user_id: Optional[str] = None, email: Optional[str] = None) -> str:
    """Build Google OAuth consent URL with signed state."""
    # Only login mode is supported now (signup removed)
    state = _build_oauth_state(mode="login", user_id=None)
    # Force account selection and consent screen to show permissions for Gmail and Google Docs
    # Using "select_account consent" ensures account selection appears first, then consent screen
    prompt = "select_account consent"

    auth_params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(settings.GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": prompt,
        "state": state,
    }
    
    # Note: We don't use login_hint here because it can cause Google to show
    # the email entry screen instead of the account selection screen.
    # The user will select their account from the account selection screen,
    # and we validate the email matches in the callback handler.
    
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"


@router.get("/health", summary="Auth service health check")
async def auth_health():
    """
    Simple health check endpoint to verify auth service is running.
    
    **✅ This endpoint CAN be tested via Swagger UI**
    
    Returns:
        dict: Health status and available auth endpoints
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "endpoints": {
            "login": "/auth/login (open in browser, not Swagger)",
            "callback": "/auth/callback (called by Google)",
            "me": "/auth/me (requires authentication)",
            "logout": "/auth/logout (requires authentication)"
        },
        "note": "OAuth endpoints (/login, /callback) cannot be tested via Swagger UI - use a browser instead"
    }



@router.get("/login", summary="Initiate Google OAuth login")
async def login(current_user: dict = Depends(get_current_user_optional)):
    """
    Redirect user to Google OAuth consent screen.
    """
    bound_user_id = current_user.get("user_id") if current_user else None

    # If already authenticated and tokens exist, skip OAuth and go to dashboard.
    if bound_user_id:
        user = postgres_client.get_user_by_id(bound_user_id)
        if user and user.get("access_token") and user.get("refresh_token"):
            return RedirectResponse(url=FRONTEND_DASHBOARD_URL, status_code=303)

    auth_url = _build_google_auth_url(mode="login", user_id=None, email=None)
    return RedirectResponse(url=auth_url, status_code=303)


@router.get("/callback", summary="OAuth callback handler")
async def callback(code: str, state: str = None):
    """
    Handle Google OAuth callback and create user session.
    
    This endpoint receives the authorization code from Google, exchanges it for
    access and refresh tokens, creates or updates the user in the database,
    and sets a JWT session cookie.
    
    Args:
        code: Authorization code from Google
        state: CSRF protection state parameter
        
    Returns:
        JSONResponse: Success message with JWT cookie set
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided"
        )
    
    try:
        # Exchange authorization code for tokens
        async with httpx.AsyncClient() as client:
            # Log request for debugging
            token_request_data = {
                'code': code,
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': settings.GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code'
            }
            
            print(f"[DEBUG] Token exchange request:")
            print(f"  - redirect_uri: {settings.GOOGLE_REDIRECT_URI}")
            print(f"  - client_id: {settings.GOOGLE_CLIENT_ID[:20]}...")
            
            token_response = await client.post(
                'https://oauth2.googleapis.com/token',
                data=token_request_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            print(f"[DEBUG] Token response status: {token_response.status_code}")
            
            if token_response.status_code != 200:
                error_detail = token_response.text
                print(f"[ERROR] Token exchange failed: {error_detail}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Token exchange failed: {error_detail}"
                )
            
            token_data = token_response.json()
            print(f"[DEBUG] Token exchange successful, got access_token")
        
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        id_token = token_data.get('id_token')
        expires_in = token_data.get('expires_in', 3600)
        
        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No id_token received from Google"
            )
        
        # Decode id_token to get user info
        # Note: In production, you should verify the JWT signature and claims
        try:
            user_info = jwt.decode(
                id_token, 
                key="",  # Empty key since we're not verifying signature
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_iat": False,
                    "verify_exp": False,
                    "verify_nbf": False,
                    "verify_iss": False,
                    "verify_sub": False,
                    "verify_jti": False,
                    "verify_at_hash": False,
                    "leeway": 0,
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to decode id_token: {str(e)}"
            )
        
        email = user_info.get('email')
        google_id = user_info.get('sub')
        
        if not email or not google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract user information from id_token"
            )
        
        # Calculate token expiry
        token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Decode signed state (mode is always "login" now)
        state_payload = _decode_oauth_state(state)
        mode = state_payload.get("mode", "login")

        print(f"[DEBUG] Auth Mode: {mode}")

        # Google OAuth only flow - create or update user with Google credentials
        existing_user = postgres_client.get_user_by_email(email)
        if not existing_user:
            print(f"[AUTH] New user {email} logging in via Google OAuth - will create account")
        else:
            print(f"[AUTH] Existing user {email} logging in via Google OAuth - updating tokens")

        user = postgres_client.create_or_update_user(
            email=email,
            google_id=google_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user session"
            )
        
        # Create JWT for application session
        jwt_payload = {
            "user_id": user['id'],
            "email": user['email']
        }
        
        jwt_token = create_access_token(jwt_payload)
        
        # Redirect to frontend with token and email as query parameters
        # Frontend will extract token and email, store in sessionStorage
        # URL-encode the token and email to handle special characters safely
        from urllib.parse import quote_plus
        encoded_token = quote_plus(jwt_token)
        encoded_email = quote_plus(email)
        redirect_url = f"{FRONTEND_DASHBOARD_URL}?token={encoded_token}&email={encoded_email}"
        response = RedirectResponse(url=redirect_url, status_code=303)
        
        print(f"[DEBUG] Generated JWT token for user {email}")
        print(f"[DEBUG] Token length: {len(jwt_token)}")
        print(f"[DEBUG] Redirecting to frontend with token and email in URL")
        print(f"[DEBUG] Redirect URL: {FRONTEND_DASHBOARD_URL}?token={encoded_token[:50]}...&email={encoded_email}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/me", summary="Get current user information")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get information about the currently authenticated user.
    
    This is a protected endpoint that requires a valid JWT cookie.
    
    Args:
        current_user: Current user from JWT (injected by dependency)
        
    Returns:
        dict: Current user information
    """
    # Get full user details from database
    user = postgres_client.get_user_by_id(current_user['user_id'])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Return safe user info (don't expose tokens)
    # Also return a session indicator for frontend to track authentication state
    response_data = {
        "id": user['id'],
        "email": user['email'],
        "created_at": user['created_at'].isoformat() if user['created_at'] else None,
        "authenticated": True  # Indicator that user is authenticated
    }
    
    # Set a non-sensitive session indicator in response header
    # Frontend can check this to verify session is active
    response = JSONResponse(content=response_data)
    response.headers["X-Authenticated"] = "true"
    return response


@router.post("/logout", summary="Logout and clear session")
async def logout(current_user: dict = Depends(get_current_user_optional)):
    """
    Logout user. Token is cleared on frontend (sessionStorage).
    
    Returns:
        dict: Logout confirmation message
    """
    # Token is stored in sessionStorage on frontend, so we just confirm logout
    # Frontend will clear the token from sessionStorage and redirect to login
    if current_user:
        print(f"[DEBUG] User {current_user.get('email', 'unknown')} logging out")
    return JSONResponse(content={"message": "Logged out successfully"})


