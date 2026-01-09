"""
GitHub App JWT Token Generator

Generates JSON Web Tokens (JWT) for authenticating as a GitHub App.
JWTs are used to request installation access tokens.
"""

import logging
import time
from pathlib import Path
from typing import Optional

import jwt

from common.config.config import (
    GITHUB_APP_ID,
    GITHUB_APP_PRIVATE_KEY_CONTENT,
    GITHUB_APP_PRIVATE_KEY_PATH,
)

logger = logging.getLogger(__name__)


class GitHubAppJWTGenerator:
    """Generates JWT tokens for GitHub App authentication."""

    def __init__(
        self, app_id: Optional[str] = None, private_key_path: Optional[str] = None
    ):
        """
        Initialize JWT generator.

        Args:
            app_id: GitHub App ID (defaults to config)
            private_key_path: Path to private key .pem file (defaults to config)
        """
        self.app_id = app_id or GITHUB_APP_ID
        self.private_key_path = private_key_path or GITHUB_APP_PRIVATE_KEY_PATH

        if not self.app_id:
            raise ValueError(
                "GitHub App ID is required. Set GITHUB_APP_ID in environment."
            )

        if not self.private_key_path:
            raise ValueError(
                "GitHub App private key path is required. Set GITHUB_APP_PRIVATE_KEY_PATH in environment."
            )

        self._private_key = None

    def _load_private_key(self) -> str:
        """
        Load private key from file or environment variable.

        Supports two modes:
        1. File path: GITHUB_APP_PRIVATE_KEY_PATH=/path/to/private-key.pem
        2. Direct content: GITHUB_APP_PRIVATE_KEY_CONTENT="-----BEGIN RSA PRIVATE KEY-----..."

        Returns:
            Private key content as string

        Raises:
            FileNotFoundError: If private key file doesn't exist
            ValueError: If private key is invalid or not configured
        """
        if self._private_key:
            return self._private_key

        # Check if private key content is provided directly (for Kubernetes secrets)
        if GITHUB_APP_PRIVATE_KEY_CONTENT:
            self._private_key = GITHUB_APP_PRIVATE_KEY_CONTENT
            if not self._private_key or len(self._private_key) < 100:
                raise ValueError("Private key content appears to be empty or invalid")
            logger.info(
                "Successfully loaded GitHub App private key from environment variable"
            )
            return self._private_key

        # Otherwise, load from file path
        key_path = Path(self.private_key_path)

        # If path is relative, resolve it relative to project root
        if not key_path.is_absolute():
            # Get project root (4 levels up from this file: application/services/github/auth/jwt_generator.py)
            project_root = Path(__file__).parent.parent.parent.parent.parent
            key_path = project_root / key_path

        if not key_path.exists():
            raise FileNotFoundError(
                f"GitHub App private key not found at: {key_path}. "
                f"Please ensure the .pem file exists at this location or set GITHUB_APP_PRIVATE_KEY_CONTENT."
            )

        try:
            with open(key_path, "r") as key_file:
                self._private_key = key_file.read()

            if not self._private_key or len(self._private_key) < 100:
                raise ValueError("Private key file appears to be empty or invalid")

            logger.info(f"Successfully loaded GitHub App private key from {key_path}")
            return self._private_key

        except Exception as e:
            logger.error(
                f"Failed to load private key from {self.private_key_path}: {e}"
            )
            raise ValueError(f"Failed to load GitHub App private key: {e}")

    def generate_jwt(self, expiration_seconds: int = 600) -> str:
        """
        Generate a JWT token for GitHub App authentication.

        GitHub requires:
        - Algorithm: RS256
        - Issued at (iat): Current time
        - Expiration (exp): Max 10 minutes from now
        - Issuer (iss): GitHub App ID

        Args:
            expiration_seconds: Token expiration in seconds (max 600 = 10 minutes)

        Returns:
            JWT token as string

        Raises:
            ValueError: If expiration is invalid or token generation fails
        """
        if expiration_seconds > 600:
            logger.warning(
                f"Requested expiration {expiration_seconds}s exceeds GitHub's 10-minute limit. "
                f"Using 600 seconds instead."
            )
            expiration_seconds = 600

        if expiration_seconds < 1:
            raise ValueError("Expiration must be at least 1 second")

        # Load private key
        private_key = self._load_private_key()

        # Current time
        now = int(time.time())

        # JWT payload
        payload = {
            "iat": now,  # Issued at
            "exp": now + expiration_seconds,  # Expiration
            "iss": self.app_id,  # Issuer (GitHub App ID)
        }

        try:
            # Generate JWT using RS256 algorithm
            token = jwt.encode(payload, private_key, algorithm="RS256")

            logger.info(
                f"Generated GitHub App JWT token (expires in {expiration_seconds}s, "
                f"app_id={self.app_id})"
            )

            return token

        except Exception as e:
            logger.error(f"Failed to generate JWT token: {e}")
            raise ValueError(f"Failed to generate GitHub App JWT: {e}")

    def is_token_expired(self, token: str) -> bool:
        """
        Check if a JWT token is expired.

        Args:
            token: JWT token to check

        Returns:
            True if token is expired, False otherwise
        """
        try:
            # Decode without verification to check expiration
            payload = jwt.decode(token, options={"verify_signature": False})
            exp = payload.get("exp", 0)
            now = int(time.time())

            # Add 60 second buffer to consider token expired before actual expiration
            return now >= (exp - 60)

        except Exception as e:
            logger.warning(f"Failed to decode JWT token: {e}")
            return True  # Consider invalid tokens as expired
