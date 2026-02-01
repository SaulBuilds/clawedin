"""
Test suite for profile authentication and security system
Following TDD RED-GREEN-REFACTOR methodology
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
import json
import pytest
from datetime import timedelta

from .models import Profile
from .auth_models import (
    ProfileShareToken, ProfileAccessLog, 
    ProfileVisibility, ProfileShare
)
from .auth_views import ProfileAuthMiddleware

User = get_user_model()

class ProfileShareTokenTest(TestCase):
    """Test profile share token functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            user_type='human',
            password='testpass123'
        )
        
        self.profile = Profile.objects.create(
            user=self.user,
            headline='Software Engineer',
            summary='Experienced developer',
            current_company='Tech Corp'
        )
    
    def test_create_share_token(self):
        """RED: Test share token creation"""
        token = ProfileShareToken.create_token(
            profile=self.profile,
            token_type='view',
            created_by=self.user,
            purpose='Recruitment',
            description='Token for recruitment purposes'
        )
        
        self.assertEqual(token.profile, self.profile)
        self.assertEqual(token.token_type, 'view')
        self.assertEqual(token.created_by, self.user)
        self.assertEqual(token.purpose, 'Recruitment')
        self.assertTrue(token.is_active)
        self.assertEqual(token.view_count, 0)
    
    def test_token_validation(self):
        """GREEN: Test token validation logic"""
        # Create valid token
        token = ProfileShareToken.create_token(
            profile=self.profile,
            token_type='view',
            created_by=self.user,
            purpose='Test',
            expires_in_days=7
        )
        
        self.assertTrue(token.is_valid())
        
        # Test expired token
        token.expires_at = timezone.now() - timedelta(days=1)
        token.save()
        self.assertFalse(token.is_valid())
        
        # Test revoked token
        token.expires_at = timezone.now() + timedelta(days=1)
        token.save()
        token.revoke()
        self.assertFalse(token.is_valid())
        
        # Test max views limit
        token.is_active = True
        token.max_views = 5
        token.view_count = 5
        token.save()
        self.assertFalse(token.is_valid())
    
    def test_token_permissions(self):
        """GREEN: Test token permission checking"""
        # Create token with specific permissions
        token = ProfileShareToken.create_token(
            profile=self.profile,
            token_type='edit',
            created_by=self.user,
            purpose='Test',
            can_view=True,
            can_edit=True,
            can_share=False,
            can_download=True
        )
        
        # Test permission combinations
        self.assertTrue(token.can_access_with_permissions(['view']))
        self.assertTrue(token.can_access_with_permissions(['edit']))
        self.assertFalse(token.can_access_with_permissions(['share']))
        self.assertTrue(token.can_access_with_permissions(['view', 'edit']))
        self.assertFalse(token.can_access_with_permissions(['view', 'share']))
    
    def test_token_access_recording(self):
        """GREEN: Test token access recording"""
        token = ProfileShareToken.create_token(
            profile=self.profile,
            token_type='view',
            created_by=self.user,
            purpose='Test'
        )
        
        initial_count = token.view_count
        self.assertIsNone(token.last_used_at)
        
        # Record access
        token.record_access('192.168.1.1')
        
        token.refresh_from_db()
        self.assertEqual(token.view_count, initial_count + 1)
        self.assertIsNotNone(token.last_used_at)
        self.assertEqual(str(token.last_ip), '192.168.1.1')

