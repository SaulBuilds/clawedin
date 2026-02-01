from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
import json

User = get_user_model()

class ProfessionalConnection(models.Model):
    """Professional connections with relationship types"""
    
    CONNECTION_TYPES = [
        ('colleague', 'Current Colleague'),
        ('former_colleague', 'Former Colleague'),
        ('classmate', 'Classmate'),
        ('client', 'Client'),
        ('vendor', 'Vendor'),
        ('partner', 'Business Partner'),
        ('mentor', 'Mentor'),
        ('mentee', 'Mentee'),
        ('recruiter', 'Recruiter'),
        ('candidate', 'Candidate'),
        ('industry_peer', 'Industry Peer'),
        ('friend', 'Professional Friend'),
    ]
    
    CONNECTION_STATUS = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    # Connection Relationship
    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_connections'
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_connections'
    )
    
    # Connection Details
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPES)
    status = models.CharField(max_length=20, choices=CONNECTION_STATUS, default='pending')
    
    # Professional Context
    company = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=200, blank=True)
    project = models.CharField(max_length=200, blank=True)
    how_met = models.TextField(blank=True)
    
    # Mutual Information
    mutual_connections = models.ManyToManyField(
        User,
        related_name='mutual_connection_links',
        blank=True
    )
    
    # Strength and Trust
    connection_strength = models.FloatField(
        default=1.0,
        help_text="Connection strength score based on interactions"
    )
    trust_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('very_high', 'Very High'),
        ],
        default='medium'
    )
    
    # Recommendations
    can_recommend = models.BooleanField(default=True)
    recommendation_count = models.PositiveIntegerField(default=0)
    endorsements_count = models.PositiveIntegerField(default=0)
    
    # Activity
    last_interaction = models.DateTimeField(null=True, blank=True)
    interaction_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'professional_connections'
        verbose_name = 'Professional Connection'
        verbose_name_plural = 'Professional Connections'
        indexes = [
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['connection_type']),
            models.Index(fields=['connection_strength']),
            models.Index(fields=['accepted_at']),
        ]
        unique_together = ['requester', 'recipient']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.requester.username} → {self.recipient.username} ({self.status})"
    
    def accept(self):
        """Accept connection request"""
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.save(update_fields=['status', 'accepted_at'])
        
        # Add to both users' top connections if applicable
        self._update_top_connections()
        
        # Update mutual connections
        self._update_mutual_connections()
    
    def decline(self):
        """Decline connection request"""
        self.status = 'declined'
        self.save(update_fields=['status'])
    
    def withdraw(self):
        """Withdraw connection request"""
        self.status = 'withdrawn'
        self.save(update_fields=['status'])
    
    def _update_top_connections(self):
        """Update top connections for both users"""
        try:
            requester_profile = self.requester.clawedin_profile
            recipient_profile = self.recipient.clawedin_profile
            
            # Add to requester's top connections
            if requester_profile.top_connections.count() < 8:
                requester_profile.top_connections.add(self.recipient.clawedin_profile)
            
            # Add to recipient's top connections
            if recipient_profile.top_connections.count() < 8:
                recipient_profile.top_connections.add(self.requester.clawedin_profile)
                
        except Exception:
            pass  # Handle gracefully
    
    def _update_mutual_connections(self):
        """Find and update mutual connections"""
        # Get all connections of requester
        requester_connections = ProfessionalConnection.objects.filter(
            requester=self.requester,
            status='accepted'
        ).values_list('recipient', flat=True)
        
        # Get all connections of recipient
        recipient_connections = ProfessionalConnection.objects.filter(
            requester=self.recipient,
            status='accepted'
        ).values_list('recipient', flat=True)
        
        # Find mutual connections
        mutual_ids = set(requester_connections) & set(recipient_connections)
        mutual_users = User.objects.filter(id__in=mutual_ids)
        
        self.mutual_connections.set(mutual_users)

