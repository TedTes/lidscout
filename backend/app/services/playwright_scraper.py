"""
Working Playwright Google Maps scraper.
Extracts real business data from Google Maps.
"""
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from app.models import SearchCriteria, Business
from app.services.interfaces import IBusinessSearchService
import re
import asyncio
from typing import Optional, List


class PlaywrightScraperService(IBusinessSearchService):
    """Scrapes Google Maps for business information."""
    
    def __init__(self):
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    async def search_businesses(self, criteria: SearchCriteria) -> list[Business]:
        """Main search method."""
        query = f"{criteria.industry} in {criteria.location}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            try:
                page = await browser.new_page(
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )
                
                print(f"\n🔍 Searching: {query}")
                
                # Search Google Maps
                businesses = await self._scrape_google_maps(page, query, criteria.max_results)
                
                if not businesses:
                    print("⚠️ No results from Maps, trying regular Google...")
                    businesses = await self._scrape_google_web(page, query, criteria.max_results)
                
                if not businesses:
                    return [Business(
                        name="No results found",
                        phone="Try different search terms or location",
                        address=f"Searched for: {query}"
                    )]
                
                return businesses[:criteria.max_results]
                
            finally:
                await browser.close()
    
    async def _scrape_google_maps(self, page, query: str, max_results: int) -> List[Business]:
        """Scrape Google Maps - the most reliable method."""
        businesses = []
        
        try:
            # Navigate to Google Maps
            url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
            print(f"📍 Loading: {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(3)  # Let it fully load
            
            # Wait for the results feed
            try:
                await page.wait_for_selector('div[role="feed"]', timeout=10000)
                print("✓ Results loaded")
            except:
                print("✗ Results feed not found")
                return []
            
            # Scroll to load more results
            await self._scroll_feed(page, max_results)
            
            # Get all business cards/links
            # These are the actual clickable business listings
            business_links = await page.query_selector_all('a[href*="/maps/place/"]')
            
            print(f"✓ Found {len(business_links)} business listings")
            
            # Extract each business
            for idx, link in enumerate(business_links[:max_results]):
                try:
                    business = await self._extract_business_from_maps(page, link, idx + 1)
                    if business:
                        businesses.append(business)
                        
                        # Don't extract too many to avoid rate limiting
                        if len(businesses) >= max_results:
                            break
                    
                    # Small delay to avoid detection
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    print(f"  ✗ [{idx + 1}] Error: {e}")
                    continue
            
        except Exception as e:
            print(f"Maps scraping failed: {e}")
        
        return businesses
    
    async def _extract_business_from_maps(self, page, link_element, index: int) -> Optional[Business]:
        """Extract business info by clicking the Maps listing."""
        try:
            # Get the aria-label which contains: "BusinessName · Rating · Category · Address"
            aria_label = await link_element.get_attribute('aria-label')
            
            if not aria_label or len(aria_label) < 5:
                return None
            
            # Parse the aria-label
            parts = [p.strip() for p in aria_label.split('·')]
            
            name = parts[0] if len(parts) > 0 else None
            
            # Skip if it's not a real business name
            if not name or len(name) < 3:
                return None
            
            # Extract rating from aria-label
            rating = None
            if len(parts) > 1:
                rating_match = re.search(r'(\d+\.?\d*)', parts[1])
                if rating_match:
                    try:
                        rating = float(rating_match.group(1))
                    except:
                        pass
            
            # Extract address (usually last part)
            address = None
            for part in reversed(parts):
                if re.search(r'\d+|Toronto|Street|Avenue|Road|Drive|Boulevard|ON', part, re.IGNORECASE):
                    address = part
                    break
            
            # Click to get more details (phone, website)
            await link_element.click()
            await asyncio.sleep(1.5)  # Wait for details panel to load
            
            # Extract phone number
            phone = await self._get_phone_from_details(page)
            
            # Extract website
            website = await self._get_website_from_details(page)
            
            # Extract reviews count
            reviews_count = await self._get_reviews_count(page)
            
            # Create business object
            business = Business(
                name=name,
                phone=phone,
                address=address,
                website=website,
                rating=rating,
                reviews_count=reviews_count
            )
            
            print(f"  ✓ [{index}] {name}")
            print(f"      Phone: {phone or 'N/A'}")
            print(f"      Rating: {rating or 'N/A'} ({reviews_count or 0} reviews)")
            
            return business
            
        except Exception as e:
            print(f"  ✗ [{index}] Extraction failed: {e}")
            return None
    
    async def _get_phone_from_details(self, page) -> Optional[str]:
        """Extract phone from the details panel."""
        try:
            # Multiple possible selectors for phone
            phone_selectors = [
                'button[data-item-id*="phone"]',
                'button[data-tooltip*="phone"]',
                'a[href^="tel:"]',
                'button[aria-label*="Phone"]'
            ]
            
            for selector in phone_selectors:
                try:
                    phone_elem = await page.wait_for_selector(selector, timeout=2000)
                    if phone_elem:
                        # Try getting from href first (tel: links)
                        href = await phone_elem.get_attribute('href')
                        if href and href.startswith('tel:'):
                            phone = href.replace('tel:', '').strip()
                            return self._clean_phone(phone)
                        
                        # Otherwise get text
                        text = await phone_elem.inner_text()
                        phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
                        if phone_match:
                            return self._clean_phone(phone_match.group(0))
                except:
                    continue
        except:
            pass
        
        return None
    
    async def _get_website_from_details(self, page) -> Optional[str]:
        """Extract website from details panel."""
        try:
            website_selectors = [
                'a[data-item-id="authority"]',
                'a[aria-label*="Website"]',
                'button[data-item-id*="authority"]'
            ]
            
            for selector in website_selectors:
                try:
                    website_elem = await page.wait_for_selector(selector, timeout=2000)
                    if website_elem:
                        href = await website_elem.get_attribute('href')
                        if href and 'http' in href and 'google.com/maps' not in href:
                            return href
                except:
                    continue
        except:
            pass
        
        return None
    
    async def _get_reviews_count(self, page) -> Optional[int]:
        """Extract number of reviews."""
        try:
            # Look for text like "(123 reviews)" or "123 reviews"
            reviews_selectors = [
                'button[aria-label*="reviews"]',
                'span[aria-label*="reviews"]'
            ]
            
            for selector in reviews_selectors:
                try:
                    elem = await page.wait_for_selector(selector, timeout=2000)
                    if elem:
                        text = await elem.get_attribute('aria-label')
                        if not text:
                            text = await elem.inner_text()
                        
                        reviews_match = re.search(r'([\d,]+)\s*reviews?', text, re.IGNORECASE)
                        if reviews_match:
                            return int(reviews_match.group(1).replace(',', ''))
                except:
                    continue
        except:
            pass
        
        return None
    
    async def _scroll_feed(self, page, target_results: int):
        """Scroll the results feed to load more businesses."""
        try:
            feed = await page.query_selector('div[role="feed"]')
            if feed:
                # Scroll 3-5 times depending on how many results we want
                scroll_times = min(5, (target_results // 5) + 1)
                
                for i in range(scroll_times):
                    await feed.evaluate('el => el.scrollBy(0, 1000)')
                    await asyncio.sleep(1)
        except:
            pass
    
    async def _scrape_google_web(self, page, query: str, max_results: int) -> List[Business]:
        """Fallback: scrape regular Google search."""
        businesses = []
        
        try:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            await page.goto(url, timeout=15000)
            await asyncio.sleep(2)
            
            # Get all text content
            body_text = await page.inner_text('body')
            
            # Split by lines and look for business-like entries
            lines = body_text.split('\n')
            
            for line in lines:
                # Must have a phone number to be considered a business
                phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', line)
                
                if phone_match and 10 < len(line) < 200:
                    name = line.split('·')[0].split('(')[0].strip()[:100]
                    phone = self._clean_phone(phone_match.group(0))
                    
                    rating_match = re.search(r'(\d+\.?\d*)\s*★', line)
                    rating = float(rating_match.group(1)) if rating_match else None
                    
                    if name and phone:
                        businesses.append(Business(
                            name=name,
                            phone=phone,
                            rating=rating
                        ))
                        
                        if len(businesses) >= max_results:
                            break
            
            print(f"✓ Extracted {len(businesses)} businesses from web search")
            
        except Exception as e:
            print(f"Web search failed: {e}")
        
        return businesses
    
    def _clean_phone(self, phone: str) -> str:
        """Format phone number."""
        if not phone:
            return None
        
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        
        return phone
