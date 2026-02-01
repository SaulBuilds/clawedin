"""
Test suite for profile template system
Following TDD RED-GREEN-REFACTOR methodology
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
import json
import pytest

from .models import (
    Profile, ProfileTemplate, ProfileTheme, 
    Experience, Education, Skill
)
from .utils import ProfileTemplateRenderer, TemplateEngine

User = get_user_model()

class ProfileTemplateModelTest(TestCase):
    """Test ProfileTemplate model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.template_data = {
            'name': 'test_template',
            'display_name': 'Test Template',
            'description': 'A test template for unit testing',
            'category': 'professional',
            'template_type': 'hybrid',
            'html_template': '''
            <div class="profile">
                <h1>{{ profile.headline }}</h1>
                <p>{{ profile.summary }}</p>
                <div class="company">{{ profile.current_company }}</div>
            </div>
            ''',
            'css_template': '''
            .profile {
                font-family: {{ customizations.font_family|default("Arial") }};
                color: {{ customizations.text_color|default("#333") }};
            }
            ''',
            'customization_options': {
                'font_family': {
                    'type': 'select',
                    'options': ['Arial', 'Helvetica', 'Georgia'],
                    'default': 'Arial'
                },
                'text_color': {
                    'type': 'color',
                    'default': '#333333'
                }
            }
        }
    
    def test_create_template(self):
        """RED: Test template creation fails initially"""
        # This should pass with our implementation
        template = ProfileTemplate.objects.create(**self.template_data)
        
        self.assertEqual(template.name, 'test_template')
        self.assertEqual(template.display_name, 'Test Template')
        self.assertTrue(template.is_active)
        self.assertEqual(template.usage_count, 0)
    
    def test_template_increment_usage(self):
        """GREEN: Test usage increment functionality"""
        template = ProfileTemplate.objects.create(**self.template_data)
        initial_count = template.usage_count
        
        template.increment_usage()
        template.refresh_from_db()
        
        self.assertEqual(template.usage_count, initial_count + 1)
    
    def test_template_render_html(self):
        """GREEN: Test HTML rendering functionality"""
        template = ProfileTemplate.objects.create(**self.template_data)
        
        # Create test profile
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            user_type='human'
        )
        profile = Profile.objects.create(
            user=user,
            headline='Test Headline',
            summary='Test summary content',
            current_company='Test Company'
        )
        
        # Render template
        rendered_html = template.get_rendered_html(profile)
        
        self.assertIn('Test Headline', rendered_html)
        self.assertIn('Test summary content', rendered_html)
        self.assertIn('Test Company', rendered_html)
    
    def test_template_render_css(self):
        """GREEN: Test CSS rendering functionality"""
        template = ProfileTemplate.objects.create(**self.template_data)
        
        customizations = {
            'font_family': 'Georgia',
            'text_color': '#666666'
        }
        
        rendered_css = template.get_rendered_css(customizations)
        
        self.assertIn('font-family: Georgia', rendered_css)
        self.assertIn('color: #666666', rendered_css)
    
    def test_template_str_representation(self):
        """GREEN: Test string representation"""
        template = ProfileTemplate.objects.create(**self.template_data)
        
        self.assertEqual(str(template), 'Test Template')

