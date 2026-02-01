from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from .models import User, UserProfile, TopConnection
from .auth.privy import privy_client
from .auth.tokens import token_manager
import json
import secrets

class OAuthLikeAuthView(View):
    """
    OAuth-like authentication that hides Web3 complexity from users
    """
    
    def get(self, request):
        """Display authentication options"""
        return render(request, 'identity/auth_options.html', {
            'user_types': User.USER_TYPES,
            'creative_styles': ['professional', 'creative', 'hybrid'],
            'industries': ['Technology', 'Design', 'Marketing', 'Finance', 'Healthcare', 'Education']
        })
    
    @method_decorator(csrf_exempt, name='csrf_exempt')
    def dispatch(self, request, *args, **kwargs):
        """Handle POST requests without CSRF for OAuth compatibility"""
        return super().dispatch(request, *args, **kwargs)

@login_required
def user_profile(request, user_id=None):
    """
    Display user profile with professional and creative elements
    """
    if user_id:
        # View another user's profile
        try:
            profile_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
    else:
        profile_user = request.user
    
    # Get profile data
    try:
        profile = UserProfile.objects.get(user=profile_user)
        top_connection_objects = profile.get_top_connections()

        # Build top connection data with business context
        top_connections = []
        top_connection_data = []
        for top_conn in top_connection_objects:
            top_connections.append(top_conn.connection)
            top_connection_data.append({
                'position': top_conn.position,
                'business_context': top_conn.business_context,
                'collaboration_history': top_conn.collaboration_history
            })

    except UserProfile.DoesNotExist:
        profile = None
        top_connections = []
        top_connection_data = []
    
    return render(request, 'identity/user_profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'top_connections': zip(top_connections, top_connection_data),
        'is_own_profile': profile_user == request.user
    })

@login_required
def dashboard(request):
    """
    User dashboard with hybrid professional-creative features
    """
    user = request.user
    
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    return render(request, 'identity/dashboard.html', {
        'user': user,
        'profile': profile,
        'user_type': user.get_user_type_display(),
        'completion_percentage': calculate_profile_completion(profile),
        'top_connections': profile.get_top_connections(),
        'recent_activity': get_recent_activity(user)
    })

def calculate_profile_completion(profile):
    """
    Calculate profile completion percentage for hybrid model
    """
    completion = 0
    total_fields = 10  # Base weight for calculation
    
    # Professional fields (LinkedIn-style)
    if profile.skills:
        completion += 2
    if profile.experience:
        completion += 2
    if profile.education:
        completion += 1
    if profile.certifications:
        completion += 1
    
    # Creative fields (MySpace-style)
    if profile.theme_choice:
        completion += 1
    if profile.custom_colors:
        completion += 1
    if profile.background_image:
        completion += 1
    if profile.layout_preference != 'professional':
        completion += 1
    if profile.featured_audio:
        completion += 1
    if profile.background_music:
        completion += 1
    
    # Social hierarchy (Top 8)
    if profile.top_connections_count >= 1:
        completion += 1
    
    return min(completion * 10, 100)  # Cap at 100%

def get_recent_activity(user):
    """
    Get recent user activity for dashboard
    """
    # This would integrate with content, networking, and other apps
    # For now, return mock data
    return [
        {'type': 'profile_update', 'message': 'Updated professional theme', 'timestamp': '2024-01-31 10:30'},
        {'type': 'connection_added', 'message': 'Added to Top 8', 'timestamp': '2024-01-31 09:15'},
        {'type': 'media_uploaded', 'message': 'Uploaded portfolio item', 'timestamp': '2024-01-30 14:20'},
    ]


def user_logout(request):
    """
    Log out the current user and redirect to home
    """
    logout(request)
    return redirect('/')


# ============================================================
# Privy Authentication Views
# ============================================================

class PrivyAuthInitView(View):
    """
    Initiate Privy OAuth-like authentication flow.
    """

    def get(self, request):
        """Redirect to Privy auth or show dev auth page"""
        redirect_uri = request.build_absolute_uri('/identity/auth/callback/')
        auth_url = privy_client.get_oauth_url(redirect_uri, scope='profile wallet')
        return redirect(auth_url)


