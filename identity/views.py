"""
Identity views combining upstream resume CRUD with Privy/Web3 authentication.
"""
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
import json
import secrets

from .models import (
    User,
    UserProfile,
    TopConnection,
    Resume,
    ResumeCertification,
    ResumeEducation,
    ResumeExperience,
    ResumeProject,
    ResumeSkill,
    UserSkill,
)

# Import forms - handle gracefully if not present
try:
    from .forms import (
        LoginForm,
        ProfileUpdateForm,
        RegisterForm,
        ResumeCertificationForm,
        ResumeEducationForm,
        ResumeExperienceForm,
        ResumeForm,
        ResumeProjectForm,
        ResumeSkillForm,
        UserSkillForm,
    )
    HAS_FORMS = True
except ImportError:
    HAS_FORMS = False

# Import Privy auth components
try:
    from .auth.privy import privy_client
    from .auth.tokens import token_manager
    HAS_PRIVY = True
except ImportError:
    HAS_PRIVY = False
    privy_client = None
    token_manager = None


# =============================================================================
# Standard Django Auth Views (from upstream)
# =============================================================================

class UserLoginView(LoginView):
    template_name = "identity/login.html"
    authentication_form = LoginForm if HAS_FORMS else None


class UserLogoutView(LogoutView):
    next_page = "identity:login"


def register(request):
    if not HAS_FORMS:
        return redirect('identity:login')

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("identity:profile")
    else:
        form = RegisterForm()

    return render(request, "identity/register.html", {"form": form})


@login_required
def profile(request):
    return render(request, "identity/profile.html")


@login_required
def profile_update(request):
    if not HAS_FORMS:
        return redirect('identity:profile')

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("identity:profile")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "identity/profile_update.html", {"form": form})


# =============================================================================
# User Skills (from upstream)
# =============================================================================

@login_required
def user_skill_list(request):
    skills = UserSkill.objects.filter(user=request.user).order_by("name")
    return render(request, "identity/user_skill_list.html", {"skills": skills})


@login_required
def user_skill_create(request):
    if not HAS_FORMS:
        return redirect('identity:user_skill_list')

    if request.method == "POST":
        form = UserSkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.user = request.user
            skill.save()
            return redirect("identity:user_skill_list")
    else:
        form = UserSkillForm()
    return render(request, "identity/user_skill_form.html", {"form": form, "mode": "create"})


@login_required
def user_skill_update(request, skill_id):
    skill = get_object_or_404(UserSkill, id=skill_id, user=request.user)
    if not HAS_FORMS:
        return redirect('identity:user_skill_list')

    if request.method == "POST":
        form = UserSkillForm(request.POST, instance=skill)
        if form.is_valid():
            form.save()
            return redirect("identity:user_skill_list")
    else:
        form = UserSkillForm(instance=skill)
    return render(request, "identity/user_skill_form.html", {"form": form, "mode": "update"})


@login_required
def user_skill_delete(request, skill_id):
    skill = get_object_or_404(UserSkill, id=skill_id, user=request.user)
    if request.method == "POST":
        skill.delete()
        return redirect("identity:user_skill_list")
    return render(request, "identity/user_skill_confirm_delete.html", {"skill": skill})


# =============================================================================
# Resume CRUD (from upstream)
# =============================================================================

@login_required
def resume_list(request):
    resumes = Resume.objects.filter(user=request.user).order_by("-updated_at")
    return render(request, "identity/resume_list.html", {"resumes": resumes})


