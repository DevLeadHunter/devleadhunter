"""
Mailjet email service for sending emails via Mailjet API.
"""
import logging
from typing import Optional, Dict
import httpx
import base64
from datetime import datetime

from core.config import settings

logger = logging.getLogger(__name__)


class MailjetService:
    """
    Service for sending emails via Mailjet API.
    
    Requires MAILJET_API_KEY and MAILJET_SECRET_KEY in environment variables.
    """
    
    def __init__(self):
        """Initialize Mailjet service."""
        self.api_key = settings.mailjet_api_key
        self.secret_key = settings.mailjet_secret_key
        self.api_url = "https://api.mailjet.com/v3.1/send"
        
        # Create basic auth header
        credentials = f"{self.api_key}:{self.secret_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
    
    async def send_email(
        self,
        from_email: str,
        from_name: str,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        custom_id: Optional[str] = None
    ) -> Dict:
        """
        Send a single email via Mailjet.
        
        Args:
            from_email: Sender email address
            from_name: Sender name
            to_email: Recipient email address
            to_name: Recipient name (optional)
            subject: Email subject
            html_body: HTML body
            text_body: Plain text body (optional)
            custom_id: Custom ID for tracking (optional)
        
        Returns:
            Dict with message_id and status
        
        Raises:
            Exception: If email sending fails
        """
        # Prepare recipient
        recipient = {"Email": to_email}
        if to_name:
            recipient["Name"] = to_name
        
        # Prepare message
        message = {
            "From": {
                "Email": from_email,
                "Name": from_name
            },
            "To": [recipient],
            "Subject": subject,
            "HTMLPart": html_body
        }
        
        # Add text part if provided
        if text_body:
            message["TextPart"] = text_body
        
        # Add custom ID for tracking
        if custom_id:
            message["CustomID"] = custom_id
        
        # Prepare payload
        payload = {
            "Messages": [message]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract message info from response
                if result.get("Messages") and len(result["Messages"]) > 0:
                    message_result = result["Messages"][0]
                    return {
                        "success": True,
                        "message_id": str(message_result.get("To", [{}])[0].get("MessageID")),
                        "status": message_result.get("Status"),
                        "provider": "mailjet"
                    }
                else:
                    raise Exception("No message info in Mailjet response")
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Mailjet API error: {e.response.text}")
            raise Exception(f"Failed to send email via Mailjet: {e.response.text}")
        except Exception as e:
            logger.error(f"Error sending email via Mailjet: {str(e)}")
            raise
    
    async def verify_dns_records(self, domain: str) -> Dict:
        """
        Verify DNS records (SPF/DKIM) for a domain.
        
        Note: This is a placeholder. In production, you would:
        1. Check actual DNS records using dnspython
        2. Query Mailjet API for domain verification status
        3. Provide specific SPF/DKIM records to add
        
        Args:
            domain: Domain name to verify
        
        Returns:
            Dict with verification status and instructions
        """
        # For now, return instructions for manual setup
        # In production, implement actual DNS checking
        
        spf_record = f"v=spf1 include:spf.mailjet.com ~all"
        dkim_instructions = (
            "To set up DKIM:\n"
            "1. Go to Mailjet dashboard\n"
            "2. Add and verify your domain\n"
            "3. Copy the DKIM DNS records provided\n"
            "4. Add them to your domain's DNS settings"
        )
        
        return {
            "spf_verified": False,  # Would check actual DNS in production
            "dkim_verified": False,  # Would check actual DNS in production
            "spf_record": spf_record,
            "dkim_instructions": dkim_instructions,
            "instructions": (
                f"To send emails from {domain}, you need to:\n\n"
                f"1. Add this SPF record to your DNS:\n"
                f"   Type: TXT\n"
                f"   Host: @\n"
                f"   Value: {spf_record}\n\n"
                f"2. Set up DKIM in Mailjet dashboard:\n"
                f"   {dkim_instructions}"
            )
        }
    
    async def get_email_statistics(self, message_id: str) -> Optional[Dict]:
        """
        Get statistics for a sent email.
        
        Args:
            message_id: Mailjet message ID
        
        Returns:
            Dict with email statistics or None if not found
        """
        # This would query Mailjet's statistics API
        # Placeholder implementation
        return {
            "message_id": message_id,
            "status": "sent",
            "delivered": False,
            "opened": False,
            "clicked": False
        }

