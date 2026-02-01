"""
Django Authentication Backends for Privy/Web3 Authentication

These backends integrate with Django's authentication system to provide
seamless Web3 authentication with an OAuth-like user experience.
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from typing import Optional, Any
import logging

from .privy import privy_client, PrivyUser

User = get_user_model()
logger = logging.getLogger(__name__)


class PrivyAuthBackend(BaseBackend):
    """
    Authentication backend for Privy OAuth-like flow.

    This backend handles authentication where users have completed
    the Privy auth flow and we have their Privy user data.
    """

    def authenticate(self, request, privy_user: PrivyUser = None, **kwargs) -> Optional[User]:
        """
        Authenticate user from Privy user data.

        Creates a new Django user if one doesn't exist.
        """
        if privy_user is None:
            return None

        try:
            # Try to find existing user by Privy ID
            user = User.objects.filter(privy_user_id=privy_user.privy_user_id).first()

            if user is None and privy_user.wallet_address:
                # Try to find by wallet address
                user = User.objects.filter(wallet_address=privy_user.wallet_address).first()

            if user is None:
                # Create new user
                user = self._create_user_from_privy(privy_user)
                logger.info(f"Created new user from Privy: {user.username}")
            else:
                # Update existing user with latest Privy data
                self._update_user_from_privy(user, privy_user)
                logger.info(f"Updated existing user from Privy: {user.username}")

            return user

        except Exception as e:
            logger.error(f"Privy authentication failed: {e}")
            return None

    def _create_user_from_privy(self, privy_user: PrivyUser) -> User:
        """Create a new Django user from Privy user data"""
        # Generate username from Privy ID or email
        if privy_user.email:
            username = privy_user.email.split('@')[0]
        else:
            username = f"user_{privy_user.privy_user_id[:8]}"

        # Ensure unique username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        user = User.objects.create(
            username=username,
            email=privy_user.email or '',
            privy_user_id=privy_user.privy_user_id,
            wallet_address=privy_user.wallet_address,
            user_type='HUMAN',  # Default to human, can be changed later
        )

        # Create associated profile
        from identity.models import UserProfile
        UserProfile.objects.get_or_create(user=user)

        return user

    def _update_user_from_privy(self, user: User, privy_user: PrivyUser) -> None:
        """Update existing user with latest Privy data"""
        updated = False

        if privy_user.wallet_address and user.wallet_address != privy_user.wallet_address:
            user.wallet_address = privy_user.wallet_address
            updated = True

        if privy_user.privy_user_id and user.privy_user_id != privy_user.privy_user_id:
            user.privy_user_id = privy_user.privy_user_id
            updated = True

        if updated:
            user.save()

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class WalletAuthBackend(BaseBackend):
    """
    Authentication backend for direct wallet signature authentication.

    Used when authenticating via wallet signature without going through
    the full Privy OAuth flow (e.g., for returning users with existing wallets).
    """

    def authenticate(self, request, wallet_address: str = None,
                     message: str = None, signature: str = None, **kwargs) -> Optional[User]:
        """
        Authenticate user via wallet signature.

        Verifies the signature and returns the associated user.
        """
        if not all([wallet_address, message, signature]):
            return None

        try:
            # Verify the signature
            if not privy_client.verify_wallet_signature(wallet_address, message, signature):
                logger.warning(f"Invalid wallet signature for {wallet_address}")
                return None

            # Find user by wallet address
            user = User.objects.filter(wallet_address=wallet_address).first()

            if user is None:
                # Check if we have Privy data for this wallet
                privy_user = privy_client.get_user_by_wallet(wallet_address)
                if privy_user:
                    # Create user from Privy data
                    backend = PrivyAuthBackend()
                    user = backend._create_user_from_privy(privy_user)
                else:
                    # Create minimal user with just wallet
                    user = self._create_user_from_wallet(wallet_address)

            return user

        except Exception as e:
            logger.error(f"Wallet authentication failed: {e}")
            return None

    def _create_user_from_wallet(self, wallet_address: str) -> User:
        """Create a minimal user from wallet address"""
        username = f"wallet_{wallet_address[:8].lower()}"

        # Ensure unique username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        user = User.objects.create(
            username=username,
            wallet_address=wallet_address,
            user_type='HUMAN',
        )

        from identity.models import UserProfile
        UserProfile.objects.get_or_create(user=user)

        return user

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class AgentAuthBackend(BaseBackend):
    """
    Authentication backend for AI agents.

    Agents authenticate using API keys that look similar to standard
    API authentication, but are linked to wallet-based identity.
    """

    def authenticate(self, request, api_key: str = None, **kwargs) -> Optional[User]:
        """
        Authenticate an AI agent via API key.
        """
        if not api_key:
            return None

        try:
            # Find agent by API key (stored in agent_capabilities JSON)
            # In production, this would be a dedicated APIKey model
            agents = User.objects.filter(user_type__in=['AGENT', 'HYBRID'])

            for agent in agents:
                if isinstance(agent.agent_capabilities, dict):
                    stored_key = agent.agent_capabilities.get('api_key')
                    if stored_key and stored_key == api_key:
                        return agent

            return None

        except Exception as e:
            logger.error(f"Agent authentication failed: {e}")
            return None

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
