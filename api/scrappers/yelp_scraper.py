"""
Yelp scraper for fetching business prospects.
"""
from typing import List, Optional
from urllib.parse import quote, urljoin
import asyncio
import logging
import re
from models.prospect import ProspectCreate
from enums.source import Source
from services.validation_service import validation_service
from services.address_service import address_service
from .base_scraper import BaseScraper
from .email_scraper import email_scraper

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


logger = logging.getLogger(__name__)


class YelpScraper(BaseScraper):
    """
    Yelp scraper for extracting business prospect data.
    
    This scraper uses Playwright to interact with Yelp
    and extract business information including name, address,
    phone, website, and category. Only businesses without websites
    are targeted.
    """
    
    def __init__(self):
        """Initialize the Yelp scraper."""
        super().__init__(source=Source.YELP)
        self.playwright = None
        self.browser = None
        self.base_url = "https://www.yelp.fr"
    
    async def ensure_browser(self) -> None:
        """
        Ensure browser is initialized and running.
        
        Raises:
            RuntimeError: If Playwright is not available
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Install it with: pip install playwright")
        
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-breakpad",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--disable-renderer-backgrounding",
                    "--force-color-profile=srgb",
                    "--metrics-recording-only",
                    "--mute-audio",
                    "--no-first-run",
                    "--enable-automation",
                    "--password-store=basic",
                    "--use-mock-keychain",
                    "--js-flags=--max-old-space-size=512"
                ]
            )
    
    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.browser = None
        self.playwright = None
        
        # Also close email scraper browser
        if email_scraper.browser:
            await email_scraper.close()
    
    @staticmethod
    def build_url(category: str, city: str) -> str:
        """
        Build search URL for Yelp.
        
        Args:
            category: Business category (e.g., "plombier", "restaurant")
            city: City name
            
        Returns:
            URL for Yelp search
        """
        # Yelp France uses format: /search?find_desc=category&find_loc=city
        search_category = quote(category)
        search_city = quote(city)
        return f"https://www.yelp.fr/search?find_desc={search_category}&find_loc={search_city}"
    
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
    
    async def accept_cookies(self, page) -> None:
        """
        Accept cookies modal if present.
        
        Args:
            page: Playwright page object
        """
        try:
            selectors = [
                'button[aria-label*="Tout accepter"]',
                'button:has-text("Tout accepter")',
                'button:has-text("Accepter")',
                '#onetrust-accept-btn-handler',
                '.ot-btn-primary'
            ]
            
            for selector in selectors:
                try:
                    accept_button = page.locator(selector)
                    if await accept_button.count() > 0:
                        await accept_button.first.wait_for(state="visible", timeout=2000)
                        await accept_button.first.click()
                        logger.info(f"Cookie consent accepted using selector: {selector}")
                        await asyncio.sleep(0.2)
                        return
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
                    
            logger.debug("No cookie consent modal found")
        except Exception as e:
            logger.debug(f"Could not handle cookie consent: {e}")
    
    async def extract_prospect_details(self, page, business_url: str) -> Optional[ProspectCreate]:
        """
        Extract prospect details from business page.
        
        Args:
            page: Playwright page object
            business_url: URL to business page
            
        Returns:
            ProspectCreate object or None if extraction fails
        """
        try:
            # Navigate to business page
            full_url = urljoin(self.base_url, business_url)
            await page.goto(full_url, wait_until="domcontentloaded", timeout=10000)
            
            # Accept cookies if present
            await self.accept_cookies(page)
            
            # Extract name
            name = None
            try:
                name_selectors = [
                    'h1[data-font-weight="semibold"]',
                    'h1.css-1se8maq',
                    'h1'
                ]
                for selector in name_selectors:
                    name_elem = page.locator(selector)
                    if await name_elem.count() > 0:
                        name = await name_elem.first.inner_text()
                        if name and name.strip():
                            break
            except Exception as e:
                logger.warning(f"Name not found: {e}")
                return None
            
            if not name:
                return None
            
            # Extract category
            category = ""
            try:
                category_selectors = [
                    'a[href*="/c/"]',
                    '.category-str-list a'
                ]
                for selector in category_selectors:
                    category_elem = page.locator(selector)
                    if await category_elem.count() > 0:
                        categories = await category_elem.all_inner_texts()
                        category = ", ".join(categories[:2])
                        break
                
                if not category:
                    category = "Inconnu"
            except Exception as e:
                logger.debug(f"Could not extract category: {e}")
                category = "Inconnu"
            
            # Extract phone
            phone = None
            try:
                phone_selectors = [
                    'p:has-text("Téléphone")',
                    '[aria-label*="Téléphone"]',
                    'p.css-1p9ibgf:has-text("0")'
                ]
                for selector in phone_selectors:
                    phone_elem = page.locator(selector)
                    if await phone_elem.count() > 0:
                        phone_text = await phone_elem.first.inner_text()
                        # Extract just the phone number
                        phone_match = re.search(r'[\d\s\.\-]+', phone_text)
                        if phone_match:
                            phone = phone_match.group(0).strip()
                            break
            except Exception as e:
                logger.debug(f"Could not extract phone: {e}")
            
            # Extract address
            address = None
            try:
                address_selectors = [
                    'address p',
                    '[itemprop="streetAddress"]',
                    'p.css-qyp8bo'
                ]
                for selector in address_selectors:
                    address_elem = page.locator(selector)
                    if await address_elem.count() > 0:
                        address = await address_elem.first.inner_text()
                        if address and address.strip():
                            break
            except Exception as e:
                logger.debug(f"Could not extract address: {e}")
            
            # Extract city
            city = self.extract_city(address) if address else "Inconnue"
            
            # Clean address
            if address:
                address = address_service.remove_city_and_postal_code(address, city)
            
            # Extract website
            website = None
            try:
                website_selectors = [
                    'a:has-text("Site Web")',
                    'a[href*="biz_redir"]',
                    'a.css-1um3nx:has-text("Site")'
                ]
                for selector in website_selectors:
                    website_elem = page.locator(selector)
                    if await website_elem.count() > 0:
                        href = await website_elem.first.get_attribute("href")
                        if href and validation_service.is_valid_website(href):
                            website = href
                            break
            except Exception as e:
                logger.debug(f"Could not extract website: {e}")
            
            # Only return prospect if no website
            if website:
                logger.info(f"Prospect {name} has a website, skipping")
                return None
            
            # Try to find email
            email = None
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
                source=Source.YELP,
                confidence=min(confidence, 4)
            )
            
            logger.info(f"Extracted: {prospect}")
            return prospect
        
        except Exception as e:
            logger.error(f"Error extracting prospect details: {e}")
            return None
    
    async def scrape(
        self,
        category: str,
        city: str,
        max_results: int = 50
    ) -> List[ProspectCreate]:
        """
        Scrape prospects from Yelp without websites.
        
        Args:
            category: Business category to search for
            city: City to search in
            max_results: Maximum number of results to return
            
        Returns:
            List of ProspectCreate objects without websites
        """
        logger.info(f"[Yelp] Starting scrape for category={category}, city={city}, max_results={max_results}")
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available, returning empty results")
            return []
        
        await self.start()
        
        try:
            await self.ensure_browser()
            
            context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="fr-FR",
                java_script_enabled=True,
                ignore_https_errors=False,
                bypass_csp=False
            )
            
            page = await context.new_page()
            page.set_default_timeout(10000)
            
            try:
                # Navigate to search page
                url = self.build_url(category, city)
                logger.info(f"Scraping Yelp: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                
                # Accept cookies if present
                await self.accept_cookies(page)
                
                # Wait for results
                try:
                    await page.wait_for_selector('ul[role="list"]', timeout=10000)
                except PlaywrightTimeoutError:
                    logger.info("No results found on Yelp")
                    return []
                
                # Get all business links
                business_links = []
                link_selectors = [
                    'a[href*="/biz/"]',
                    'h3 a',
                    'a.css-19v1rkv'
                ]
                
                for selector in link_selectors:
                    links = page.locator(selector)
                    count = await links.count()
                    if count > 0:
                        for i in range(min(count, max_results * 3)):
                            try:
                                href = await links.nth(i).get_attribute('href')
                                if href and '/biz/' in href and href not in business_links:
                                    business_links.append(href)
                            except:
                                continue
                        if business_links:
                            break
                
                logger.info(f"Found {len(business_links)} business links")
                
                prospects = []
                
                # Process each business
                for i, link in enumerate(business_links[:max_results * 3]):
                    if len(prospects) >= max_results:
                        break
                    
                    try:
                        detail_page = await context.new_page()
                        detail_page.set_default_timeout(8000)
                        try:
                            prospect = await self.extract_prospect_details(detail_page, link)
                            if prospect:
                                prospects.append(prospect)
                        finally:
                            await detail_page.close()
                        
                        await asyncio.sleep(0.3)
                    
                    except Exception as e:
                        logger.error(f"Error processing business {i}: {e}")
                        continue
                
                logger.info(f"Yelp scraping complete: {len(prospects)} prospects without websites")
                return prospects
            
            except Exception as e:
                logger.error(f"Error in Yelp scraping: {e}", exc_info=True)
                return []
            finally:
                await context.close()
        
        finally:
            await self.stop()