@login_required
def resume_detail(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    return render(request, "identity/resume_detail.html", {"resume": resume})


@login_required
def resume_create(request):
    if not HAS_FORMS:
        return redirect('identity:resume_list')

    if request.method == "POST":
        form = ResumeForm(request.POST)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.user = request.user
            resume.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeForm()

    return render(request, "identity/resume_form.html", {"form": form, "mode": "create"})


@login_required
def resume_update(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeForm(request.POST, instance=resume)
        if form.is_valid():
            form.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeForm(instance=resume)

    return render(request, "identity/resume_form.html", {"form": form, "mode": "update"})


@login_required
def resume_delete(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    if request.method == "POST":
        resume.delete()
        return redirect("identity:resume_list")
    return render(request, "identity/resume_confirm_delete.html", {"resume": resume})


def _resume_for_user(request, resume_id):
    return get_object_or_404(Resume, id=resume_id, user=request.user)


# Resume Experience CRUD
@login_required
def experience_create(request, resume_id):
    resume = _resume_for_user(request, resume_id)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeExperienceForm(request.POST)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.resume = resume
            experience.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeExperienceForm()
    return render(request, "identity/resume_item_form.html",
                  {"form": form, "resume": resume, "title": "Add experience"})


@login_required
def experience_update(request, resume_id, item_id):
    resume = _resume_for_user(request, resume_id)
    experience = get_object_or_404(ResumeExperience, id=item_id, resume=resume)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeExperienceForm(request.POST, instance=experience)
        if form.is_valid():
            form.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeExperienceForm(instance=experience)
    return render(request, "identity/resume_item_form.html",
                  {"form": form, "resume": resume, "title": "Edit experience"})


@login_required
def experience_delete(request, resume_id, item_id):
    resume = _resume_for_user(request, resume_id)
    experience = get_object_or_404(ResumeExperience, id=item_id, resume=resume)
    if request.method == "POST":
        experience.delete()
        return redirect("identity:resume_detail", resume_id=resume.id)
    return render(request, "identity/resume_item_confirm_delete.html",
                  {"resume": resume, "item": experience, "title": "Delete experience"})


# Resume Education CRUD
@login_required
def education_create(request, resume_id):
    resume = _resume_for_user(request, resume_id)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeEducationForm(request.POST)
        if form.is_valid():
            education = form.save(commit=False)
            education.resume = resume
            education.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeEducationForm()
    return render(request, "identity/resume_item_form.html",
                  {"form": form, "resume": resume, "title": "Add education"})


@login_required
def education_update(request, resume_id, item_id):
    resume = _resume_for_user(request, resume_id)
    education = get_object_or_404(ResumeEducation, id=item_id, resume=resume)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeEducationForm(request.POST, instance=education)
        if form.is_valid():
            form.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeEducationForm(instance=education)
    return render(request, "identity/resume_item_form.html",
                  {"form": form, "resume": resume, "title": "Edit education"})


@login_required
def education_delete(request, resume_id, item_id):
    resume = _resume_for_user(request, resume_id)
    education = get_object_or_404(ResumeEducation, id=item_id, resume=resume)
    if request.method == "POST":
        education.delete()
        return redirect("identity:resume_detail", resume_id=resume.id)
    return render(request, "identity/resume_item_confirm_delete.html",
                  {"resume": resume, "item": education, "title": "Delete education"})


# Resume Skills CRUD
@login_required
def skill_create(request, resume_id):
    resume = _resume_for_user(request, resume_id)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeSkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.resume = resume
            skill.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeSkillForm()
    return render(request, "identity/resume_item_form.html",
                  {"form": form, "resume": resume, "title": "Add skill"})


@login_required
def skill_update(request, resume_id, item_id):
    resume = _resume_for_user(request, resume_id)
    skill = get_object_or_404(ResumeSkill, id=item_id, resume=resume)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeSkillForm(request.POST, instance=skill)
        if form.is_valid():
            form.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeSkillForm(instance=skill)
    return render(request, "identity/resume_item_form.html",
                  {"form": form, "resume": resume, "title": "Edit skill"})


@login_required
def skill_delete(request, resume_id, item_id):
    resume = _resume_for_user(request, resume_id)
    skill = get_object_or_404(ResumeSkill, id=item_id, resume=resume)
    if request.method == "POST":
        skill.delete()
        return redirect("identity:resume_detail", resume_id=resume.id)
    return render(request, "identity/resume_item_confirm_delete.html",
                  {"resume": resume, "item": skill, "title": "Delete skill"})


# Resume Projects CRUD
@login_required
def project_create(request, resume_id):
    resume = _resume_for_user(request, resume_id)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.resume = resume
            project.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeProjectForm()
    return render(request, "identity/resume_item_form.html",
                  {"form": form, "resume": resume, "title": "Add project"})


@login_required
def project_update(request, resume_id, item_id):
    resume = _resume_for_user(request, resume_id)
    project = get_object_or_404(ResumeProject, id=item_id, resume=resume)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeProjectForm(instance=project)
    return render(request, "identity/resume_item_form.html",
                  {"form": form, "resume": resume, "title": "Edit project"})


@login_required
def project_delete(request, resume_id, item_id):
    resume = _resume_for_user(request, resume_id)
    project = get_object_or_404(ResumeProject, id=item_id, resume=resume)
    if request.method == "POST":
        project.delete()
        return redirect("identity:resume_detail", resume_id=resume.id)
    return render(request, "identity/resume_item_confirm_delete.html",
                  {"resume": resume, "item": project, "title": "Delete project"})


# Resume Certifications CRUD
@login_required
def certification_create(request, resume_id):
    resume = _resume_for_user(request, resume_id)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeCertificationForm(request.POST)
        if form.is_valid():
            certification = form.save(commit=False)
            certification.resume = resume
            certification.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeCertificationForm()
    return render(request, "identity/resume_item_form.html",
                  {"form": form, "resume": resume, "title": "Add certification"})


@login_required
def certification_update(request, resume_id, item_id):
    resume = _resume_for_user(request, resume_id)
    certification = get_object_or_404(ResumeCertification, id=item_id, resume=resume)
    if not HAS_FORMS:
        return redirect('identity:resume_detail', resume_id=resume_id)

    if request.method == "POST":
        form = ResumeCertificationForm(request.POST, instance=certification)
        if form.is_valid():
            form.save()
            return redirect("identity:resume_detail", resume_id=resume.id)
    else:
        form = ResumeCertificationForm(instance=certification)
    return render(request, "identity/resume_item_form.html",
                  {"form": form, "resume": resume, "title": "Edit certification"})


@login_required
def certification_delete(request, resume_id, item_id):
    resume = _resume_for_user(request, resume_id)
    certification = get_object_or_404(ResumeCertification, id=item_id, resume=resume)
    if request.method == "POST":
        certification.delete()
        return redirect("identity:resume_detail", resume_id=resume.id)
    return render(request, "identity/resume_item_confirm_delete.html",
                  {"resume": resume, "item": certification, "title": "Delete certification"})


# =============================================================================
# Hybrid Profile Views (local additions)
# =============================================================================

class OAuthLikeAuthView(View):
    """OAuth-like authentication that hides Web3 complexity from users"""

    def get(self, request):
        """Display authentication options"""
        return render(request, 'identity/auth_options.html', {
            'user_types': User.USER_TYPES,
            'creative_styles': ['professional', 'creative', 'hybrid'],
            'industries': ['Technology', 'Design', 'Marketing', 'Finance', 'Healthcare', 'Education']
        })

    @method_decorator(csrf_exempt, name='csrf_exempt')
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


@login_required
def user_profile(request, user_id=None):
    """Display user profile with professional and creative elements"""
    if user_id:
        try:
            profile_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
    else:
        profile_user = request.user

    try:
        user_profile = UserProfile.objects.get(user=profile_user)
        top_connection_objects = user_profile.get_top_connections()
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
        user_profile = None
        top_connections = []
        top_connection_data = []

    return render(request, 'identity/user_profile.html', {
        'profile_user': profile_user,
        'profile': user_profile,
        'top_connections': zip(top_connections, top_connection_data),
        'is_own_profile': profile_user == request.user
    })


@login_required
def dashboard(request):
    """User dashboard with hybrid professional-creative features"""
    user = request.user

    try:
        user_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=user)

    return render(request, 'identity/dashboard.html', {
        'user': user,
        'profile': user_profile,
        'user_type': user.get_user_type_display(),
        'completion_percentage': calculate_profile_completion(user_profile),
        'top_connections': user_profile.get_top_connections(),
        'recent_activity': get_recent_activity(user)
    })


def calculate_profile_completion(profile):
    """Calculate profile completion percentage for hybrid model"""
    completion = 0

    # Professional fields
    if profile.skills:
        completion += 2
    if profile.experience:
        completion += 2
    if profile.education:
        completion += 1
    if profile.certifications:
        completion += 1

    # Creative fields
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

    # Social hierarchy
    if profile.top_connections_count >= 1:
        completion += 1

    return min(completion * 10, 100)


def get_recent_activity(user):
    """Get recent user activity for dashboard"""
    return [
        {'type': 'profile_update', 'message': 'Updated professional theme', 'timestamp': '2024-01-31 10:30'},
        {'type': 'connection_added', 'message': 'Added to Top 8', 'timestamp': '2024-01-31 09:15'},
        {'type': 'media_uploaded', 'message': 'Uploaded portfolio item', 'timestamp': '2024-01-30 14:20'},
    ]


def user_logout(request):
    """Log out and redirect to home"""
    logout(request)
    return redirect('/')


# =============================================================================
# Privy Authentication Views
# =============================================================================

class PrivyAuthInitView(View):
    """Initiate Privy OAuth-like authentication flow"""

    def get(self, request):
        if not HAS_PRIVY:
            return redirect('identity:login')
        redirect_uri = request.build_absolute_uri('/identity/auth/callback/')
        auth_url = privy_client.get_oauth_url(redirect_uri, scope='profile wallet')
        return redirect(auth_url)


class PrivyAuthCallbackView(View):
    """Handle Privy OAuth callback"""

    def get(self, request):
        code = request.GET.get('code')
        error = request.GET.get('error')

        if error:
            return render(request, 'identity/auth_error.html', {
                'error': error,
                'error_description': request.GET.get('error_description', '')
            })

        if code and HAS_PRIVY:
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
                user = authenticate(request, privy_user=privy_user)
                if user:
                    login(request, user)
                    return redirect(settings.LOGIN_REDIRECT_URL)

        return render(request, 'identity/auth_error.html', {
            'error': 'authentication_failed',
            'error_description': 'Unable to complete authentication'
        })


class DevAuthCallbackView(View):
    """Development-only auth callback for testing without Privy API keys"""

    def get(self, request):
        state = request.GET.get('state', '')
        redirect_uri = request.GET.get('redirect_uri', '/identity/dashboard/')
        return render(request, 'identity/dev_auth.html', {
            'state': state,
            'redirect_uri': redirect_uri,
        })

    def post(self, request):
        username = request.POST.get('username', '')
        user_type = request.POST.get('user_type', 'HUMAN')
        redirect_uri = request.POST.get('redirect_uri', '/identity/dashboard/')

        if not username:
            username = f"dev_user_{secrets.token_hex(4)}"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'user_type': user_type,
                'email': f'{username}@clawedin.local',
            }
        )

        if created:
            user.wallet_address = f"0x{secrets.token_hex(20)}"
            user.privy_user_id = f"privy_dev_{secrets.token_hex(8)}"
            user.save()
            UserProfile.objects.get_or_create(user=user)

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect(redirect_uri)


# =============================================================================
# Agent API Views
# =============================================================================

class AgentRegistrationView(View):
    """Register a new AI agent"""

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        name = data.get('name', '')
        capabilities = data.get('capabilities', [])
        owner_id = data.get('owner_id')

        if not name:
            return JsonResponse({'error': 'Agent name required'}, status=400)

        username = f"agent_{name.lower().replace(' ', '_')}"
        counter = 1
        base_username = username
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

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

        if HAS_PRIVY:
            agent.wallet_address = privy_client.create_embedded_wallet(str(agent.id))
        else:
            agent.wallet_address = f"0x{secrets.token_hex(20)}"
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
    """Authenticate an AI agent via API key"""

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
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
            if HAS_PRIVY and token_manager:
                tokens = token_manager.create_token_pair(user)
            else:
                tokens = {'access_token': 'dev_token', 'refresh_token': 'dev_refresh'}
            return JsonResponse({
                'success': True,
                'agent_id': user.id,
                'username': user.username,
                **tokens,
            })
        else:
            return JsonResponse({'error': 'Invalid API key'}, status=401)
