"""
Email scraper using Google search to find contact emails.
"""
import asyncio
import re
import logging
from typing import Optional

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


logger = logging.getLogger(__name__)


class EmailScraper:
    """
    Email scraper that searches Google to find business emails.
    
    This scraper performs Google searches to find email addresses
    associated with business names and locations.
    """
    
    def __init__(self):
        """Initialize the email scraper."""
        self.playwright = None
        self.browser = None
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
    
    async def ensure_browser(self) -> None:
        """Ensure browser is initialized and running."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available, email scraping will be skipped")
            return
        
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
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
    
    def extract_emails_from_text(self, text: str) -> list:
        """
        Extract email addresses from text using regex.
        
        Args:
            text: Text to search for emails
            
        Returns:
            List of email addresses found
        """
        if not text:
            return []
        return self.email_pattern.findall(text)
    
    async def accept_google_cookies(self, page) -> None:
        """
        Accept Google cookies if present.
        
        Args:
            page: Playwright page object
        """
        try:
            await asyncio.sleep(0.5)
            
            # Check if there's an iframe for the consent dialog
            frames = page.frames
            consent_frame = None
            for frame in frames:
                if 'consent.google.com' in frame.url:
                    consent_frame = frame
                    break
            
            if not consent_frame:
                logger.debug("No consent frame found")
                return
            
            # Try multiple selectors for the "Accept all" button inside the iframe
            selectors = [
                'input[value="Tout accepter"]',
                'input[aria-label="Tout accepter"]',
                'button[aria-label="Tout accepter"]',
                '.searchButton[value="Tout accepter"]',
                'input.button[value="Tout accepter"]',
                'input.baseButtonGm3.filledButtonGm3'
            ]
            
            for selector in selectors:
                try:
                    accept_button = consent_frame.locator(selector)
                    count = await accept_button.count()
                    print(f"COOKIE MODAL GOOGLE DEBUG: Found {count} elements with selector {selector}")
                    if count > 0:
                        await accept_button.first.click()
                        logger.info("Google cookies accepted")
                        await asyncio.sleep(0.5)
                        return
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # Fallback: try to find any button with "Tout accepter" text
            try:
                all_buttons = consent_frame.locator('input, button')
                count = await all_buttons.count()
                for i in range(count):
                    btn = all_buttons.nth(i)
                    text = await btn.text_content()
                    value = await btn.get_attribute('value')
                    aria_label = await btn.get_attribute('aria-label')
                    if text and 'accepter' in text.lower():
                        await btn.click()
                        logger.info("Google cookies accepted (by text)")
                        await asyncio.sleep(0.5)
                        return
                    if value and 'accepter' in value.lower():
                        await btn.click()
                        logger.info("Google cookies accepted (by value)")
                        await asyncio.sleep(0.5)
                        return
                    if aria_label and 'accepter' in aria_label.lower():
                        await btn.click()
                        logger.info("Google cookies accepted (by aria-label)")
                        await asyncio.sleep(0.5)
                        return
            except Exception as e:
                logger.debug(f"Could not search all buttons: {e}")
                
        except Exception as e:
            logger.debug(f"Could not handle Google cookie consent: {e}")
    
    async def search_google_page(self, page, query: str, page_number: int = 0) -> Optional[str]:
        """
        Search Google on a specific page and extract the first valid email from results.
        
        Args:
            page: Playwright page object
            query: Search query
            page_number: Page number (0 = first page, 1 = second page, etc.)
            
        Returns:
            First email found or None
        """
        try:
            # Navigate to Google search
            from urllib.parse import quote_plus
            if page_number == 0:
                search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            else:
                # For subsequent pages, use start parameter
                start_param = page_number * 10
                search_url = f"https://www.google.com/search?q={quote_plus(query)}&start={start_param}"
            
            await page.goto(search_url, wait_until="domcontentloaded", timeout=10000)
            
            # Accept cookies if present (only on first page)
            if page_number == 0:
                await self.accept_google_cookies(page)
                await asyncio.sleep(0.5)
            
            # Get page content
            page_text = await page.content()
            
            # Extract emails from the page
            emails = self.extract_emails_from_text(page_text)
            
            if emails:
                # Filter out common spam/irrelevant emails (domains de test et services, mais pas les fournisseurs d'email)
                spam_domains = [
                    'example.com', 'test.com', 'domain.com', 'yoursite.com',
                    'google.com', 'gstatic.com', 'facebook.com'
                ]
                filtered_emails = [
                    email for email in emails 
                    if not any(spam in email.lower() for spam in spam_domains)
                ]
                if filtered_emails:
                    logger.info(f"Found email(s) for query '{query}' on page {page_number + 1}: {filtered_emails}")
                    return filtered_emails[0]
            
            return None
            
        except Exception as e:
            logger.debug(f"Error searching Google page {page_number + 1} for '{query}': {e}")
            return None
    
    async def search_google_multiple_pages(self, page, query: str, max_pages: int = 3) -> Optional[str]:
        """
        Search Google on multiple pages and return the first valid email found.
        Stops as soon as an email is found.
        
        Args:
            page: Playwright page object
            query: Search query
            max_pages: Maximum number of pages to search
            
        Returns:
            First email found or None
        """
        for page_num in range(max_pages):
            email = await self.search_google_page(page, query, page_num)
            if email:
                return email
            # Small delay between page searches
            if page_num < max_pages - 1:
                await asyncio.sleep(0.5)
        return None
    
    async def find_email(self, name: str, city: str) -> Optional[str]:
        """
        Find email address for a business by searching Google.
        
        Strategy:
        1. Search "nom + ville + email" on 3 pages of Google results
        2. If no email found, search "nom + ville + contact" on 3 pages
        3. Stop as soon as an email is found
        
        Args:
            name: Business name
            city: City name
            
        Returns:
            Email address if found, None otherwise
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available, skipping email search")
            return None
        
        try:
            await self.ensure_browser()
            
            if not self.browser:
                return None
            
            context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            
            page = await context.new_page()
            page.set_default_timeout(10000)
            
            try:
                # First search: "nom + ville + email" on 3 pages
                query1 = f"{name} {city} email"
                logger.info(f"Searching for email with query: {query1} (3 pages)")
                email = await self.search_google_multiple_pages(page, query1, max_pages=3)
                
                if email:
                    logger.info(f"Email found with 'email' query: {email}")
                    return email
                
                # If no email found, try with "contact" on 3 pages
                query2 = f"{name} {city} contact"
                logger.info(f"No email found with 'email' query, trying with: {query2} (3 pages)")
                email = await self.search_google_multiple_pages(page, query2, max_pages=3)
                
                if email:
                    logger.info(f"Email found with 'contact' query: {email}")
                
                return email
                
            finally:
                await context.close()
                
        except Exception as e:
            logger.error(f"Error in email scraper: {e}")
            return None


# Singleton instance
email_scraper = EmailScraper()

