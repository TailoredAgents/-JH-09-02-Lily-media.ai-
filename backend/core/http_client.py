"""
Centralized HTTP Client Configuration

Provides standardized async HTTP client with proper configuration, 
timeouts, retry logic, and connection pooling.
Replaces ad-hoc httpx.AsyncClient() and requests calls.
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class HTTPClientConfig:
    """Configuration for HTTP client."""
    
    def __init__(self):
        self.timeout = float(os.getenv('HTTP_TIMEOUT', '30.0'))
        self.max_retries = int(os.getenv('HTTP_MAX_RETRIES', '3'))
        self.max_connections = int(os.getenv('HTTP_MAX_CONNECTIONS', '100'))
        self.max_keepalive_connections = int(os.getenv('HTTP_MAX_KEEPALIVE', '20'))
        self.user_agent = os.getenv('HTTP_USER_AGENT', 'AI-Social-Media-Agent/2.0')
        
        # Retry configuration
        self.retry_on_status = [408, 429, 500, 502, 503, 504]
        self.retry_backoff_factor = 0.3
        
    def to_limits(self):
        """Convert to httpx.Limits object."""
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections
        )
    
    def to_timeout(self):
        """Convert to httpx.Timeout object."""
        return httpx.Timeout(self.timeout)


class HTTPClient:
    """Centralized async HTTP client with standard configuration."""
    
    def __init__(self, config: Optional[HTTPClientConfig] = None):
        self.config = config or HTTPClientConfig()
        self._client: Optional[httpx.AsyncClient] = None
        
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                limits=self.config.to_limits(),
                timeout=self.config.to_timeout(),
                headers={
                    'User-Agent': self.config.user_agent
                },
                follow_redirects=True
            )
            
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            
    async def request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPError: For HTTP errors
        """
        await self._ensure_client()
        
        retry_count = 0
        last_exception = None
        
        while retry_count <= self.config.max_retries:
            try:
                response = await self._client.request(method, url, **kwargs)
                
                # Check if we should retry based on status code
                if response.status_code in self.config.retry_on_status and retry_count < self.config.max_retries:
                    retry_count += 1
                    backoff_time = self.config.retry_backoff_factor * (2 ** (retry_count - 1))
                    logger.warning(
                        "HTTP {} {} returned {}. Retrying in {:.1f}s (attempt {}/{})".format(
                            method, url, response.status_code, backoff_time, retry_count, self.config.max_retries
                        )
                    )
                    await asyncio.sleep(backoff_time)
                    continue
                    
                return response
                
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if retry_count < self.config.max_retries:
                    retry_count += 1
                    backoff_time = self.config.retry_backoff_factor * (2 ** (retry_count - 1))
                    logger.warning(
                        "HTTP {} {} failed: {}. Retrying in {:.1f}s (attempt {}/{})".format(
                            method, url, str(e), backoff_time, retry_count, self.config.max_retries
                        )
                    )
                    await asyncio.sleep(backoff_time)
                    continue
                break
                
        # All retries failed
        if last_exception:
            raise last_exception
        else:
            response.raise_for_status()
            return response
    
    # Convenience methods
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make GET request."""
        return await self.request('GET', url, **kwargs)
        
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make POST request."""
        return await self.request('POST', url, **kwargs)
        
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make PUT request."""
        return await self.request('PUT', url, **kwargs)
        
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make DELETE request."""
        return await self.request('DELETE', url, **kwargs)
        
    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """Make PATCH request."""
        return await self.request('PATCH', url, **kwargs)


# Global HTTP client instance
_global_client: Optional[HTTPClient] = None


async def get_http_client() -> HTTPClient:
    """Get the global HTTP client instance."""
    global _global_client
    if _global_client is None:
        _global_client = HTTPClient()
    return _global_client


async def close_http_client():
    """Close the global HTTP client."""
    global _global_client
    if _global_client:
        await _global_client.close()
        _global_client = None


@asynccontextmanager
async def http_client_context():
    """Context manager for HTTP client lifecycle."""
    client = HTTPClient()
    try:
        yield client
    finally:
        await client.close()


# Convenience functions that use the global client
async def get(url: str, **kwargs) -> httpx.Response:
    """Make GET request using global client."""
    client = await get_http_client()
    return await client.get(url, **kwargs)


async def post(url: str, **kwargs) -> httpx.Response:
    """Make POST request using global client."""
    client = await get_http_client()
    return await client.post(url, **kwargs)


async def put(url: str, **kwargs) -> httpx.Response:
    """Make PUT request using global client."""
    client = await get_http_client()
    return await client.put(url, **kwargs)


async def delete(url: str, **kwargs) -> httpx.Response:
    """Make DELETE request using global client."""
    client = await get_http_client()
    return await client.delete(url, **kwargs)


async def patch(url: str, **kwargs) -> httpx.Response:
    """Make PATCH request using global client."""
    client = await get_http_client()
    return await client.patch(url, **kwargs)


# Legacy sync wrapper for gradual migration
def sync_request(method: str, url: str, **kwargs) -> httpx.Response:
    """
    Synchronous wrapper for async HTTP requests.
    
    DEPRECATED: Use async methods instead.
    This is provided for gradual migration only.
    """
    import warnings
    warnings.warn(
        "sync_request is deprecated. Use async HTTP methods instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    async def _request():
        client = await get_http_client()
        return await client.request(method, url, **kwargs)
    
    return asyncio.run(_request())