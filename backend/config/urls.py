from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('apps.users.urls')),
    path('api/projects/', include('apps.projects.urls')),
    path('api/scanner/', include('apps.scans.urls')),
    path('api/github-app/', include('integrations.github_app.urls')),
]
