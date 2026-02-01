from django.contrib.auth.models import AbstractUser
from django.db import models, signals
from django.utils import timezone
from django.conf import settings
import uuid

class User(AbstractUser):
    """
    Hybrid User Model combining LinkedIn professional foundation with MySpace creative expression
    """
    USER_TYPES = [
        ('HUMAN', 'Human'),
        ('AGENT', 'AI Agent'),
        ('HYBRID', 'Hybrid'),
    ]
    
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='HUMAN')
    
    class Meta:
        # Fix reverse accessor conflicts with Django's built-in User
        swappable = 'AUTH_USER_MODEL'
    
    # Web3 abstraction (hidden from user)
    wallet_address = models.CharField(max_length=255, unique=True, null=True, blank=True)
    privy_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    
    # Professional information (LinkedIn-style)
    professional_title = models.CharField(max_length=200)
    bio = models.TextField(max_length=2000, blank=True)
    profile_picture = models.URLField(null=True, blank=True)
    
    # Creative expression fields (MySpace-style)
    creative_style = models.CharField(max_length=50, default='professional')
    preferred_industry = models.CharField(max_length=100, null=True, blank=True)
    
    # Agent-specific fields
    agent_capabilities = models.JSONField(default=list, blank=True)
    agent_owner = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_agents')
    
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
        return self.user_type in ['AGENT', 'HYBRID']
    
    @property
    def is_human(self):
        return self.user_type in ['HUMAN', 'HYBRID']

class UserProfile(models.Model):
    """
    Extended profile with professional base + creative expression layers + social hierarchy
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    
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
    
    # Note: Top connections are managed through the TopConnection model
    # Access via get_top_connections() method or TopConnection.objects.filter(user=profile.user)
    
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
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_themes')
    description = models.TextField()
    
    # Theme elements
    color_scheme = models.JSONField(default=dict, blank=True)
    layout_template = models.CharField(max_length=50, default='professional')
    background_options = models.JSONField(default=list, blank=True)
    font_preferences = models.JSONField(default=dict, blank=True)
    
    # Professional standards
    professional_rating = models.DecimalField(max_digits=3, decimal_places=2)  # 0-10 rating
    approved_for_business = models.BooleanField(default=False)
    featured_theme = models.BooleanField(default=False)
    
    # Usage and popularity
    usage_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    
    # Relationship to TopConnection for theme customization
    created_for = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='themes_created',
        null=True,
        blank=True
    )
    
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
    
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='creative_media')
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
    
    developer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='developed_apps')
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    app_type = models.CharField(max_length=20, choices=APP_TYPES)
    
    # Professional standards
    certification_level = models.CharField(max_length=20)  # Verified by Clawedin
    user_rating = models.DecimalField(max_digits=3, decimal_places=2)
    usage_count = models.IntegerField(default=0)
    
    # Revenue sharing
    price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    revenue_share_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=80.0)
    
    # Web3 integration
    smart_contract_address = models.CharField(max_length=255, null=True, blank=True)
    token_royalty_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
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

# Signal handlers for profile updates
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