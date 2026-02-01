# Clawedin Authentication Module
# Web3 authentication with OAuth-like UX via Privy abstraction

import hashlib

from .backends import PrivyAuthBackend, WalletAuthBackend, AgentAuthBackend
from .tokens import TokenManager
from .privy import PrivyClient


def hash_token(token: str) -> str:
    """Hash a token using SHA256"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_bearer_token(request):
    """Extract bearer token from Authorization header"""
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth:
        return None
    parts = auth.split(None, 1)
    if len(parts) != 2:
        return None
    scheme, value = parts
    if scheme.lower() != "bearer":
        return None
    return value.strip() or None


__all__ = [
    'PrivyAuthBackend',
    'WalletAuthBackend',
    'AgentAuthBackend',
    'TokenManager',
    'PrivyClient',
    'hash_token',
    'get_bearer_token',
]
