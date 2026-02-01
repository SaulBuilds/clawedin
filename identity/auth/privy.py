"""
Privy Client for Web3 Authentication Abstraction

This module provides OAuth-like authentication that hides blockchain complexity
from users. In production, it integrates with Privy's SDK. In development,
it uses mock data.
"""
import os
import hashlib
import secrets
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class PrivyUser:
    """Represents a user authenticated via Privy"""
    privy_user_id: str
    wallet_address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime = None
    linked_accounts: list = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.linked_accounts is None:
            self.linked_accounts = []


class PrivyClient:
    """
    Client for Privy authentication service.

    Provides OAuth-like authentication flows while managing Web3 wallets
    behind the scenes. Users never need to understand blockchain concepts.
    """

    def __init__(self):
        self.app_id = os.environ.get('PRIVY_APP_ID', '')
        self.app_secret = os.environ.get('PRIVY_APP_SECRET', '')

        # Check if we have real production credentials
        # Placeholder values like "development-*" or "your-*" indicate dev mode
        dev_patterns = ['development', 'dev-', 'test', 'your-', 'placeholder', 'example']
        is_real_app_id = self.app_id and not any(p in self.app_id.lower() for p in dev_patterns)
        is_real_secret = self.app_secret and not any(p in self.app_secret.lower() for p in dev_patterns)
        self.is_production = is_real_app_id and is_real_secret

        # In-memory session store for development
        self._dev_sessions: Dict[str, PrivyUser] = {}
        self._dev_wallets: Dict[str, str] = {}

        if not self.is_production:
            logger.warning("Privy running in development mode - using mock authentication")

    def get_oauth_url(self, redirect_uri: str, scope: str = 'profile') -> str:
        """
        Generate OAuth-style authorization URL.

        In production, this redirects to Privy's auth flow.
        In development, it returns a local auth endpoint.
        """
        if self.is_production:
            # Production Privy OAuth URL
            return f"https://auth.privy.io/oauth/authorize?app_id={self.app_id}&redirect_uri={redirect_uri}&scope={scope}"
        else:
            # Development mock auth
            state = secrets.token_urlsafe(32)
            return f"/identity/auth/dev-callback/?state={state}&redirect_uri={redirect_uri}"

    async def exchange_code_for_user(self, auth_code: str) -> Optional[PrivyUser]:
        """
        Exchange authorization code for user data.

        In production, this calls Privy's API.
        In development, it creates a mock user.
        """
        if self.is_production:
            return await self._production_exchange(auth_code)
        else:
            return self._dev_exchange(auth_code)

    async def _production_exchange(self, auth_code: str) -> Optional[PrivyUser]:
        """Production Privy API call"""
        # TODO: Implement actual Privy API integration
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         'https://auth.privy.io/api/v1/oauth/token',
        #         json={'code': auth_code, 'app_id': self.app_id},
        #         headers={'Authorization': f'Bearer {self.app_secret}'}
        #     )
        #     data = response.json()
        #     return PrivyUser(...)
        raise NotImplementedError("Production Privy integration requires API keys")

    def _dev_exchange(self, auth_code: str) -> PrivyUser:
        """Development mock authentication"""
        # Generate deterministic user ID from code
        privy_id = f"privy_dev_{hashlib.sha256(auth_code.encode()).hexdigest()[:16]}"

        # Generate mock wallet address
        wallet = f"0x{hashlib.sha256((auth_code + 'wallet').encode()).hexdigest()[:40]}"

        user = PrivyUser(
            privy_user_id=privy_id,
            wallet_address=wallet,
            email=f"dev_{privy_id[:8]}@clawedin.local",
            linked_accounts=['email', 'wallet']
        )

        self._dev_sessions[privy_id] = user
        self._dev_wallets[wallet] = privy_id

        return user

    def create_embedded_wallet(self, user_id: str) -> str:
        """
        Create an embedded wallet for a user.

        Users don't need to manage private keys - Privy handles this
        behind the scenes with secure key management.
        """
        if self.is_production:
            # TODO: Call Privy API to create embedded wallet
            raise NotImplementedError("Production wallet creation requires Privy API")
        else:
            # Development mock wallet
            wallet = f"0x{hashlib.sha256((user_id + 'embedded').encode()).hexdigest()[:40]}"
            self._dev_wallets[wallet] = user_id
            return wallet

    def verify_wallet_signature(self, wallet_address: str, message: str, signature: str) -> bool:
        """
        Verify a wallet signature.

        Used for authentication and transaction verification.
        In development mode, always returns True for valid-looking signatures.
        """
        if self.is_production:
            # TODO: Implement actual signature verification
            raise NotImplementedError("Production signature verification requires Web3")
        else:
            # Development mode - accept any signature that looks valid
            return len(signature) > 0 and signature.startswith('0x')

    def get_user_by_wallet(self, wallet_address: str) -> Optional[PrivyUser]:
        """Get user by their wallet address"""
        if self.is_production:
            # TODO: Call Privy API
            raise NotImplementedError("Production API required")
        else:
            privy_id = self._dev_wallets.get(wallet_address)
            if privy_id:
                return self._dev_sessions.get(privy_id)
            return None

    def get_user_by_id(self, privy_user_id: str) -> Optional[PrivyUser]:
        """Get user by their Privy user ID"""
        if self.is_production:
            # TODO: Call Privy API
            raise NotImplementedError("Production API required")
        else:
            return self._dev_sessions.get(privy_user_id)


# Global client instance
privy_client = PrivyClient()
