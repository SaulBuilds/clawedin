from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import uuid

# Import Company for resume experience linking (optional)
try:
    from companies.models import Company
except ImportError:
    Company = None


class User(AbstractUser):
    """
    Hybrid User Model combining LinkedIn professional foundation with MySpace creative expression.
    Supports human users, AI agents, and hybrid accounts.
    """
    # User type choices - supports both naming conventions
    HUMAN = "human"
    AGENT = "agent"
    HYBRID = "hybrid"

    USER_TYPES = [
        ('HUMAN', 'Human'),
        ('AGENT', 'AI Agent'),
        ('HYBRID', 'Hybrid'),
    ]

    ACCOUNT_TYPE_CHOICES = [
        (HUMAN, "Human"),
        (AGENT, "Agent"),
    ]

    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='HUMAN')

    class Meta:
        swappable = 'AUTH_USER_MODEL'

    # Display and identity
    display_name = models.CharField(max_length=150, blank=True)

    # Web3 abstraction (hidden from user)
    wallet_address = models.CharField(max_length=255, unique=True, null=True, blank=True)
    privy_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    # Professional information (LinkedIn-style)
    professional_title = models.CharField(max_length=200, blank=True, default='')
    bio = models.TextField(max_length=2000, blank=True)
    profile_picture = models.URLField(null=True, blank=True)
    location = models.CharField(max_length=120, blank=True)
    website = models.URLField(blank=True)

    # Creative expression fields (MySpace-style)
    creative_style = models.CharField(max_length=50, default='professional')
    preferred_industry = models.CharField(max_length=100, null=True, blank=True)

    # Agent-specific fields
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional agent or client identifier.",
    )
    agent_capabilities = models.JSONField(default=list, blank=True)
    agent_owner = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_agents'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Reputation and credits
    reputation_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    credit_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

    @property
    def is_agent(self):
        return self.user_type in ['AGENT', 'HYBRID', 'agent']

    @property
    def is_human(self):
        return self.user_type in ['HUMAN', 'HYBRID', 'human']

    @property
    def account_type(self):
        """Compatibility property for upstream code"""
        return self.user_type.lower() if self.user_type else 'human'


class UserProfile(models.Model):
    """
    Extended profile with professional base + creative expression layers + social hierarchy
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    # Professional information (LinkedIn-style)
    skills = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    education = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)

    # Creative expression layers (MySpace-style)
    theme_choice = models.CharField(max_length=50, null=True, blank=True)
    custom_colors = models.JSONField(default=dict, blank=True)
    layout_preference = models.CharField(max_length=20, default='professional')
    background_image = models.URLField(null=True, blank=True)

    # Media integration
    portfolio_media = models.JSONField(default=list, blank=True)
    featured_audio = models.URLField(null=True, blank=True)
    background_music = models.URLField(null=True, blank=True)

    # Preferences
    privacy_settings = models.JSONField(default=dict, blank=True)
    notification_settings = models.JSONField(default=dict, blank=True)

    # Credits and earnings
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_top_connections(self, limit=8):
        """Get user's top connections ordered by position"""
        return TopConnection.objects.filter(
            user=self.user
        ).select_related('connection').order_by('position')[:limit]

    @property
    def top_connections_count(self):
        """Get count of top connections"""
        return TopConnection.objects.filter(user=self.user).count()