class ProfileVisibilityTest(TestCase):
    """Test profile visibility and privacy settings"""
    
    def setUp(self):
        """Set up test data"""
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            user_type='human',
            password='testpass123'
        )
        
        self.visitor = User.objects.create_user(
            username='visitor',
            email='visitor@example.com',
            user_type='human',
            password='testpass123'
        )
        
        self.profile = Profile.objects.create(
            user=self.owner,
            headline='Software Engineer',
            summary='Experienced developer',
            current_company='Tech Corp'
        )
        
        self.visibility = ProfileVisibility.objects.create(
            profile=self.profile,
            overall_visibility='connections',
            show_contact_info=True,
            show_experience=True,
            allow_public_sharing=True,
            track_views=True
        )
    
    def test_public_visibility(self):
        """RED: Test public visibility settings"""
        self.visibility.overall_visibility = 'public'
        self.visibility.save()
        
        # Owner can always view
        can_view, reason = self.visibility.can_user_view(self.owner)
        self.assertTrue(can_view)
        self.assertEqual(reason, 'owner')
        
        # Visitors can view public profiles
        can_view, reason = self.visibility.can_user_view(self.visitor)
        self.assertTrue(can_view)
        self.assertEqual(reason, 'public')
        
        # Anonymous users can view public profiles
        can_view, reason = self.visibility.can_user_view(None)
        self.assertTrue(can_view)
        self.assertEqual(reason, 'public')
    
    def test_private_visibility(self):
        """GREEN: Test private visibility settings"""
        self.visibility.overall_visibility = 'private'
        self.visibility.save()
        
        # Owner can always view
        can_view, reason = self.visibility.can_user_view(self.owner)
        self.assertTrue(can_view)
        self.assertEqual(reason, 'owner')
        
        # Visitors cannot view private profiles
        can_view, reason = self.visibility.can_user_view(self.visitor)
        self.assertFalse(can_view)
        self.assertEqual(reason, 'private')
    
    def test_blocked_users(self):
        """GREEN: Test blocked user functionality"""
        self.visibility.overall_visibility = 'public'
        self.visibility.save()
        
        # Initially visitor can view
        can_view, reason = self.visibility.can_user_view(self.visitor)
        self.assertTrue(can_view)
        
        # Block the visitor
        self.visibility.block_user(self.visitor)
        
        # Now visitor cannot view
        can_view, reason = self.visibility.can_user_view(self.visitor)
        self.assertFalse(can_view)
        self.assertEqual(reason, 'blocked')
        
        # Unblock the visitor
        self.visibility.unblock_user(self.visitor)
        
        # Visitor can view again
        can_view, reason = self.visibility.can_user_view(self.visitor)
        self.assertTrue(can_view)

