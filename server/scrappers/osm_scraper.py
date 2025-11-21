"""
OpenStreetMap (Nominatim) scraper for fetching business prospects.
"""
from typing import List, Optional
import asyncio
import logging
import re
import aiohttp
from models.prospect import ProspectCreate
from enums.source import Source
from services.validation_service import validation_service
from services.address_service import address_service
from .base_scraper import BaseScraper
from .email_scraper import email_scraper

logger = logging.getLogger(__name__)


class OSMScraper(BaseScraper):
    """
    OpenStreetMap scraper for extracting business prospect data.
    
    This scraper uses the Nominatim API to search for businesses
    and extract information including name, address, phone, and category.
    Only businesses without websites are targeted.
    """
    
    def __init__(self):
        """Initialize the OSM scraper."""
        super().__init__(source=Source.OSM)
        self.base_url = "https://nominatim.openstreetmap.org"
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def ensure_session(self) -> None:
        """Ensure HTTP session is initialized."""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "DevLeadHunter/1.0 (Prospect Tool)",
                    "Accept": "application/json"
                }
            )
    
    async def close(self) -> None:
        """Close HTTP session and cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None
        
        # Also close email scraper browser
        if email_scraper.browser:
            await email_scraper.close()
    
    @staticmethod
    def extract_city(address: str) -> str:
        """
        Extract city from full address.
        
        Args:
            address: Full address string
            
        Returns:
            Extracted city name
        """
        if not address:
            return "Inconnue"
        
        # Chercher un code postal français (5 chiffres consécutifs)
        postal_code_pattern = r'\b(\d{5})\s+(.+)$'
        match = re.search(postal_code_pattern, address)
        
        if match:
            city = match.group(2).strip()
            return city
        
        # Fallback: prendre après la virgule ou le dernier élément
        if ',' in address:
            parts = [p.strip() for p in address.split(',')]
            return parts[-1]
        
        parts = address.split()
        if len(parts) >= 2:
            return parts[-1]
        return "Inconnue"
    
    def build_overpass_query(self, category: str, city: str) -> str:
        """
        Build Overpass API query for searching businesses.
        
        Args:
            category: Business category (e.g., "plombier", "restaurant")
            city: City name
            
        Returns:
            Overpass QL query string
        """
        # Map categories to OSM tags
        category_tags = {
            "restaurant": "amenity=restaurant",
            "plombier": "craft=plumber",
            "electricien": "craft=electrician",
            "coiffeur": "shop=hairdresser",
            "boulangerie": "shop=bakery",
            "garage": "shop=car_repair"
        }
        
        tag = category_tags.get(category.lower(), f"name~'{category}'")
        
        # Overpass query to search in area
        query = f"""
        [out:json][timeout:25];
        area["name"="{city}"]["admin_level"~"[8-9]"]->.searchArea;
        (
          node[{tag}](area.searchArea);
          way[{tag}](area.searchArea);
          relation[{tag}](area.searchArea);
        );
        out body;
        >;
        out skel qt;
        """
        
        return query
    
    async def search_overpass(self, category: str, city: str, max_results: int) -> List[dict]:
        """
        Search for businesses using Overpass API.
        
        Args:
            category: Business category
            city: City name
            max_results: Maximum number of results
            
        Returns:
            List of business data dictionaries
        """
        try:
            await self.ensure_session()
            
            query = self.build_overpass_query(category, city)
            
            async with self.session.post(
                self.overpass_url,
                data={"data": query},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    logger.error(f"Overpass API error: {response.status}")
                    return []
                
                data = await response.json()
                elements = data.get("elements", [])
                
                # Filter and process results
                businesses = []
                for elem in elements[:max_results * 2]:
                    tags = elem.get("tags", {})
                    if not tags.get("name"):
                        continue
                    
                    businesses.append({
                        "id": elem.get("id"),
                        "type": elem.get("type"),
                        "lat": elem.get("lat"),
                        "lon": elem.get("lon"),
                        "tags": tags
                    })
                
                logger.info(f"Found {len(businesses)} businesses from Overpass API")
                return businesses[:max_results * 2]
        
        except asyncio.TimeoutError:
            logger.error("Overpass API timeout")
            return []
        except Exception as e:
            logger.error(f"Error querying Overpass API: {e}")
            return []
    
    async def extract_prospect_from_osm_data(self, business: dict, city_search: str) -> Optional[ProspectCreate]:
        """
        Extract prospect details from OSM business data.
        
        Args:
            business: Business data from OSM/Overpass
            city_search: City searched for
            
        Returns:
            ProspectCreate object or None if extraction fails
        """
        try:
            tags = business.get("tags", {})
            
            # Extract name
            name = tags.get("name")
            if not name:
                return None
            
            # Extract category
            category = (
                tags.get("amenity") or 
                tags.get("shop") or 
                tags.get("craft") or 
                tags.get("cuisine") or
                "Inconnu"
            )
            
            # Extract phone
            phone = tags.get("phone") or tags.get("contact:phone")
            
            # Extract address components
            street = tags.get("addr:street", "")
            housenumber = tags.get("addr:housenumber", "")
            postcode = tags.get("addr:postcode", "")
            city_tag = tags.get("addr:city", city_search)
            
            # Build address
            address_parts = []
            if housenumber:
                address_parts.append(housenumber)
            if street:
                address_parts.append(street)
            
            address = " ".join(address_parts) if address_parts else None
            full_address = f"{address} {postcode} {city_tag}" if address else None
            
            # Extract city
            city = city_tag if city_tag else city_search
            
            # Clean address
            if address:
                address = address_service.remove_city_and_postal_code(address, city)
            
            # Extract website
            website = tags.get("website") or tags.get("contact:website")
            if website and not validation_service.is_valid_website(website):
                website = None
            
            # Only return prospect if no website
            if website:
                logger.info(f"Prospect {name} has a website, skipping")
                return None
            
            # Try to find email
            email = tags.get("email") or tags.get("contact:email")
            if not email:
                try:
                    email = await email_scraper.find_email(name, city)
                    if email:
                        logger.info(f"Found email for {name}: {email}")
                except Exception as e:
                    logger.debug(f"Could not find email: {e}")
            
            # Calculate confidence
            confidence = validation_service.calculate_confidence_score(
                phone=phone,
                address=address,
                email=email,
                website=website
            )
            
            prospect = ProspectCreate(
                name=name.strip(),
                address=address,
                city=city,
                phone=phone,
                email=email,
                website=website,
                category=category,
                source=Source.OSM,
                confidence=min(confidence, 4)
            )
            
            logger.info(f"Extracted: {prospect}")
            return prospect
        
        except Exception as e:
            logger.error(f"Error extracting prospect from OSM data: {e}")
            return None
    
    async def scrape(
        self,
        category: str,
        city: str,
        max_results: int = 50
    ) -> List[ProspectCreate]:
        """
        Scrape prospects from OpenStreetMap without websites.
        
        Args:
            category: Business category to search for
            city: City to search in
            max_results: Maximum number of results to return
            
        Returns:
            List of ProspectCreate objects without websites
        """
        logger.info(f"[OSM] Starting scrape for category={category}, city={city}, max_results={max_results}")
        
        await self.start()
        
        try:
            await self.ensure_session()
            
            # Search using Overpass API
            businesses = await self.search_overpass(category, city, max_results)
            
            if not businesses:
                logger.info("No results found on OpenStreetMap")
                return []
            
            prospects = []
            
            # Process each business
            for business in businesses:
                if len(prospects) >= max_results:
                    break
                
                try:
                    prospect = await self.extract_prospect_from_osm_data(business, city)
                    if prospect:
                        prospects.append(prospect)
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                
                except Exception as e:
                    logger.error(f"Error processing business: {e}")
                    continue
            
            logger.info(f"OSM scraping complete: {len(prospects)} prospects without websites")
            return prospects
        
        except Exception as e:
            logger.error(f"Error in OSM scraping: {e}", exc_info=True)
            return []
        
        finally:
            await self.stop()

