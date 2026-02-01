from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.exceptions import ValidationError
import json
import logging

from .models import Profile, ProfileTemplate, ProfileTheme
from .utils import ProfileTemplateRenderer

User = get_user_model()
logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class ProfileTemplateView(View):
    """API for managing profile templates"""
    
    def get(self, request):
        """Get available templates"""
        try:
            templates = ProfileTemplate.objects.filter(is_active=True)
            
            # Filter by category if provided
            category = request.GET.get('category')
            if category:
                templates = templates.filter(category=category)
            
            template_data = []
            for template in templates:
                template_data.append({
                    'id': template.id,
                    'name': template.name,
                    'display_name': template.display_name,
                    'description': template.description,
                    'category': template.category,
                    'template_type': template.template_type,
                    'preview_image_url': template.preview_image_url,
                    'color_scheme': template.color_scheme,
                    'customization_options': template.customization_options,
                    'usage_count': template.usage_count,
                    'is_featured': template.is_featured,
                })
            
            return JsonResponse({
                'success': True,
                'templates': template_data,
                'total': len(template_data)
            })
            
        except Exception as e:
            logger.error(f"Error fetching templates: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch templates'
            }, status=500)
    
    def post(self, request):
        """Create new template (admin function)"""
        try:
            if not request.user.is_authenticated or not request.user.is_staff:
                return JsonResponse({
                    'success': False,
                    'error': 'Admin access required'
                }, status=403)
            
            data = json.loads(request.body)
            
            template = ProfileTemplate.objects.create(
                name=data['name'],
                display_name=data['display_name'],
                description=data['description'],
                category=data['category'],
                template_type=data.get('template_type', 'hybrid'),
                preview_image_url=data.get('preview_image_url', ''),
                color_scheme=data.get('color_scheme', {}),
                layout_config=data.get('layout_config', {}),
                html_template=data['html_template'],
                css_template=data['css_template'],
                customization_options=data.get('customization_options', {}),
                is_featured=data.get('is_featured', False),
            )
            
            return JsonResponse({
                'success': True,
                'template_id': template.id,
                'message': 'Template created successfully'
            })
            
        except (json.JSONDecodeError, KeyError) as e:
            return JsonResponse({
                'success': False,
                'error': 'Invalid data provided'
            }, status=400)
        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create template'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ProfileTemplateSelectionView(View):
    """API for selecting and applying templates to profiles"""
    
    def post(self, request):
        """Apply template to user's profile"""
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required'
                }, status=401)
            
            data = json.loads(request.body)
            template_id = data.get('template_id')
            customizations = data.get('customizations', {})
            
            # Get template and profile
            template = ProfileTemplate.objects.get(id=template_id, is_active=True)
            profile = request.user.profile
            
            # Apply template
            with transaction.atomic():
                profile.profile_template = template.name
                if customizations:
                    profile.custom_css = customizations.get('custom_css', '')
                    profile.background_image_url = customizations.get('background_image_url', '')
                
                profile.save()
                
                # Update template usage
                template.increment_usage()
            
            # Render profile with new template
            renderer = ProfileTemplateRenderer()
            rendered_html = renderer.render_profile(profile, template, customizations)
            rendered_css = renderer.render_css(template, customizations)
            
            return JsonResponse({
                'success': True,
                'message': 'Template applied successfully',
                'template_applied': template.display_name,
                'rendered_html': rendered_html,
                'rendered_css': rendered_css
            })
            
        except ProfileTemplate.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Template not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error applying template: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to apply template'
            }, status=500)
    
    def get(self, request):
        """Preview template with user's profile data"""
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required'
                }, status=401)
            
            template_id = request.GET.get('template_id')
            customizations = request.GET.get('customizations', '{}')
            
            try:
                customizations = json.loads(customizations)
            except json.JSONDecodeError:
                customizations = {}
            
            template = ProfileTemplate.objects.get(id=template_id, is_active=True)
            profile = request.user.profile
            
            # Render preview
            renderer = ProfileTemplateRenderer()
            rendered_html = renderer.render_profile(profile, template, customizations)
            rendered_css = renderer.render_css(template, customizations)
            
            return JsonResponse({
                'success': True,
                'template': {
                    'id': template.id,
                    'display_name': template.display_name,
                    'description': template.description,
                    'template_type': template.template_type,
                },
                'preview_html': rendered_html,
                'preview_css': rendered_css,
                'customizations_used': customizations
            })
            
        except ProfileTemplate.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Template not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error previewing template: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to preview template'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ProfileThemeView(View):
    """API for managing profile themes"""
    
    def get(self, request):
        """Get available themes"""
        try:
            themes = ProfileTheme.objects.filter(is_active=True)
            
            # Filter by type if provided
            theme_type = request.GET.get('type')
            if theme_type:
                themes = themes.filter(theme_type=theme_type)
            
            theme_data = []
            for theme in themes:
                theme_data.append({
                    'id': theme.id,
                    'name': theme.name,
                    'display_name': theme.display_name,
                    'description': theme.description,
                    'theme_type': theme.theme_type,
                    'color_palette': {
                        'primary': theme.primary_color,
                        'secondary': theme.secondary_color,
                        'background': theme.background_color,
                        'text': theme.text_color,
                        'accent': theme.accent_color,
                    },
                    'typography': {
                        'font_family': theme.font_family,
                        'heading_font': theme.heading_font,
                    },
                    'usage_count': theme.usage_count,
                    'is_featured': theme.is_featured,
                })
            
            return JsonResponse({
                'success': True,
                'themes': theme_data,
                'total': len(theme_data)
            })
            
        except Exception as e:
            logger.error(f"Error fetching themes: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch themes'
            }, status=500)
    
    def post(self, request):
        """Apply theme to user's profile"""
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required'
                }, status=401)
            
            data = json.loads(request.body)
            theme_id = data.get('theme_id')
            
            theme = ProfileTheme.objects.get(id=theme_id, is_active=True)
            profile = request.user.profile
            
            with transaction.atomic():
                profile.profile_theme = theme.name
                profile.save()
                
                # Update theme usage
                theme.increment_usage()
            
            return JsonResponse({
                'success': True,
                'message': 'Theme applied successfully',
                'theme_applied': theme.display_name,
                'css_variables': theme.to_css_variables()
            })
            
        except ProfileTheme.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Theme not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error applying theme: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to apply theme'
            }, status=500)

