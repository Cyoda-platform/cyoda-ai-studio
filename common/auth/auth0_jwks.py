"""
Auth0 JWKS (JSON Web Key Set) validator for token signature verification.

Fetches and caches Auth0's public keys to validate JWT token signatures.
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import httpx
import jwt
from jwt.exceptions import InvalidTokenError

from common.utils.jwt_utils import TokenExpiredError

logger = logging.getLogger(__name__)


class Auth0JWKSValidator:
    """Validates JWT tokens signed by Auth0 using JWKS."""

    def __init__(self, domain: str, audience: str):
        """
        Initialize Auth0 JWKS validator.

        Args:
            domain: Auth0 domain (e.g., 'example.auth0.com')
            audience: Auth0 API audience identifier
        """
        self.domain = domain
        self.audience = audience
        self.jwks_url = f"https://{domain}/.well-known/jwks.json"
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=24)

    async def _fetch_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Auth0."""
        try:
            timeout_config = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout_config, trust_env=False) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch JWKS from {self.jwks_url}: {e}")
            raise

    async def _get_jwks(self) -> Dict[str, Any]:
        """Get JWKS with caching."""
        now = datetime.now()
        if self._jwks_cache and self._cache_time and (now - self._cache_time) < self._cache_ttl:
            return self._jwks_cache

        self._jwks_cache = await self._fetch_jwks()
        self._cache_time = now
        return self._jwks_cache

    def _get_key_from_jwks(self, token: str, jwks: Dict[str, Any]) -> str:
        """Extract the public key from JWKS that matches the token."""
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            if not kid:
                raise ValueError("Token missing 'kid' in header")

            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    return jwt.algorithms.RSAAlgorithm.from_jwk(key)

            raise ValueError(f"Key with kid '{kid}' not found in JWKS")
        except Exception as e:
            logger.error(f"Failed to extract key from JWKS: {e}")
            raise

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate Auth0 token signature and claims.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            ValueError: If token is invalid or signature verification fails
        """
        try:
            jwks = await self._get_jwks()
            key = self._get_key_from_jwks(token, jwks)

            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=f"https://{self.domain}/"
            )

            logger.debug(f"Token validated successfully for user: {payload.get('sub')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Auth0 token has expired")
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Auth0 token validation failed: {e}")
            raise ValueError(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error validating Auth0 token: {e}")
            raise ValueError(f"Token validation error: {e}")


# Global validator instance
_auth0_validator: Optional[Auth0JWKSValidator] = None


def get_auth0_validator() -> Auth0JWKSValidator:
    """Get or create Auth0 JWKS validator."""
    global _auth0_validator

    if _auth0_validator is None:
        domain = os.getenv("AUTH0_DOMAIN")
        audience = os.getenv("AUTH0_AUDIENCE")

        if not domain or not audience:
            raise ValueError(
                "AUTH0_DOMAIN and AUTH0_AUDIENCE environment variables must be set"
            )

        _auth0_validator = Auth0JWKSValidator(domain, audience)

    return _auth0_validator