class ProfileThemeModelTest(TestCase):
    """Test ProfileTheme model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.theme_data = {
            'name': 'test_theme',
            'display_name': 'Test Theme',
            'description': 'A test theme for unit testing',
            'theme_type': 'professional',
            'primary_color': '#0073b6',
            'secondary_color': '#e74c3c',
            'background_color': '#ffffff',
            'text_color': '#333333',
            'accent_color': '#f39c12',
        }
    
    def test_create_theme(self):
        """RED: Test theme creation"""
        theme = ProfileTheme.objects.create(**self.theme_data)
        
        self.assertEqual(theme.name, 'test_theme')
        self.assertEqual(theme.display_name, 'Test Theme')
        self.assertTrue(theme.is_active)
        self.assertEqual(theme.usage_count, 0)
    
    def test_theme_increment_usage(self):
        """GREEN: Test theme usage increment"""
        theme = ProfileTheme.objects.create(**self.theme_data)
        initial_count = theme.usage_count
        
        theme.increment_usage()
        theme.refresh_from_db()
        
        self.assertEqual(theme.usage_count, initial_count + 1)
    
    def test_theme_css_variables(self):
        """GREEN: Test CSS variables generation"""
        theme = ProfileTheme.objects.create(**self.theme_data)
        
        css_vars = theme.to_css_variables()
        
        self.assertEqual(css_vars['--primary-color'], '#0073b6')
        self.assertEqual(css_vars['--secondary-color'], '#e74c3c')
        self.assertEqual(css_vars['--background-color'], '#ffffff')
    
    def test_theme_str_representation(self):
        """GREEN: Test string representation"""
        theme = ProfileTheme.objects.create(**self.theme_data)
        
        self.assertEqual(str(theme), 'Test Theme')

class ProfileModelTest(TestCase):
    """Test Profile model with template integration"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            user_type='human'
        )
        
        self.template = ProfileTemplate.objects.create(
            name='test_template',
            display_name='Test Template',
            description='Test template',
            category='professional',
            html_template='<div class="profile">{{ profile.headline }}</div>',
            css_template='.profile { color: #333; }'
        )
        
        self.profile = Profile.objects.create(
            user=self.user,
            headline='Software Engineer',
            summary='Experienced software developer',
            current_company='Tech Corp',
            profile_template='test_template'
        )
    
    def test_profile_creation(self):
        """RED: Test profile creation with template"""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.headline, 'Software Engineer')
        self.assertEqual(self.profile.profile_template, 'test_template')
    
    def test_professional_summary(self):
        """GREEN: Test professional summary generation"""
        self.profile.years_experience = 5
        
        summary = self.profile.get_professional_summary()
        
        self.assertIn('Software Engineer', summary)
        self.assertIn('5+ years', summary)
        self.assertIn('Tech Corp', summary)
    
    def test_css_validation(self):
        """GREEN: Test CSS validation for professional standards"""
        # Valid CSS
        valid_css = ".profile { color: #333; font-size: 16px; }"
        is_valid, message = self.profile.validate_css_professional_standards(valid_css)
        self.assertTrue(is_valid)
        
        # Invalid CSS with dangerous properties
        invalid_css = ".profile { position: fixed; z-index: 9999; }"
        is_valid, message = self.profile.validate_css_professional_standards(invalid_css)
        self.assertFalse(is_valid)
    
    def test_top_connections_management(self):
        """GREEN: Test top 8 connections management"""
        # Create additional users and profiles
        users = []
        profiles = []
        for i in range(10):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                user_type='human'
            )
            profile = Profile.objects.create(
                user=user,
                headline=f'User {i}',
                summary=f'Summary for user {i}'
            )
            users.append(user)
            profiles.append(profile)
        
        # Add 10 connections (should only keep 8)
        for i, profile in enumerate(profiles):
            self.profile.add_top_connection(profile)
        
        # Should only have 8 connections
        self.assertEqual(self.profile.top_connections.count(), 8)
        
        # Should have the 8 most recently added
        latest_connections = self.profile.get_top_connections_ordered()
        self.assertEqual(len(latest_connections), 8)