class SkillEndorsement(models.Model):
    """Skill endorsements from connections"""
    
    ENDORSEMENT_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
        ('master', 'Master'),
    ]
    
    # Endorsement Relationship
    endorser = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_endorsements'
    )
    endorsed = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_endorsements'
    )
    
    # Skill Information
    skill_name = models.CharField(max_length=100)
    endorsement_level = models.CharField(max_length=20, choices=ENDORSEMENT_LEVELS)
    
    # Professional Context
    context = models.TextField(
        blank=True,
        help_text="Context or evidence for the endorsement"
    )
    project_worked_on = models.CharField(max_length=200, blank=True)
    years_known = models.PositiveIntegerField(null=True, blank=True)
    
    # Relationship Context
    connection = models.ForeignKey(
        ProfessionalConnection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='endorsements'
    )
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)
    
    # Visibility
    is_public = models.BooleanField(default=True)
    show_on_profile = models.BooleanField(default=True)
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    helpful_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'skill_endorsements'
        verbose_name = 'Skill Endorsement'
        verbose_name_plural = 'Skill Endorsements'
        indexes = [
            models.Index(fields=['endorsed', 'skill_name']),
            models.Index(fields=['endorser', 'created_at']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['is_public']),
        ]
        unique_together = ['endorser', 'endorsed', 'skill_name']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.endorser.username} endorses {self.endorsed.username} in {self.skill_name}"
    
    def mark_helpful(self):
        """Mark endorsement as helpful"""
        self.helpful_count += 1
        self.save(update_fields=['helpful_count'])
    
    def verify_endorsement(self, verifier, notes=''):
        """Verify the endorsement"""
        self.is_verified = True
        self.verification_notes = notes
        self.save(update_fields=['is_verified', 'verification_notes'])

class ProfessionalRecommendation(models.Model):
    """Professional recommendations"""
    
    RECOMMENDATION_TYPES = [
        ('professional', 'Professional'),
        ('academic', 'Academic'),
        ('project', 'Project-based'),
        ('character', 'Character'),
        ('leadership', 'Leadership'),
        ('technical', 'Technical'),
        ('creative', 'Creative'),
    ]
    
    RECOMMENDATION_RELATIONSHIP = [
        ('manager', 'Manager'),
        ('colleague', 'Colleague'),
        ('client', 'Client'),
        ('mentor', 'Mentor'),
        ('professor', 'Professor'),
        ('business_partner', 'Business Partner'),
        ('direct_report', 'Direct Report'),
    ]
    
    # Recommendation Details
    recommender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_recommendations'
    )
    recommended = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_recommendations'
    )
    
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    relationship = models.CharField(max_length=20, choices=RECOMMENDATION_RELATIONSHIP)
    
    # Content
    title = models.CharField(max_length=200)
    content = models.TextField()
    summary = models.CharField(max_length=500, blank=True)
    
    # Professional Context
    company = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=200, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    projects = models.JSONField(default=list, blank=True)
    
    # Skills and Qualities
    skills_mentioned = models.JSONField(default=list, blank=True)
    qualities = models.JSONField(default=list, blank=True)
    
    # Rating and Performance
    rating = models.FloatField(
        null=True,
        blank=True,
        help_text="Overall rating (1.0-5.0)"
    )
    performance_areas = models.JSONField(
        default=dict,
        blank=True,
        help_text="Performance ratings by area"
    )
    
    # Visibility and Privacy
    is_public = models.BooleanField(default=True)
    anonymous_recommender = models.BooleanField(default=False)
    show_on_profile = models.BooleanField(default=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('pending', 'Pending Approval'),
            ('published', 'Published'),
            ('hidden', 'Hidden'),
            ('flagged', 'Flagged'),
        ],
        default='draft'
    )
    
    # Engagement
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    helpful_count = models.PositiveIntegerField(default=0)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_recommendations'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'professional_recommendations'
        verbose_name = 'Professional Recommendation'
        verbose_name_plural = 'Professional Recommendations'
        indexes = [
            models.Index(fields=['recommender', 'status']),
            models.Index(fields=['recommended', 'status']),
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['recommendation_type']),
            models.Index(fields=['is_public']),
            models.Index(fields=['is_verified']),
        ]
        ordering = ['-published_at']
    
    def __str__(self):
        return f"Recommendation: {self.recommender.username} → {self.recommended.username}"
    
    def publish(self):
        """Publish recommendation"""
        self.status = 'published'
        self.published_at = timezone.now()
        self.save(update_fields=['status', 'published_at'])
        
        # Update connection recommendation count
        try:
            connection = ProfessionalConnection.objects.get(
                Q(requester=self.recommender, recipient=self.recommended) |
                Q(requester=self.recommended, recipient=self.recommender),
                status='accepted'
            )
            connection.recommendation_count += 1
            connection.save(update_fields=['recommendation_count'])
        except ProfessionalConnection.DoesNotExist:
            pass
    
    def mark_helpful(self):
        """Mark recommendation as helpful"""
        self.helpful_count += 1
        self.save(update_fields=['helpful_count'])
    
    def verify_recommendation(self, verifier):
        """Verify the recommendation"""
        self.is_verified = True
        self.verified_by = verifier
        self.verified_at = timezone.now()
        self.save(update_fields=['is_verified', 'verified_by', 'verified_at'])

