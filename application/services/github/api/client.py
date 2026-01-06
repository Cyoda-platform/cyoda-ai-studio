"""
GitHub API client for making authenticated requests.
Supports both personal access tokens and GitHub App installation tokens.
"""

import logging
from typing import Optional, Dict, Any
import httpx

from common.config.config import GH_DEFAULT_OWNER
from application.services.github.auth.installation_token_manager import InstallationTokenManager

logger = logging.getLogger(__name__)


class GitHubAPIClient:
    """Base client for GitHub API interactions with dual-mode authentication."""

    BASE_URL = "https://api.github.com"
    API_VERSION = "2022-11-28"

    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        installation_id: Optional[int] = None
    ):
        """Initialize GitHub API client.

        Args:
            token: GitHub API token (optional, for backward compatibility)
            owner: Default repository owner (defaults to config)
            installation_id: GitHub App installation ID (required for authentication)
        """
        self.token = token
        self.owner = owner or GH_DEFAULT_OWNER
        self.installation_id = installation_id
        self._installation_token_manager = None

        if installation_id:
            self._installation_token_manager = InstallationTokenManager()
            logger.info(f"GitHub API client initialized with installation ID: {installation_id}")
        else:
            logger.warning("GitHub API client initialized without installation ID - authentication may fail")
    
    async def _get_token(self) -> str:
        """Get authentication token (installation token or personal access token).

        Returns:
            Authentication token
        """
        if self.installation_id and self._installation_token_manager:
            return await self._installation_token_manager.get_installation_token(self.installation_id)
        return self.token

    async def _get_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests.

        Returns:
            Headers dictionary
        """
        token = await self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION,
            "Content-Type": "application/json"
        }
    
    async def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 150.0
    ) -> Optional[Dict[str, Any]]:
        """Make a GitHub API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (without base URL)
            data: Request body data
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Response data or None if request failed

        Raises:
            Exception: If request fails
        """
        url = f"{self.BASE_URL}/{path}"
        headers = await self._get_headers()

        try:
            timeout_config = httpx.Timeout(timeout, connect=60.0)
            response = await self._execute_http_request(
                method, url, headers, data, params, timeout_config
            )

            return self._process_response(response, method, url)

        except httpx.RequestError as e:
            error_msg = f"GitHub API request error: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Unexpected error in GitHub API request: {e}")
            raise

    async def _execute_http_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        data: Optional[Dict[str, Any]],
        params: Optional[Dict[str, Any]],
        timeout_config: httpx.Timeout,
    ) -> httpx.Response:
        """Execute HTTP request with method routing.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            data: Request body data
            params: Query parameters
            timeout_config: Timeout configuration

        Returns:
            HTTP response

        Raises:
            ValueError: If HTTP method is unsupported
        """
        method_upper = method.upper()

        async with httpx.AsyncClient(timeout=timeout_config, trust_env=False) as client:
            if method_upper == "GET":
                return await client.get(url, headers=headers, params=params)
            elif method_upper == "POST":
                return await client.post(url, json=data, headers=headers, params=params)
            elif method_upper == "PUT":
                return await client.put(url, json=data, headers=headers, params=params)
            elif method_upper == "DELETE":
                return await client.delete(url, headers=headers, params=params)
            elif method_upper == "PATCH":
                return await client.patch(url, json=data, headers=headers, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

    def _process_response(
        self, response: httpx.Response, method: str, url: str
    ) -> Optional[Dict[str, Any]]:
        """Process HTTP response and extract data.

        Args:
            response: HTTP response object
            method: HTTP method used
            url: Request URL

        Returns:
            Response data as dict or empty dict

        Raises:
            Exception: If response status indicates failure
        """
        if response.status_code in (200, 201, 204):
            logger.info(
                f"GitHub API {method} request to {url} "
                f"successful (status: {response.status_code})"
            )
            if response.content:
                try:
                    return response.json()
                except Exception:
                    return {}
            return {}

        error_msg = f"GitHub API request failed (status {response.status_code}): {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make a GET request.
        
        Args:
            path: API path
            params: Query parameters
            
        Returns:
            Response data
        """
        return await self.request("GET", path, params=params)
    
    async def post(self, path: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make a POST request.
        
        Args:
            path: API path
            data: Request body
            
        Returns:
            Response data
        """
        return await self.request("POST", path, data=data)
    
    async def put(self, path: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make a PUT request.
        
        Args:
            path: API path
            data: Request body
            
        Returns:
            Response data
        """
        return await self.request("PUT", path, data=data)
    
    async def delete(self, path: str) -> Optional[Dict[str, Any]]:
        """Make a DELETE request.
        
        Args:
            path: API path
            
        Returns:
            Response data
        """
        return await self.request("DELETE", path)
    
    async def patch(self, path: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make a PATCH request.
        
        Args:
            path: API path
            data: Request body
            
        Returns:
            Response data
        """
        return await self.request("PATCH", path, data=data)
    
    async def download_file(self, url: str) -> bytes:
        """Download a file from URL.

        Args:
            url: File URL

        Returns:
            File content as bytes
        """
        headers = await self._get_headers()
        
        try:
            timeout_config = httpx.Timeout(150.0, connect=60.0)
            async with httpx.AsyncClient(timeout=timeout_config, trust_env=False) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return response.content
                else:
                    error_msg = f"File download failed (status {response.status_code})"
                    logger.error(error_msg)
                    raise Exception(error_msg)
        
        except httpx.RequestError as e:
            error_msg = f"File download error: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

