"""
Google scraper service implementation.
Following Single Responsibility Principle - only handles Google scraping.
Following Open/Closed Principle - can extend without modifying interface.
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional
import re
import time
from app.models import SearchCriteria, Business
from app.services.interfaces import IBusinessSearchService


class GoogleScraperService(IBusinessSearchService):
    """
    Scrapes Google search results to find business information.
    Note: This is a basic implementation. For production, consider using Google Places API.
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.base_url = "https://www.google.com/search"
    
    async def search_businesses(self, criteria: SearchCriteria) -> list[Business]:
        """
        Search for businesses using Google search.
        
        Args:
            criteria: Search criteria
            
        Returns:
            List of Business objects
        """
        query = self._build_query(criteria)
        html_content = await self._fetch_search_results(query)
        businesses = self._parse_results(html_content, criteria.max_results)
        
        return businesses
    
    def _build_query(self, criteria: SearchCriteria) -> str:
        """Build Google search query from criteria."""
        # Example: "restaurants near New York, NY"
        query = f"{criteria.industry} near {criteria.location}"
        if criteria.radius_km:
            query += f" within {criteria.radius_km}km"
        return query
    
    async def _fetch_search_results(self, query: str) -> str:
        """Fetch HTML content from Google search."""
        try:
            params = {'q': query, 'num': 20}
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching search results: {e}")
            return ""
    
    def _parse_results(self, html_content: str, max_results: int) -> list[Business]:
        """Parse HTML to extract business information."""
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'lxml')
        businesses = []
        
        # Parse business listings from Google search results
        # This targets the local business results section
        business_divs = soup.find_all('div', class_='VkpGBb')
        
        for div in business_divs[:max_results]:
            business = self._extract_business_info(div)
            if business and business.name:
                businesses.append(business)
        
        # Fallback: Try alternative parsing if no results
        if not businesses:
            businesses = self._parse_alternative_format(soup, max_results)
        
        return businesses[:max_results]
    
    def _extract_business_info(self, element) -> Optional[Business]:
        """Extract business information from a single element."""
        try:
            # Extract business name
            name_elem = element.find('div', class_='dbg0pd') or element.find('h3')
            name = name_elem.get_text(strip=True) if name_elem else None
            
            # Extract address
            address_elem = element.find('span', class_='rllt__details')
            address = address_elem.get_text(strip=True) if address_elem else None
            
            # Extract phone (look for phone patterns)
            phone = self._extract_phone(element)
            
            # Extract rating
            rating_elem = element.find('span', class_='yi40Hd')
            rating = None
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                try:
                    rating = float(rating_text.split()[0])
                except:
                    pass
            
            return Business(
                name=name,
                phone=phone,
                email=None,  # Email typically not in search results
                address=address,
                website=None,
                rating=rating
            )
        except Exception as e:
            print(f"Error extracting business info: {e}")
            return None
    
    def _extract_phone(self, element) -> Optional[str]:
        """Extract phone number from element."""
        text = element.get_text()
        # Simple phone pattern matching
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        match = re.search(phone_pattern, text)
        return match.group(0) if match else None
    
    def _parse_alternative_format(self, soup: BeautifulSoup, max_results: int) -> list[Business]:
        """Alternative parsing method for different Google result formats."""
        businesses = []
        
        # Try to find any divs that might contain business info
        all_divs = soup.find_all('div', class_=re.compile(r'.*'))
        
        for div in all_divs[:max_results * 3]:  # Check more to find valid ones
            text = div.get_text(strip=True)
            if len(text) > 10 and len(text) < 200:  # Reasonable business name length
                # Basic heuristic: if it has a phone pattern or rating, might be a business
                if re.search(r'\d{3}.*\d{4}', text) or re.search(r'\d\.\d.*★', text):
                    business = Business(
                        name=text.split('\n')[0][:100] if '\n' in text else text[:100],
                        phone=self._extract_phone(div),
                        address=None
                    )
                    businesses.append(business)
            
            if len(businesses) >= max_results:
                break
        
        return businesses