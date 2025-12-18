"""
Request/Response models for token routes.

Provides type-safe models for JWT token generation endpoints.
"""

from pydantic import BaseModel, Field, field_validator


class GenerateTestTokenRequest(BaseModel):
    """
    Request model for test token generation.

    Used for development/testing purposes to create JWT tokens.
    """

    user_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User ID for the token",
        examples=["alice", "bob@example.com"]
    )

    is_superuser: bool = Field(
        default=False,
        description="Whether user has superuser privileges"
    )

    expiry_hours: int = Field(
        default=24,
        ge=1,
        le=8760,  # Max 1 year
        description="Token expiry in hours"
    )

    @field_validator('user_id')
    @classmethod
    def user_id_not_empty(cls, v: str) -> str:
        """Validate user_id is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError('user_id cannot be empty or whitespace')
        return v.strip()


class TokenResponse(BaseModel):
    """
    Response model for token generation.

    Returned by both guest and test token endpoints.
    """

    access_token: str = Field(
        ...,
        description="JWT access token"
    )

    token_type: str = Field(
        default="Bearer",
        description="Token type (always Bearer)"
    )

    expires_in: int = Field(
        ...,
        description="Token expiry in seconds"
    )

    user_id: str = Field(
        ...,
        description="User ID in the token"
    )

    is_superuser: bool = Field(
        default=False,
        description="Whether user has superuser privileges"
    )


class GuestTokenResponse(BaseModel):
    """
    Response model for guest token generation.

    Specific to guest token endpoint.
    """

    access_token: str = Field(
        ...,
        description="JWT access token"
    )

    token_type: str = Field(
        default="Bearer",
        description="Token type (always Bearer)"
    )

    expires_in: int = Field(
        ...,
        description="Token expiry in seconds"
    )

    guest_id: str = Field(
        ...,
        description="Guest user ID (starts with 'guest.')"
    )