class TopConnection(models.Model):
    """
    Professional Top 8 with business context (MySpace-style for professionals)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owner_top_connections'
    )
    connection = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='featured_as_connection'
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='theme_creator',
        null=True,
        blank=True
    )
    position = models.IntegerField(default=1)  # 1-8 position
    collaboration_history = models.JSONField(default=list, blank=True)
    business_context = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'connection']
        ordering = ['position']

    def __str__(self):
        return f"{self.user.username}'s Top 8 - Position {self.position}"


class ProfessionalTheme(models.Model):
    """
    Professional themes with creative elements
    """
    name = models.CharField(max_length=100, unique=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_themes'
    )
    description = models.TextField()

    # Theme elements
    color_scheme = models.JSONField(default=dict, blank=True)
    layout_template = models.CharField(max_length=50, default='professional')
    background_options = models.JSONField(default=list, blank=True)
    font_preferences = models.JSONField(default=dict, blank=True)

    # Professional standards
    professional_rating = models.DecimalField(max_digits=3, decimal_places=2)
    approved_for_business = models.BooleanField(default=False)
    featured_theme = models.BooleanField(default=False)

    # Usage and popularity
    usage_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} by {self.creator.username}"

    @property
    def is_premium(self):
        return self.professional_rating >= 7.0


class CreativeMedia(models.Model):
    """
    Professional media showcase with creative presentation
    """
    MEDIA_TYPES = [
        ('MUSIC', 'Music/Audio'),
        ('VIDEO', 'Video Content'),
        ('DESIGN', 'Design Portfolio'),
        ('PHOTOGRAPHY', 'Photography'),
        ('WRITING', 'Writing Samples'),
        ('CODE', 'Code Projects'),
        ('ART', 'Art & Illustration'),
    ]

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='creative_media'
    )
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()

    # Media files and metadata
    file_url = models.URLField()
    thumbnail_url = models.URLField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # For audio/video
    file_size = models.IntegerField(null=True, blank=True)

    # Creative elements
    creative_tags = models.JSONField(default=list, blank=True)
    artistic_style = models.CharField(max_length=100, null=True, blank=True)
    professional_context = models.CharField(max_length=500, null=True, blank=True)

    # Web3 ownership
    blockchain_hash = models.CharField(max_length=255, null=True, blank=True)
    ownership_token = models.CharField(max_length=255, null=True, blank=True)

    # Usage metrics
    plays_count = models.IntegerField(default=0)
    downloads_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)

    # Professional verification
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} by {self.creator.username}"


class ProfessionalApp(models.Model):
    """
    Professional applications and tools
    """
    APP_TYPES = [
        ('TOOL', 'Professional Tool'),
        ('TEMPLATE', 'Creative Template'),
        ('WIDGET', 'Profile Widget'),
        ('ANALYTICS', 'Analytics Dashboard'),
        ('COLLABORATION', 'Collaboration Tool'),
        ('CREATIVE', 'Creative Tool'),
    ]

    developer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='developed_apps'
    )
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    app_type = models.CharField(max_length=20, choices=APP_TYPES)

    # Professional standards
    certification_level = models.CharField(max_length=20)
    user_rating = models.DecimalField(max_digits=3, decimal_places=2)
    usage_count = models.IntegerField(default=0)

    # Revenue sharing
    price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    revenue_share_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=80.0
    )

    # Web3 integration
    smart_contract_address = models.CharField(max_length=255, null=True, blank=True)
    token_royalty_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0
    )

    # App metadata
    icon_url = models.URLField(null=True, blank=True)
    screenshots = models.JSONField(default=list, blank=True)
    api_documentation = models.URLField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} by {self.developer.username}"

    @property
    def is_certified(self):
        return self.certification_level == 'VERIFIED'


# =============================================================================
# Resume Models (from upstream)
# =============================================================================

class Resume(models.Model):
    """LinkedIn-style resume with multiple sections"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resumes",
    )
    title = models.CharField(max_length=200, default="Resume")
    headline = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user.username} - {self.title}"


class ResumeExperience(models.Model):
    """Work experience entry for a resume"""
    EMPLOYMENT_TYPES = [
        ("full_time", "Full-time"),
        ("part_time", "Part-time"),
        ("contract", "Contract"),
        ("internship", "Internship"),
        ("freelance", "Freelance"),
        ("temporary", "Temporary"),
        ("other", "Other"),
    ]

    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="experiences",
    )
    title = models.CharField(max_length=200)
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resume_experiences",
    ) if Company else None
    company_name = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=120, blank=True)
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPES,
        blank=True,
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def display_company(self) -> str:
        if self.company:
            return self.company.name
        return self.company_name

    def __str__(self) -> str:
        return f"{self.title} at {self.display_company() or 'Unknown'}"


class ResumeEducation(models.Model):
    """Education entry for a resume"""
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="educations",
    )
    school = models.CharField(max_length=200)
    degree = models.CharField(max_length=120, blank=True)
    field_of_study = models.CharField(max_length=120, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    activities = models.TextField(blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.school} - {self.degree}".strip(" -")


class ResumeSkill(models.Model):
    """Skill entry for a resume"""
    PROFICIENCY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
        ("expert", "Expert"),
    ]

    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="skills",
    )
    name = models.CharField(max_length=120)
    proficiency = models.CharField(
        max_length=20,
        choices=PROFICIENCY_CHOICES,
        blank=True,
    )
    years_of_experience = models.PositiveSmallIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class ResumeProject(models.Model):
    """Project entry for a resume"""
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=120, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class ResumeCertification(models.Model):
    """Certification entry for a resume"""
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE,
        related_name="certifications",
    )
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    credential_id = models.CharField(max_length=120, blank=True)
    credential_url = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class UserSkill(models.Model):
    """User's skills independent of resumes"""
    PROFICIENCY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
        ("expert", "Expert"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="skills_profile",
    )
    name = models.CharField(max_length=120)
    proficiency = models.CharField(
        max_length=20,
        choices=PROFICIENCY_CHOICES,
        blank=True,
    )
    years_of_experience = models.PositiveSmallIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "name")

    def __str__(self) -> str:
        return self.name


class ApiToken(models.Model):
    """API tokens for bearer authentication"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_tokens",
    )
    name = models.CharField(max_length=120, blank=True)
    token_hash = models.CharField(max_length=64, unique=True)
    prefix = models.CharField(max_length=12)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def __str__(self) -> str:
        label = self.name or self.prefix
        return f"{label} ({self.user})"


# =============================================================================
# Signal handlers for profile updates
# =============================================================================

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created and not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def update_profile_timestamp(sender, instance, **kwargs):
    """Update profile timestamp when user is updated"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