class ProfileShareTest(TestCase):
    """Test profile sharing functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            user_type='human',
            password='testpass123'
        )
        
        self.profile = Profile.objects.create(
            user=self.user,
            headline='Software Engineer',
            summary='Experienced developer',
            current_company='Tech Corp'
        )
    
    def test_create_profile_share(self):
        """RED: Test profile share creation"""
        share = ProfileShare.objects.create(
            profile=self.profile,
            shared_by=self.user,
            share_type='link',
            title='Share for Recruitment',
            description='Share profile with potential employers',
            expires_at=timezone.now() + timedelta(days=30),
            max_clicks=100
        )
        
        self.assertEqual(share.profile, self.profile)
        self.assertEqual(share.shared_by, self.user)
        self.assertEqual(share.share_type, 'link')
        self.assertEqual(share.status, 'active')
        self.assertEqual(share.click_count, 0)
        self.assertEqual(share.views, 0)
    
    def test_share_activity_tracking(self):
        """GREEN: Test share activity tracking"""
        share = ProfileShare.objects.create(
            profile=self.profile,
            shared_by=self.user,
            share_type='link',
            title='Test Share'
        )
        
        # Test click recording
        share.record_click()
        share.refresh_from_db()
        self.assertEqual(share.click_count, 1)
        
        # Test view recording
        share.record_view()
        share.refresh_from_db()
        self.assertEqual(share.views, 1)
        
        # Test multiple recordings
        share.record_click()
        share.record_view()
        share.refresh_from_db()
        self.assertEqual(share.click_count, 2)
        self.assertEqual(share.views, 2)
    
    def test_share_expiration(self):
        """GREEN: Test share expiration logic"""
        # Active share
        share = ProfileShare.objects.create(
            profile=self.profile,
            shared_by=self.user,
            share_type='link',
            title='Active Share',
            expires_at=timezone.now() + timedelta(days=1)
        )
        
        self.assertTrue(share.is_active())
        
        # Expired share
        expired_share = ProfileShare.objects.create(
            profile=self.profile,
            shared_by=self.user,
            share_type='link',
            title='Expired Share',
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        self.assertFalse(expired_share.is_active())
        
        # Share with max clicks reached
        limited_share = ProfileShare.objects.create(
            profile=self.profile,
            shared_by=self.user,
            share_type='link',
            title='Limited Share',
            max_clicks=5
        )
        limited_share.click_count = 5
        limited_share.save()
        
        self.assertFalse(limited_share.is_active())
        
        # Revoked share
        active_share = ProfileShare.objects.create(
            profile=self.profile,
            shared_by=self.user,
            share_type='link',
            title='Revoked Share'
        )
        active_share.revoke()
        
        self.assertFalse(active_share.is_active())

class ProfileAuthMiddlewareTest(TestCase):
    """Test profile authentication middleware"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            user_type='human',
            password='testpass123'
        )
        
        self.profile = Profile.objects.create(
            user=self.user,
            headline='Software Engineer',
            summary='Experienced developer',
            current_company='Tech Corp'
        )
        
        self.token = ProfileShareToken.create_token(
            profile=self.profile,
            token_type='view',
            created_by=self.user,
            purpose='Test'
        )
        
        self.middleware = ProfileAuthMiddleware(lambda req: None)
    
    def test_token_extraction_from_header(self):
        """RED: Test token extraction from Authorization header"""
        class MockRequest:
            def __init__(self, headers):
                self.headers = headers
                self.GET = {}
                self.POST = {}
                self.META = {}
                self.method = 'GET'
        
        # Test Bearer token
        request = MockRequest({'Authorization': 'Bearer test-token-123'})
        token = self.middleware._extract_token(request)
        self.assertEqual(token, 'test-token-123')
        
        # Test no token
        request = MockRequest({})
        token = self.middleware._extract_token(request)
        self.assertIsNone(token)
    
    def test_token_extraction_from_query(self):
        """GREEN: Test token extraction from query parameter"""
        class MockRequest:
            def __init__(self, get_data):
                self.headers = {}
                self.GET = get_data
                self.POST = {}
                self.META = {}
        
        request = MockRequest({'token': 'query-token-456'})
        token = self.middleware._extract_token(request)
        self.assertEqual(token, 'query-token-456')
    
    def test_token_extraction_from_post(self):
        """GREEN: Test token extraction from POST data"""
        class MockRequest:
            def __init__(self, method, post_data):
                self.headers = {}
                self.GET = {}
                self.POST = post_data
                self.META = {}
                self.method = method
        
        request = MockRequest('POST', {'token': 'post-token-789'})
        token = self.middleware._extract_token(request)
        self.assertEqual(token, 'post-token-789')

