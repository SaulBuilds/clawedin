from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import json

User = get_user_model()

class ProfessionalContent(models.Model):
    """Base model for professional content"""
    
    CONTENT_TYPES = [
        ('post', 'Professional Post'),
        ('article', 'Professional Article'),
        ('achievement', 'Professional Achievement'),
        ('update', 'Career Update'),
        ('insight', 'Professional Insight'),
        ('milestone', 'Career Milestone'),
        ('project', 'Project Showcase'),
    ]
    
    VISIBILITY_LEVELS = [
        ('public', 'Public'),
        ('connections', 'Connections Only'),
        ('network', 'Network Only'),
        ('private', 'Private'),
        ('custom', 'Custom Rules'),
    ]
    
    # Content Information
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_authored')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    summary = models.CharField(max_length=500, blank=True)
    
    # Media
    featured_image = models.URLField(blank=True)
    attachments = models.JSONField(default=list, blank=True)
    
    # Professional Context
    skills_mentioned = models.JSONField(default=list, blank=True)
    companies_mentioned = models.JSONField(default=list, blank=True)
    projects_mentioned = models.JSONField(default=list, blank=True)
    
    # Visibility and Engagement
    visibility = models.CharField(max_length=20, choices=VISIBILITY_LEVELS, default='public')
    allow_comments = models.BooleanField(default=True)
    allow_shares = models.BooleanField(default=True)
    allow_likes = models.BooleanField(default=True)
    
    # Analytics
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    engagement_score = models.FloatField(default=0.0)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    moderation_flags = models.PositiveIntegerField(default=0)
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    published_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'professional_content'
        verbose_name = 'Professional Content'
        verbose_name_plural = 'Professional Content'
        indexes = [
            models.Index(fields=['author', 'published_at']),
            models.Index(fields=['content_type', 'is_approved']),
            models.Index(fields=['visibility', 'published_at']),
            models.Index(fields=['is_featured', 'published_at']),
            models.Index(fields=['engagement_score', 'published_at']),
            models.Index(fields=['published_at']),
        ]
        ordering = ['-published_at']
    
    def __str__(self):
        return f"{self.content_type}: {self.title}"
    
    def calculate_engagement_score(self):
        """Calculate engagement score based on interactions"""
        # Weighted engagement calculation
        like_weight = 1.0
        comment_weight = 2.0
        share_weight = 3.0
        view_weight = 0.1
        
        # Time decay factor (recent content gets higher score)
        days_since_published = (timezone.now() - self.published_at).days
        time_decay = max(0.1, 1.0 - (days_since_published * 0.01))
        
        score = (
            self.likes * like_weight +
            self.comments_count * comment_weight +
            self.shares * share_weight +
            self.views * view_weight
        ) * time_decay
        
        self.engagement_score = score
        self.save(update_fields=['engagement_score'])
        
        return score
    
    def can_user_view(self, user):
        """Check if user can view this content"""
        # Author can always view
        if user == self.author:
            return True, 'author'
        
        # Public content
        if self.visibility == 'public':
            return True, 'public'
        
        # Private content - only author
        if self.visibility == 'private':
            return False, 'private'
        
        # Check connection status for connections/network visibility
        if self.visibility in ['connections', 'network']:
            try:
                author_profile = self.author.clawedin_profile
                if hasattr(author_profile, 'visibility_settings'):
                    can_view, reason = author_profile.visibility_settings.can_user_view(user, 'view')
                    return can_view, reason
            except:
                pass
            
            # Fallback: check if connected
            if user and user.is_authenticated:
                try:
                    author_profile = self.author.clawedin_profile
                    user_profile = user.clawedin_profile
                    
                    # Direct connection
                    if author_profile.top_connections.filter(id=user_profile.id).exists():
                        return True, 'connection'
                    
                    # Network connection (2nd degree)
                    if self.visibility == 'network':
                        mutual_count = author_profile.top_connections.filter(
                            id__in=user_profile.top_connections.all()
                        ).count()
                        if mutual_count > 0:
                            return True, 'network'
                    
                except:
                    pass
            
            return False, 'access_denied'
        
        # Custom rules would be evaluated here
        return False, 'custom_rules'
    
    def increment_views(self):
        """Increment view count"""
        self.views += 1
        self.save(update_fields=['views'])
        self.calculate_engagement_score()

