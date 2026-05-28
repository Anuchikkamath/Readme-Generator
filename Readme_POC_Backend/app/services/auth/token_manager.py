"""
Token Manager Module
Handles OAuth token refresh logic for Google API access.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
import httpx
from app.core.config import settings
from app.services.storage.postgres_client import PostgresClient


class TokenManager:
    """Manages OAuth token refresh for user authentication."""
    
    def __init__(self):
        """Initialize token manager."""
        self.postgres_client = PostgresClient()
    
    def check_token_expiry(self, user: Dict) -> bool:
        """
        Check if user's access token is expired or about to expire.
        
        Args:
            user: User dictionary with token_expiry
            
        Returns:
            bool: True if token needs refresh, False otherwise
        """
        if not user.get('token_expiry'):
            return True  # No expiry time, assume expired
        
        # Refresh if token expires within 5 minutes
        expiry = user['token_expiry']
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
        
        buffer_time = datetime.utcnow() + timedelta(minutes=5)
        return expiry <= buffer_time
    
    async def refresh_access_token(self, user: Dict) -> Optional[str]:
        """
        Use refresh token to get a new access token from Google.
        
        Args:
            user: User dictionary with refresh_token
            
        Returns:
            str: New access token or None if refresh failed
        """
        refresh_token = user.get('refresh_token')
        if not refresh_token:
            print(f"[ERROR] No refresh token available for user {user.get('email')}")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://oauth2.googleapis.com/token',
                    data={
                        'client_id': settings.GOOGLE_CLIENT_ID,
                        'client_secret': settings.GOOGLE_CLIENT_SECRET,
                        'refresh_token': refresh_token,
                        'grant_type': 'refresh_token'
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                
                if response.status_code != 200:
                    print(f"[ERROR] Token refresh failed: {response.text}")
                    return None
                
                token_data = response.json()
                new_access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                
                # Calculate new expiry time
                new_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                
                # Update database
                self.postgres_client.update_access_token(
                    user_id=user['id'],
                    access_token=new_access_token,
                    token_expiry=new_expiry
                )
                
                print(f"[OK] Refreshed access token for user {user.get('email')}")
                return new_access_token
                
        except Exception as e:
            print(f"[ERROR] Error refreshing token: {e}")
            return None
    
    async def get_valid_token(self, user: Dict) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            user: User dictionary
            
        Returns:
            str: Valid access token or None if unable to get one
        """
        if self.check_token_expiry(user):
            print(f"[INFO] Token expired for {user.get('email')}, refreshing...")
            new_token = await self.refresh_access_token(user)
            return new_token if new_token else user.get('access_token')
        
        return user.get('access_token')
