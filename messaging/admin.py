from django.contrib import admin

from .models import DirectMessage, GroupMessage, GroupThread, InMail


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "sender", "recipient", "created_at")
    search_fields = ("subject", "body", "sender__username", "recipient__username")


@admin.register(InMail)
class InMailAdmin(admin.ModelAdmin):
    list_display = ("subject", "sender", "recipient", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("subject", "body", "sender__username", "recipient__username")


@admin.register(GroupThread)
class GroupThreadAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at")
    search_fields = ("name",)
    filter_horizontal = ("members",)


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sender", "created_at")
    search_fields = ("body", "sender__username", "thread__name")