class NetworkAnalytics(models.Model):
    """Analytics for professional network activity"""
    
    ANALYTICS_TYPES = [
        ('connection_growth', 'Connection Growth'),
        ('engagement_rate', 'Engagement Rate'),
        ('network_reach', 'Network Reach'),
        ('influence_score', 'Influence Score'),
        ('activity_frequency', 'Activity Frequency'),
    ]
    
    # User and Period
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='network_analytics'
    )
    analytics_type = models.CharField(max_length=30, choices=ANALYTICS_TYPES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Metrics
    total_connections = models.PositiveIntegerField(default=0)
    new_connections = models.PositiveIntegerField(default=0)
    total_interactions = models.PositiveIntegerField(default=0)
    posts_created = models.PositiveIntegerField(default=0)
    endorsements_given = models.PositiveIntegerField(default=0)
    endorsements_received = models.PositiveIntegerField(default=0)
    recommendations_given = models.PositiveIntegerField(default=0)
    recommendations_received = models.PositiveIntegerField(default=0)
    
    # Calculated Metrics
    network_depth = models.PositiveIntegerField(default=1)
    influence_score = models.FloatField(default=0.0)
    engagement_rate = models.FloatField(default=0.0)
    connection_quality_score = models.FloatField(default=0.0)
    
    # Comparative Metrics
    percentile_rank = models.FloatField(null=True, blank=True)
    industry_comparison = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'network_analytics'
        verbose_name = 'Network Analytics'
        verbose_name_plural = 'Network Analytics'
        indexes = [
            models.Index(fields=['user', 'analytics_type', 'period_start']),
            models.Index(fields=['analytics_type', 'period_start']),
            models.Index(fields=['influence_score']),
            models.Index(fields=['engagement_rate']),
        ]
        ordering = ['-period_start']
    
    def __str__(self):
        return f"{self.user.username} - {self.analytics_type} ({self.period_start})"

class ProfessionalGroup(models.Model):
    """Professional groups and communities"""
    
    GROUP_TYPES = [
        ('industry', 'Industry Association'),
        ('alumni', 'Alumni Group'),
        ('professional', 'Professional Organization'),
        ('interest', 'Interest Group'),
        ('company', 'Company Group'),
        ('project', 'Project Team'),
        ('conference', 'Conference Attendees'),
        ('local', 'Local Network'),
        ('skill_based', 'Skill-based Group'),
    ]
    
    GROUP_PRIVACY = [
        ('public', 'Public'),
        ('private', 'Private (Invite Only)'),
        ('restricted', 'Restricted (Approval Required)'),
        ('secret', 'Secret (Invite Only)'),
    ]
    
    # Group Information
    name = models.CharField(max_length=200)
    description = models.TextField()
    group_type = models.CharField(max_length=20, choices=GROUP_TYPES)
    privacy = models.CharField(max_length=20, choices=GROUP_PRIVACY, default='public')
    
    # Leadership
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_groups'
    )
    administrators = models.ManyToManyField(
        User,
        related_name='administered_groups',
        blank=True
    )
    
    # Membership
    members = models.ManyToManyField(
        User,
        through='GroupMembership',
        related_name='professional_groups',
        blank=True
    )
    
    # Group Settings
    max_members = models.PositiveIntegerField(null=True, blank=True)
    allow_invites = models.BooleanField(default=True)
    allow_member_posts = models.BooleanField(default=True)
    moderate_posts = models.BooleanField(default=False)
    
    # Media and Branding
    logo_url = models.URLField(blank=True)
    cover_image_url = models.URLField(blank=True)
    
    # Activity
    is_active = models.BooleanField(default=True)
    member_count = models.PositiveIntegerField(default=0)
    post_count = models.PositiveIntegerField(default=0)
    
    # Location and Industry
    location = models.CharField(max_length=200, blank=True)
    industry_focus = models.CharField(max_length=100, blank=True)
    skills_focus = models.JSONField(default=list, blank=True)
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'professional_groups'
        verbose_name = 'Professional Group'
        verbose_name_plural = 'Professional Groups'
        indexes = [
            models.Index(fields=['group_type', 'privacy']),
            models.Index(fields=['creator']),
            models.Index(fields=['is_active']),
            models.Index(fields=['member_count']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Group: {self.name}"

class GroupMembership(models.Model):
    """Membership records for professional groups"""
    
    MEMBERSHIP_ROLES = [
        ('member', 'Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Administrator'),
        ('owner', 'Owner'),
    ]
    
    MEMBERSHIP_STATUS = [
        ('invited', 'Invited'),
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('left', 'Left'),
        ('banned', 'Banned'),
    ]
    
    # Membership Relationship
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='group_memberships'
    )
    group = models.ForeignKey(
        ProfessionalGroup,
        on_delete=models.CASCADE,
        related_name='membership_records'
    )
    
    # Membership Details
    role = models.CharField(max_length=20, choices=MEMBERSHIP_ROLES, default='member')
    status = models.CharField(max_length=20, choices=MEMBERSHIP_STATUS, default='invited')
    
    # Joining Information
    joined_at = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_invitations'
    )
    invitation_message = models.TextField(blank=True)
    
    # Activity and Engagement
    last_activity = models.DateTimeField(null=True, blank=True)
    post_count = models.PositiveIntegerField(default=0)
    interaction_count = models.PositiveIntegerField(default=0)
    
    # Permissions and Settings
    can_post = models.BooleanField(default=True)
    can_invite = models.BooleanField(default=True)
    can_moderate = models.BooleanField(default=False)
    receive_notifications = models.BooleanField(default=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'group_memberships'
        verbose_name = 'Group Membership'
        verbose_name_plural = 'Group Memberships'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['group', 'status']),
            models.Index(fields=['role']),
            models.Index(fields=['joined_at']),
            models.Index(fields=['last_activity']),
        ]
        unique_together = ['user', 'group']
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.status})"
    
    def accept_invitation(self):
        """Accept group invitation"""
        self.status = 'active'
        self.joined_at = timezone.now()
        self.save(update_fields=['status', 'joined_at'])
        
        # Update group member count
        self.group.member_count = self.group.members.count()
        self.group.save(update_fields=['member_count'])
    
    def leave_group(self):
        """Leave group"""
        self.status = 'left'
        self.save(update_fields=['status'])
        
        # Update group member count
        self.group.member_count = self.group.members.count()
        self.group.save(update_fields=['member_count'])