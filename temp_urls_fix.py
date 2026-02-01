
# Add import at the top
from django.urls import path, include

# Add to the end of urlpatterns
urlpatterns += [
    path('api/profiles/', include('clawedin.urls')),
]

# Save and run server

