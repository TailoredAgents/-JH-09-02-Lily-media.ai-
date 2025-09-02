"""
Real Web Research Service for Company Analysis

This service performs ONLY real web searches. No mock data or fallbacks.
When search fails, Lily provides a cute error message and logs the failure.
"""
import asyncio
import logging
import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
import requests
from urllib.parse import quote_plus
from dataclasses import dataclass

from backend.core.config import get_settings
def log_api_error(endpoint: str, method: str, error: Exception, request_data: Optional[Dict] = None, user_id: Optional[int] = None):
    """Production-ready error logging with structured format"""
    logger.error(
        f"Web research API error",
        extra={
            "endpoint": endpoint,
            "method": method,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "user_id": user_id,
            "request_data": request_data,
            "service": "web_research"
        },
        exc_info=True
    )

settings = get_settings()
logger = logging.getLogger(__name__)

class WebSearchException(Exception):
    """Exception raised when web search fails completely"""
    def __init__(self, message: str, cute_lily_message: str):
        super().__init__(message)
        self.cute_lily_message = cute_lily_message

@dataclass
class WebSearchResult:
    """Structure for web search results"""
    title: str
    url: str
    snippet: str
    date: Optional[str] = None
    source: str = "web_search"

@dataclass 
class CompanyWebData:
    """Real company data gathered from web sources"""
    company_name: str
    industry: str
    description: str
    website_url: Optional[str]
    founded: Optional[str]
    headquarters: Optional[str]
    size: Optional[str]
    recent_news: List[WebSearchResult]
    company_info: Dict[str, Any]
    social_links: Dict[str, str]
    confidence_score: float