class ProfessionalArticle(models.Model):
    """Extended article model for long-form professional content"""
    
    # Reference to base content
    content = models.OneToOneField(
        ProfessionalContent,
        on_delete=models.CASCADE,
        related_name='article_details'
    )
    
    # Article-specific fields
    reading_time = models.PositiveIntegerField(help_text="Estimated reading time in minutes")
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('expert', 'Expert'),
        ],
        default='intermediate'
    )
    
    # SEO and Discovery
    seo_title = models.CharField(max_length=60, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)
    focus_keywords = models.JSONField(default=list, blank=True)
    
    # Publication Details
    publication_status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('published', 'Published'),
            ('archived', 'Archived'),
        ],
        default='published'
    )
    
    # Analytics
    read_through_rate = models.FloatField(default=0.0)
    bookmark_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'professional_articles'
        verbose_name = 'Professional Article'
        verbose_name_plural = 'Professional Articles'
        indexes = [
            models.Index(fields=['content', 'publication_status']),
            models.Index(fields=['difficulty_level']),
            models.Index(fields=['reading_time']),
        ]
    
    def __str__(self):
        return f"Article: {self.content.title}"

class ProfessionalAchievement(models.Model):
    """Professional achievements and certifications"""
    
    ACHIEVEMENT_TYPES = [
        ('certification', 'Certification'),
        ('award', 'Award'),
        ('milestone', 'Career Milestone'),
        ('recognition', 'Recognition'),
        ('publication', 'Publication'),
        ('patent', 'Patent'),
        ('speaking', 'Speaking Engagement'),
        ('conference', 'Conference Attendance'),
        ('course', 'Course Completion'),
        ('project', 'Project Completion'),
    ]
    
    VERIFICATION_STATUS = [
        ('unverified', 'Unverified'),
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    # Achievement Information
    profile = models.ForeignKey(
        'Profile',
        on_delete=models.CASCADE,
        related_name='achievements'
    )
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Issuer Details
    issuer_name = models.CharField(max_length=200)
    issuer_website = models.URLField(blank=True)
    issuer_logo = models.URLField(blank=True)
    
    # Date Information
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    
    # Verification
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='unverified')
    verification_code = models.CharField(max_length=100, blank=True)
    verification_url = models.URLField(blank=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_achievements'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Supporting Documents
    certificate_url = models.URLField(blank=True)
    supporting_documents = models.JSONField(default=list, blank=True)
    
    # Skills and Competencies
    skills_demonstrated = models.JSONField(default=list, blank=True)
    competency_level = models.CharField(
        max_length=20,
        choices=[
            ('basic', 'Basic'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('expert', 'Expert'),
        ],
        default='intermediate'
    )
    
    # Visibility and Display
    is_featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    show_on_profile = models.BooleanField(default=True)
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    endorsement_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'professional_achievements'
        verbose_name = 'Professional Achievement'
        verbose_name_plural = 'Professional Achievements'
        indexes = [
            models.Index(fields=['profile', 'achievement_type']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['is_featured', 'display_order']),
            models.Index(fields=['issue_date']),
            models.Index(fields=['expiry_date']),
        ]
        ordering = ['-display_order', '-issue_date']
    
    def __str__(self):
        return f"{self.get_achievement_type_display()}: {self.title}"
    
    def is_current(self):
        """Check if achievement is still valid"""
        if self.expiry_date:
            return timezone.now().date() <= self.expiry_date
        return True
    
    def verify_achievement(self, verified_by, verification_code):
        """Verify an achievement"""
        self.verification_status = 'verified'
        self.verification_code = verification_code
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.save(update_fields=[
            'verification_status', 'verification_code', 
            'verified_by', 'verified_at'
        ])

class ProfessionalProject(models.Model):
    """Professional projects and portfolio items"""
    
    PROJECT_TYPES = [
        ('work', 'Work Project'),
        ('personal', 'Personal Project'),
        ('open_source', 'Open Source'),
        ('freelance', 'Freelance Project'),
        ('academic', 'Academic Project'),
        ('startup', 'Startup Project'),
    ]
    
    PROJECT_STATUS = [
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
        ('archived', 'Archived'),
    ]
    
    # Project Information
    profile = models.ForeignKey(
        'Profile',
        on_delete=models.CASCADE,
        related_name='projects'
    )
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Timeline
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PROJECT_STATUS, default='completed')
    
    # Project Details
    role = models.CharField(max_length=100, help_text="Your role in the project")
    team_size = models.PositiveIntegerField(null=True, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Technologies and Skills
    technologies_used = models.JSONField(default=list, blank=True)
    skills_demonstrated = models.JSONField(default=list, blank=True)
    responsibilities = models.JSONField(default=list, blank=True)
    
    # Results and Impact
    key_achievements = models.JSONField(default=list, blank=True)
    metrics_and_results = models.JSONField(default=dict, blank=True)
    
    # Media and Documentation
    project_url = models.URLField(blank=True)
    repository_url = models.URLField(blank=True)
    demo_url = models.URLField(blank=True)
    documentation_url = models.URLField(blank=True)
    images = models.JSONField(default=list, blank=True)
    
    # Collaboration
    collaborators = models.ManyToManyField(
        User,
        related_name='collaborated_projects',
        blank=True
    )
    
    # Recognition
    awards = models.JSONField(default=list, blank=True)
    publications = models.JSONField(default=list, blank=True)
    patents = models.JSONField(default=list, blank=True)
    
    # Visibility and Display
    is_featured = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'professional_projects'
        verbose_name = 'Professional Project'
        verbose_name_plural = 'Professional Projects'
        indexes = [
            models.Index(fields=['profile', 'status']),
            models.Index(fields=['project_type']),
            models.Index(fields=['is_featured', 'display_order']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['is_public']),
        ]
        ordering = ['-display_order', '-start_date']
    
    def __str__(self):
        return f"Project: {self.title}"
    
    def get_duration_display(self):
        """Get human-readable project duration"""
        if self.end_date:
            duration = self.end_date - self.start_date
            days = duration.days
            months = days // 30
            years = months // 12
            
            if years > 0:
                remaining_months = months % 12
                return f"{years} yr {remaining_months} mos"
            else:
                return f"{months} mos"
        else:
            # Ongoing project
            duration = timezone.now().date() - self.start_date
            days = duration.days
            months = days // 30
            years = months // 12
            
            if years > 0:
                remaining_months = months % 12
                return f"{years} yr {remaining_months} mos (ongoing)"
            else:
                return f"{months} mos (ongoing)"

class ContentInteraction(models.Model):
    """Track user interactions with content"""
    
    INTERACTION_TYPES = [
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('share', 'Share'),
        ('bookmark', 'Bookmark'),
        ('view', 'View'),
        ('click', 'Link Click'),
    ]
    
    # Interaction Information
    content = models.ForeignKey(
        ProfessionalContent,
        on_delete=models.CASCADE,
        related_name='interactions'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='content_interactions'
    )
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    
    # Interaction Details
    comment_text = models.TextField(blank=True)
    comment_parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    # Metadata
    interaction_data = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    moderation_flags = models.PositiveIntegerField(default=0)
    moderated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_interactions'
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'content_interactions'
        verbose_name = 'Content Interaction'
        verbose_name_plural = 'Content Interactions'
        indexes = [
            models.Index(fields=['content', 'interaction_type', 'created_at']),
            models.Index(fields=['user', 'interaction_type', 'created_at']),
            models.Index(fields=['is_approved']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
        unique_together = ['content', 'user', 'interaction_type']
    
    def __str__(self):
        return f"{self.user.username} {self.interaction_type} {self.content.title}"
    
    def approve(self, moderator):
        """Approve the interaction"""
        self.is_approved = True
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        self.moderation_flags = 0
        self.save()
        
        # Update content engagement counts
        if self.interaction_type == 'like':
            self.content.likes += 1
        elif self.interaction_type == 'comment':
            self.content.comments_count += 1
        elif self.interaction_type == 'share':
            self.content.shares += 1
        
        self.content.save(update_fields=['likes', 'comments_count', 'shares'])
        self.content.calculate_engagement_score()
    
    def reject(self, moderator, reason):
        """Reject the interaction"""
        self.is_approved = False
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        self.interaction_data['rejection_reason'] = reason
        self.save()
    
    def flag(self):
        """Flag interaction for moderation"""
        self.moderation_flags += 1
        self.save(update_fields=['moderation_flags'])

class ContentModerationQueue(models.Model):
    """Queue for moderating content and interactions"""
    
    CONTENT_TYPES = [
        ('professional_content', 'Professional Content'),
        ('interaction', 'Content Interaction'),
        ('achievement', 'Achievement'),
        ('project', 'Project'),
    ]
    
    MODERATION_ACTIONS = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('request_changes', 'Request Changes'),
        ('escalate', 'Escalate'),
    ]
    
    # Content Reference
    content_type = models.CharField(max_length=30, choices=CONTENT_TYPES)
    content_id = models.PositiveIntegerField()
    
    # Generic foreign key to any content type
    content_type_model = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    content_object = GenericForeignKey('content_type_model', 'content_id')
    
    # Moderation Details
    moderation_type = models.CharField(max_length=50)
    reason = models.TextField()
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium'
    )
    
    # Reporter Information
    reporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reported_content'
    )
    reporter_reason = models.TextField(blank=True)
    
    # Review Information
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_moderations'
    )
    action_taken = models.CharField(max_length=20, choices=MODERATION_ACTIONS, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('in_review', 'In Review'),
            ('resolved', 'Resolved'),
            ('escalated', 'Escalated'),
        ],
        default='pending'
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'content_moderation_queue'
        verbose_name = 'Content Moderation Queue'
        verbose_name_plural = 'Content Moderation Queue'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['content_type', 'content_id']),
            models.Index(fields=['severity']),
            models.Index(fields=['reporter']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Moderation: {self.content_type} ID {self.content_id}"
    
    def approve(self, reviewer, notes=''):
        """Approve the content"""
        self.status = 'resolved'
        self.action_taken = 'approve'
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.resolved_at = timezone.now()
        self.save()
        
        # Update content approval status if applicable
        if self.content_type == 'professional_content':
            try:
                content = ProfessionalContent.objects.get(id=self.content_id)
                content.is_approved = True
                content.moderation_flags = 0
                content.save(update_fields=['is_approved', 'moderation_flags'])
            except ProfessionalContent.DoesNotExist:
                pass
    
    def reject(self, reviewer, notes=''):
        """Reject the content"""
        self.status = 'resolved'
        self.action_taken = 'reject'
        self.reviewed_by = reviewer
        self.review_notes = notes
        self.reviewed_at = timezone.now()
        self.resolved_at = timezone.now()
        self.save()
        
        # Update content approval status if applicable
        if self.content_type == 'professional_content':
            try:
                content = ProfessionalContent.objects.get(id=self.content_id)
                content.is_approved = False
                content.save(update_fields=['is_approved'])
            except ProfessionalContent.DoesNotExist:
                pass