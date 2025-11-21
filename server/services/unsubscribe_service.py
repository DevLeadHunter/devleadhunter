"""
Unsubscribe service for managing email unsubscriptions (RGPD compliance).
"""
from typing import Optional
from sqlalchemy.orm import Session
import secrets

from models.email_unsubscribe import EmailUnsubscribe


class UnsubscribeService:
    """Service for managing email unsubscriptions."""
    
    def is_unsubscribed(self, db: Session, email: str) -> bool:
        """
        Check if an email address is unsubscribed.
        
        Args:
            db: Database session
            email: Email address to check
            
        Returns:
            True if unsubscribed, False otherwise
        """
        unsubscribe = db.query(EmailUnsubscribe).filter(
            EmailUnsubscribe.email == email.lower()
        ).first()
        
        return unsubscribe is not None
    
    def unsubscribe(
        self,
        db: Session,
        email: str,
        prospect_id: Optional[int] = None,
        user_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> EmailUnsubscribe:
        """
        Unsubscribe an email address.
        
        Args:
            db: Database session
            email: Email address to unsubscribe
            prospect_id: Optional prospect ID
            user_id: Optional user ID
            reason: Optional reason for unsubscribing
            
        Returns:
            Created or existing unsubscribe record
        """
        # Check if already unsubscribed
        existing = db.query(EmailUnsubscribe).filter(
            EmailUnsubscribe.email == email.lower()
        ).first()
        
        if existing:
            return existing
        
        # Create new unsubscribe record
        unsubscribe = EmailUnsubscribe(
            email=email.lower(),
            prospect_id=prospect_id,
            user_id=user_id,
            reason=reason
        )
        
        db.add(unsubscribe)
        db.commit()
        db.refresh(unsubscribe)
        
        return unsubscribe
    
    def resubscribe(self, db: Session, email: str) -> bool:
        """
        Resubscribe an email address (remove from unsubscribe list).
        
        Args:
            db: Database session
            email: Email address to resubscribe
            
        Returns:
            True if resubscribed, False if not found
        """
        unsubscribe = db.query(EmailUnsubscribe).filter(
            EmailUnsubscribe.email == email.lower()
        ).first()
        
        if not unsubscribe:
            return False
        
        db.delete(unsubscribe)
        db.commit()
        
        return True
    
    def generate_unsubscribe_link(
        self,
        email: str,
        prospect_id: Optional[int] = None,
        base_url: str = "http://localhost:8000"
    ) -> str:
        """
        Generate an unsubscribe link for an email.
        
        Args:
            email: Email address
            prospect_id: Optional prospect ID
            base_url: Base URL of the application
            
        Returns:
            Unsubscribe link URL
        """
        # For security, we'll use a simple token-based system
        # In production, consider using JWT tokens with expiration
        from urllib.parse import quote
        
        email_encoded = quote(email)
        link = f"{base_url}/api/v1/unsubscribe?email={email_encoded}"
        
        if prospect_id:
            link += f"&prospect_id={prospect_id}"
        
        return link
    
    def add_unsubscribe_footer(self, html_body: str, unsubscribe_link: str) -> str:
        """
        Add unsubscribe footer to email HTML body.
        
        Args:
            html_body: Original HTML body
            unsubscribe_link: Unsubscribe link URL
            
        Returns:
            HTML body with unsubscribe footer
        """
        footer = f"""
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #999; text-align: center;">
    <p>
        Vous recevez cet email car vous êtes dans notre liste de prospects.
    </p>
    <p>
        <a href="{unsubscribe_link}" style="color: #999; text-decoration: underline;">
            Se désabonner
        </a>
    </p>
</div>
"""
        
        # Try to insert before closing </body> tag
        if '</body>' in html_body:
            html_body = html_body.replace('</body>', f'{footer}</body>')
        else:
            # If no </body> tag, append to end
            html_body += footer
        
        return html_body


# Singleton instance
unsubscribe_service = UnsubscribeService()