class WebResearchService:
    """
    Service that performs real web searches and data gathering for companies
    """
    
    def __init__(self):
        self.session = None
        # NO FALLBACK ENGINES - only real web search
        self.search_engines = {
            'gpt_web_search': self._search_with_gpt,
            'serper': self._search_serper,
            'duckduckgo': self._search_duckduckgo
        }
        
    async def research_company_web(self, company_name: str) -> CompanyWebData:
        """
        Perform comprehensive web research on a company
        
        Args:
            company_name: Name of the company to research
            
        Returns:
            CompanyWebData with real information gathered from the web
        """
        logger.info(f"Starting real web research for: {company_name}")
        
        try:
            # Initialize HTTP session
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ) as session:
                self.session = session
                
                # Perform multiple search queries
                search_tasks = [
                    self._search_company_basic_info(company_name),
                    self._search_company_news(company_name),
                    self._search_company_industry(company_name),
                    self._search_company_details(company_name)
                ]
                
                # Execute searches concurrently
                results = await asyncio.gather(*search_tasks, return_exceptions=True)
                
                # Process and combine results
                company_data = await self._process_web_results(company_name, results)
                
                logger.info(f"Web research completed for {company_name} with confidence: {company_data.confidence_score}")
                return company_data
                
        except Exception as e:
            # Log the error properly
            log_api_error(
                endpoint="/web-research",
                method="POST", 
                error=e,
                request_data={"company_name": company_name},
                user_id=None
            )
            
            # Lily's cute error response
            cute_message = f"Oopsie 🤭 That's not right, let me just write that down... I couldn't find real web information about {company_name}. My web search tools seem to be having a little hiccup!"
            
            raise WebSearchException(
                f"All web search methods failed for {company_name}: {str(e)}",
                cute_message
            )
    
    async def _search_company_basic_info(self, company_name: str) -> List[WebSearchResult]:
        """Search for basic company information"""
        query = f'"{company_name}" company about information'
        return await self._perform_search(query, max_results=5)
    
    async def _search_company_news(self, company_name: str) -> List[WebSearchResult]:
        """Search for recent company news"""
        query = f'"{company_name}" news 2024 2025 recent updates'
        return await self._perform_search(query, max_results=3)
    
    async def _search_company_industry(self, company_name: str) -> List[WebSearchResult]:
        """Search for company industry and market position"""
        query = f'"{company_name}" industry market business sector'
        return await self._perform_search(query, max_results=3)
    
    async def _search_company_details(self, company_name: str) -> List[WebSearchResult]:
        """Search for detailed company information"""
        query = f'"{company_name}" founded headquarters employees size'
        return await self._perform_search(query, max_results=3)
    
    async def _perform_search(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        """Perform web search using GPT-5's native web search capabilities"""
        
        search_errors = []
        
        # PRIMARY METHOD: GPT-5's built-in web search (if OpenAI key available)
        if hasattr(settings, 'openai_api_key') and settings.openai_api_key and settings.openai_api_key != "sk-your_openai_api_key_here":
            try:
                logger.info(f"Using GPT-5's native web search for: {query}")
                return await self._search_with_gpt(query, max_results)
            except Exception as e:
                search_errors.append(f"GPT-5 web search: {e}")
                logger.warning(f"GPT-5 web search failed (will retry with fallbacks): {e}")
        else:
            logger.warning("OpenAI API key not configured - GPT-5 web search unavailable")
        
        # OPTIONAL FALLBACK: Serper API (only if configured and GPT-5 fails)
        # Note: Serper is no longer needed with GPT-5's built-in search
        if hasattr(settings, 'serper_api_key') and settings.serper_api_key and settings.serper_api_key != "your_serper_api_key_here":
            try:
                logger.info(f"Falling back to Serper API search for: {query}")
                return await self._search_serper(query, max_results)
            except Exception as e:
                search_errors.append(f"Serper API: {e}")
                logger.warning(f"Serper search failed: {e}")
        
        # LAST RESORT: DuckDuckGo (free but limited)
        try:
            logger.info(f"Attempting DuckDuckGo search as last resort for: {query}")
            results = await self._search_duckduckgo(query, max_results)
            if results:  # Only return if we got actual results
                logger.info(f"DuckDuckGo returned {len(results)} results")
                return results
            else:
                search_errors.append("DuckDuckGo: No results returned")
        except Exception as e:
            search_errors.append(f"DuckDuckGo: {e}")
            logger.warning(f"DuckDuckGo search failed: {e}")
        
        # ALL METHODS FAILED - Return graceful error
        error_summary = "; ".join(search_errors)
        raise WebSearchException(
            f"Web search unavailable for query '{query}': {error_summary}",
            "Oopsie! 🔍 I'm having trouble searching the web right now. Let me try again in a moment! - Lily"
        )
    
    async def _search_with_gpt(self, query: str, max_results: int) -> List[WebSearchResult]:
        """Search using GPT-5 mini's web search via Responses API"""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Use GPT-5 mini with web search via Responses API
            response = await client.responses.create(
                model="gpt-5-mini",
                input=f"Search for: {query}. Provide current, accurate information with {max_results} relevant results.",
                tools=[
                    {
                        "type": "web_search"
                    }
                ]
            )
            
            # Use shared parser utility
            from backend.services.web_search_utils import parse_openai_web_search_results, as_web_results
            results_dicts = parse_openai_web_search_results(response, query, max_results=max_results)
            results = as_web_results(results_dicts)
                
            logger.info(f"GPT-5 web search returned {len(results)} results for: {query}")
            return results
        except Exception as e:
            raise Exception(f"GPT web search failed: {str(e)}")
    
    async def _search_serper(self, query: str, max_results: int) -> List[WebSearchResult]:
        """Search using Serper API"""
        if not hasattr(settings, 'serper_api_key') or not settings.serper_api_key:
            raise Exception("Serper API key not available")
        
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": settings.serper_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": max_results,
            "gl": "us",
            "hl": "en"
        }
        
        async with self.session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                results = []
                
                # Process organic results
                for item in data.get('organic', [])[:max_results]:
                    results.append(WebSearchResult(
                        title=item.get('title', ''),
                        url=item.get('link', ''),
                        snippet=item.get('snippet', ''),
                        date=item.get('date'),
                        source='serper'
                    ))
                
                return results
            else:
                raise Exception(f"Serper API returned {response.status}")
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> List[WebSearchResult]:
        """Search using DuckDuckGo Instant Answer API"""
        try:
            # Use DuckDuckGo's instant answer API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    
                    # Extract abstract if available
                    abstract = data.get('Abstract', '')
                    if abstract:
                        results.append(WebSearchResult(
                            title=data.get('Heading', query),
                            url=data.get('AbstractURL', ''),
                            snippet=abstract,
                            source='duckduckgo'
                        ))
                    
                    # Extract related topics
                    for topic in data.get('RelatedTopics', [])[:max_results-1]:
                        if isinstance(topic, dict) and 'Text' in topic:
                            results.append(WebSearchResult(
                                title=topic.get('Text', '').split(' - ')[0],
                                url=topic.get('FirstURL', ''),
                                snippet=topic.get('Text', ''),
                                source='duckduckgo'
                            ))
                    
                    return results
                else:
                    raise Exception(f"DuckDuckGo API returned {response.status}")
                    
        except Exception as e:
            logger.warning(f"DuckDuckGo search error: {e}")
            return []
    
    async def _process_web_results(self, company_name: str, results: List[Any]) -> CompanyWebData:
        """Process web search results into structured company data - NO MOCK DATA"""
        
        # Combine all search results
        all_results = []
        for result_set in results:
            if isinstance(result_set, list):
                all_results.extend(result_set)
        
        # If no real results found, fail immediately - NO FALLBACK TO MOCK DATA
        if not all_results:
            raise Exception(f"No web search results obtained for {company_name} - cannot provide company data without real sources")
        
        # Extract information using AI/NLP analysis
        industry = await self._extract_industry_from_results(all_results, company_name)
        description = await self._extract_description_from_results(all_results, company_name)
        website_url = await self._extract_website_from_results(all_results, company_name)
        company_details = await self._extract_company_details(all_results, company_name)
        
        # Filter for recent news
        recent_news = [r for r in all_results if 'news' in r.snippet.lower() or r.date][:5]
        
        # Calculate confidence score based on result quality
        confidence = self._calculate_confidence_score(all_results)
        
        return CompanyWebData(
            company_name=company_name,
            industry=industry,
            description=description,
            website_url=website_url,
            founded=company_details.get('founded'),
            headquarters=company_details.get('headquarters'),
            size=company_details.get('size'),
            recent_news=recent_news,
            company_info=company_details,
            social_links={},
            confidence_score=confidence
        )
    
    async def _extract_industry_from_results(self, results: List[WebSearchResult], company_name: str) -> str:
        """Extract industry from search results"""
        
        industry_keywords = {
            'Software Development': ['software', 'development', 'programming', 'coding'],
            'SaaS & Cloud Computing': ['saas', 'cloud', 'software as a service', 'subscription'],
            'Artificial Intelligence & ML': ['ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning'],
            'E-commerce': ['ecommerce', 'e-commerce', 'online store', 'marketplace'],
            'Healthcare': ['health', 'medical', 'healthcare', 'hospital'],
            'Finance': ['finance', 'financial', 'banking', 'investment'],
            'Marketing & Advertising': ['marketing', 'advertising', 'digital marketing', 'ads'],
            'Real Estate': ['real estate', 'property', 'housing', 'construction'],
            'Food & Beverage': ['food', 'restaurant', 'beverage', 'catering'],
            'Education': ['education', 'learning', 'school', 'training'],
        }
        
        # Analyze all snippets for industry keywords
        combined_text = ' '.join([r.snippet.lower() for r in results])
        
        industry_scores = {}
        for industry, keywords in industry_keywords.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                industry_scores[industry] = score
        
        # Return industry with highest score, or fail if no data
        if industry_scores:
            return max(industry_scores.keys(), key=lambda k: industry_scores[k])
        else:
            # No industry data found - this indicates insufficient search results
            raise Exception(f"Cannot determine industry for {company_name} from search results")
    
    async def _extract_description_from_results(self, results: List[WebSearchResult], company_name: str) -> str:
        """Extract company description from search results"""
        
        # Look for the most comprehensive snippet
        best_snippet = ""
        max_length = 0
        
        for result in results:
            # Prioritize results that mention the company name
            if company_name.lower() in result.snippet.lower():
                if len(result.snippet) > max_length and len(result.snippet) > 50:
                    best_snippet = result.snippet
                    max_length = len(result.snippet)
        
        # If no good snippet found, we cannot provide accurate information
        if not best_snippet:
            if results:
                # Try to use any available snippet, but mark it as uncertain
                best_snippet = f"Limited information available: " + results[0].snippet[:200] + "..."
            else:
                # No results at all - this should cause the entire process to fail
                raise Exception(f"No web search results found for {company_name} - cannot extract description")
        
        # Clean up the description
        description = best_snippet.strip()
        if len(description) > 300:
            description = description[:297] + "..."
            
        return description
    
    async def _extract_website_from_results(self, results: List[WebSearchResult], company_name: str) -> Optional[str]:
        """Extract company website from search results"""
        
        # Look for official website in URLs
        company_variations = [
            company_name.lower().replace(' ', ''),
            company_name.lower().replace(' ', '-'),
            company_name.lower().replace(' ', '_')
        ]
        
        for result in results:
            url_lower = result.url.lower()
            for variation in company_variations:
                if variation in url_lower and any(domain in url_lower for domain in ['.com', '.org', '.net', '.io']):
                    # Skip common non-company domains
                    if not any(skip in url_lower for skip in ['news', 'wiki', 'linkedin', 'facebook', 'twitter']):
                        return result.url
        
        return None
    
    async def _extract_company_details(self, results: List[WebSearchResult], company_name: str) -> Dict[str, Any]:
        """Extract detailed company information"""
        
        details = {}
        combined_text = ' '.join([r.snippet for r in results])
        
        # Extract founding year
        year_match = re.search(r'founded.*?(\d{4})', combined_text.lower())
        if year_match:
            details['founded'] = year_match.group(1)
        
        # Extract headquarters
        hq_patterns = [
            r'headquarters.*?in ([^.]+)',
            r'based in ([^.]+)',
            r'located in ([^.]+)'
        ]
        
        for pattern in hq_patterns:
            hq_match = re.search(pattern, combined_text.lower())
            if hq_match:
                details['headquarters'] = hq_match.group(1).strip()
                break
        
        # Extract company size indicators
        size_patterns = [
            r'(\d+[,\d]*)\s*employees',
            r'team of (\d+[,\d]*)',
            r'(\d+[,\d]*)\s*people'
        ]
        
        for pattern in size_patterns:
            size_match = re.search(pattern, combined_text.lower())
            if size_match:
                details['size'] = f"{size_match.group(1)} employees"
                break
        
        return details
    
    def _calculate_confidence_score(self, results: List[WebSearchResult]) -> float:
        """Calculate confidence score based on search result quality"""
        
        if not results:
            return 0.1
        
        # Base score
        score = 0.3
        
        # Add points for number of results
        score += min(len(results) * 0.1, 0.3)
        
        # Add points for result quality
        for result in results:
            if len(result.snippet) > 100:
                score += 0.05
            if result.date:
                score += 0.05
            if 'serper' in result.source:
                score += 0.1
            elif 'duckduckgo' in result.source:
                score += 0.05
        
        return min(score, 0.95)

# Global service instance
web_research_service = WebResearchService()