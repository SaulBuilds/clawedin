from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "updated_at")
    search_fields = ("title", "author__username", "author__email")
