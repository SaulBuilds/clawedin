from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
import json

User = get_user_model()

class ProfileTemplate(models.TextChoices):
    """Professional profile templates with creative elements"""
    
    # Professional Foundation Templates
    EXECUTIVE_PRO = 'executive_pro', 'Executive Professional'
    TECH_INNOVATOR = 'tech_innovator', 'Tech Innovator'
    CREATIVE_DIRECTOR = 'creative_director', 'Creative Director'
    CONSULTANT_PRO = 'consultant_pro', 'Consultant Professional'
    ENTREPRENEUR = 'entrepreneur', 'Entrepreneur'
    
    # Creative Hybrid Templates
    ARTIST_PRO = 'artist_pro', 'Professional Artist'
    DESIGNER_PRO = 'designer_pro', 'Professional Designer'
    MUSICIAN_PRO = 'musician_pro', 'Professional Musician'
    WRITER_PRO = 'writer_pro', 'Professional Writer'
    PHOTOGRAPHER_PRO = 'photographer_pro', 'Professional Photographer'
    
    # Industry Specialized Templates
    HEALTHCARE_PRO = 'healthcare_pro', 'Healthcare Professional'
    LEGAL_PRO = 'legal_pro', 'Legal Professional'
    EDUCATION_PRO = 'education_pro', 'Education Professional'
    FINANCE_PRO = 'finance_pro', 'Finance Professional'
    MARKETING_PRO = 'marketing_pro', 'Marketing Professional'

class ProfileTheme(models.TextChoices):
    """Creative themes that maintain professional standards"""
    
    # Modern Professional Themes
    MINIMALIST_PRO = 'minimalist_pro', 'Minimalist Professional'
    DARK_PROFESSIONAL = 'dark_professional', 'Dark Professional'
    LIGHT_ACADEMIC = 'light_academic', 'Light Academic'
    CORPORATE_ELEGANT = 'corporate_elegant', 'Corporate Elegant'
    
    # Creative Professional Themes
    CREATIVE_STUDIO = 'creative_studio', 'Creative Studio'
    ARTISTIC_GALLERY = 'artistic_gallery', 'Artistic Gallery'
    MODERN_PORTFOLIO = 'modern_portfolio', 'Modern Portfolio'
    TECH_HUB = 'tech_hub', 'Tech Hub'
    
    # Dynamic Themes
    SEASONAL_PRO = 'seasonal_pro', 'Seasonal Professional'
    TRENDING_PRO = 'trending_pro', 'Trending Professional'

