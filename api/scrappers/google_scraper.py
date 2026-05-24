"""
Google Maps scraper for fetching business prospects.
"""
from typing import List, Optional
from urllib.parse import quote
import asyncio
import logging
from models.prospect import ProspectCreate
from enums.source import Source
from services.validation_service import validation_service
from .base_scraper import BaseScraper
from .email_scraper import email_scraper

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


logger = logging.getLogger(__name__)


class GoogleScraper(BaseScraper):
    """
    Google Maps scraper for extracting business prospect data.
    
    This scraper uses Playwright to interact with Google Maps
    and extract business information including name, address,
    phone, website, and category.
    """
    
    def __init__(self):
        """Initialize the Google scraper."""
        super().__init__(source=Source.GOOGLE)
        self.playwright = None
        self.browser = None
    
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
    async def accept_cookies(page) -> bool:
        """
        Accept cookies on Google Maps.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if cookies were accepted, False otherwise
        """
        try:
            accept_selectors = [
                'button[aria-label*="Tout accepter"]',
                'button:has-text("Tout accepter")',
                'input[value="Tout accepter"]',
                'button[jsname="j6LkBc"]',
            ]
            
            for selector in accept_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    await page.click(selector)
                    logger.info("Cookies accepted")
                    await asyncio.sleep(0.5)
                    return True
                except PlaywrightTimeoutError:
                    continue
            
            logger.warning("No 'Accept All' button found")
            return False
        except Exception as e:
            logger.error(f"Error accepting cookies: {e}")
            return False
    
    @staticmethod
    async def accept_web_modal(page) -> bool:
        """
        Accept the "Stay on web" modal.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if modal was accepted, False otherwise
        """
        try:
            await page.wait_for_selector('[class*="qgMOee"]', timeout=5000)
            await page.click('[class*="qgMOee"]')
            logger.info("Web modal accepted")
            await asyncio.sleep(0.5)
            return True
        except PlaywrightTimeoutError:
            return False
        except Exception as e:
            logger.error(f"Error accepting web modal: {e}")
            return False
    
    @staticmethod
    def build_query(category: Optional[str], city: Optional[str]) -> str:
        """
        Build search query for Google Maps.
        
        Args:
            category: Business category (e.g., "restaurant", "plombier")
            city: City name
            
        Returns:
            URL-encoded search query
        """
        parts = []
        if category:
            parts.append(category)
        if city:
            parts.append(f"à {city}")
        query = " ".join(parts).strip()
        return quote(query) if query else "entreprises"
    
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
        
        parts = [p.strip() for p in address.split(",")]
        return parts[-2] if len(parts) >= 2 else parts[-1]
    
    async def scrape(
        self,
        category: str,
        city: str,
        max_results: int = 50
    ) -> List[ProspectCreate]:
        """
        Scrape prospects from Google Maps.
        
        Args:
            category: Business category to search for
            city: City to search in
            max_results: Maximum number of results to return
            
        Returns:
            List of ProspectCreate objects
        """
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
                bypass_csp=True
            )
            
            # Anti-detection
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """)
            
            page = await context.new_page()
            page.set_default_timeout(4000)
            
            try:
                query = self.build_query(category, city)
                url = f"https://www.google.com/maps/search/{query}"
                logger.info(f"Scraping: {url}")
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Accept cookies and modal
                await self.accept_cookies(page)
                await self.accept_web_modal(page)
                
                # Wait for feed
                try:
                    await page.wait_for_selector("div[role='feed']", timeout=20000)
                except PlaywrightTimeoutError:
                    logger.error("Feed not found - page blocked?")
                    return []
                
                prospects = []
                seen_urls = set()
                scroll_attempts = 0
                max_scrolls = 15
                
                while len(prospects) < max_results and scroll_attempts < max_scrolls:
                    feed = page.locator("div[role='feed']")
                    items = await feed.locator("a[href*='/maps/place/']").element_handles()
                    logger.info(f"Found {len(items)} links on page")
                    
                    for item in items:
                        if len(prospects) >= max_results:
                            break
                        
                        href = await item.get_attribute("href")
                        if not href or href in seen_urls:
                            continue
                        seen_urls.add(href)
                        
                        # Open the card in the right panel (same tab)
                        await item.evaluate("el => el.removeAttribute('target')")
                        await item.click()
                        
                        item_timeout = 1000
                        
                        # Wait for card to be visible and extract data
                        address_elem = page.locator("[data-item-id='address']")
                        phone_elem = page.locator("[data-item-id='phone']")
                        website_elem = page.locator("a[data-item-id='authority']")
                        category_elem = page.locator("button[data-value='Main category']")
                        
                        await page.wait_for_selector("h1", timeout=item_timeout)
                        name = await page.locator("h1").first.inner_text(timeout=item_timeout)
                        address = await address_elem.inner_text(timeout=item_timeout) if await address_elem.count() > 0 else ""
                        phone = await phone_elem.inner_text(timeout=item_timeout) if await phone_elem.count() > 0 else None
                        website = await website_elem.get_attribute("href", timeout=item_timeout) if await website_elem.count() > 0 else None
                        extracted_category = await category_elem.inner_text(timeout=item_timeout) if await category_elem.count() > 0 else category
                        
                        print(f"Found prospect: {name} | {address} | {phone} | {website} | {extracted_category}")
                        
                        # Create prospect with confidence calculation
                        confidence = validation_service.calculate_confidence_score(
                            phone=phone,
                            address=address,
                            website=website
                        )
                        
                        # Try to find email if not already available
                        email = None
                        city_name = self.extract_city(address)
                        try:
                            email = await email_scraper.find_email(name, city_name)
                            if email:
                                print(f"Found email for {name}: {email}")
                        except Exception as e:
                            logger.debug(f"Could not find email: {e}")
                        
                        prospect = ProspectCreate(
                            name=name,
                            address=address,
                            city=city_name,
                            phone=phone,
                            email=email,
                            website=website,
                            category=extracted_category,
                            source=Source.GOOGLE,
                            confidence=confidence
                        )
                        
                        prospects.append(prospect)
                        
                        # Return to list (close card)
                        await asyncio.sleep(0.2)
                    
                    # Scroll + pause
                    await page.locator("div[role='feed']").evaluate("el => el.scrollBy(0, 3000)")
                    await asyncio.sleep(0.5)
                    scroll_attempts += 1
                
                logger.info(f"Scraping complete: {len(prospects)} prospects found")
                return prospects
            
            except Exception as e:
                logger.error(f"Error in Google scraping: {e}")
                return []
            finally:
                await context.close()
        
        finally:
            await self.stop()
    

