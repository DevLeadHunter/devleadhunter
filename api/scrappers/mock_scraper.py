"""
Mock scraper for testing and development.
"""
from typing import List
import random
from models.prospect import ProspectCreate
from enums.source import Source
from .base_scraper import BaseScraper


class MockScraper(BaseScraper):
    """
    Mock scraper that generates fake prospect data.
    
    This scraper is used for development and testing purposes.
    It generates random prospect data based on the provided
    category and city.
    """
    
    def __init__(self):
        """Initialize the mock scraper."""
        super().__init__(source=Source.MOCK)
        
        self._names = {
            "restaurant": ["Le Bon Goût", "Chez Marie", "La Cantine", "Bistro Cozy", "Le Gourmet"],
            "plombier": ["Plomberie Pro", "Dépannage Rapide", "Artisan Plombier", "SOS Plomberie", "Plomberie Expert"],
            "electricien": ["Électricité Pro", "Dépannage Elec", "Artisan Électricien", "SOS Électricité", "Elec Expert"],
            "coiffeur": ["Salon Chic", "Hair Style", "Coiffure Moderne", "Hair Design", "Salon Beauté"],
            "garage": ["Garage Auto", "Auto Service", "Méca Pro", "Auto Dépannage", "Garage Expert"]
        }
        
        self._suffixes = {
            "restaurant": ["Restaurant", "Bistro", "Café", "Brasserie"],
            "plombier": ["Plomberie", "Chauffage"],
            "electricien": ["Électricité", "Éclairage"],
            "coiffeur": ["Coiffure", "Salon"],
            "garage": ["Garage", "Auto"]
        }
    
    async def scrape(
        self, 
        category: str, 
        city: str, 
        max_results: int = 50
    ) -> List[ProspectCreate]:
        """
        Generate mock prospect data.
        
        Args:
            category: Business category
            city: City name
            max_results: Number of mock results to generate
            
        Returns:
            List of mock ProspectCreate objects
        """
        await self.start()
        
        try:
            prospects = []
            
            # Generate random prospects
            for i in range(min(max_results, 20)):  # Limit to 20 for performance
                name = self._generate_name(category, i)
                address = self._generate_address(city)
                phone = self._generate_phone()
                email = self._generate_email(name)
                website = self._generate_website(name) if random.random() > 0.3 else None
                
                prospect = ProspectCreate(
                    name=name,
                    address=address,
                    city=city,
                    phone=phone,
                    email=email,
                    website=website,
                    category=category,
                    source=Source.MOCK,
                    confidence=random.randint(1, 4)
                )
                
                prospects.append(prospect)
            
            return prospects
        
        finally:
            await self.stop()
    
    def _generate_name(self, category: str, index: int) -> str:
        """Generate a business name."""
        names = self._names.get(category, ["Business"])
        suffixes = self._suffixes.get(category, ["Services"])
        
        if index < len(names):
            return f"{names[index]}"
        else:
            return f"{random.choice(names)} {random.choice(suffixes)}"
    
    def _generate_address(self, city: str) -> str:
        """Generate a street address."""
        street_number = random.randint(1, 200)
        streets = ["Rue de la Paix", "Avenue des Champs", "Boulevard Saint-Michel", 
                   "Rue de Paris", "Place Centrale", "Rue du Commerce"]
        return f"{street_number} {random.choice(streets)}, {city}"
    
    def _generate_phone(self) -> str:
        """Generate a phone number."""
        return f"+331{random.randint(10000000, 99999999)}"
    
    def _generate_email(self, business_name: str) -> str:
        """Generate an email address."""
        name_part = business_name.lower().replace(" ", "").replace("é", "e")
        domains = ["contact", "info", "commercial", "service"]
        return f"{random.choice(domains)}@{name_part}.fr"
    
    def _generate_website(self, business_name: str) -> str:
        """Generate a website URL."""
        name_part = business_name.lower().replace(" ", "-").replace("é", "e")
        return f"https://www.{name_part}.fr"