class Profile(models.Model):
    """Hybrid professional-creative profile with LinkedIn foundation and MySpace-style customization"""
    
    class Meta:
        app_label = 'clawedin'
    
    # Core Profile Information
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='clawedin_profile')
    headline = models.CharField(max_length=255, help_text="Professional headline/title")
    summary = models.TextField(
        max_length=3000,
        help_text="Professional summary with creative elements allowed"
    )
    
    # Professional Foundation (LinkedIn-style)
    current_company = models.CharField(max_length=200, blank=True)
    current_position = models.CharField(max_length=200, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    
    # Professional Experience Summary
    years_experience = models.PositiveIntegerField(default=0, help_text="Total years of professional experience")
    skills_list = models.JSONField(
        default=list,
        help_text="List of professional skills"
    )
    education_history = models.JSONField(
        default=list,
        help_text="Education history with degrees and institutions"
    )
    
    # Creative Elements (MySpace-style with professional boundaries)
    profile_template = models.CharField(
        max_length=50,
        choices=ProfileTemplate.choices,
        default=ProfileTemplate.EXECUTIVE_PRO,
        help_text="Professional template with creative elements"
    )
    profile_theme = models.CharField(
        max_length=50,
        choices=ProfileTheme.choices,
        default=ProfileTheme.MINIMALIST_PRO,
        help_text="Visual theme maintaining professional standards"
    )
    custom_css = models.TextField(
        blank=True,
        help_text="Custom CSS within professional guidelines",
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9\s\-\.\#\:;,\(\)\{\}\[\]\"\'\/\%\*]*$',
                message='CSS contains invalid characters'
            )
        ]
    )
    background_image_url = models.URLField(
        blank=True,
        help_text="Professional background image",
        validators=[
            RegexValidator(
                regex=r'^https?:\/\/.*\.(jpg|jpeg|png|gif|webp)$',
                message='Invalid image URL format'
            )
        ]
    )
    
    # Top 8 Professional Network (MySpace concept for business)
    top_connections = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='featured_in',
        blank=True,
        help_text="Top 8 professional connections"
    )
    
    # Professional Status
    is_open_to_work = models.BooleanField(default=False)
    is_available_for_consulting = models.BooleanField(default=False)
    networking_preferences = models.JSONField(
        default=dict,
        help_text="Networking preferences and settings"
    )
    
    # Social Media Links (Professional)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    
    # Profile Settings
    profile_visibility = models.CharField(
        max_length=20,
        choices=[
            ('public', 'Public'),
            ('connections', 'Connections Only'),
            ('private', 'Private')
        ],
        default='public'
    )
    show_contact_info = models.BooleanField(default=True)
    
    # Profile Analytics
    profile_views = models.PositiveIntegerField(default=0)
    last_profile_update = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profiles'
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['profile_template', 'profile_theme']),
            models.Index(fields=['is_open_to_work', 'profile_visibility']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.headline}"
    
    def get_full_profile_url(self):
        """Get full profile URL for sharing"""
        return f"/profile/{self.user.username}/"
    
    def get_top_connections_ordered(self):
        """Get top 8 connections ordered by relationship strength"""
        return self.top_connections.select_related('user').order_by('-updated_at')[:8]
    
    def add_top_connection(self, profile_user):
        """Add user to top connections (maintain max 8)"""
        if self.top_connections.count() >= 8:
            # Remove oldest connection
            oldest = self.top_connections.order_by('updated_at').first()
            self.top_connections.remove(oldest)
        self.top_connections.add(profile_user)
    
    def get_professional_summary(self):
        """Generate professional summary with creative elements"""
        experience_text = f"{self.years_experience}+ years" if self.years_experience > 0 else "Entry level"
        return f"{self.headline} • {experience_text} • {self.current_company or 'Independent'}"
    
    def validate_css_professional_standards(self, css_code):
        """Validate CSS meets professional standards"""
        disallowed_properties = [
            'position: fixed', 'position: absolute',
            'z-index', 'overflow', 'cursor: pointer',
            'animation', 'transition'
        ]
        
        css_lower = css_code.lower()
        for prop in disallowed_properties:
            if prop in css_lower:
                return False, f"Property '{prop}' not allowed in professional profiles"
        
        return True, "CSS meets professional standards"
    
    def clean(self):
        """Validate profile data"""
        if self.custom_css:
            is_valid, message = self.validate_css_professional_standards(self.custom_css)
            if not is_valid:
                from django.core.exceptions import ValidationError
                raise ValidationError({'custom_css': message})
        
        # Validate skills_list format
        if isinstance(self.skills_list, list):
            for skill in self.skills_list:
                if not isinstance(skill, str) or len(skill) > 50:
                    from django.core.exceptions import ValidationError
                    raise ValidationError({'skills_list': 'Each skill must be a string under 50 characters'})

class Experience(models.Model):
    """Professional experience with creative presentation options"""
    
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='experiences')
    
    # Professional Information
    company = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    
    # Timeline
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank for current position")
    is_current = models.BooleanField(default=False)
    
    # Description with Creative Elements
    description = models.TextField(
        max_length=2000,
        help_text="Professional description with creative presentation options"
    )
    achievements = models.JSONField(
        default=list,
        help_text="List of key achievements"
    )
    
    # Visual Enhancement Options
    company_logo_url = models.URLField(blank=True)
    project_images = models.JSONField(
        default=list,
        help_text="URLs to project/portfolio images"
    )
    
    # Skills Used
    skills_used = models.JSONField(
        default=list,
        help_text="Skills used in this role"
    )
    
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'experiences'
        verbose_name = 'Experience'
        verbose_name_plural = 'Experiences'
        ordering = ['-is_current', '-order', '-start_date']
        indexes = [
            models.Index(fields=['profile', 'is_current']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.position} at {self.company}"
    
    def get_duration_display(self):
        """Get human-readable duration"""
        if self.is_current or not self.end_date:
            from datetime import date
            duration = date.today() - self.start_date
            months = duration.days // 30
            years = months // 12
            remaining_months = months % 12
            
            if years > 0:
                return f"{years} yr {remaining_months} mos"
            else:
                return f"{months} mos"
        else:
            duration = self.end_date - self.start_date
            months = duration.days // 30
            years = months // 12
            remaining_months = months % 12
            
            if years > 0:
                return f"{years} yr {remaining_months} mos"
            else:
                return f"{months} mos"

class Education(models.Model):
    """Education with professional presentation"""
    
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='education')
    
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    
    gpa = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="GPA out of 4.0"
    )
    
    description = models.TextField(blank=True)
    achievements = models.JSONField(default=list, help_text="Academic achievements")
    
    institution_logo_url = models.URLField(blank=True)
    
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'education'
        verbose_name = 'Education'
        verbose_name_plural = 'Education'
        ordering = ['-is_current', '-order', '-start_date']
        indexes = [
            models.Index(fields=['profile', 'is_current']),
        ]
    
    def __str__(self):
        return f"{self.degree} from {self.institution}"

