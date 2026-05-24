"""
Validation service for prospect data.
"""
from typing import Optional


class ValidationService:
    """
    Service for validating prospect data.
    
    This service provides utility methods for validating
    and checking prospect information such as websites,
    contact details, etc.
    """
    
    @staticmethod
    def is_valid_website(url: Optional[str]) -> bool:
        """
        Check if a website URL is valid (not a social media platform).
        
        This method filters out social media URLs and determines
        if a URL points to a real business website.
        
        Args:
            url: Website URL to validate
            
        Returns:
            True if URL points to a valid business website, False otherwise
            
        Examples:
            >>> ValidationService.is_valid_website("https://www.example.com")
            True
            
            >>> ValidationService.is_valid_website("https://www.facebook.com/mybusiness")
            False
            
            >>> ValidationService.is_valid_website("http://example.fr")
            True
        """
        if not url:
            return False
        
        # Remove protocol if present
        url_clean = url.replace("http://", "").replace("https://", "").replace("www.", "").strip()
        
        # List of invalid domains (social media platforms)
        invalid_domains = [
            "facebook.com",
            "instagram.com",
            "twitter.com",
            "linkedin.com",
            "youtube.com",
            "pinterest.com",
            "tiktok.com",
            "snapchat.com"
        ]
        
        # Check if URL contains any invalid domain
        for domain in invalid_domains:
            if domain in url_clean:
                return False
        
        # Check if it's a real website (contains a dot and not just a domain name)
        if "." in url_clean and not url_clean.startswith("www."):
            # Basic validation: should have at least domain name
            parts = url_clean.split("/")
            domain = parts[0]
            
            # Domain should have at least one dot (e.g., example.com)
            if domain.count(".") >= 1:
                # Split domain and check parts
                domain_parts = domain.split(".")
                # Should have at least 2 parts (name and extension)
                if len(domain_parts) >= 2 and len(domain_parts[0]) > 0:
                    return True
        
        return False
    
    @staticmethod
    def is_valid_email(email: Optional[str]) -> bool:
        """
        Check if an email address is valid.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email is valid, False otherwise
        """
        if not email:
            return False
        
        # Basic email pattern validation
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def normalize_phone(phone: Optional[str]) -> Optional[str]:
        """
        Normalize phone number format.
        
        Removes spaces, dashes, and other formatting characters
        to standardize phone number format.
        
        Args:
            phone: Phone number to normalize
            
        Returns:
            Normalized phone number or None if invalid
        """
        if not phone:
            return None
        
        # Remove common formatting characters
        normalized = phone.replace(" ", "").replace("-", "").replace(".", "").replace("(", "").replace(")", "")
        
        # Remove leading + if present
        if normalized.startswith("+"):
            normalized = normalized[1:]
        
        # Check if it's a valid phone number (at least 9 digits)
        if normalized and normalized.isdigit() and len(normalized) >= 9:
            return normalized
        
        return phone  # Return original if normalization failed
    
    @staticmethod
    def calculate_confidence_score(
        phone: Optional[str] = None,
        address: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None
    ) -> int:
        """
        Calculate confidence score based on data completeness.
        
        Score rules:
        - Base score: 1 (for name, category, source)
        - +1 if phone is present
        - +1 if address is present with street number
        - -1 if website is present and valid
        - +1 if email is present and valid
        - Maximum score: 4
        
        Args:
            phone: Phone number
            address: Full address
            email: Email address
            website: Website URL
            
        Returns:
            Confidence score from 1 to 4
        """
        score = 1  # Base score
        
        if phone and phone.strip():
            score += 1
        
        if address and address.strip() and any(c.isdigit() for c in address):
            score += 1
        
        if website and ValidationService.is_valid_website(website):
            score -= 1
        
        if email and ValidationService.is_valid_email(email):
            score += 1
        
        return min(max(score, 1), 4)


# Global service instance
validation_service = ValidationService()

