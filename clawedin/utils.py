from django.template import engines
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)

class ProfileTemplateRenderer:
    """Renderer for profile templates with Jinja2 integration"""
    
    def __init__(self):
        self.jinja_env = engines['jinja2'].env
    
    def render_profile(self, profile, template, customizations=None):
        """Render profile HTML using Jinja2 template"""
        try:
            # Prepare template context
            context = self._prepare_template_context(profile, template, customizations)
            
            # Add custom filters to environment
            self.jinja_env.filters['truncate_text'] = self._truncate_text
            
            # Render using Jinja2
            jinja_template = self.jinja_env.from_string(template.html_template)
            rendered_html = jinja_template.render(**context)
            
            # Sanitize HTML for security
            sanitized_html = self._sanitize_html(rendered_html)
            
            return mark_safe(sanitized_html)
            
        except Exception as e:
            logger.error(f"Error rendering profile template: {str(e)}")
            # Fallback to basic profile rendering
            return self._render_fallback_profile(profile)
    
    def render_css(self, template, customizations=None):
        """Render CSS with customizations"""
        try:
            context = {
                'template': template,
                'customizations': customizations or {},
            }
            
            jinja_template = self.jinja_env.from_string(template.css_template)
            rendered_css = jinja_template.render(**context)
            
            # Validate CSS for security
            validated_css = self._validate_css(rendered_css)
            
            return validated_css
            
        except Exception as e:
            logger.error(f"Error rendering CSS template: {str(e)}")
            return self._render_fallback_css()
    
    def _prepare_template_context(self, profile, template, customizations=None):
        """Prepare comprehensive template context"""
        
        # Basic profile information
        context = {
            'profile': profile,
            'user': profile.user,
            'template': template,
            'customizations': customizations or {},
            
            # Professional information
            'headline': profile.headline,
            'summary': profile.summary,
            'current_company': profile.current_company,
            'current_position': profile.current_position,
            'industry': profile.industry,
            'location': profile.location,
            'years_experience': profile.years_experience,
            'skills_list': profile.skills_list,
            
            # Creative elements
            'background_image_url': profile.background_image_url,
            'custom_css': profile.custom_css,
            
            # Top 8 connections
            'top_connections': profile.get_top_connections_ordered(),
            
            # Experience and education
            'experiences': profile.experiences.all(),
            'education': profile.education.all(),
            'skills': profile.skills.all().order_by('order', 'name'),
            
            # Social links
            'social_links': {
                'linkedin': profile.linkedin_url,
                'twitter': profile.twitter_url,
                'portfolio': profile.portfolio_url,
                'github': profile.github_url,
            },
            
            # Professional summary
            'professional_summary': profile.get_professional_summary(),
            
            # Profile URLs
            'profile_url': profile.get_full_profile_url(),
        }
        
        # Add custom template variables
        if customizations:
            context.update(customizations)
        
        # Add template-specific helpers
        helpers = self._get_template_helpers()
        if helpers:
            context.update(helpers)
        
        return context
    
    def _get_template_helpers(self):
        """Template helper functions for Jinja2"""
        
        def format_date(date_obj):
            if not date_obj:
                return ''
            return date_obj.strftime('%B %Y')
        
        def format_duration(start_date, end_date=None, is_current=False):
            if not start_date:
                return ''
            
            if is_current or not end_date:
                from datetime import date
                duration = date.today() - start_date
            else:
                duration = end_date - start_date
            
            months = duration.days // 30
            years = months // 12
            remaining_months = months % 12
            
            if years > 0:
                return f"{years} yr {remaining_months} mos"
            else:
                return f"{months} mos"
        
        def skill_level_badge(level):
            badges = {
                'beginner': '<span class="skill-badge beginner">Beginner</span>',
                'intermediate': '<span class="skill-badge intermediate">Intermediate</span>',
                'advanced': '<span class="skill-badge advanced">Advanced</span>',
                'expert': '<span class="skill-badge expert">Expert</span>',
            }
            return badges.get(level, '')
        
    def _truncate_text(self, text, length=150):
        """Truncate text to specified length"""
        if not text:
            return ''
        if len(text) <= length:
            return text
        return text[:length] + '...'
    
    def _format_date(self, date_obj):
        """Format date for display"""
        if not date_obj:
            return ''
        return date_obj.strftime('%B %Y')
    
    def _format_duration(self, start_date, end_date=None, is_current=False):
        """Format duration between dates"""
        if not start_date:
            return ''
        
        if is_current or not end_date:
            from datetime import date
            duration = date.today() - start_date
        else:
            duration = end_date - start_date
        
        months = duration.days // 30
        years = months // 12
        remaining_months = months % 12
        
        if years > 0:
            return f"{years} yr {remaining_months} mos"
        else:
            return f"{months} mos"
    
    def _skill_level_badge(self, level):
        """Generate skill level badge HTML"""
        badges = {
            'beginner': '<span class="skill-badge beginner">Beginner</span>',
            'intermediate': '<span class="skill-badge intermediate">Intermediate</span>',
            'advanced': '<span class="skill-badge advanced">Advanced</span>',
            'expert': '<span class="skill-badge expert">Expert</span>',
        }
        return badges.get(level, '')
    
    def _is_valid_url(self, url):
        """Check if URL is valid"""
        if not url:
            return False
        return url.startswith(('http://', 'https://'))
        
        def is_valid_url(url):
            if not url:
                return False
            return url.startswith(('http://', 'https://'))
        
        return {
            'format_date': format_date,
            'format_duration': format_duration,
            'skill_level_badge': skill_level_badge,
            'truncate_text': truncate_text,
            'is_valid_url': is_valid_url,
        }
    
    def _sanitize_html(self, html_content):
        """Sanitize HTML to prevent XSS while allowing creative elements"""
        try:
            # Basic HTML sanitization
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove dangerous tags and attributes
            dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input']
            for tag in dangerous_tags:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Remove dangerous attributes
            dangerous_attrs = ['onclick', 'onload', 'onerror', 'onmouseover', 'style']
            for tag in soup.find_all():
                for attr in dangerous_attrs:
                    if tag.has_attr(attr):
                        del tag[attr]
            
            # Allow certain safe attributes
            safe_attrs = ['href', 'src', 'alt', 'title', 'class', 'id']
            for tag in soup.find_all():
                attrs = dict(tag.attrs)
                for attr in attrs:
                    if attr not in safe_attrs:
                        del tag[attr]
            
            return str(soup)
            
        except Exception as e:
            logger.error(f"Error sanitizing HTML: {str(e)}")
            return '<div class="error">Profile rendering error</div>'
    
    def _validate_css(self, css_content):
        """Validate CSS against professional standards"""
        try:
            # Remove dangerous CSS properties
            dangerous_patterns = [
                r'position\s*:\s*(fixed|absolute)',
                r'z-index\s*:\s*\d+',
                r'overflow\s*:\s*hidden',
                r'cursor\s*:\s*pointer',
                r'animation\s*:',
                r'transition\s*:',
                r'transform\s*:',
                r'@import',
                r'javascript:',
                r'expression\s*\(',
            ]
            
            validated_css = css_content
            for pattern in dangerous_patterns:
                validated_css = re.sub(pattern, '/* REMOVED */', validated_css, flags=re.IGNORECASE)
            
            # Add security comment
            validated_css = '/* CSS validated for professional standards */\n' + validated_css
            
            return validated_css
            
        except Exception as e:
            logger.error(f"Error validating CSS: {str(e)}")
            return '/* CSS validation failed */\n.profile { font-family: Arial, sans-serif; }'
    
    def _render_fallback_profile(self, profile):
        """Fallback profile rendering if template fails"""
        return f"""
        <div class="profile-fallback">
            <h2>{profile.headline}</h2>
            <p>{profile.summary}</p>
            <div class="company">{profile.current_company}</div>
            <div class="experience">{profile.years_experience}+ years experience</div>
        </div>
        """
    
    def _render_fallback_css(self):
        """Fallback CSS if template CSS fails"""
        return """
        /* Fallback Professional Profile Styles */
        .profile-fallback {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #ffffff;
            border: 1px solid #e1e5e9;
            border-radius: 8px;
        }
        
        .profile-fallback h2 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .profile-fallback p {
            color: #34495e;
            line-height: 1.6;
            margin-bottom: 15px;
        }
        
        .profile-fallback .company {
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }
        
        .profile-fallback .experience {
            color: #7f8c8d;
            font-style: italic;
        }
        """