class ProfileTemplateRendererTest(TestCase):
    """Test template rendering functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.renderer = ProfileTemplateRenderer()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            user_type='human'
        )
        
        self.profile = Profile.objects.create(
            user=self.user,
            headline='Test Engineer',
            summary='Test summary',
            current_company='Test Corp',
            skills_list=['Python', 'Django', 'JavaScript']
        )
        
        self.template = ProfileTemplate.objects.create(
            name='render_test',
            display_name='Render Test Template',
            description='Template for testing rendering',
            category='test',
            html_template='''
            <div class="profile">
                <h1>{{ profile.headline }}</h1>
                <p>{{ profile.summary|truncate_text(20) }}</p>
                <div class="company">{{ profile.current_company }}</div>
                <div class="skills">
                {% for skill in profile.skills_list %}
                    <span class="skill">{{ skill }}</span>
                {% endfor %}
                </div>
            </div>
            ''',
            css_template='''
            .profile {
                font-family: {{ customizations.font_family|default("Arial") }};
                color: {{ customizations.text_color|default("#333") }};
            }
            .skill {
                background: {{ customizations.skill_bg|default("#f0f0f0") }};
            }
            '''
        )
    
    def test_render_profile_html(self):
        """RED: Test profile HTML rendering"""
        customizations = {
            'font_family': 'Georgia',
            'text_color': '#666'
        }
        
        rendered_html = self.renderer.render_profile(
            self.profile, 
            self.template, 
            customizations
        )
        
        self.assertIn('Test Engineer', rendered_html)
        self.assertIn('Test summary', rendered_html)
        self.assertIn('Test Corp', rendered_html)
        self.assertIn('Python', rendered_html)
        self.assertIn('Django', rendered_html)
        self.assertIn('JavaScript', rendered_html)
    
    def test_render_profile_css(self):
        """GREEN: Test CSS rendering with customizations"""
        customizations = {
            'font_family': 'Helvetica',
            'text_color': '#444',
            'skill_bg': '#e0e0e0'
        }
        
        rendered_css = self.renderer.render_css(
            self.template, 
            customizations
        )
        
        self.assertIn('font-family: Helvetica', rendered_css)
        self.assertIn('color: #444', rendered_css)
        self.assertIn('background: #e0e0e0', rendered_css)
    
    def test_html_sanitization(self):
        """GREEN: Test HTML sanitization for security"""
        dangerous_template = ProfileTemplate.objects.create(
            name='dangerous',
            display_name='Dangerous Template',
            description='Template with dangerous content',
            category='test',
            html_template='''
            <div class="profile">
                <h1>{{ profile.headline }}</h1>
                <script>alert('xss')</script>
                <iframe src="malicious.com"></iframe>
                <p onclick="dangerous()">Safe content</p>
            </div>
            ''',
            css_template='.profile { color: #333; }'
        )
        
        rendered_html = self.renderer.render_profile(
            self.profile, 
            dangerous_template
        )
        
        # Should contain safe content
        self.assertIn('Test Engineer', rendered_html)
        self.assertIn('Safe content', rendered_html)
        
        # Should NOT contain dangerous elements
        self.assertNotIn('<script>', rendered_html)
        self.assertNotIn('<iframe>', rendered_html)
        self.assertNotIn('onclick=', rendered_html)
    
    def test_css_validation(self):
        """GREEN: Test CSS validation"""
        dangerous_template = ProfileTemplate.objects.create(
            name='dangerous_css',
            display_name='Dangerous CSS Template',
            description='Template with dangerous CSS',
            category='test',
            html_template='<div>{{ profile.headline }}</div>',
            css_template='''
            .profile {
                position: fixed;
                z-index: 9999;
                animation: slideIn 1s;
                transition: all 0.3s;
                color: #333;
            }
            '''
        )
        
        rendered_css = self.renderer.render_css(
            dangerous_template
        )
        
        # Should contain safe CSS
        self.assertIn('color: #333', rendered_css)
        
        # Should NOT contain dangerous CSS
        self.assertNotIn('position: fixed', rendered_css)
        self.assertNotIn('z-index: 9999', rendered_css)
        self.assertNotIn('animation:', rendered_css)
        self.assertNotIn('transition:', rendered_css)

class TemplateEngineTest(TestCase):
    """Test high-level template engine"""
    
    def setUp(self):
        """Set up test data"""
        self.engine = TemplateEngine()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            user_type='human'
        )
        
        self.profile = Profile.objects.create(
            user=self.user,
            headline='Senior Developer',
            summary='Full-stack developer with 5+ years experience',
            current_company='Tech Startup',
            profile_template='test_template'
        )
        
        self.template = ProfileTemplate.objects.create(
            name='test_template',
            display_name='Test Template',
            description='Template for engine testing',
            category='test',
            html_template='''
            <div class="profile">
                <h1>{{ profile.headline }}</h1>
                <p>{{ profile.summary }}</p>
                <div>{{ profile.current_company }}</div>
            </div>
            ''',
            css_template='''
            .profile {
                font-family: Arial;
                color: #333;
            }
            '''
        )
    
    def test_render_complete_profile(self):
        """RED: Test complete profile rendering"""
        result = self.engine.render_complete_profile(self.profile)
        
        self.assertTrue(result['success'])
        self.assertIn('html', result)
        self.assertIn('css', result)
        self.assertIn('complete', result)
        self.assertIn('template_info', result)
        
        # Check rendered content
        self.assertIn('Senior Developer', result['html'])
        self.assertIn('Tech Startup', result['html'])
        self.assertIn('font-family: Arial', result['css'])
    
    def test_preview_template(self):
        """GREEN: Test template preview with sample data"""
        result = self.engine.preview_template(self.template.id)
        
        self.assertTrue(result['success'])
        self.assertIn('html', result)
        self.assertIn('css', result)
        self.assertIn('template', result)
        
        # Should contain sample data
        self.assertIn('Sample Professional Profile', result['html'])
        self.assertIn('Sample Company', result['html'])

class ProfileTemplateAPITest(TestCase):
    """Test profile template API endpoints"""
    
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
            headline='Test User',
            summary='Test user profile',
            current_company='Test Company'
        )
        
        self.template = ProfileTemplate.objects.create(
            name='api_test',
            display_name='API Test Template',
            description='Template for API testing',
            category='test',
            html_template='<div>{{ profile.headline }}</div>',
            css_template='.profile { color: #333; }'
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_get_templates_list(self):
        """RED: Test GET templates list API"""
        url = reverse('clawedin:template_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('templates', data)
        self.assertEqual(len(data['templates']), 1)
        
        template_data = data['templates'][0]
        self.assertEqual(template_data['name'], 'api_test')
        self.assertEqual(template_data['display_name'], 'API Test Template')
    
    def test_preview_template_api(self):
        """GREEN: Test template preview API"""
        url = reverse('clawedin:template_preview')
        response = self.client.get(url, {'template_id': self.template.id})
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('preview_html', data)
        self.assertIn('preview_css', data)
        self.assertIn('Test User', data['preview_html'])
    
    def test_apply_template_api(self):
        """GREEN: Test template application API"""
        url = reverse('clawedin:template_apply')
        data = {
            'template_id': self.template.id,
            'customizations': {
                'custom_css': '.profile { margin: 10px; }'
            }
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['template_applied'], 'API Test Template')
        
        # Check profile was updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_template, 'api_test')
    
    def test_validate_css_api(self):
        """GREEN: Test CSS validation API"""
        url = reverse('clawedin:validate_css')
        
        # Valid CSS
        valid_data = {'css_code': '.profile { color: #333; }'}
        response = self.client.post(
            url,
            data=json.dumps(valid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertTrue(response_data['is_valid'])
        
        # Invalid CSS
        invalid_data = {'css_code': '.profile { position: fixed; }'}
        response = self.client.post(
            url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertFalse(response_data['is_valid'])
    
    def test_get_user_customization_api(self):
        """GREEN: Test user customization API"""
        url = reverse('clawedin:user_customization')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('customization', data)
        
        customization = data['customization']
        self.assertIsNotNone(customization['current_template'])
        self.assertEqual(customization['current_template']['name'], 'api_test')

class IntegrationTest(TestCase):
    """Integration tests for complete template system"""
    
    def setUp(self):
        """Set up integration test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='integration_user',
            email='integration@example.com',
            user_type='human',
            password='testpass123'
        )
        
        # Create comprehensive template
        self.template = ProfileTemplate.objects.create(
            name='integration_template',
            display_name='Integration Template',
            description='Comprehensive template for integration testing',
            category='professional',
            template_type='hybrid',
            html_template='''
            <div class="profile-container" style="background-image: url('{{ profile.background_image_url }}');">
                <header class="profile-header">
                    <h1 class="profile-name">{{ profile.headline }}</h1>
                    <p class="profile-summary">{{ profile.summary }}</p>
                    <div class="professional-info">
                        <span class="company">{{ profile.current_company }}</span>
                        <span class="experience">{{ profile.years_experience }}+ years</span>
                    </div>
                </header>
                
                <section class="skills-section">
                    <h2>Skills</h2>
                    <div class="skills-grid">
                    {% for skill in profile.skills_list %}
                        <div class="skill-item">{{ skill }}</div>
                    {% endfor %}
                    </div>
                </section>
                
                <section class="top-connections">
                    <h2>Top Professional Connections</h2>
                    <div class="connections-grid">
                    {% for connection in top_connections %}
                        <div class="connection-card">
                            <h3>{{ connection.headline }}</h3>
                            <p>{{ connection.current_company }}</p>
                        </div>
                    {% endfor %}
                    </div>
                </section>
            </div>
            ''',
            css_template='''
            .profile-container {
                font-family: {{ customizations.font_family|default("Arial, sans-serif") }};
                background-color: {{ customizations.bg_color|default("#ffffff") }};
                color: {{ customizations.text_color|default("#333333") }};
                padding: {{ customizations.padding|default("20px") }};
                border-radius: {{ customizations.border_radius|default("8px") }};
            }
            .profile-header {
                background: linear-gradient(135deg, {{ customizations.primary_color|default("#0073b6") }}, {{ customizations.secondary_color|default("#e74c3c") }});
                color: white;
                padding: 30px;
                border-radius: 8px;
                margin-bottom: 30px;
            }
            .skill-item {
                background: {{ customizations.skill_bg|default("#f8f9fa") }};
                color: {{ customizations.skill_color|default("#0073b6") }};
                padding: 8px 16px;
                border-radius: 20px;
                margin: 4px;
                display: inline-block;
            }
            ''',
            customization_options={
                'font_family': {
                    'type': 'select',
                    'options': ['Arial, sans-serif', 'Georgia, serif', 'Helvetica, sans-serif'],
                    'default': 'Arial, sans-serif'
                },
                'bg_color': {'type': 'color', 'default': '#ffffff'},
                'text_color': {'type': 'color', 'default': '#333333'},
                'primary_color': {'type': 'color', 'default': '#0073b6'},
                'secondary_color': {'type': 'color', 'default': '#e74c3c'},
                'padding': {'type': 'text', 'default': '20px'},
                'border_radius': {'type': 'text', 'default': '8px'},
                'skill_bg': {'type': 'color', 'default': '#f8f9fa'},
                'skill_color': {'type': 'color', 'default': '#0073b6'}
            }
        )
        
        self.profile = Profile.objects.create(
            user=self.user,
            headline='Senior Full-Stack Developer',
            summary='Passionate developer with expertise in modern web technologies and a track record of delivering high-quality solutions.',
            current_company='Tech Innovation Labs',
            years_experience=7,
            skills_list=[
                'Python', 'Django', 'JavaScript', 'React', 
                'PostgreSQL', 'Docker', 'AWS', 'Git'
            ],
            background_image_url='https://example.com/professional-bg.jpg',
            profile_template='integration_template'
        )
        
        # Create top connections
        for i in range(5):
            connection_user = User.objects.create_user(
                username=f'connection_{i}',
                email=f'connection{i}@example.com',
                user_type='human'
            )
            connection_profile = Profile.objects.create(
                user=connection_user,
                headline=f'Connection {i}',
                summary=f'Professional connection {i}',
                current_company=f'Company {i}'
            )
            self.profile.top_connections.add(connection_profile)
        
        self.client.login(username='integration_user', password='testpass123')
    
    def test_complete_template_workflow(self):
        """RED: Test complete template workflow from selection to rendering"""
        # 1. Get available templates
        url = reverse('clawedin:template_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        templates_data = json.loads(response.content)
        self.assertTrue(templates_data['success'])
        self.assertEqual(len(templates_data['templates']), 1)
        
        # 2. Preview template with customizations
        preview_url = reverse('clawedin:template_preview')
        customizations = {
            'font_family': 'Georgia, serif',
            'bg_color': '#f8f9fa',
            'primary_color': '#28a745',
            'secondary_color': '#dc3545'
        }
        
        response = self.client.get(
            preview_url,
            {
                'template_id': self.template.id,
                'customizations': json.dumps(customizations)
            }
        )
        self.assertEqual(response.status_code, 200)
        
        preview_data = json.loads(response.content)
        self.assertTrue(preview_data['success'])
        self.assertIn('Senior Full-Stack Developer', preview_data['preview_html'])
        self.assertIn('font-family: Georgia', preview_data['preview_css'])
        self.assertIn('#28a745', preview_data['preview_css'])
        
        # 3. Apply template to profile
        apply_url = reverse('clawedin:template_apply')
        apply_data = {
            'template_id': self.template.id,
            'customizations': customizations
        }
        
        response = self.client.post(
            apply_url,
            data=json.dumps(apply_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        apply_response = json.loads(response.content)
        self.assertTrue(apply_response['success'])
        self.assertIn('rendered_html', apply_response)
        self.assertIn('rendered_css', apply_response)
        
        # 4. Verify applied template
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.profile_template, 'integration_template')
        
        # 5. Get user customization settings
        customization_url = reverse('clawedin:user_customization')
        response = self.client.get(customization_url)
        self.assertEqual(response.status_code, 200)
        
        customization_data = json.loads(response.content)
        self.assertTrue(customization_data['success'])
        self.assertEqual(
            customization_data['customization']['current_template']['name'],
            'integration_template'
        )
    
    def test_template_engine_integration(self):
        """GREEN: Test template engine integration with real data"""
        engine = TemplateEngine()
        
        # Render complete profile
        customizations = {
            'font_family': 'Helvetica, sans-serif',
            'bg_color': '#ffffff',
            'text_color': '#2c3e50',
            'primary_color': '#3498db',
            'secondary_color': '#e74c3c'
        }
        
        result = engine.render_complete_profile(self.profile, customizations)
        
        self.assertTrue(result['success'])
        
        # Verify HTML content
        html = result['html']
        self.assertIn('Senior Full-Stack Developer', html)
        self.assertIn('Tech Innovation Labs', html)
        self.assertIn('Python', html)
        self.assertIn('Django', html)
        self.assertIn('Connection 0', html)
        self.assertIn('Company 1', html)
        
        # Verify CSS content
        css = result['css']
        self.assertIn('font-family: Helvetica', css)
        self.assertIn('color: #2c3e50', css)
        self.assertIn('#3498db', css)
        self.assertIn('#e74c3c', css)
        
        # Verify complete HTML document
        complete = result['complete']
        self.assertIn('<!DOCTYPE html>', complete)
        self.assertIn('<html lang="en">', complete)
        self.assertIn('<head>', complete)
        self.assertIn('<title>Senior Full-Stack Developer', complete)
        self.assertIn('<body>', complete)
        self.assertIn('</body>', complete)
        self.assertIn('</html>', complete)