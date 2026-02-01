"""
Tests for the hybrid user model combining LinkedIn professional foundation with MySpace creative expression.
Following TDD RED-GREEN-REFACTOR methodology.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model, authenticate
from django.db import transaction
from django.urls import reverse

from .auth.privy import PrivyUser, privy_client
from .auth.tokens import token_manager
from .models import UserProfile

User = get_user_model()

class TestHybridUserModel(TestCase):
    """Test cases for the hybrid user model with professional-creative layers"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'user_type': 'HUMAN',
            'professional_title': 'Software Developer',
            'bio': 'Passionate about code and creativity',
            'creative_style': 'professional',
            'preferred_industry': 'Technology'
        }
    
    def test_create_human_user(self):
        """Test creating a human user with professional information"""
        # RED: Write test before implementation
        user = User.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password']
        )
        
        self.assertEqual(user.username, self.user_data['username'])
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.user_type, 'HUMAN')
        
    def test_create_ai_agent_user(self):
        """Test creating an AI agent user"""
        agent_data = {
            'username': 'aiagent',
            'email': 'agent@example.com',
            'password': 'agentpass123',
            'user_type': 'AGENT',
            'agent_capabilities': ['code_review', 'documentation', 'analysis']
        }
        
        user = User.objects.create_user(
            username=agent_data['username'],
            email=agent_data['email'],
            password=agent_data['password']
        )
        user.user_type = agent_data['user_type']
        user.agent_capabilities = agent_data['agent_capabilities']
        user.save()
        
        self.assertEqual(user.user_type, 'AGENT')
        self.assertEqual(user.agent_capabilities, ['code_review', 'documentation', 'analysis'])
        
    def test_user_properties(self):
        """Test user helper properties"""
        human_user = User.objects.create_user(
            username='human',
            email='human@example.com',
            password='pass123'
        )
        human_user.user_type = 'HUMAN'
        human_user.save()
        
        agent_user = User.objects.create_user(
            username='agent',
            email='agent@example.com',
            password='pass123'
        )
        agent_user.user_type = 'AGENT'
        agent_user.save()
        
        self.assertTrue(hasattr(human_user, 'is_human'))
        self.assertTrue(hasattr(agent_user, 'is_agent'))
        
    def test_str_representation(self):
        """Test string representation of user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass123'
        )
        user.user_type = 'HUMAN'
        user.save()

        expected_str = f"testuser (Human)"
        self.assertEqual(str(user), expected_str)


class TestPrivyAuthBackend(TestCase):
    """Test cases for Privy OAuth-like authentication backend"""

    def test_authenticate_with_privy_user_creates_new_user(self):
        """Test that authenticating with Privy data creates a new user"""
        privy_user = PrivyUser(
            privy_user_id='privy_test_123',
            email='newuser@example.com',
            wallet_address='0x1234567890abcdef1234567890abcdef12345678'
        )

        user = authenticate(None, privy_user=privy_user)

        self.assertIsNotNone(user)
        self.assertEqual(user.privy_user_id, 'privy_test_123')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.wallet_address, '0x1234567890abcdef1234567890abcdef12345678')

    def test_authenticate_with_existing_privy_id(self):
        """Test that authenticating with existing Privy ID returns existing user"""
        existing_user = User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='pass123'
        )
        existing_user.privy_user_id = 'privy_existing_456'
        existing_user.save()

        privy_user = PrivyUser(
            privy_user_id='privy_existing_456',
            email='existing@example.com'
        )

        user = authenticate(None, privy_user=privy_user)

        self.assertEqual(user.id, existing_user.id)

    def test_authenticate_without_privy_user_returns_none(self):
        """Test that authentication without Privy user returns None"""
        user = authenticate(None, privy_user=None)
        self.assertIsNone(user)


class TestAgentAuthBackend(TestCase):
    """Test cases for AI agent API key authentication"""

    def setUp(self):
        """Set up test agent"""
        self.agent = User.objects.create_user(
            username='test_agent',
            email='agent@example.com',
            password='pass123'
        )
        self.agent.user_type = 'AGENT'
        self.agent.agent_capabilities = {
            'api_key': 'clwd_agent_test_key_12345',
            'listed_capabilities': ['code_review']
        }
        self.agent.save()

    def test_authenticate_with_valid_api_key(self):
        """Test that valid API key authenticates agent"""
        user = authenticate(None, api_key='clwd_agent_test_key_12345')

        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.agent.id)
        self.assertEqual(user.user_type, 'AGENT')

    def test_authenticate_with_invalid_api_key(self):
        """Test that invalid API key returns None"""
        user = authenticate(None, api_key='invalid_key')
        self.assertIsNone(user)

    def test_authenticate_without_api_key(self):
        """Test that authentication without API key returns None"""
        user = authenticate(None, api_key=None)
        self.assertIsNone(user)


class TestTokenManager(TestCase):
    """Test cases for JWT token management"""

    def setUp(self):
        """Set up test user"""
        self.user = User.objects.create_user(
            username='tokenuser',
            email='token@example.com',
            password='pass123'
        )
        self.user.privy_user_id = 'privy_token_123'
        self.user.wallet_address = '0xabcd1234'
        self.user.save()

    def test_create_access_token(self):
        """Test creating an access token"""
        token = token_manager.create_access_token(self.user)

        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)

        # Verify token can be decoded
        payload = token_manager.verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.user_id, self.user.id)
        self.assertEqual(payload.token_type, 'access')

    def test_create_refresh_token(self):
        """Test creating a refresh token"""
        token = token_manager.create_refresh_token(self.user)

        self.assertIsNotNone(token)
        payload = token_manager.verify_token(token)
        self.assertEqual(payload.token_type, 'refresh')

    def test_create_token_pair(self):
        """Test creating both access and refresh tokens"""
        tokens = token_manager.create_token_pair(self.user)

        self.assertIn('access_token', tokens)
        self.assertIn('refresh_token', tokens)
        self.assertEqual(tokens['token_type'], 'Bearer')
        self.assertIn('expires_in', tokens)

    def test_get_user_from_token(self):
        """Test retrieving user from token"""
        token = token_manager.create_access_token(self.user)

        retrieved_user = token_manager.get_user_from_token(token)

        self.assertEqual(retrieved_user.id, self.user.id)

    def test_verify_invalid_token_returns_none(self):
        """Test that invalid token returns None"""
        payload = token_manager.verify_token('invalid_token_string')
        self.assertIsNone(payload)


class TestAuthViews(TestCase):
    """Test cases for authentication views"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()

    def test_auth_options_page_loads(self):
        """Test that auth options page loads correctly"""
        response = self.client.get(reverse('identity:auth_options'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clawedin')

    def test_dev_auth_page_loads(self):
        """Test that dev auth page loads in development mode"""
        response = self.client.get(reverse('identity:dev_auth_callback'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Development Mode')

    def test_dev_auth_creates_user(self):
        """Test that dev auth creates and logs in user"""
        response = self.client.post(reverse('identity:dev_auth_callback'), {
            'username': 'devtestuser',
            'user_type': 'HUMAN',
            'redirect_uri': '/identity/dashboard/'
        })

        self.assertEqual(response.status_code, 302)  # Redirect after login

        # Check user was created
        user = User.objects.filter(username='devtestuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.user_type, 'HUMAN')

    def test_agent_registration(self):
        """Test AI agent registration endpoint"""
        response = self.client.post(
            reverse('identity:register_agent'),
            data='{"name": "TestBot", "capabilities": ["analysis"]}',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('api_key', data)
        self.assertIn('agent_id', data)

        # Verify agent was created
        agent = User.objects.get(id=data['agent_id'])
        self.assertEqual(agent.user_type, 'AGENT')

    def test_agent_auth_with_valid_key(self):
        """Test agent authentication with valid API key"""
        # First register an agent
        reg_response = self.client.post(
            reverse('identity:register_agent'),
            data='{"name": "AuthTestBot"}',
            content_type='application/json'
        )
        api_key = reg_response.json()['api_key']

        # Now authenticate
        auth_response = self.client.post(
            reverse('identity:agent_auth'),
            data=f'{{"api_key": "{api_key}"}}',
            content_type='application/json'
        )

        self.assertEqual(auth_response.status_code, 200)
        data = auth_response.json()

        self.assertTrue(data['success'])
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)

    def test_agent_auth_with_invalid_key(self):
        """Test agent authentication fails with invalid API key"""
        response = self.client.post(
            reverse('identity:agent_auth'),
            data='{"api_key": "invalid_key"}',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 401)

    def test_login_page_loads(self):
        """Test that login page loads"""
        response = self.client.get(reverse('identity:login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In')

    def test_logout_redirects(self):
        """Test that logout redirects to home"""
        # Create and log in user
        user = User.objects.create_user(
            username='logouttest',
            email='logout@example.com',
            password='pass123'
        )
        self.client.force_login(user)

        response = self.client.get(reverse('identity:logout'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')


class TestDashboardView(TestCase):
    """Test cases for dashboard view"""

    def setUp(self):
        """Set up test user and client"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='dashuser',
            email='dash@example.com',
            password='pass123'
        )

    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication"""
        response = self.client.get(reverse('identity:dashboard'))

        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_loads_for_authenticated_user(self):
        """Test that dashboard loads for logged in user"""
        self.client.force_login(self.user)

        response = self.client.get(reverse('identity:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'dashuser')