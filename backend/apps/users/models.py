from django.db import models
from django.contrib.auth.models import User


class GitHubProfile(models.Model):
    """Profil GitHub lié à un utilisateur Django"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='github_profile')
    github_id = models.BigIntegerField(unique=True)
    github_login = models.CharField(max_length=255)  # nom d'utilisateur GitHub
    github_name = models.CharField(max_length=255, blank=True)
    github_email = models.CharField(max_length=255, blank=True)
    github_avatar_url = models.URLField(blank=True)
    github_access_token = models.TextField()  # token OAuth
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.github_login} ({self.user.username})"

    class Meta:
        verbose_name = "Profil GitHub"
        verbose_name_plural = "Profils GitHub"
