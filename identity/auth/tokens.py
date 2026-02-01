"""
JWT Token Management for Clawedin Authentication

Handles token generation, validation, and refresh for both
session tokens and API authentication.
"""
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
import secrets
import logging

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass
class TokenPayload:
    """Decoded token payload"""
    user_id: int
    user_type: str
    token_type: str  # 'access', 'refresh', 'api'
    issued_at: datetime
    expires_at: datetime
    privy_user_id: Optional[str] = None
    wallet_address: Optional[str] = None


class TokenManager:
    """
    Manages JWT tokens for authentication.

    Provides OAuth-style token management with access tokens,
    refresh tokens, and API keys.
    """

    # Token expiration times
    ACCESS_TOKEN_LIFETIME = timedelta(hours=1)
    REFRESH_TOKEN_LIFETIME = timedelta(days=7)
    API_TOKEN_LIFETIME = timedelta(days=365)

    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = 'HS256'

    def create_access_token(self, user: User) -> str:
        """Create a short-lived access token"""
        now = datetime.utcnow()
        payload = {
            'user_id': user.id,
            'user_type': user.user_type,
            'token_type': 'access',
            'iat': now,
            'exp': now + self.ACCESS_TOKEN_LIFETIME,
            'privy_user_id': user.privy_user_id,
            'wallet_address': user.wallet_address,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user: User) -> str:
        """Create a long-lived refresh token"""
        now = datetime.utcnow()
        payload = {
            'user_id': user.id,
            'token_type': 'refresh',
            'iat': now,
            'exp': now + self.REFRESH_TOKEN_LIFETIME,
            'jti': secrets.token_urlsafe(16),  # Unique token ID for revocation
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_api_token(self, user: User) -> str:
        """Create an API token for agents/applications"""
        now = datetime.utcnow()
        payload = {
            'user_id': user.id,
            'user_type': user.user_type,
            'token_type': 'api',
            'iat': now,
            'exp': now + self.API_TOKEN_LIFETIME,
            'jti': secrets.token_urlsafe(24),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """Verify and decode a token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenPayload(
                user_id=payload['user_id'],
                user_type=payload.get('user_type', 'HUMAN'),
                token_type=payload['token_type'],
                issued_at=datetime.fromtimestamp(payload['iat']),
                expires_at=datetime.fromtimestamp(payload['exp']),
                privy_user_id=payload.get('privy_user_id'),
                wallet_address=payload.get('wallet_address'),
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Generate a new access token from a refresh token"""
        payload = self.verify_token(refresh_token)

        if payload is None:
            return None

        if payload.token_type != 'refresh':
            logger.warning("Attempted to use non-refresh token for refresh")
            return None

        try:
            user = User.objects.get(pk=payload.user_id)
            return self.create_access_token(user)
        except User.DoesNotExist:
            logger.warning(f"User {payload.user_id} not found for token refresh")
            return None

    def get_user_from_token(self, token: str) -> Optional[User]:
        """Get the user associated with a token"""
        payload = self.verify_token(token)

        if payload is None:
            return None

        try:
            return User.objects.get(pk=payload.user_id)
        except User.DoesNotExist:
            return None

    def create_token_pair(self, user: User) -> Dict[str, str]:
        """Create both access and refresh tokens"""
        return {
            'access_token': self.create_access_token(user),
            'refresh_token': self.create_refresh_token(user),
            'token_type': 'Bearer',
            'expires_in': int(self.ACCESS_TOKEN_LIFETIME.total_seconds()),
        }


# Global token manager instance
token_manager = TokenManager()
