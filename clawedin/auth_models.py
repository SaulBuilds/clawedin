from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
import secrets
import hashlib

User = get_user_model()

class ProfileShareToken(models.Model):
    """OAuth-like tokens for secure profile sharing"""
    
    TOKEN_TYPES = [
        ('view', 'View Only'),
        ('edit', 'Edit Access'),
        ('share', 'Share Permission'),
        ('api', 'API Access'),
    ]
    
    VISIBILITY_LEVELS = [
        ('public', 'Public'),
        ('connections', 'Connections Only'),
        ('private', 'Private'),
        ('token', 'Token Access Only'),
    ]
    
    # Core Token Information
    profile = models.ForeignKey(
        'Profile', 
        on_delete=models.CASCADE, 
        related_name='share_tokens'
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    token_type = models.CharField(max_length=20, choices=TOKEN_TYPES)
    
    # Access Control
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Permissions
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
    can_share = models.BooleanField(default=False)
    can_download = models.BooleanField(default=False)
    
    # Restrictions
    max_views = models.PositiveIntegerField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)
    allowed_domains = models.JSONField(default=list, blank=True)
    ip_whitelist = models.JSONField(default=list, blank=True)
    
    # Metadata
    purpose = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Security
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_ip = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profile_share_tokens'
        verbose_name = 'Profile Share Token'
        verbose_name_plural = 'Profile Share Tokens'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['profile', 'is_active']),
            models.Index(fields=['expires_at', 'is_active']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.token_type} token for {self.profile.user.username}"
    
    @classmethod
    def generate_token(cls):
        """Generate secure random token"""
        return secrets.token_urlsafe(48)
    
    @classmethod
    def create_token(cls, profile, token_type, created_by, expires_in_days=30, **kwargs):
        """Create new share token"""
        token = cls(
            profile=profile,
            token=cls.generate_token(),
            token_type=token_type,
            created_by=created_by,
            expires_at=timezone.now() + timezone.timedelta(days=expires_in_days),
            **kwargs
        )
        token.save()
        return token
    
    def is_valid(self):
        """Check if token is valid and not expired"""
        if not self.is_active:
            return False
        
        if timezone.now() > self.expires_at:
            return False
        
        if self.max_views and self.view_count >= self.max_views:
            return False
        
        return True
    
    def can_access_with_permissions(self, required_permissions):
        """Check if token provides required permissions"""
        required = set(required_permissions)
        available = set()
        
        if self.can_view:
            available.add('view')
        if self.can_edit:
            available.add('edit')
        if self.can_share:
            available.add('share')
        if self.can_download:
            available.add('download')
        
        return required.issubset(available)
    
    def record_access(self, ip_address=None):
        """Record token access"""
        self.view_count += 1
        self.last_used_at = timezone.now()
        if ip_address:
            self.last_ip = ip_address
        self.save(update_fields=['view_count', 'last_used_at', 'last_ip'])
    
    def revoke(self):
        """Revoke token"""
        self.is_active = False
        self.save(update_fields=['is_active'])
    
    def extend_expiry(self, days):
        """Extend token expiry"""
        self.expires_at = timezone.now() + timezone.timedelta(days=days)
        self.save(update_fields=['expires_at'])