class PrivyAuthCallbackView(View):
    """
    Handle Privy OAuth callback.
    """

    def get(self, request):
        """Process auth callback and create session"""
        code = request.GET.get('code')
        error = request.GET.get('error')

        if error:
            return render(request, 'identity/auth_error.html', {
                'error': error,
                'error_description': request.GET.get('error_description', '')
            })

        if code:
            # Exchange code for user data
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                privy_user = loop.run_until_complete(
                    privy_client.exchange_code_for_user(code)
                )
                loop.close()
            except Exception:
                privy_user = privy_client._dev_exchange(code)

            if privy_user:
                # Authenticate with Django
                user = authenticate(request, privy_user=privy_user)
                if user:
                    login(request, user)
                    return redirect(settings.LOGIN_REDIRECT_URL)

        return render(request, 'identity/auth_error.html', {
            'error': 'authentication_failed',
            'error_description': 'Unable to complete authentication'
        })


class DevAuthCallbackView(View):
    """
    Development-only auth callback for testing without Privy API keys.
    """

    def get(self, request):
        """Show dev auth form"""
        state = request.GET.get('state', '')
        redirect_uri = request.GET.get('redirect_uri', '/identity/dashboard/')
        return render(request, 'identity/dev_auth.html', {
            'state': state,
            'redirect_uri': redirect_uri,
        })

    def post(self, request):
        """Process dev auth form"""
        username = request.POST.get('username', '')
        user_type = request.POST.get('user_type', 'HUMAN')
        redirect_uri = request.POST.get('redirect_uri', '/identity/dashboard/')

        if not username:
            username = f"dev_user_{secrets.token_hex(4)}"

        # Create or get user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'user_type': user_type,
                'email': f'{username}@clawedin.local',
            }
        )

        if created:
            # Generate mock wallet
            user.wallet_address = f"0x{secrets.token_hex(20)}"
            user.privy_user_id = f"privy_dev_{secrets.token_hex(8)}"
            user.save()
            UserProfile.objects.get_or_create(user=user)

        # Log in the user
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect(redirect_uri)


class AgentRegistrationView(View):
    """
    Register a new AI agent.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        """Register a new agent"""
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        name = data.get('name', '')
        capabilities = data.get('capabilities', [])
        owner_id = data.get('owner_id')

        if not name:
            return JsonResponse({'error': 'Agent name required'}, status=400)

        # Create agent user
        username = f"agent_{name.lower().replace(' ', '_')}"
        counter = 1
        base_username = username
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        # Generate API key
        api_key = f"clwd_agent_{secrets.token_urlsafe(32)}"

        agent = User.objects.create(
            username=username,
            user_type='AGENT',
            agent_capabilities={
                'listed_capabilities': capabilities,
                'api_key': api_key,
            },
        )

        if owner_id:
            try:
                owner = User.objects.get(id=owner_id)
                agent.agent_owner = owner
                agent.save()
            except User.DoesNotExist:
                pass

        # Create wallet for agent
        agent.wallet_address = privy_client.create_embedded_wallet(str(agent.id))
        agent.privy_user_id = f"privy_agent_{secrets.token_hex(8)}"
        agent.save()

        UserProfile.objects.get_or_create(user=agent)

        return JsonResponse({
            'success': True,
            'agent_id': agent.id,
            'username': agent.username,
            'api_key': api_key,
            'wallet_address': agent.wallet_address,
        })


class AgentAuthView(View):
    """
    Authenticate an AI agent via API key.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        """Authenticate agent and return tokens"""
        api_key = request.headers.get('X-API-Key') or request.POST.get('api_key')

        if not api_key:
            try:
                data = json.loads(request.body)
                api_key = data.get('api_key')
            except (json.JSONDecodeError, AttributeError):
                pass

        if not api_key:
            return JsonResponse({'error': 'API key required'}, status=401)

        user = authenticate(request, api_key=api_key)

        if user:
            tokens = token_manager.create_token_pair(user)
            return JsonResponse({
                'success': True,
                'agent_id': user.id,
                'username': user.username,
                **tokens,
            })
        else:
            return JsonResponse({'error': 'Invalid API key'}, status=401)
