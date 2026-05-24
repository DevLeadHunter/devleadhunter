"""
Gmail OAuth service for sending emails via Gmail API.
"""
import logging
from typing import Optional, Dict
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from datetime import datetime, timedelta

from core.config import settings

logger = logging.getLogger(__name__)


class GmailOAuthService:
    """
    Service for sending emails via Gmail API using OAuth2.
    
    Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in environment variables.
    """
    
    def __init__(self):
        """Initialize Gmail OAuth service."""
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        
        self.token_url = "https://oauth2.googleapis.com/token"
        self.gmail_api_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Get Google OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
        
        Returns:
            Authorization URL to redirect user to
        """
        scopes = "https://www.googleapis.com/auth/gmail.send"
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"response_type=code&"
            f"scope={scopes}&"
            f"access_type=offline&"
            f"prompt=consent"
        )
        
        if state:
            auth_url += f"&state={state}"
        
        return auth_url
    
    async def exchange_code_for_tokens(self, code: str) -> Dict:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from Google
        
        Returns:
            Dict with access_token, refresh_token, and expires_in
        
        Raises:
            Exception: If token exchange fails
        """
        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Calculate expiration time
                expires_in = result.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                return {
                    "access_token": result.get("access_token"),
                    "refresh_token": result.get("refresh_token"),
                    "expires_at": expires_at,
                    "token_type": result.get("token_type")
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Google OAuth error: {e.response.text}")
            raise Exception(f"Failed to exchange code for tokens: {e.response.text}")
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {str(e)}")
            raise
    
    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: Refresh token
        
        Returns:
            Dict with new access_token and expires_in
        
        Raises:
            Exception: If token refresh fails
        """
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Calculate expiration time
                expires_in = result.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                return {
                    "access_token": result.get("access_token"),
                    "expires_at": expires_at,
                    "token_type": result.get("token_type")
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Token refresh error: {e.response.text}")
            raise Exception(f"Failed to refresh token: {e.response.text}")
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise
    
    async def send_email(
        self,
        access_token: str,
        from_email: str,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> Dict:
        """
        Send an email via Gmail API.
        
        Args:
            access_token: Valid OAuth access token
            from_email: Sender email (must match the authenticated Gmail account)
            to_email: Recipient email address
            to_name: Recipient name (optional)
            subject: Email subject
            html_body: HTML body
            text_body: Plain text body (optional)
        
        Returns:
            Dict with message_id and status
        
        Raises:
            Exception: If email sending fails
        """
        try:
            # Create message
            if text_body:
                # Multipart message with both HTML and text
                message = MIMEMultipart('alternative')
                message['From'] = from_email
                message['To'] = f"{to_name} <{to_email}>" if to_name else to_email
                message['Subject'] = subject
                
                # Attach both parts
                part1 = MIMEText(text_body, 'plain')
                part2 = MIMEText(html_body, 'html')
                message.attach(part1)
                message.attach(part2)
            else:
                # HTML only message
                message = MIMEText(html_body, 'html')
                message['From'] = from_email
                message['To'] = f"{to_name} <{to_email}>" if to_name else to_email
                message['Subject'] = subject
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send via Gmail API
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "raw": raw_message
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.gmail_api_url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "message_id": result.get("id"),
                    "thread_id": result.get("threadId"),
                    "provider": "gmail"
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Gmail API error: {e.response.text}")
            raise Exception(f"Failed to send email via Gmail: {e.response.text}")
        except Exception as e:
            logger.error(f"Error sending email via Gmail: {str(e)}")
            raise
    
    async def get_user_info(self, access_token: str) -> Dict:
        """
        Get user information from Google.
        
        Args:
            access_token: Valid OAuth access token
        
        Returns:
            Dict with user email and name
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                return {
                    "email": result.get("email"),
                    "name": result.get("name"),
                    "verified_email": result.get("verified_email", False)
                }
                
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            raise

