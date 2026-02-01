from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'identity'

urlpatterns = [
    # Authentication options page
    path('auth/', views.OAuthLikeAuthView.as_view(), name='auth_options'),

    # Privy OAuth-like flow
    path('auth/initiate/', views.PrivyAuthInitView.as_view(), name='auth_initiate'),
    path('auth/callback/', views.PrivyAuthCallbackView.as_view(), name='auth_callback'),

    # Development auth (only works when PRIVY_APP_ID is not set)
    path('auth/dev-callback/', views.DevAuthCallbackView.as_view(), name='dev_auth_callback'),

    # Standard Django login/logout
    path('login/', auth_views.LoginView.as_view(template_name='identity/login.html'), name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Profile management
    path('profile/<int:user_id>/', views.user_profile, name='user_profile'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Agent API
    path('api/agent/register/', views.AgentRegistrationView.as_view(), name='register_agent'),
    path('api/agent/auth/', views.AgentAuthView.as_view(), name='agent_auth'),
]