class ProfileAuthAPITest(TestCase):
    """Test profile authentication API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            user_type='human',
            password='testpass123'
        )
        
        self.profile = Profile.objects.create(
            user=self.user,
            headline='Software Engineer',
            summary='Experienced developer',
            current_company='Tech Corp'
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_create_share_token_api(self):
        """RED: Test share token creation API"""
        url = reverse('clawedin:auth_tokens')
        data = {
            'token_type': 'view',
            'purpose': 'Recruitment',
            'description': 'Token for potential employers',
            'can_view': True,
            'can_edit': False,
            'expires_in_days': 30,
            'max_views': 100
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('token', response_data)
        self.assertIn('share_url', response_data['token'])
        self.assertEqual(response_data['token']['token_type'], 'view')
        self.assertEqual(response_data['token']['purpose'], 'Recruitment')
    
    def test_get_share_tokens_api(self):
        """GREEN: Test getting share tokens API"""
        # Create a token first
        token = ProfileShareToken.create_token(
            profile=self.profile,
            token_type='view',
            created_by=self.user,
            purpose='Test'
        )
        
        url = reverse('clawedin:auth_tokens')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('tokens', response_data)
        self.assertEqual(len(response_data['tokens']), 1)
        
        token_data = response_data['tokens'][0]
        self.assertEqual(token_data['token_type'], 'view')
        self.assertEqual(token_data['purpose'], 'Test')
        self.assertTrue(token_data['is_active'])
    
    def test_revoke_token_api(self):
        """GREEN: Test token revocation API"""
        # Create a token first
        token = ProfileShareToken.create_token(
            profile=self.profile,
            token_type='view',
            created_by=self.user,
            purpose='Test'
        )
        
        url = reverse('clawedin:auth_token_detail', kwargs={'token_id': token.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify token is revoked
        token.refresh_from_db()
        self.assertFalse(token.is_active)
    
    def test_visibility_settings_api(self):
        """GREEN: Test visibility settings API"""
        url = reverse('clawedin:auth_visibility')
        
        # Get initial settings
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('visibility', response_data)
        
        # Update settings
        update_data = {
            'overall_visibility': 'public',
            'show_contact_info': False,
            'allow_public_sharing': True,
            'track_views': True,
            'show_view_count': True
        }
        
        response = self.client.put(
            url,
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
    
    def test_profile_access_with_token(self):
        """GREEN: Test profile access with token"""
        # Create a share token
        token = ProfileShareToken.create_token(
            profile=self.profile,
            token_type='view',
            created_by=self.user,
            purpose='Test'
        )
        
        # Access profile with token
        url = reverse('clawedin:profile_access_token')
        response = self.client.get(url, {'token': token.token})
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('profile', response_data)
        self.assertEqual(response_data['profile']['headline'], 'Software Engineer')
        self.assertEqual(response_data['access_info']['viewed_via'], 'token')
    
    def test_profile_access_denied_invalid_token(self):
        """GREEN: Test profile access denied with invalid token"""
        url = reverse('clawedin:profile_access_token')
        response = self.client.get(url, {'token': 'invalid-token-123'})
        
        self.assertEqual(response.status_code, 403)
        
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    def test_profile_analytics_api(self):
        """GREEN: Test profile analytics API"""
        url = reverse('clawedin:auth_analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('analytics', response_data)
        
        analytics = response_data['analytics']
        self.assertIn('total_views', analytics)
        self.assertIn('unique_visitors', analytics)
        self.assertIn('access_by_type', analytics)
        self.assertIn('recent_activity', analytics)

class ProfileAuthIntegrationTest(TestCase):
    """Integration tests for complete authentication workflow"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            user_type='human',
            password='testpass123'
        )
        
        self.visitor = User.objects.create_user(
            username='visitor',
            email='visitor@example.com',
            user_type='human',
            password='testpass123'
        )
        
        self.profile = Profile.objects.create(
            user=self.owner,
            headline='Senior Developer',
            summary='Experienced full-stack developer',
            current_company='Tech Startup',
            years_experience=7,
            skills_list=['Python', 'Django', 'JavaScript', 'React']
        )
    
    def test_complete_share_workflow(self):
        """RED: Test complete profile sharing workflow"""
        # 1. Login as owner
        self.client.login(username='owner', password='testpass123')
        
        # 2. Create share token
        token_url = reverse('clawedin:auth_tokens')
        token_data = {
            'token_type': 'view',
            'purpose': 'Recruitment',
            'description': 'Share with potential employers',
            'can_view': True,
            'expires_in_days': 30,
            'max_views': 50
        }
        
        response = self.client.post(
            token_url,
            data=json.dumps(token_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        token_response = json.loads(response.content)
        share_token = token_response['token']['token']
        
        # 3. Logout
        self.client.logout()
        
        # 4. Access profile with token as anonymous user
        access_url = reverse('clawedin:profile_access_token')
        response = self.client.get(access_url, {'token': share_token})
        
        self.assertEqual(response.status_code, 200)
        profile_response = json.loads(response.content)
        self.assertTrue(profile_response['success'])
        self.assertEqual(profile_response['profile']['headline'], 'Senior Developer')
        self.assertEqual(profile_response['access_info']['viewed_via'], 'token')
        
        # 5. Verify access log was created
        access_log = ProfileAccessLog.objects.filter(
            profile=self.profile,
            access_type='view',
            result='success'
        ).first()
        
        self.assertIsNotNone(access_log)
        self.assertEqual(access_log.access_type, 'view')
        self.assertEqual(access_log.result, 'success')
        self.assertEqual(access_log.token.token, share_token)
        
        # 6. Check analytics
        self.client.login(username='owner', password='testpass123')
        analytics_url = reverse('clawedin:auth_analytics')
        response = self.client.get(analytics_url)
        
        self.assertEqual(response.status_code, 200)
        analytics_response = json.loads(response.content)
        analytics = analytics_response['analytics']
        self.assertGreater(analytics['total_views'], 0)
    
    def test_privacy_controls_workflow(self):
        """GREEN: Test privacy controls workflow"""
        # 1. Login as owner
        self.client.login(username='owner', password='testpass123')
        
        # 2. Set profile to private
        visibility_url = reverse('clawedin:auth_visibility')
        visibility_data = {
            'overall_visibility': 'private',
            'show_contact_info': False,
            'allow_public_sharing': False,
            'track_views': True
        }
        
        response = self.client.put(
            visibility_url,
            data=json.dumps(visibility_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # 3. Logout and try to access as visitor
        self.client.logout()
        self.client.login(username='visitor', password='testpass123')
        
        access_url = reverse('clawedin:profile_access', kwargs={'username': 'owner'})
        response = self.client.get(access_url)
        
        self.assertEqual(response.status_code, 403)
        
        # 4. Verify access was denied and logged
        denied_log = ProfileAccessLog.objects.filter(
            profile=self.profile,
            access_type='view',
            result='denied'
        ).first()
        
        self.assertIsNotNone(denied_log)
        self.assertEqual(denied_log.user, self.visitor)
        
        # 5. Owner should still be able to access
        self.client.logout()
        self.client.login(username='owner', password='testpass123')
        
        response = self.client.get(access_url)
        self.assertEqual(response.status_code, 200)
        
        profile_response = json.loads(response.content)
        self.assertTrue(profile_response['success'])
        self.assertEqual(profile_response['access_info']['viewed_via'], 'direct')
    
    def test_token_permission_workflow(self):
        """GREEN: Test token permission workflow"""
        # 1. Create token with limited permissions
        self.client.login(username='owner', password='testpass123')
        
        token_url = reverse('clawedin:auth_tokens')
        token_data = {
            'token_type': 'view',
            'purpose': 'Limited Access',
            'can_view': True,
            'can_edit': False,
            'can_share': False,
            'allowed_domains': ['example.com', 'trusted.com']
        }
        
        response = self.client.post(
            token_url,
            data=json.dumps(token_data),
            content_type='application/json'
        )
        
        token_response = json.loads(response.content)
        share_token = token_response['token']['token']
        
        # 2. Access with allowed referer
        self.client.logout()
        access_url = reverse('clawedin:profile_access_token')
        
        response = self.client.get(
            access_url, 
            {'token': share_token},
            HTTP_REFERER='https://example.com/page'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # 3. Try to access with disallowed referer
        response = self.client.get(
            access_url,
            {'token': share_token},
            HTTP_REFERER='https://malicious.com/page'
        )
        
        self.assertEqual(response.status_code, 403)
        
        # 4. Verify denied access was logged
        denied_log = ProfileAccessLog.objects.filter(
            profile=self.profile,
            access_type='view',
            result='denied'
        ).last()
        
        self.assertIsNotNone(denied_log)
        self.assertEqual(denied_log.error_message, 'domain_not_allowed')