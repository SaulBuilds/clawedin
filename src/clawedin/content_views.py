from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
import json
import logging

from .models import Profile
from .content_models import (
    ProfessionalContent, ProfessionalArticle, ProfessionalAchievement,
    ProfessionalProject, ContentInteraction, ContentModerationQueue
)

User = get_user_model()
logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class ProfessionalContentView(View):
    """API for managing professional content"""
    
    def get(self, request):
        """Get content with filtering and pagination"""
        try:
            # Parse query parameters
            content_type = request.GET.get('content_type')
            visibility = request.GET.get('visibility')
            author_id = request.GET.get('author_id')
            skills = request.GET.getlist('skills')
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)
            
            # Build base query
            query = ProfessionalContent.objects.filter(is_approved=True)
            
            # Apply filters
            if content_type:
                query = query.filter(content_type=content_type)
            
            if visibility:
                if visibility == 'public':
                    query = query.filter(visibility='public')
                elif request.user.is_authenticated:
                    # For authenticated users, include content they can access
                    accessible_query = Q(visibility='public') | Q(author=request.user)
                    query = query.filter(accessible_query)
                else:
                    # Anonymous users only see public content
                    query = query.filter(visibility='public')
            
            if author_id:
                query = query.filter(author_id=author_id)
            
            if skills:
                for skill in skills:
                    query = query.filter(skills_mentioned__contains=[skill])
            
            # Order by engagement score and recency
            query = query.order_by('-engagement_score', '-published_at')
            
            # Paginate
            paginator = Paginator(query, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize content
            content_data = []
            for content in page_obj:
                content_data.append(self._serialize_content(content, request.user))
            
            return JsonResponse({
                'success': True,
                'content': content_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching content: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch content'
            }, status=500)
    
    def post(self, request):
        """Create new professional content"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required_fields = ['content_type', 'title', 'content']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Create content
            content = ProfessionalContent.objects.create(
                author=request.user,
                content_type=data['content_type'],
                title=data['title'],
                content=data['content'],
                summary=data.get('summary', '')[:500],
                featured_image=data.get('featured_image', ''),
                attachments=data.get('attachments', []),
                skills_mentioned=data.get('skills_mentioned', []),
                companies_mentioned=data.get('companies_mentioned', []),
                projects_mentioned=data.get('projects_mentioned', []),
                visibility=data.get('visibility', 'public'),
                allow_comments=data.get('allow_comments', True),
                allow_shares=data.get('allow_shares', True),
                allow_likes=data.get('allow_likes', True),
                tags=data.get('tags', []),
                metadata=data.get('metadata', {}),
                published_at=timezone.now()
            )
            
            return JsonResponse({
                'success': True,
                'content': self._serialize_content(content, request.user),
                'message': 'Content created successfully'
            })
            
        except (json.JSONDecodeError, KeyError) as e:
            return JsonResponse({
                'success': False,
                'error': 'Invalid request data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error creating content: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create content'
            }, status=500)
    
    def _serialize_content(self, content, user):
        """Serialize content for API response"""
        data = {
            'id': content.id,
            'content_type': content.content_type,
            'title': content.title,
            'content': content.content,
            'summary': content.summary,
            'featured_image': content.featured_image,
            'attachments': content.attachments,
            'skills_mentioned': content.skills_mentioned,
            'companies_mentioned': content.companies_mentioned,
            'projects_mentioned': content.projects_mentioned,
            'visibility': content.visibility,
            'allow_comments': content.allow_comments,
            'allow_shares': content.allow_shares,
            'allow_likes': content.allow_likes,
            'views': content.views,
            'likes': content.likes,
            'shares': content.shares,
            'comments_count': content.comments_count,
            'engagement_score': content.engagement_score,
            'is_approved': content.is_approved,
            'is_featured': content.is_featured,
            'is_pinned': content.is_pinned,
            'tags': content.tags,
            'metadata': content.metadata,
            'published_at': content.published_at.isoformat(),
            'updated_at': content.updated_at.isoformat(),
            'created_at': content.created_at.isoformat(),
            
            'author': {
                'id': content.author.id,
                'username': content.author.username,
                'full_name': getattr(content.author, 'full_name', ''),
            },
            
            'permissions': {
                'can_view': content.can_user_view(user)[0],
                'can_edit': user == content.author,
                'can_delete': user == content.author,
                'can_moderate': user.is_staff or user.is_superuser,
            }
        }
        
        # Add article-specific data if applicable
        try:
            article = content.article_details
            data['article_details'] = {
                'reading_time': article.reading_time,
                'difficulty_level': article.difficulty_level,
                'seo_title': article.seo_title,
                'seo_description': article.seo_description,
                'focus_keywords': article.focus_keywords,
                'publication_status': article.publication_status,
                'read_through_rate': article.read_through_rate,
                'bookmark_count': article.bookmark_count,
            }
        except ProfessionalArticle.DoesNotExist:
            pass
        
        return data

@method_decorator(csrf_exempt, name='dispatch')
class ContentInteractionView(View):
    """API for content interactions (likes, comments, shares)"""
    
    def post(self, request, content_id):
        """Create interaction with content"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            data = json.loads(request.body)
            interaction_type = data.get('interaction_type')
            
            if interaction_type not in ['like', 'comment', 'share', 'bookmark']:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid interaction type'
                }, status=400)
            
            # Get content
            try:
                content = ProfessionalContent.objects.get(id=content_id)
            except ProfessionalContent.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Content not found'
                }, status=404)
            
            # Check if user can interact
            can_view, reason = content.can_user_view(request.user)
            if not can_view:
                return JsonResponse({
                    'success': False,
                    'error': f'Cannot interact: {reason}'
                }, status=403)
            
            # Check if interaction type is allowed
            if interaction_type == 'like' and not content.allow_likes:
                return JsonResponse({
                    'success': False,
                    'error': 'Likes not allowed for this content'
                }, status=403)
            
            if interaction_type == 'comment' and not content.allow_comments:
                return JsonResponse({
                    'success': False,
                    'error': 'Comments not allowed for this content'
                }, status=403)
            
            if interaction_type == 'share' and not content.allow_shares:
                return JsonResponse({
                    'success': False,
                    'error': 'Shares not allowed for this content'
                }, status=403)
            
            # Create interaction
            with transaction.atomic():
                # Check for existing interaction (except comments)
                if interaction_type != 'comment':
                    existing = ContentInteraction.objects.filter(
                        content=content,
                        user=request.user,
                        interaction_type=interaction_type
                    ).first()
                    
                    if existing:
                        # Unlike/unbookmark
                        existing.delete()
                        
                        # Update content counts
                        if interaction_type == 'like':
                            content.likes = max(0, content.likes - 1)
                        elif interaction_type == 'bookmark':
                            # Bookmarks are tracked separately
                            pass
                        
                        content.save(update_fields=['likes'])
                        content.calculate_engagement_score()
                        
                        return JsonResponse({
                            'success': True,
                            'action': 'removed',
                            'message': f'{interaction_type.capitalize()} removed'
                        })
                
                # Create new interaction
                interaction = ContentInteraction.objects.create(
                    content=content,
                    user=request.user,
                    interaction_type=interaction_type,
                    comment_text=data.get('comment_text', ''),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    interaction_data=data.get('interaction_data', {})
                )
                
                # Auto-approve simple interactions
                if interaction_type in ['like', 'share', 'bookmark']:
                    interaction.approve(None)
                
                return JsonResponse({
                    'success': True,
                    'action': 'created',
                    'interaction': {
                        'id': interaction.id,
                        'type': interaction.interaction_type,
                        'is_approved': interaction.is_approved,
                        'created_at': interaction.created_at.isoformat(),
                    },
                    'message': f'{interaction_type.capitalize()} added'
                })
                
        except Exception as e:
            logger.error(f"Error creating interaction: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create interaction'
            }, status=500)
    
    def delete(self, request, interaction_id):
        """Remove interaction"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            interaction = ContentInteraction.objects.get(
                id=interaction_id,
                user=request.user
            )
            
            # Update content counts before deleting
            content = interaction.content
            if interaction.interaction_type == 'like':
                content.likes = max(0, content.likes - 1)
            elif interaction.interaction_type == 'comment' and interaction.is_approved:
                content.comments_count = max(0, content.comments_count - 1)
            
            content.save(update_fields=['likes', 'comments_count'])
            content.calculate_engagement_score()
            
            # Delete interaction
            interaction.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Interaction removed successfully'
            })
            
        except ContentInteraction.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Interaction not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error removing interaction: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to remove interaction'
            }, status=500)
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

@method_decorator(csrf_exempt, name='dispatch')
class ProfessionalAchievementView(View):
    """API for managing professional achievements"""
    
    def get(self, request):
        """Get user's achievements"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            # Get user's profile
            profile = request.user.clawedin_profile
            
            # Get achievements
            achievements = ProfessionalAchievement.objects.filter(profile=profile)
            
            # Filter by type if specified
            achievement_type = request.GET.get('achievement_type')
            if achievement_type:
                achievements = achievements.filter(achievement_type=achievement_type)
            
            # Filter by verification status
            verification_status = request.GET.get('verification_status')
            if verification_status:
                achievements = achievements.filter(verification_status=verification_status)
            
            achievement_data = []
            for achievement in achievements:
                achievement_data.append({
                    'id': achievement.id,
                    'achievement_type': achievement.achievement_type,
                    'title': achievement.title,
                    'description': achievement.description,
                    'issuer_name': achievement.issuer_name,
                    'issuer_website': achievement.issuer_website,
                    'issuer_logo': achievement.issuer_logo,
                    'issue_date': achievement.issue_date.isoformat(),
                    'expiry_date': achievement.expiry_date.isoformat() if achievement.expiry_date else None,
                    'verification_status': achievement.verification_status,
                    'verification_url': achievement.verification_url,
                    'verified_by': achievement.verified_by.username if achievement.verified_by else None,
                    'verified_at': achievement.verified_at.isoformat() if achievement.verified_at else None,
                    'certificate_url': achievement.certificate_url,
                    'supporting_documents': achievement.supporting_documents,
                    'skills_demonstrated': achievement.skills_demonstrated,
                    'competency_level': achievement.competency_level,
                    'is_featured': achievement.is_featured,
                    'show_on_profile': achievement.show_on_profile,
                    'view_count': achievement.view_count,
                    'endorsement_count': achievement.endorsement_count,
                    'tags': achievement.tags,
                    'metadata': achievement.metadata,
                    'is_current': achievement.is_current(),
                    'created_at': achievement.created_at.isoformat(),
                    'updated_at': achievement.updated_at.isoformat(),
                })
            
            return JsonResponse({
                'success': True,
                'achievements': achievement_data
            })
            
        except Exception as e:
            logger.error(f"Error fetching achievements: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch achievements'
            }, status=500)
    
    def post(self, request):
        """Create new achievement"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            data = json.loads(request.body)
            profile = request.user.clawedin_profile
            
            # Validate required fields
            required_fields = ['achievement_type', 'title', 'description', 'issuer_name', 'issue_date']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Create achievement
            achievement = ProfessionalAchievement.objects.create(
                profile=profile,
                achievement_type=data['achievement_type'],
                title=data['title'],
                description=data['description'],
                issuer_name=data['issuer_name'],
                issuer_website=data.get('issuer_website', ''),
                issuer_logo=data.get('issuer_logo', ''),
                issue_date=data['issue_date'],
                expiry_date=data.get('expiry_date'),
                verification_status='unverified',
                verification_code=data.get('verification_code', ''),
                verification_url=data.get('verification_url', ''),
                certificate_url=data.get('certificate_url', ''),
                supporting_documents=data.get('supporting_documents', []),
                skills_demonstrated=data.get('skills_demonstrated', []),
                competency_level=data.get('competency_level', 'intermediate'),
                tags=data.get('tags', []),
                metadata=data.get('metadata', {}),
                show_on_profile=data.get('show_on_profile', True)
            )
            
            return JsonResponse({
                'success': True,
                'achievement': {
                    'id': achievement.id,
                    'title': achievement.title,
                    'achievement_type': achievement.achievement_type,
                    'verification_status': achievement.verification_status,
                    'created_at': achievement.created_at.isoformat(),
                },
                'message': 'Achievement created successfully'
            })
            
        except Exception as e:
            logger.error(f"Error creating achievement: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create achievement'
            }, status=500)
    
    def put(self, request, achievement_id):
        """Update achievement"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            data = json.loads(request.body)
            profile = request.user.clawedin_profile
            
            achievement = ProfessionalAchievement.objects.get(
                id=achievement_id,
                profile=profile
            )
            
            # Update allowed fields
            updatable_fields = [
                'title', 'description', 'issuer_name', 'issuer_website',
                'issuer_logo', 'issue_date', 'expiry_date', 'certificate_url',
                'supporting_documents', 'skills_demonstrated', 'competency_level',
                'tags', 'metadata', 'show_on_profile', 'is_featured'
            ]
            
            for field in updatable_fields:
                if field in data:
                    setattr(achievement, field, data[field])
            
            achievement.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Achievement updated successfully'
            })
            
        except ProfessionalAchievement.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Achievement not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error updating achievement: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to update achievement'
            }, status=500)
    
    def delete(self, request, achievement_id):
        """Delete achievement"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            profile = request.user.clawedin_profile
            achievement = ProfessionalAchievement.objects.get(
                id=achievement_id,
                profile=profile
            )
            
            achievement.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Achievement deleted successfully'
            })
            
        except ProfessionalAchievement.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Achievement not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error deleting achievement: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to delete achievement'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ProfessionalProjectView(View):
    """API for managing professional projects"""
    
    def get(self, request):
        """Get professional projects"""
        try:
            # Parse query parameters
            profile_id = request.GET.get('profile_id')
            project_type = request.GET.get('project_type')
            status = request.GET.get('status')
            skills = request.GET.getlist('skills')
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)
            
            # Build base query
            query = ProfessionalProject.objects.filter(is_public=True)
            
            if profile_id:
                query = query.filter(profile_id=profile_id)
            elif request.user.is_authenticated:
                # Include user's private projects
                query = ProfessionalProject.objects.filter(
                    Q(profile=request.user.clawedin_profile) | Q(is_public=True)
                )
            
            # Apply filters
            if project_type:
                query = query.filter(project_type=project_type)
            
            if status:
                query = query.filter(status=status)
            
            if skills:
                for skill in skills:
                    query = query.filter(technologies_used__contains=[skill])
            
            # Order by featured status and start date
            query = query.order_by('-is_featured', '-display_order', '-start_date')
            
            # Paginate
            paginator = Paginator(query, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize projects
            project_data = []
            for project in page_obj:
                project_data.append(self._serialize_project(project, request.user))
            
            return JsonResponse({
                'success': True,
                'projects': project_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching projects: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch projects'
            }, status=500)
    
    def post(self, request):
        """Create new project"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            data = json.loads(request.body)
            profile = request.user.clawedin_profile
            
            # Validate required fields
            required_fields = ['project_type', 'title', 'description', 'start_date', 'role']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Create project
            project = ProfessionalProject.objects.create(
                profile=profile,
                project_type=data['project_type'],
                title=data['title'],
                description=data['description'],
                start_date=data['start_date'],
                end_date=data.get('end_date'),
                status=data.get('status', 'completed'),
                role=data['role'],
                team_size=data.get('team_size'),
                budget=data.get('budget'),
                technologies_used=data.get('technologies_used', []),
                skills_demonstrated=data.get('skills_demonstrated', []),
                responsibilities=data.get('responsibilities', []),
                key_achievements=data.get('key_achievements', []),
                metrics_and_results=data.get('metrics_and_results', {}),
                project_url=data.get('project_url', ''),
                repository_url=data.get('repository_url', ''),
                demo_url=data.get('demo_url', ''),
                documentation_url=data.get('documentation_url', ''),
                images=data.get('images', []),
                awards=data.get('awards', []),
                publications=data.get('publications', []),
                patents=data.get('patents', []),
                is_public=data.get('is_public', True),
                tags=data.get('tags', []),
                metadata=data.get('metadata', {})
            )
            
            # Add collaborators if specified
            if 'collaborator_ids' in data:
                collaborators = User.objects.filter(id__in=data['collaborator_ids'])
                project.collaborators.set(collaborators)
            
            return JsonResponse({
                'success': True,
                'project': self._serialize_project(project, request.user),
                'message': 'Project created successfully'
            })
            
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create project'
            }, status=500)
    
    def _serialize_project(self, project, user):
        """Serialize project for API response"""
        return {
            'id': project.id,
            'project_type': project.project_type,
            'title': project.title,
            'description': project.description,
            'start_date': project.start_date.isoformat(),
            'end_date': project.end_date.isoformat() if project.end_date else None,
            'status': project.status,
            'role': project.role,
            'team_size': project.team_size,
            'budget': str(project.budget) if project.budget else None,
            'technologies_used': project.technologies_used,
            'skills_demonstrated': project.skills_demonstrated,
            'responsibilities': project.responsibilities,
            'key_achievements': project.key_achievements,
            'metrics_and_results': project.metrics_and_results,
            'project_url': project.project_url,
            'repository_url': project.repository_url,
            'demo_url': project.demo_url,
            'documentation_url': project.documentation_url,
            'images': project.images,
            'collaborators': [
                {
                    'id': collab.id,
                    'username': collab.username,
                    'full_name': getattr(collab, 'full_name', ''),
                }
                for collab in project.collaborators.all()
            ],
            'awards': project.awards,
            'publications': project.publications,
            'patents': project.patents,
            'is_featured': project.is_featured,
            'is_public': project.is_public,
            'view_count': project.view_count,
            'like_count': project.like_count,
            'share_count': project.share_count,
            'tags': project.tags,
            'metadata': project.metadata,
            'duration_display': project.get_duration_display(),
            'permissions': {
                'can_edit': user and user == project.profile.user,
                'can_delete': user and user == project.profile.user,
                'can_view': project.is_public or (user and user == project.profile.user),
            },
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
        }