class TemplateEngine:
    """High-level template engine for profile rendering"""
    
    def __init__(self):
        self.renderer = ProfileTemplateRenderer()
    
    def render_complete_profile(self, profile, customizations=None):
        """Render complete profile with HTML and CSS"""
        try:
            from .models import ProfileTemplate
            
            # Get current template
            template = ProfileTemplate.objects.get(name=profile.profile_template, is_active=True)
            
            # Render components
            html_content = self.renderer.render_profile(profile, template, customizations)
            css_content = self.renderer.render_css(template, customizations)
            
            # Combine into complete profile
            complete_profile = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{profile.headline} - Professional Profile</title>
                <style>
                    {css_content}
                </style>
            </head>
            <body>
                <div class="profile-container">
                    {html_content}
                </div>
            </body>
            </html>
            """
            
            return {
                'success': True,
                'html': html_content,
                'css': css_content,
                'complete': complete_profile,
                'template_info': {
                    'name': template.name,
                    'display_name': template.display_name,
                    'type': template.template_type,
                }
            }
            
        except ProfileTemplate.DoesNotExist:
            return {
                'success': False,
                'error': 'Template not found'
            }
        except Exception as e:
            logger.error(f"Error rendering complete profile: {str(e)}")
            return {
                'success': False,
                'error': 'Profile rendering failed'
            }
    
    def preview_template(self, template_id, customizations=None):
        """Preview template with sample data"""
        try:
            from .models import ProfileTemplate, Profile
            
            template = ProfileTemplate.objects.get(id=template_id, is_active=True)
            
            # Create sample profile data for preview
            sample_profile = Profile(
                headline="Sample Professional Profile",
                summary="This is a sample profile to preview the template design and layout.",
                current_company="Sample Company",
                current_position="Sample Position",
                industry="Technology",
                location="San Francisco, CA",
                years_experience=5,
                skills_list=["Python", "Django", "JavaScript", "UI/UX Design"],
                background_image_url=customizations.get('background_image_url', '') if customizations else '',
            )
            
            # Render preview
            html_content = self.renderer.render_profile(sample_profile, template, customizations)
            css_content = self.renderer.render_css(template, customizations)
            
            return {
                'success': True,
                'html': html_content,
                'css': css_content,
                'template': {
                    'id': template.id,
                    'name': template.name,
                    'display_name': template.display_name,
                    'type': template.template_type,
                    'category': template.category,
                }
            }
            
        except ProfileTemplate.DoesNotExist:
            return {
                'success': False,
                'error': 'Template not found'
            }
        except Exception as e:
            logger.error(f"Error previewing template: {str(e)}")
            return {
                'success': False,
                'error': 'Template preview failed'
            }