from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.middleware.security import SecurityMiddleware
import json
import logging
import hashlib

from .models import Profile
from .auth_models import (
    ProfileShareToken, ProfileAccessLog, 
    ProfileVisibility, ProfileShare
)
from .utils import ProfileTemplateRenderer

User = get_user_model()
logger = logging.getLogger(__name__)

class ProfileAuthMiddleware:
    """Middleware for OAuth-like profile authentication"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Extract token from request
        token = self._extract_token(request)
        
        if token:
            try:
                share_token = ProfileShareToken.objects.get(
                    token=token,
                    is_active=True
                )
                
                if share_token.is_valid():
                    request.profile_token = share_token
                    # Record access
                    self._log_access(request, share_token)
                else:
                    request.profile_token = None
                    
            except ProfileShareToken.DoesNotExist:
                request.profile_token = None
        
        response = self.get_response(request)
        return response
    
    def _extract_token(self, request):
        """Extract token from various sources"""
        # Check Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # Check query parameter
        token = request.GET.get('token')
        if token:
            return token
        
        # Check POST data
        if request.method == 'POST':
            token = request.POST.get('token')
            if token:
                return token
        
        return None
    
    def _log_access(self, request, token):
        """Log profile access attempt"""
        try:
            ProfileAccessLog.objects.create(
                profile=token.profile,
                access_type='api',
                result='success',
                token=token,
                user=request.user if request.user.is_authenticated else None,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referer=request.META.get('HTTP_REFERER', ''),
                endpoint=request.path,
                method=request.method,
            )
        except Exception as e:
            logger.error(f"Failed to log profile access: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

@method_decorator(csrf_exempt, name='dispatch')
class ProfileShareTokenView(View):
    """API for managing profile share tokens (OAuth-like)"""
    
    def get(self, request):
        """Get user's share tokens"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            profile = request.user.clawedin_profile
            tokens = ProfileShareToken.objects.filter(
                created_by=request.user,
                is_active=True
            ).order_by('-created_at')
            
            token_data = []
            for token in tokens:
                token_data.append({
                    'id': token.id,
                    'token': token.token,
                    'token_type': token.token_type,
                    'purpose': token.purpose,
                    'description': token.description,
                    'can_view': token.can_view,
                    'can_edit': token.can_edit,
                    'can_share': token.can_share,
                    'can_download': token.can_download,
                    'expires_at': token.expires_at.isoformat(),
                    'max_views': token.max_views,
                    'view_count': token.view_count,
                    'is_active': token.is_valid(),
                    'last_used_at': token.last_used_at.isoformat() if token.last_used_at else None,
                    'created_at': token.created_at.isoformat(),
                })
            
            return JsonResponse({
                'success': True,
                'tokens': token_data
            })
            
        except Exception as e:
            logger.error(f"Error fetching share tokens: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch tokens'
            }, status=500)
    
    def post(self, request):
        """Create new share token"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            data = json.loads(request.body)
            profile = request.user.clawedin_profile
            
            # Validate required fields
            required_fields = ['token_type', 'purpose']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Create token
            token = ProfileShareToken.create_token(
                profile=profile,
                token_type=data['token_type'],
                created_by=request.user,
                purpose=data['purpose'],
                description=data.get('description', ''),
                can_view=data.get('can_view', True),
                can_edit=data.get('can_edit', False),
                can_share=data.get('can_share', False),
                can_download=data.get('can_download', False),
                expires_in_days=data.get('expires_in_days', 30),
                max_views=data.get('max_views'),
                allowed_domains=data.get('allowed_domains', []),
                metadata=data.get('metadata', {})
            )
            
            return JsonResponse({
                'success': True,
                'token': {
                    'id': token.id,
                    'token': token.token,
                    'token_type': token.token_type,
                    'purpose': token.purpose,
                    'expires_at': token.expires_at.isoformat(),
                    'share_url': f"{request.build_absolute_uri('/api/profiles/view/')}?token={token.token}"
                }
            })
            
        except (json.JSONDecodeError, KeyError) as e:
            return JsonResponse({
                'success': False,
                'error': 'Invalid request data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error creating share token: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create token'
            }, status=500)
    
    def put(self, request, token_id):
        """Update existing token"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            data = json.loads(request.body)
            token = ProfileShareToken.objects.get(
                id=token_id,
                created_by=request.user
            )
            
            # Update allowed fields
            updatable_fields = [
                'purpose', 'description', 'can_view', 'can_edit', 
                'can_share', 'can_download', 'max_views'
            ]
            
            for field in updatable_fields:
                if field in data:
                    setattr(token, field, data[field])
            
            # Handle expiry extension
            if 'extend_days' in data:
                token.extend_expiry(data['extend_days'])
            
            token.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Token updated successfully'
            })
            
        except ProfileShareToken.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Token not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error updating token: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to update token'
            }, status=500)
    
    def delete(self, request, token_id):
        """Revoke/delete token"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            token = ProfileShareToken.objects.get(
                id=token_id,
                created_by=request.user
            )
            
            token.revoke()
            
            return JsonResponse({
                'success': True,
                'message': 'Token revoked successfully'
            })
            
        except ProfileShareToken.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Token not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error revoking token: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to revoke token'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ProfileVisibilityView(View):
    """API for managing profile visibility settings"""
    
    def get(self, request):
        """Get user's visibility settings"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            profile = request.user.clawedin_profile
            
            # Get or create visibility settings
            visibility, created = ProfileVisibility.objects.get_or_create(
                profile=profile
            )
            
            return JsonResponse({
                'success': True,
                'visibility': {
                    'overall_visibility': visibility.overall_visibility,
                    'show_contact_info': visibility.show_contact_info,
                    'show_experience': visibility.show_experience,
                    'show_education': visibility.show_education,
                    'show_skills': visibility.show_skills,
                    'show_connections': visibility.show_connections,
                    'show_activity': visibility.show_activity,
                    'appear_in_search': visibility.appear_in_search,
                    'search_visibility_level': visibility.search_visibility_level,
                    'allow_public_sharing': visibility.allow_public_sharing,
                    'require_approval_for_sharing': visibility.require_approval_for_sharing,
                    'auto_approve_connections': visibility.auto_approve_connections,
                    'visible_to_alumni': visibility.visible_to_alumni,
                    'visible_to_colleagues': visibility.visible_to_colleagues,
                    'visible_to_group_members': visibility.visible_to_group_members,
                    'custom_visibility_rules': visibility.custom_visibility_rules,
                    'max_share_duration_days': visibility.max_share_duration_days,
                    'require_2fa_for_sensitive': visibility.require_2fa_for_sensitive,
                    'track_views': visibility.track_views,
                    'show_view_count': visibility.show_view_count,
                },
                'blocked_users': list(
                    visibility.blocked_users.values_list('id', flat=True)
                )
            })
            
        except Exception as e:
            logger.error(f"Error fetching visibility settings: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch visibility settings'
            }, status=500)
    
    def put(self, request):
        """Update visibility settings"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            data = json.loads(request.body)
            profile = request.user.clawedin_profile
            
            visibility, created = ProfileVisibility.objects.get_or_create(
                profile=profile
            )
            
            # Update allowed fields
            updatable_fields = [
                'overall_visibility', 'show_contact_info', 'show_experience',
                'show_education', 'show_skills', 'show_connections',
                'show_activity', 'appear_in_search', 'search_visibility_level',
                'allow_public_sharing', 'require_approval_for_sharing',
                'auto_approve_connections', 'visible_to_alumni',
                'visible_to_colleagues', 'visible_to_group_members',
                'custom_visibility_rules', 'max_share_duration_days',
                'require_2fa_for_sensitive', 'track_views', 'show_view_count'
            ]
            
            for field in updatable_fields:
                if field in data:
                    setattr(visibility, field, data[field])
            
            visibility.save()
            
            # Handle blocked users
            if 'blocked_users' in data:
                visibility.blocked_users.set(data['blocked_users'])
            
            return JsonResponse({
                'success': True,
                'message': 'Visibility settings updated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error updating visibility settings: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to update visibility settings'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ProfileShareView(View):
    """API for sharing profiles"""
    
    def get(self, request):
        """Get user's profile shares"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            profile = request.user.clawedin_profile
            shares = ProfileShare.objects.filter(
                shared_by=request.user
            ).order_by('-created_at')
            
            share_data = []
            for share in shares:
                share_data.append({
                    'id': share.id,
                    'share_type': share.share_type,
                    'status': share.status,
                    'title': share.title,
                    'description': share.description,
                    'share_url': share.share_url,
                    'expires_at': share.expires_at.isoformat() if share.expires_at else None,
                    'max_clicks': share.max_clicks,
                    'click_count': share.click_count,
                    'views': share.views,
                    'unique_views': share.unique_views,
                    'shares': share.shares,
                    'downloads': share.downloads,
                    'is_active': share.is_active(),
                    'created_at': share.created_at.isoformat(),
                })
            
            return JsonResponse({
                'success': True,
                'shares': share_data
            })
            
        except Exception as e:
            logger.error(f"Error fetching profile shares: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch shares'
            }, status=500)
    
    def post(self, request):
        """Create new profile share"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            data = json.loads(request.body)
            profile = request.user.clawedin_profile
            
            # Validate required fields
            required_fields = ['share_type', 'title']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Check visibility settings
            visibility = getattr(profile, 'visibility_settings', None)
            if visibility and not visibility.allow_public_sharing:
                return JsonResponse({
                    'success': False,
                    'error': 'Public sharing not allowed'
                }, status=403)
            
            # Create share
            share = ProfileShare.objects.create(
                profile=profile,
                shared_by=request.user,
                share_type=data['share_type'],
                title=data['title'],
                description=data.get('description', ''),
                share_url=data.get('share_url', ''),
                password=data.get('password', ''),
                expires_at=timezone.now() + timezone.timedelta(days=data.get('expires_in_days', 30)) if data.get('expires_in_days') else None,
                max_clicks=data.get('max_clicks'),
                allowed_emails=data.get('allowed_emails', []),
                allowed_domains=data.get('allowed_domains', []),
                metadata=data.get('metadata', {})
            )
            
            return JsonResponse({
                'success': True,
                'share': {
                    'id': share.id,
                    'share_type': share.share_type,
                    'title': share.title,
                    'share_url': share.share_url or f"{request.build_absolute_uri('/api/profiles/view/')}",
                    'expires_at': share.expires_at.isoformat() if share.expires_at else None,
                    'is_active': share.is_active(),
                }
            })
            
        except Exception as e:
            logger.error(f"Error creating profile share: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create share'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ProfileAccessView(View):
    """API for accessing profiles with authentication"""
    
    def get(self, request, username=None):
        """View profile with OAuth-like authentication"""
        try:
            # Get profile
            if username:
                profile_user = User.objects.get(username=username)
                profile = profile_user.clawedin_profile
            elif hasattr(request, 'profile_token') and request.profile_token:
                profile = request.profile_token.profile
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Profile identifier required'
                }, status=400)
            
            # Check access permissions
            can_view, reason = self._check_view_permission(request, profile)
            if not can_view:
                self._log_denied_access(request, profile, reason)
                return JsonResponse({
                    'success': False,
                    'error': f'Access denied: {reason}'
                }, status=403)
            
            # Render profile
            renderer = ProfileTemplateRenderer()
            
            # Get template and theme
            from .models import ProfileTemplate, ProfileTheme
            template_name = profile.profile_template or 'executive_pro'
            theme_name = profile.profile_theme or 'minimalist_pro'
            
            try:
                template = ProfileTemplate.objects.get(name=template_name, is_active=True)
            except ProfileTemplate.DoesNotExist:
                template = None
            
            try:
                theme = ProfileTheme.objects.get(name=theme_name, is_active=True)
            except ProfileTheme.DoesNotExist:
                theme = None
            
            if template:
                rendered_html = renderer.render_profile(profile, template)
                rendered_css = renderer.render_css(template) if theme else ''
            else:
                # Fallback rendering
                rendered_html = f"<div><h1>{profile.headline}</h1><p>{profile.summary}</p></div>"
                rendered_css = ""
            
            # Record successful access
            self._log_successful_access(request, profile)
            
            # Update view count if tracking enabled
            if hasattr(profile, 'visibility_settings') and profile.visibility_settings.track_views:
                profile.profile_views += 1
                profile.save(update_fields=['profile_views'])
            
            return JsonResponse({
                'success': True,
                'profile': {
                    'username': profile.user.username,
                    'headline': profile.headline,
                    'summary': profile.summary,
                    'current_company': profile.current_company,
                    'current_position': profile.current_position,
                    'industry': profile.industry,
                    'location': profile.location,
                    'years_experience': profile.years_experience,
                    'skills_list': profile.skills_list,
                    'profile_views': profile.profile_views,
                    'rendered_html': rendered_html,
                    'rendered_css': rendered_css,
                },
                'access_info': {
                    'viewed_via': 'token' if hasattr(request, 'profile_token') else 'direct',
                    'viewed_at': timezone.now().isoformat(),
                }
            })
            
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Profile not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error accessing profile: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to access profile'
            }, status=500)
    
    def _check_view_permission(self, request, profile):
        """Check if user has permission to view profile"""
        # Profile owner can always view
        if request.user.is_authenticated and request.user == profile.user:
            return True, 'owner'
        
        # Token-based access
        if hasattr(request, 'profile_token') and request.profile_token:
            token = request.profile_token
            
            if token.profile != profile:
                return False, 'token_profile_mismatch'
            
            if not token.is_valid():
                return False, 'token_invalid'
            
            if not token.can_view:
                return False, 'token_no_view_permission'
            
            # Check domain restrictions
            if token.allowed_domains:
                referer = request.META.get('HTTP_REFERER', '')
                domain = referer.split('/')[2] if '/' in referer else ''
                if domain not in token.allowed_domains:
                    return False, 'domain_not_allowed'
            
            return True, 'token_authorized'
        
        # Regular user access (check visibility settings)
        if hasattr(profile, 'visibility_settings'):
            visibility = profile.visibility_settings
            return visibility.can_user_view(
                request.user if request.user.is_authenticated else None,
                'view'
            )
        
        # Default to public if no visibility settings
        return True, 'public'
    
    def _log_successful_access(self, request, profile):
        """Log successful profile access"""
        try:
            ProfileAccessLog.objects.create(
                profile=profile,
                access_type='view',
                result='success',
                token=getattr(request, 'profile_token', None),
                user=request.user if request.user.is_authenticated else None,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referer=request.META.get('HTTP_REFERER', ''),
                endpoint=request.path,
                method=request.method,
                status_code=200
            )
        except Exception as e:
            logger.error(f"Failed to log successful access: {str(e)}")
    
    def _log_denied_access(self, request, profile, reason):
        """Log denied profile access"""
        try:
            ProfileAccessLog.objects.create(
                profile=profile,
                access_type='view',
                result='denied',
                token=getattr(request, 'profile_token', None),
                user=request.user if request.user.is_authenticated else None,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referer=request.META.get('HTTP_REFERER', ''),
                endpoint=request.path,
                method=request.method,
                status_code=403,
                error_message=reason
            )
        except Exception as e:
            logger.error(f"Failed to log denied access: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

@require_http_methods(["GET"])
def get_profile_analytics(request):
    """Get profile access analytics"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    try:
        profile = request.user.clawedin_profile
        
        # Get access logs
        logs = ProfileAccessLog.objects.filter(
            profile=profile
        ).order_by('-created_at')[:100]
        
        # Calculate analytics
        total_views = logs.filter(access_type='view', result='success').count()
        unique_visitors = logs.filter(access_type='view', result='success').values(
            'ip_address'
        ).distinct().count()
        access_by_type = logs.values('access_type').annotate(count=models.Count('id'))
        access_by_result = logs.values('result').annotate(count=models.Count('id'))
        
        # Recent activity
        recent_activity = logs[:20]
        activity_data = []
        for activity in recent_activity:
            activity_data.append({
                'access_type': activity.access_type,
                'result': activity.result,
                'ip_address': activity.ip_address,
                'user_agent': activity.user_agent[:100] if activity.user_agent else '',
                'created_at': activity.created_at.isoformat(),
                'error_message': activity.error_message,
            })
        
        return JsonResponse({
            'success': True,
            'analytics': {
                'total_views': total_views,
                'unique_visitors': unique_visitors,
                'access_by_type': list(access_by_type),
                'access_by_result': list(access_by_result),
                'recent_activity': activity_data,
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching profile analytics: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch analytics'
        }, status=500)