@method_decorator(csrf_exempt, name='dispatch')
class ActivityFeedView(View):
    """API for professional activity feed"""
    
    def get(self, request):
        """Get activity feed"""
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        try:
            # Parse query parameters
            feed_type = request.GET.get('feed_type', 'all')
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 50)
            
            # Get user's connections
            user_profile = request.user.clawedin_profile
            connected_users = User.objects.filter(
                clawedin_profile__in=user_profile.top_connections.all()
            )
            
            # Build base query
            if feed_type == 'connections':
                # Content from connections only
                query = ProfessionalContent.objects.filter(
                    author__in=connected_users,
                    is_approved=True
                )
            elif feed_type == 'network':
                # Content from 2nd degree network
                # This would be more complex in a real implementation
                query = ProfessionalContent.objects.filter(
                    author__in=connected_users,
                    is_approved=True
                )
            else:
                # All content (connections + public)
                query = ProfessionalContent.objects.filter(
                    Q(author__in=connected_users) | Q(visibility='public'),
                    is_approved=True
                )
            
            # Order by engagement and recency
            query = query.order_by('-engagement_score', '-published_at')
            
            # Paginate
            paginator = Paginator(query, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize feed items
            feed_data = []
            for content in page_obj:
                feed_data.append(self._serialize_feed_item(content, request.user))
            
            return JsonResponse({
                'success': True,
                'feed': feed_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching activity feed: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch activity feed'
            }, status=500)
    
    def _serialize_feed_item(self, content, user):
        """Serialize content for feed"""
        return {
            'id': content.id,
            'content_type': content.content_type,
            'title': content.title,
            'summary': content.summary,
            'featured_image': content.featured_image,
            'author': {
                'id': content.author.id,
                'username': content.author.username,
                'full_name': getattr(content.author, 'full_name', ''),
            },
            'engagement': {
                'views': content.views,
                'likes': content.likes,
                'shares': content.shares,
                'comments_count': content.comments_count,
                'engagement_score': content.engagement_score,
            },
            'published_at': content.published_at.isoformat(),
            'is_pinned': content.is_pinned,
            'is_featured': content.is_featured,
        }

@require_http_methods(["GET"])
def get_content_analytics(request):
    """Get content analytics for user"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required'
        }, status=401)
    
    try:
        profile = request.user.clawedin_profile
        
        # Get content analytics
        content_analytics = ProfessionalContent.objects.filter(author=request.user).aggregate(
            total_content=Count('id'),
            total_views=Sum('views'),
            total_likes=Sum('likes'),
            total_shares=Sum('shares'),
            total_comments=Sum('comments_count'),
            avg_engagement=Avg('engagement_score')
        )
        
        # Content type breakdown
        content_by_type = ProfessionalContent.objects.filter(
            author=request.user
        ).values('content_type').annotate(
            count=Count('id'),
            total_views=Sum('views'),
            total_likes=Sum('likes')
        )
        
        # Achievement analytics
        achievement_analytics = ProfessionalAchievement.objects.filter(profile=profile).aggregate(
            total_achievements=Count('id'),
            verified_achievements=Count('id', filter=Q(verification_status='verified')),
            featured_achievements=Count('id', filter=Q(is_featured=True))
        )
        
        # Project analytics
        project_analytics = ProfessionalProject.objects.filter(profile=profile).aggregate(
            total_projects=Count('id'),
            public_projects=Count('id', filter=Q(is_public=True)),
            completed_projects=Count('id', filter=Q(status='completed'))
        )
        
        return JsonResponse({
            'success': True,
            'analytics': {
                'content': content_analytics,
                'content_by_type': list(content_by_type),
                'achievements': achievement_analytics,
                'projects': project_analytics,
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching content analytics: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch analytics'
        }, status=500)