@require_http_methods(["GET"])
def get_template_categories(request):
    """Get available template categories"""
    try:
        categories = ProfileTemplate.objects.values_list('category', flat=True).distinct()
        
        return JsonResponse({
            'success': True,
            'categories': list(categories)
        })
        
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch categories'
        }, status=500)

@require_http_methods(["POST"])
@csrf_exempt
def validate_custom_css(request):
    """Validate custom CSS against professional standards"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        data = json.loads(request.body)
        css_code = data.get('css_code', '')
        
        if not css_code.strip():
            return JsonResponse({
                'success': True,
                'is_valid': True,
                'message': 'Empty CSS is valid'
            })
        
        # Create a temporary profile instance to validate
        profile = Profile(user=request.user)
        is_valid, message = profile.validate_css_professional_standards(css_code)
        
        return JsonResponse({
            'success': True,
            'is_valid': is_valid,
            'message': message
        })
        
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({
            'success': False,
            'error': 'Invalid request data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error validating CSS: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to validate CSS'
        }, status=500)

@require_http_methods(["GET"])
def get_user_customization(request):
    """Get user's current profile customization settings"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        profile = request.user.profile
        
        # Get current template and theme info
        try:
            current_template = ProfileTemplate.objects.get(name=profile.profile_template)
            template_info = {
                'id': current_template.id,
                'display_name': current_template.display_name,
                'category': current_template.category,
                'template_type': current_template.template_type,
                'customization_options': current_template.customization_options,
            }
        except ProfileTemplate.DoesNotExist:
            template_info = None
        
        try:
            current_theme = ProfileTheme.objects.get(name=profile.profile_theme)
            theme_info = {
                'id': current_theme.id,
                'display_name': current_theme.display_name,
                'theme_type': current_theme.theme_type,
                'color_palette': {
                    'primary': current_theme.primary_color,
                    'secondary': current_theme.secondary_color,
                    'background': current_theme.background_color,
                    'text': current_theme.text_color,
                    'accent': current_theme.accent_color,
                },
            }
        except ProfileTheme.DoesNotExist:
            theme_info = None
        
        customization_data = {
            'current_template': template_info,
            'current_theme': theme_info,
            'custom_css': profile.custom_css,
            'background_image_url': profile.background_image_url,
            'profile_visibility': profile.profile_visibility,
            'show_contact_info': profile.show_contact_info,
        }
        
        return JsonResponse({
            'success': True,
            'customization': customization_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching user customization: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch customization settings'
        }, status=500)