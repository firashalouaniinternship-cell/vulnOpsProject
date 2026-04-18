"""
Tests pour l'authentification OAuth GitHub
Exécutez avec: python manage.py test apps.users.tests
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from apps.users.models import GitHubProfile


class GitHubAuthTests(APITestCase):
    """Tests pour le système d'authentification GitHub"""
    
    def setUp(self):
        self.client = Client()
        self.api_client = self.client
    
    def test_github_login_endpoint_exists(self):
        """Vérifier que l'endpoint de connexion GitHub existe"""
        response = self.client.get(reverse('github-login'))
        self.assertEqual(response.status_code, 200)
    
    def test_github_login_returns_auth_url(self):
        """Vérifier que l'endpoint retourne une URL d'authentification"""
        response = self.client.get(reverse('github-login'))
        self.assertIn('auth_url', response.json())
        auth_url = response.json()['auth_url']
        self.assertIn('github.com/login/oauth/authorize', auth_url)
    
    def test_me_endpoint_requires_authentication(self):
        """Vérifier que l'endpoint /me/ nécessite une authentification"""
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, 401)
    
    def test_me_endpoint_with_authenticated_user(self):
        """Vérifier que l'endpoint /me/ retourne les infos utilisateur"""
        # Créer un utilisateur
        user = User.objects.create_user(username='testuser', email='test@example.com')
        
        # Créer un profil GitHub
        github_profile = GitHubProfile.objects.create(
            user=user,
            github_id=12345,
            github_login='testuser',
            github_name='Test User',
            github_email='test@example.com',
            github_avatar_url='https://example.com/avatar.jpg',
            github_access_token='test_token'
        )
        
        # Se connecter
        self.client.force_login(user)
        
        # Vérifier /me/
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['github_login'], 'testuser')
    
    def test_logout_endpoint(self):
        """Vérifier que la disconnexion fonctionne"""
        # Créer et connecter un utilisateur
        user = User.objects.create_user(username='testuser')
        self.client.force_login(user)
        
        # Se déconnecter
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 200)
    
    def test_github_profile_creation(self):
        """Vérifier la création de profil GitHub"""
        user = User.objects.create_user(username='ghuser')
        
        profile = GitHubProfile.objects.create(
            user=user,
            github_id=999,
            github_login='ghuser',
            github_name='GitHub User',
            github_email='ghuser@example.com',
            github_avatar_url='https://avatars.githubusercontent.com/u/999',
            github_access_token='gho_token123'
        )
        
        self.assertEqual(profile.user.username, 'ghuser')
        self.assertEqual(profile.github_id, 999)
        self.assertEqual(profile.github_login, 'ghuser')
