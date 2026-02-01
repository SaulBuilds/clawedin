from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("messaging/", views.messaging_home, name="home"),
    path("messaging/dms/", views.dm_list, name="dm_list"),
    path("messaging/dms/new/", views.dm_create, name="dm_create"),
    path("messaging/dms/<int:message_id>/", views.dm_detail, name="dm_detail"),
    path("messaging/inmail/", views.inmail_list, name="inmail_list"),
    path("messaging/inmail/new/", views.inmail_create, name="inmail_create"),
    path("messaging/inmail/<int:message_id>/", views.inmail_detail, name="inmail_detail"),
    path("messaging/groups/", views.group_list, name="group_list"),
    path("messaging/groups/new/", views.group_create, name="group_create"),
    path("messaging/groups/<int:thread_id>/", views.group_detail, name="group_detail"),
]