class Skill(models.Model):
    """Professional skills with endorsements"""
    
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='skills')
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, help_text="Skill category")
    proficiency_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
            ('expert', 'Expert')
        ],
        default='intermediate'
    )
    
    # Endorsements
    endorsements_count = models.PositiveIntegerField(default=0)
    endorsed_by = models.ManyToManyField(
        User,
        related_name='skill_endorsements',
        blank=True
    )
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_source = models.CharField(max_length=200, blank=True)
    
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'skills'
        verbose_name = 'Skill'
        verbose_name_plural = 'Skills'
        unique_together = ['profile', 'name']
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['profile', 'category']),
            models.Index(fields=['proficiency_level']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.proficiency_level})"

class ProfileTemplate(models.Model):
    """Predefined profile templates with professional-creative hybrid designs"""
    
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50)
    
    # Template Configuration
    template_type = models.CharField(
        max_length=20,
        choices=[
            ('professional', 'Professional'),
            ('creative', 'Creative'),
            ('hybrid', 'Hybrid')
        ],
        default='hybrid'
    )
    
    # Visual Design
    preview_image_url = models.URLField(blank=True)
    color_scheme = models.JSONField(default=dict, help_text="Color palette")
    layout_config = models.JSONField(default=dict, help_text="Layout configuration")
    
    # Template Content
    html_template = models.TextField(help_text="Jinja2 template for profile rendering")
    css_template = models.TextField(help_text="Base CSS for template")
    
    # Customization Options
    customization_options = models.JSONField(
        default=dict,
        help_text="Available customization options"
    )
    
    # Usage Tracking
    usage_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profile_templates'
        verbose_name = 'Profile Template'
        verbose_name_plural = 'Profile Templates'
        ordering = ['-is_featured', '-usage_count', 'display_name']
        indexes = [
            models.Index(fields=['template_type', 'is_active']),
            models.Index(fields=['category', 'is_featured']),
        ]
    
    def __str__(self):
        return self.display_name
    
    def increment_usage(self):
        """Increment template usage count"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
    
    def get_rendered_html(self, profile, customizations=None):
        """Render HTML template with profile data"""
        from django.template import engines
        from django.template.loader import get_template
        from django.template import Context
        
        # Prepare template context
        context_data = {
            'profile': profile,
            'template': self,
            'customizations': customizations or {},
        }
        
        # Create Jinja2 template
        jinja_env = engines['jinja2'].env
        template = jinja_env.from_string(self.html_template)
        
        return template.render(**context_data)
    
    def get_rendered_css(self, customizations=None):
        """Render CSS with customizations"""
        from django.template import engines
        
        # Create Jinja2 template
        jinja_env = engines['jinja2'].env
        template = jinja_env.from_string(self.css_template)
        
        return template.render(
            template=self,
            customizations=customizations or {},
        )

class ProfileTheme(models.Model):
    """Visual themes for profile customization"""
    
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Theme Configuration
    theme_type = models.CharField(
        max_length=20,
        choices=[
            ('professional', 'Professional'),
            ('creative', 'Creative'),
            ('seasonal', 'Seasonal')
        ],
        default='professional'
    )
    
    # Color Palette
    primary_color = models.CharField(max_length=7, default="#0073b6")  # LinkedIn blue
    secondary_color = models.CharField(max_length=7, default="#e74c3c")
    background_color = models.CharField(max_length=7, default="#ffffff")
    text_color = models.CharField(max_length=7, default="#333333")
    accent_color = models.CharField(max_length=7, default="#f39c12")
    
    # Typography
    font_family = models.CharField(max_length=100, default="Arial, sans-serif")
    heading_font = models.CharField(max_length=100, default="Arial, sans-serif")
    
    # Visual Elements
    border_radius = models.CharField(max_length=10, default="8px")
    shadow_style = models.CharField(max_length=50, default="0 2px 4px rgba(0,0,0,0.1)")
    
    # Theme CSS
    css_variables = models.JSONField(default=dict, help_text="CSS custom properties")
    full_css = models.TextField(help_text="Complete theme CSS")
    
    # Usage
    usage_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profile_themes'
        verbose_name = 'Profile Theme'
        verbose_name_plural = 'Profile Themes'
        ordering = ['-is_featured', '-usage_count', 'display_name']
        indexes = [
            models.Index(fields=['theme_type', 'is_active']),
        ]
    
    def __str__(self):
        return self.display_name
    
    def increment_usage(self):
        """Increment theme usage count"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
    
    def to_css_variables(self):
        """Convert theme to CSS custom properties"""
        return {
            '--primary-color': self.primary_color,
            '--secondary-color': self.secondary_color,
            '--background-color': self.background_color,
            '--text-color': self.text_color,
            '--accent-color': self.accent_color,
            '--font-family': self.font_family,
            '--heading-font': self.heading_font,
            '--border-radius': self.border_radius,
            '--shadow-style': self.shadow_style,
        }