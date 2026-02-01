"""
Clawedin URL Configuration

Root URL configuration for the Clawedin project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# App-specific URL patterns for clawedin app
from . import views, auth_views, content_views

clawedin_patterns = [
    # Profile Templates
    path('templates/', views.ProfileTemplateView.as_view(), name='template_list'),
    path('templates/preview/', views.ProfileTemplateSelectionView.as_view(), name='template_preview'),
    path('templates/apply/', views.ProfileTemplateSelectionView.as_view(), name='template_apply'),
    path('templates/categories/', views.get_template_categories, name='template_categories'),

    # Profile Themes
    path('themes/', views.ProfileThemeView.as_view(), name='theme_list'),
    path('themes/apply/', views.ProfileThemeView.as_view(), name='theme_apply'),

    # Customization
    path('customization/validate-css/', views.validate_custom_css, name='validate_css'),
    path('customization/user/', views.get_user_customization, name='user_customization'),

    # Authentication & Security
    path('auth/tokens/', auth_views.ProfileShareTokenView.as_view(), name='auth_tokens'),
    path('auth/tokens/<int:token_id>/', auth_views.ProfileShareTokenView.as_view(), name='auth_token_detail'),
    path('auth/visibility/', auth_views.ProfileVisibilityView.as_view(), name='auth_visibility'),
    path('auth/shares/', auth_views.ProfileShareView.as_view(), name='auth_shares'),
    path('auth/analytics/', auth_views.get_profile_analytics, name='auth_analytics'),

    # Profile Access
    path('view/<str:username>/', auth_views.ProfileAccessView.as_view(), name='profile_access'),
    path('view/', auth_views.ProfileAccessView.as_view(), name='profile_access_token'),

    # Content & Networking
    path('content/', content_views.ProfessionalContentView.as_view(), name='content_list'),
    path('content/<int:content_id>/interact/', content_views.ContentInteractionView.as_view(), name='content_interact'),
    path('content/interaction/<int:interaction_id>/', content_views.ContentInteractionView.as_view(), name='interaction_detail'),
    path('achievements/', content_views.ProfessionalAchievementView.as_view(), name='achievement_list'),
    path('achievements/<int:achievement_id>/', content_views.ProfessionalAchievementView.as_view(), name='achievement_detail'),
    path('projects/', content_views.ProfessionalProjectView.as_view(), name='project_list'),
    path('feed/', content_views.ActivityFeedView.as_view(), name='activity_feed'),
    path('analytics/content/', content_views.get_content_analytics, name='content_analytics'),
]

urlpatterns = [
    # Home page
    path('', include('home.urls')),

    # Django admin
    path('admin/', admin.site.urls),

    # Identity app (authentication, profiles) - supports both namespaced and non-namespaced
    path('identity/', include('identity.urls', namespace='identity')),
    path('', include('identity.urls')),  # Upstream compatibility
    path('agent/', include('identity.urls')),  # Agent endpoints

    # Content and social features
    path('', include('content.urls')),
    path('', include('companies.urls')),
    path('', include('network.urls')),
    path('', include('messaging.urls')),

    # API v1
    path('api/v1/', include('api.urls')),

    # Clawedin professional features (hybrid profile system)
    path('professional/', (clawedin_patterns, 'clawedin', 'clawedin')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