class ProfileAccessLog(models.Model):
    """Log all profile access attempts and results"""
    
    ACCESS_TYPES = [
        ('view', 'View Profile'),
        ('edit', 'Edit Profile'),
        ('share', 'Share Profile'),
        ('download', 'Download Profile'),
        ('api', 'API Access'),
    ]
    
    RESULTS = [
        ('success', 'Success'),
        ('denied', 'Access Denied'),
        ('expired', 'Token Expired'),
        ('revoked', 'Token Revoked'),
        ('forbidden', 'Forbidden'),
    ]
    
    # Access Information
    profile = models.ForeignKey(
        'Profile', 
        on_delete=models.CASCADE, 
        related_name='access_logs'
    )
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPES)
    result = models.CharField(max_length=20, choices=RESULTS)
    
    # Request Information
    token = models.ForeignKey(
        ProfileShareToken, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Request Metadata
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True)
    
    # Request Details
    endpoint = models.CharField(max_length=200, blank=True)
    method = models.CharField(max_length=10, blank=True)
    
    # Response Information
    status_code = models.PositiveIntegerField(null=True, blank=True)
    response_size = models.PositiveIntegerField(null=True, blank=True)
    
    # Additional Data
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'profile_access_logs'
        verbose_name = 'Profile Access Log'
        verbose_name_plural = 'Profile Access Logs'
        indexes = [
            models.Index(fields=['profile', 'created_at']),
            models.Index(fields=['access_type', 'result']),
            models.Index(fields=['token']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.access_type} - {self.result} - {self.profile.user.username}"

class ProfileVisibility(models.Model):
    """Advanced profile visibility and privacy settings"""
    
    VISIBILITY_LEVELS = [
        ('public', 'Public - Everyone'),
        ('connections', 'Connections Only'),
        ('network', 'Network (2nd degree)'),
        ('private', 'Private - Invite Only'),
        ('custom', 'Custom Rules'),
    ]
    
    profile = models.OneToOneField(
        'Profile', 
        on_delete=models.CASCADE, 
        related_name='visibility_settings'
    )
    
    # General Visibility
    overall_visibility = models.CharField(
        max_length=20, 
        choices=VISIBILITY_LEVELS, 
        default='connections'
    )
    
    # Profile Section Visibility
    show_contact_info = models.BooleanField(default=True)
    show_experience = models.BooleanField(default=True)
    show_education = models.BooleanField(default=True)
    show_skills = models.BooleanField(default=True)
    show_connections = models.BooleanField(default=True)
    show_activity = models.BooleanField(default=True)
    
    # Search Visibility
    appear_in_search = models.BooleanField(default=True)
    search_visibility_level = models.CharField(
        max_length=20,
        choices=VISIBILITY_LEVELS,
        default='connections'
    )
    
    # External Sharing
    allow_public_sharing = models.BooleanField(default=True)
    require_approval_for_sharing = models.BooleanField(default=False)
    auto_approve_connections = models.BooleanField(default=True)
    
    # Network Visibility
    visible_to_alumni = models.BooleanField(default=True)
    visible_to_colleagues = models.BooleanField(default=True)
    visible_to_group_members = models.BooleanField(default=True)
    
    # Custom Rules (JSON-based)
    custom_visibility_rules = models.JSONField(default=dict, blank=True)
    blocked_users = models.ManyToManyField(
        User,
        related_name='blocked_by_profiles',
        blank=True
    )
    
    # Sharing Restrictions
    max_share_duration_days = models.PositiveIntegerField(default=365)
    require_2fa_for_sensitive = models.BooleanField(default=False)
    
    # Analytics Settings
    track_views = models.BooleanField(default=True)
    show_view_count = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profile_visibility'
        verbose_name = 'Profile Visibility'
        verbose_name_plural = 'Profile Visibility Settings'
    
    def __str__(self):
        return f"Visibility for {self.profile.user.username}"
    
    def can_user_view(self, user, access_type='view'):
        """Check if user can view profile based on visibility settings"""
        # Profile owner can always view
        if user == self.profile.user:
            return True, 'owner'
        
        # Blocked users cannot view
        if user in self.blocked_users.all():
            return False, 'blocked'
        
        # Check based on overall visibility
        if self.overall_visibility == 'public':
            return True, 'public'
        elif self.overall_visibility == 'connections':
            # Check if users are connected
            if self._is_connected(user):
                return True, 'connection'
            return False, 'not_connected'
        elif self.overall_visibility == 'network':
            # Check if users are in same network
            if self._is_in_network(user):
                return True, 'network'
            return False, 'not_in_network'
        elif self.overall_visibility == 'private':
            return False, 'private'
        
        # Custom rules evaluation
        return self._evaluate_custom_rules(user, access_type)
    
    def _is_connected(self, user):
        """Check if user is connected to profile owner"""
        return self.profile.top_connections.filter(
            user=user
        ).exists()
    
    def _is_in_network(self, user):
        """Check if user is in 2nd degree network"""
        # Implementation would check mutual connections
        try:
            user_profile = user.clawedin_profile
            # Check for mutual connections
            mutual_count = self.profile.top_connections.filter(
                id__in=user_profile.top_connections.all()
            ).count()
            return mutual_count > 0
        except:
            return False
    
    def _evaluate_custom_rules(self, user, access_type):
        """Evaluate custom visibility rules"""
        # Implementation would evaluate custom JSON rules
        # For now, default to connection check
        return self._is_connected(user), 'custom_rule'
    
    def block_user(self, user):
        """Block user from viewing profile"""
        self.blocked_users.add(user)
        self.save(update_fields=[])
    
    def unblock_user(self, user):
        """Unblock user"""
        self.blocked_users.remove(user)
        self.save(update_fields=[])

class ProfileShare(models.Model):
    """Track profile sharing instances and permissions"""
    
    SHARE_TYPES = [
        ('link', 'Shareable Link'),
        ('email', 'Email Invite'),
        ('social', 'Social Media'),
        ('embed', 'Embedded'),
        ('api', 'API Share'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ]
    
    # Share Information
    profile = models.ForeignKey(
        'Profile', 
        on_delete=models.CASCADE, 
        related_name='shares'
    )
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE)
    share_type = models.CharField(max_length=20, choices=SHARE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Share Details
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    share_url = models.URLField(blank=True)
    
    # Access Control
    token = models.ForeignKey(
        ProfileShareToken, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    password = models.CharField(max_length=128, blank=True)
    
    # Constraints
    expires_at = models.DateTimeField(null=True, blank=True)
    max_clicks = models.PositiveIntegerField(null=True, blank=True)
    click_count = models.PositiveIntegerField(default=0)
    
    # Targeting
    allowed_emails = models.JSONField(default=list, blank=True)
    allowed_domains = models.JSONField(default=list, blank=True)
    
    # Analytics
    views = models.PositiveIntegerField(default=0)
    unique_views = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profile_shares'
        verbose_name = 'Profile Share'
        verbose_name_plural = 'Profile Shares'
        indexes = [
            models.Index(fields=['profile', 'status']),
            models.Index(fields=['shared_by']),
            models.Index(fields=['share_type']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.share_type} - {self.profile.user.username}"
    
    def is_active(self):
        """Check if share is currently active"""
        if self.status != 'active':
            return False
        
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        
        if self.max_clicks and self.click_count >= self.max_clicks:
            return False
        
        return True
    
    def record_click(self):
        """Record a click on the share"""
        self.click_count += 1
        self.save(update_fields=['click_count'])
    
    def record_view(self):
        """Record a profile view from the share"""
        self.views += 1
        self.save(update_fields=['views'])
    
    def revoke(self):
        """Revoke the share"""
        self.status = 'revoked'
        self.save(update_fields=['status'])
        
        if self.token:
            self.token.revoke()