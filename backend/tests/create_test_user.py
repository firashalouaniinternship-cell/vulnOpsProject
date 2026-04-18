import sys
import os
import django
from pathlib import Path

# Add the backend root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Configuration de l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.users.models import GitHubProfile

def create_mock_user():
    username = "testuser"
    if User.objects.filter(username=username).exists():
        print(f"L'utilisateur {username} existe déjà.")
        user = User.objects.get(username=username)
    else:
        user = User.objects.create_user(
            username=username,
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User"
        )
        print(f"Utilisateur {username} créé.")

    # Création ou mise à jour du profil GitHub
    profile, created = GitHubProfile.objects.update_or_create(
        user=user,
        defaults={
            'github_id': 1234567,
            'github_login': "testgithub",
            'github_name': "Test GitHub User",
            'github_email': "test@example.com",
            'github_avatar_url': "https://avatars.githubusercontent.com/u/1?v=4",
            'github_access_token': "mock_access_token"
        }
    )
    
    if created:
        print("Profil GitHub créé pour l'utilisateur.")
    else:
        print("Profil GitHub mis à jour.")

if __name__ == "__main__":
    create_mock_user()
