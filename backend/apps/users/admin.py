from django.contrib import admin
from .models import GitHubProfile

@admin.register(GitHubProfile)
class GitHubProfileAdmin(admin.ModelAdmin):
    list_display = ['github_login', 'github_name', 'user', 'created_at']
    search_fields = ['github_login', 'github_name']
    readonly_fields = ['created_at', 'updated_at']
