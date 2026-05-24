"""
Pages Jaunes scraper for fetching business prospects.
"""
from typing import List, Optional
from urllib.parse import quote, urljoin
import asyncio
import base64
import json
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


class PagesJaunesScraper(BaseScraper):
    """
    Pages Jaunes scraper for extracting business prospect data.
    
    This scraper uses Playwright to interact with Pages Jaunes
    and extract business information including name, address,
    phone, website, and category. Only businesses without websites
    are targeted.
    """
    
    def __init__(self):
        """Initialize the Pages Jaunes scraper."""
        super().__init__(source=Source.PAGESJAUNES)
        self.playwright = None
        self.browser = None
        self.base_url = "https://www.pagesjaunes.fr"
    
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
                    "--disable-dev-shm-usage",  # Utilise /tmp au lieu de /dev/shm pour éviter les crashes sur VPS
                    "--disable-gpu",  # Obligatoire en mode headless
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
                    "--js-flags=--max-old-space-size=512"  # Limite la mémoire JavaScript
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
        Build search URL for Pages Jaunes.
        
        Args:
            category: Business category (e.g., "plombier", "restaurant")
            city: City name
            
        Returns:
            URL for Pages Jaunes search
        """
        # Map categories to Pages Jaunes categories
        category_map = {
            "plombier": "plombiers",
            "restaurant": "restaurants",
            "coiffeur": "coiffeurs",
            "electricien": "electriciens",
            "garage": "garages-auto"
        }
        
        search_category = category_map.get(category, category)
        return f"https://www.pagesjaunes.fr/annuaire/{city.lower().replace(' ', '-')}/{search_category}"
    
    @staticmethod
    def extract_city(address: str) -> str:
        """
        Extract city from full address.
        
        Pages Jaunes format: "50 La Lande de la Motte 35590 Saint Gilles"
        Format: [adresse] [code postal 5 chiffres] [ville]
        
        Args:
            address: Full address string
            
        Returns:
            Extracted city name
        """
        if not address:
            return "Inconnue"
        
        # Chercher un code postal français (5 chiffres consécutifs)
        # Le format est: [adresse] [code postal] [ville]
        postal_code_pattern = r'\b(\d{5})\s+(.+)$'
        match = re.search(postal_code_pattern, address)
        
        if match:
            # Tout ce qui suit le code postal est la ville
            city = match.group(2).strip()
            return city
        
        # Fallback: si pas de code postal trouvé, prendre le dernier mot
        # (pour les anciens formats ou formats différents)
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
            # Check if the modal with id="appconsent" exists (no initial sleep)
            consent_modal = page.locator('#appconsent')
            modal_count = await consent_modal.count()
            print(f"DEBUG: Modal count: {modal_count}")
            
            if modal_count > 0:
                logger.info("Cookie consent modal detected, attempting to accept")
                
                # Check if there's an iframe inside the modal
                iframe_locator = consent_modal.locator('iframe')
                iframe_count = await iframe_locator.count()
                print(f"DEBUG: Iframe count: {iframe_count}")
                
                if iframe_count > 0:
                    logger.info("Detected iframe in consent modal")
                    
                    # Wait briefly for iframe to load
                    await asyncio.sleep(0.3)
                    
                    # Create a frame locator to access iframe content
                    frame_locator = page.frame_locator('#appconsent iframe')
                    
                    # Try multiple selectors inside the iframe
                    selectors = [
                        'button[class*="button__acceptAll"]',  # Button with class containing button__acceptAll
                        'button.button__acceptAll',  # Button with class
                        '.button__acceptAll',  # Element with class
                        'button:has-text("Accepter")',  # Button by text
                        'button[aria-label*="Accepter"]',  # By aria-label
                        'button:has-text("Tout accepter")',  # Alternative text
                    ]
                    
                    # Debug: list all buttons in iframe
                    try:
                        all_buttons = frame_locator.locator('button')
                        button_count = await all_buttons.count()
                        print(f"DEBUG: Found {button_count} buttons in iframe")
                        
                        # List all button classes for debugging
                        for i in range(button_count):
                            btn = all_buttons.nth(i)
                            classes = await btn.get_attribute('class')
                            text = await btn.text_content()
                            print(f"DEBUG: Button {i}: class='{classes}', text='{text}'")
                    except Exception as e:
                        print(f"DEBUG: Could not list buttons: {e}")
                    
                    # Try each selector
                    for selector in selectors:
                        try:
                            print(f"DEBUG: Trying selector in iframe: {selector}")
                            accept_button = frame_locator.locator(selector)
                            count = await accept_button.count()
                            print(f"DEBUG: Found {count} elements with selector {selector}")
                            
                            if count > 0:
                                # Wait for button to be visible
                                await accept_button.first.wait_for(state="visible", timeout=2000)
                                await accept_button.first.click()
                                logger.info(f"Cookie consent accepted using selector: {selector}")
                                await asyncio.sleep(0.1)
                                return
                        except Exception as e:
                            print(f"DEBUG: Selector {selector} failed: {e}")
                            continue
                    
                    logger.warning("Could not find accept button in iframe")
                else:
                    logger.info("No iframe detected, trying to find button in modal")
                    
                    # Fallback: try to find button directly in modal (not in iframe)
                    selectors = [
                        'button[class*="button__acceptAll"]',
                        'button.button__acceptAll',
                        '.button__acceptAll',
                        'button:has-text("Accepter")',
                        'button[aria-label*="Accepter"]',
                    ]
                    
                    for selector in selectors:
                        try:
                            print(f"DEBUG: Trying selector: {selector}")
                            accept_button = page.locator(selector)
                            count = await accept_button.count()
                            print(f"DEBUG: Found {count} elements with selector {selector}")
                            
                            if count > 0:
                                await accept_button.first.wait_for(state="visible", timeout=1500)
                                await accept_button.first.click()
                                logger.info(f"Cookie consent accepted using selector: {selector}")
                                await asyncio.sleep(0.1)
                                return
                        except Exception as e:
                            print(f"DEBUG: Selector {selector} failed: {e}")
                            continue
                    
                    logger.warning("Could not find accept button")
        except Exception as e:
            logger.debug(f"Could not handle cookie consent: {e}")
            import traceback
            traceback.print_exc()
    
    async def extract_prospect_details(self, page, link_url: str) -> Optional[ProspectCreate]:
        """
        Extract prospect details from detail page.
        
        Args:
            page: Playwright page object
            link_url: URL to prospect detail page
            
        Returns:
            ProspectCreate object or None if extraction fails
        """
        try:
            # Navigate to detail page with faster load strategy
            full_url = urljoin(self.base_url, link_url)
            await page.goto(full_url, wait_until="domcontentloaded", timeout=10000)
            
            # Accept cookies if present (with reduced timeout for accept_cookies)
            await self.accept_cookies(page)
            
            # Extract name with timeout - get only direct text, not button text
            name_elem = page.locator("#teaser-header h1.noTrad.no-margin")
            try:
                await name_elem.first.wait_for(state="visible", timeout=3000)
                # Get the full HTML to extract only the first text node before any span/button
                name_html = await name_elem.first.inner_html()
                # Extract only the first text before the first <
                match = re.search(r'^([^<\n]+)', name_html)
                if match:
                    name = match.group(1).strip()
                else:
                    # Fallback: try to get text but split by newlines and take first
                    full_text = await name_elem.first.inner_text()
                    name = full_text.split('\n')[0].strip()
            except Exception as e:
                logger.warning(f"Name not found: {e}")
                return None
            
            # Extract category
            category_elem = page.locator(".zone-activites .activite")
            category = ""
            if await category_elem.count() > 0:
                categories = await category_elem.all_inner_texts()
                category = ", ".join(categories[:2])  # Take first 2 categories
            else:
                category = "Inconnu"
            
            # Extract phone (already in DOM, no need to click)
            phone = None
            try:
                # Try different selectors to find the phone number
                phone_selectors = [
                    'span.coord-numero.noTrad',
                    'span.coord-numero',
                    '.num-container span.coord-numero',
                    '#coord-liste-numero_1 span.coord-numero'
                ]
                
                for phone_selector in phone_selectors:
                    phone_elem = page.locator(phone_selector)
                    count = await phone_elem.count()
                    if count > 0:
                        # Try to extract phone from any matching element
                        for i in range(count):
                            elem = phone_elem.nth(i)
                            phone_text = await elem.text_content()
                            if phone_text and phone_text.strip():
                                # Clean phone number
                                phone = re.sub(r'\s+', ' ', phone_text).strip()
                                # Check if it looks like a phone number (contains digits)
                                if phone and any(c.isdigit() for c in phone) and len(phone) >= 8:
                                    break
                        if phone:
                            break
            except Exception as e:
                logger.debug(f"Could not extract phone: {e}")
            
            # Extract address
            address = None
            try:
                # Try different selectors for address
                address_selectors = [
                    'a.black-icon.teaser-item span.noTrad',
                    '.address.streetAddress',
                    '#blocCoordonnees a.black-icon span.noTrad',
                    'a[title*="carte"] span.noTrad'
                ]
                
                for selector in address_selectors:
                    address_elem = page.locator(selector)
                    if await address_elem.count() > 0:
                        address = await address_elem.first.inner_text()
                        if address and address.strip():
                            break
            except Exception as e:
                logger.debug(f"Could not extract address: {e}")
            
            # Extract city from address
            city = self.extract_city(address) if address else "Inconnue"
            
            # Clean address: remove postal code and city
            if address:
                address = address_service.remove_city_and_postal_code(address, city)
            
            # Extract website
            website = None
            try:
                # Look for MINISITE or SITE_EXTERNE link
                website_selectors = [
                    '.MINISITE.pj-link',
                    '.SITE_EXTERNE.pj-link'
                ]
                
                for selector in website_selectors:
                    website_elem = page.locator(selector)
                    if await website_elem.count() > 0:
                        # First try to get href
                        href = await website_elem.get_attribute("href")
                        
                        # If href is not valid, try to get from data-pjlb (base64 encoded)
                        if not href or href == '#' or not href.startswith('http'):
                            data_pjlb = await website_elem.get_attribute("data-pjlb")
                            if data_pjlb:
                                try:
                                    # Parse the JSON data
                                    data = json.loads(data_pjlb.replace("&quot;", '"'))
                                    encoded_url = data.get('url', '')
                                    # Decode base64
                                    decoded_url = base64.b64decode(encoded_url).decode('utf-8')
                                    href = decoded_url
                                except Exception as e:
                                    logger.debug(f"Could not decode data-pjlb: {e}")
                        
                        # Validate the website
                        if href and validation_service.is_valid_website(href):
                            website = href
                            break
            except Exception as e:
                logger.debug(f"Could not extract website: {e}")
            
            # Only return prospect if no website (target criteria)
            if website:
                logger.info(f"Prospect {name} has a website, skipping")
                return None
            
            # Try to find email if not already available
            email = None
            try:
                email = await email_scraper.find_email(name, city)
                if email:
                    logger.info(f"Found email for {name}: {email}")
            except Exception as e:
                logger.debug(f"Could not find email: {e}")


            # Calculate confidence using validation service
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
                source=Source.PAGESJAUNES,
                confidence=min(confidence, 4)
            )
            
            # log the prospect
            print(f"Extracted: {prospect}")
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
        Scrape prospects from Pages Jaunes without websites.
        
        Args:
            category: Business category to search for
            city: City to search in
            max_results: Maximum number of results to return
            
        Returns:
            List of ProspectCreate objects without websites
        """
        print(f"[PagesJaunes] Scrape method called for category={category}, city={city}, max_results={max_results}")
        logger.info(f"[PagesJaunes] Starting scrape for category={category}, city={city}, max_results={max_results}")
        
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
                # Navigate to search page with faster load strategy
                url = self.build_url(category, city)
                logger.info(f"Scraping Pages Jaunes: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                
                # Accept cookies if present
                await self.accept_cookies(page)
                
                # Check for no results
                no_results = page.locator('h1.wording-no-responses')
                if await no_results.count() > 0:
                    logger.info("No results found on Pages Jaunes")
                    return []
                
                # Wait for results list with shorter timeout
                results_section = page.locator('section.results#listResults')
                await results_section.wait_for(timeout=10000)
                
                # Get all prospect cards
                cards = results_section.locator('li.bi')
                card_count = await cards.count()
                logger.info(f"Found {card_count} prospect cards")
                
                prospects = []
                processed = 0
                
                # Process up to max(max_results * 3, 10) to find enough without websites
                # This gives more margin since many prospects might have websites
                max_to_check = min(max(max_results * 3, 10), card_count)
                
                for i in range(max_to_check):
                    if len(prospects) >= max_results:
                        break
                    
                    try:
                        card = cards.nth(i)
                        
                        # Extract link to detail page
                        link_elem = card.locator('a.bi-denomination')
                        if await link_elem.count() == 0:
                            continue
                        
                        href = await link_elem.get_attribute('href')
                        if not href or href == '#':
                            # Try to get data from data attribute
                            data_pjlb = await link_elem.get_attribute('data-pjlb')
                            if data_pjlb and 'url' in data_pjlb:
                                # Decode base64 URL from data
                                try:
                                    import base64
                                    import json
                                    data = json.loads(data_pjlb.replace("&quot;", '"'))
                                    encoded_url = data['url']
                                    href = base64.b64decode(encoded_url).decode('utf-8')
                                    href = href[1:]  # Remove leading /
                                except Exception as e:
                                    logger.debug(f"Could not decode href: {e}")
                                    continue
                        
                        # Extract prospect details in a new tab
                        detail_page = await context.new_page()
                        # Set shorter timeout for detail page
                        detail_page.set_default_timeout(8000)
                        try:
                            prospect = await self.extract_prospect_details(detail_page, href)
                            if prospect:
                                prospects.append(prospect)
                            processed += 1
                        finally:
                            await detail_page.close()
                        
                        # Small delay between requests
                        await asyncio.sleep(0.2)
                    
                    except Exception as e:
                        logger.error(f"Error processing card {i}: {e}")
                        continue
                
                logger.info(f"Pages Jaunes scraping complete: {len(prospects)} prospects without websites from {processed} processed")
                return prospects
            
            except Exception as e:
                logger.error(f"Error in Pages Jaunes scraping: {e}", exc_info=True)
                return []
            finally:
                await context.close()
        
        finally:
            await self.stop()

