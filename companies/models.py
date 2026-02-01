from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Company(models.Model):
    SIZE_CHOICES = [
        ("1-10", "1-10 employees"),
        ("11-50", "11-50 employees"),
        ("51-200", "51-200 employees"),
        ("201-500", "201-500 employees"),
        ("501-1000", "501-1,000 employees"),
        ("1001-5000", "1,001-5,000 employees"),
        ("5001-10000", "5,001-10,000 employees"),
        ("10000+", "10,000+ employees"),
    ]

    TYPE_CHOICES = [
        ("public", "Public company"),
        ("private", "Private company"),
        ("nonprofit", "Nonprofit"),
        ("government", "Government"),
        ("self_employed", "Self-employed"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=120, blank=True)
    company_type = models.CharField(max_length=20, choices=TYPE_CHOICES, blank=True)
    company_size = models.CharField(max_length=20, choices=SIZE_CHOICES, blank=True)
    headquarters = models.CharField(max_length=200, blank=True)
    founded_year = models.PositiveSmallIntegerField(null=True, blank=True)
    specialties = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    cover_url = models.URLField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="companies",
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
