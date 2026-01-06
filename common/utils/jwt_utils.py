"""
JWT Token Utilities for AI Assistant Application

Provides functions for generating and validating JWT tokens for:
- Guest users (temporary sessions)
- Authenticated users (from external auth providers)
- Superuser access control

Based on the implementation from ai_assistant_deprecated/common/utils/auth_utils.py
"""

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

logger = logging.getLogger(__name__)


class JWTConfig:
    """JWT configuration from environment variables."""
    
    def __init__(self):
        self.secret_key = os.getenv("AUTH_SECRET_KEY", "dev-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.guest_token_expiry_weeks = 50  # 50 weeks for guest tokens
        self.user_token_expiry_hours = 24  # 24 hours for user tokens
        
        if self.secret_key == "dev-secret-key-change-in-production":
            logger.warning(
                "Using default AUTH_SECRET_KEY! "
                "Set AUTH_SECRET_KEY environment variable in production!"
            )


_config = JWTConfig()


class TokenValidationError(Exception):
    """Raised when token validation fails."""
    pass


class TokenExpiredError(Exception):
    """Raised when token has expired."""
    pass


def generate_guest_token() -> dict:
    """
    Generate a JWT token for a guest user.
    
    Guest tokens:
    - Have a long expiry (50 weeks)
    - Include 'guest.' prefix in user_id
    - Do not have superuser privileges
    
    Returns:
        dict: Token response with access_token, token_type, expires_in, guest_id
    """
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(weeks=_config.guest_token_expiry_weeks)
    
    guest_id = f"guest.{session_id}"
    
    payload = {
        "sub": guest_id,
        "caas_org_id": guest_id,  # User ID field (Cyoda convention)
        "caas_cyoda_employee": False,  # Not a superuser
        "iat": now,
        "exp": expiry
    }
    
    token = jwt.encode(payload, _config.secret_key, algorithm=_config.algorithm)
    
    logger.info(f"Generated guest token for {guest_id}")
    
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": int(timedelta(weeks=_config.guest_token_expiry_weeks).total_seconds()),
        "guest_id": guest_id
    }


def generate_user_token(
    user_id: str,
    is_superuser: bool = False,
    expiry_hours: Optional[int] = None
) -> str:
    """
    Generate a JWT token for an authenticated user.
    
    Args:
        user_id: The user's unique identifier
        is_superuser: Whether the user has superuser privileges
        expiry_hours: Token expiry in hours (default: 24)
    
    Returns:
        str: JWT token string
    """
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=expiry_hours or _config.user_token_expiry_hours)
    
    payload = {
        "sub": user_id,
        "caas_org_id": user_id,  # User ID field (Cyoda convention)
        "caas_cyoda_employee": is_superuser,  # Superuser flag
        "iat": now,
        "exp": expiry
    }
    
    token = jwt.encode(payload, _config.secret_key, algorithm=_config.algorithm)
    
    logger.info(f"Generated user token for {user_id} (superuser: {is_superuser})")
    
    return token


def validate_token(token: str, verify_signature: bool = True) -> dict:
    """
    Validate a JWT token and return its payload.
    
    Args:
        token: JWT token string
        verify_signature: Whether to verify the token signature (default: True)
    
    Returns:
        dict: Decoded token payload
    
    Raises:
        TokenExpiredError: If token has expired
        TokenValidationError: If token is invalid
    """
    try:
        if verify_signature:
            payload = jwt.decode(
                token,
                _config.secret_key,
                algorithms=[_config.algorithm]
            )
        else:
            # Decode without verification (useful for extracting payload only)
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )
        
        return payload
    
    except ExpiredSignatureError:
        logger.warning("Token has expired")
        raise TokenExpiredError("Token has expired")
    
    except InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise TokenValidationError(f"Invalid token: {e}")


def extract_bearer_token(auth_header: str) -> str:
    """
    Extract the token from an Authorization header.
    
    Args:
        auth_header: Authorization header value (e.g., "Bearer <token>")
    
    Returns:
        str: The extracted token
    
    Raises:
        TokenValidationError: If header format is invalid
    """
    if not auth_header:
        raise TokenValidationError("Missing Authorization header")
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise TokenValidationError("Invalid Authorization header format")
    
    return parts[1]


def get_user_info_from_token(token: str) -> Tuple[str, bool]:
    """
    Extract user ID and superuser status from a JWT token.
    
    For guest tokens (user_id starts with 'guest.'), validates the signature.
    For other tokens, only extracts the payload without verification
    (assumes external auth provider has already validated).
    
    Args:
        token: JWT token string
    
    Returns:
        tuple: (user_id, is_superuser)
    
    Raises:
        TokenValidationError: If token is invalid
        TokenExpiredError: If token has expired
    """
    # First decode without verification to check if it's a guest token
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except InvalidTokenError as e:
        raise TokenValidationError(f"Invalid token format: {e}")
    
    user_id = payload.get("caas_org_id")
    if not user_id:
        raise TokenValidationError("Token missing user_id (caas_org_id)")
    
    # For guest tokens, validate the signature
    if user_id.startswith("guest."):
        payload = validate_token(token, verify_signature=True)
    
    # Extract superuser status (defaults to False if not present)
    is_superuser = payload.get("caas_cyoda_employee", False)
    
    return user_id, is_superuser


def get_user_info_from_header(auth_header: str) -> Tuple[str, bool]:
    """
    Extract user ID and superuser status from an Authorization header.
    
    Convenience function that combines extract_bearer_token and get_user_info_from_token.
    
    Args:
        auth_header: Authorization header value (e.g., "Bearer <token>")
    
    Returns:
        tuple: (user_id, is_superuser)
    
    Raises:
        TokenValidationError: If header or token is invalid
        TokenExpiredError: If token has expired
    """
    token = extract_bearer_token(auth_header)
    return get_user_info_from_token(token)

