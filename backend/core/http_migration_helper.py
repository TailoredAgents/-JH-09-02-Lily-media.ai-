"""
HTTP Migration Helper

Provides utilities for gradually migrating from requests to async httpx.
Allows mixed sync/async usage during transition period.
"""
import asyncio
import logging
from functools import wraps
from typing import Any, Dict, Optional

import httpx
from backend.core.http_client import get_http_client

logger = logging.getLogger(__name__)


def run_async_in_sync(coro):
    """
    Run an async coroutine in a sync context.
    
    This is a temporary helper for migration from sync requests to async httpx.
    """
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use run()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(coro))
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(coro)


class SyncHTTPClient:
    """
    Synchronous wrapper around async HTTP client.
    
    DEPRECATED: Use async methods instead.
    This is provided for gradual migration only.
    """
    
    def __init__(self):
        import warnings
        warnings.warn(
            "SyncHTTPClient is deprecated. Migrate to async HTTP methods.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def get(self, url: str, **kwargs) -> httpx.Response:
        """Synchronous GET request."""
        async def _get():
            client = await get_http_client()
            return await client.get(url, **kwargs)
        
        return run_async_in_sync(_get())
    
    def post(self, url: str, **kwargs) -> httpx.Response:
        """Synchronous POST request.""" 
        async def _post():
            client = await get_http_client()
            return await client.post(url, **kwargs)
        
        return run_async_in_sync(_post())
    
    def put(self, url: str, **kwargs) -> httpx.Response:
        """Synchronous PUT request."""
        async def _put():
            client = await get_http_client()
            return await client.put(url, **kwargs)
        
        return run_async_in_sync(_put())
    
    def delete(self, url: str, **kwargs) -> httpx.Response:
        """Synchronous DELETE request."""
        async def _delete():
            client = await get_http_client()
            return await client.delete(url, **kwargs)
        
        return run_async_in_sync(_delete())


def requests_to_httpx_params(
    url: str,
    method: str = 'GET',
    headers: Optional[Dict[str, str]] = None,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Any] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convert requests-style parameters to httpx format.
    
    Args:
        url: Request URL
        method: HTTP method
        headers: Request headers
        json: JSON data to send
        data: Form data to send
        params: URL parameters
        timeout: Request timeout
        **kwargs: Other arguments
        
    Returns:
        Dictionary of httpx-compatible parameters
    """
    httpx_params = {
        'url': url,
        'method': method
    }
    
    if headers:
        httpx_params['headers'] = headers
    
    if json is not None:
        httpx_params['json'] = json
    
    if data is not None:
        httpx_params['data'] = data
    
    if params:
        httpx_params['params'] = params
    
    if timeout:
        httpx_params['timeout'] = timeout
    
    # Add other supported kwargs
    for key in ['cookies', 'auth', 'follow_redirects']:
        if key in kwargs:
            httpx_params[key] = kwargs[key]
    
    return httpx_params


# Global sync client for backwards compatibility
_sync_client: Optional[SyncHTTPClient] = None


def get_sync_client() -> SyncHTTPClient:
    """
    Get a synchronous HTTP client.
    
    DEPRECATED: Use async methods instead.
    """
    global _sync_client
    if _sync_client is None:
        _sync_client = SyncHTTPClient()
    return _sync_client


# Drop-in replacement functions for requests
def get(url: str, **kwargs) -> httpx.Response:
    """Drop-in replacement for requests.get()"""
    client = get_sync_client()
    return client.get(url, **kwargs)


def post(url: str, **kwargs) -> httpx.Response:
    """Drop-in replacement for requests.post()"""
    client = get_sync_client()
    return client.post(url, **kwargs)


def put(url: str, **kwargs) -> httpx.Response:
    """Drop-in replacement for requests.put()"""
    client = get_sync_client()
    return client.put(url, **kwargs)


def delete(url: str, **kwargs) -> httpx.Response:
    """Drop-in replacement for requests.delete()"""
    client = get_sync_client()
    return client.delete(url, **kwargs)