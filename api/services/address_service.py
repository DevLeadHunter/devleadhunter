"""
Service for cleaning and processing addresses.
"""
import re
from typing import Optional


class AddressService:
    """Service for address cleaning operations."""
    
    def __init__(self):
        pass
    
    def remove_postal_code(self, address: Optional[str]) -> Optional[str]:
        """
        Remove postal code from address.
        
        Args:
            address: Address string that may contain postal code
            
        Returns:
            Address without postal code
        """
        if not address:
            return address
        
        # Pattern for French postal codes: 5 digits at the beginning or after a word boundary
        # Matches: "12345 ", "12345", "Paris 12345", etc.
        postal_code_pattern = r'\b\d{5}\b\s*'
        cleaned_address = re.sub(postal_code_pattern, '', address)
        return cleaned_address.strip()
    
    def remove_city(self, address: Optional[str], city: Optional[str]) -> Optional[str]:
        """
        Remove city name from address.
        
        Args:
            address: Address string that may contain city name
            city: City name to remove from address
            
        Returns:
            Address without city name
        """
        if not address or not city:
            return address
        
        # Remove the city name (case insensitive)
        # Use word boundaries but allow multi-word city names
        # Escape special characters but allow spaces in city name
        escaped_city = re.escape(city)
        # Remove word boundaries within the city name pattern to allow multi-word cities
        pattern = rf'\s+{escaped_city}\s*$'
        cleaned_address = re.sub(pattern, '', address, flags=re.IGNORECASE)
        # Also try without the leading space requirement
        if cleaned_address == address:
            pattern = rf'\b{escaped_city}\b\s*'
            cleaned_address = re.sub(pattern, '', address, flags=re.IGNORECASE)
        return cleaned_address.strip()
    
    def remove_city_and_postal_code(self, address: Optional[str], city: Optional[str]) -> Optional[str]:
        """
        Remove postal code and city from address.
        
        Args:
            address: Address string that may contain postal code and city
            city: City name to remove from address
            
        Returns:
            Cleaned address without postal code and city
        """
        if not address:
            return address
        
        # First remove postal code
        cleaned = self.remove_postal_code(address)
        
        # Then remove city
        cleaned = self.remove_city(cleaned, city)
        
        return cleaned.strip()


# Singleton instance
address_service = AddressService()

