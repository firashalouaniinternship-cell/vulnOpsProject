"""
Tests d'intégration pour l'authentification OAuth GitHub
Exécutez avec: python manage.py test apps.users.integration_tests
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch, MagicMock
import json

class GitHubOAuthIntegrationTests(TestCase):
    """Tests d'intégration pour le fluxe OAuth complète"""
    
    def setUp(self):
        self.client = Client()
    
    @patch('apps.users.views.requests.post')
    @patch('apps.users.views.requests.get')
    def test_complete_oauth_flow(self, mock_get, mock_post):
        """
        Test le fluxe OAuth complète:
        1. L'utilisateur clique "Se connecter"
        2. Reçoit l'URL OAuth
        3. GitHub renvoie un code
        4. On échange le code contre un token
        5. On récupère le profil utilisateur
        6. On crée/met à jour l'utilisateur
        7. On redirige vers le frontend
        """
        
        # Étape 1: Récupérer l'URL d'authentification
        response = self.client.get(reverse('github-login'))
        self.assertEqual(response.status_code, 200)
        auth_url = response.json().get('auth_url')
        self.assertIn('github.com/login/oauth/authorize', auth_url)
        self.assertIn('client_id=', auth_url)
        self.assertIn('redirect_uri=', auth_url)
        
        # Étape 2: Simuler le retour de GitHub
        # Mock la réponse du token
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            'access_token': 'gho_test_token_123',
            'scope': 'repo,user:email',
            'token_type': 'bearer'
        }
        mock_post.return_value = mock_token_response
        
        # Mock la réponse du profil utilisateur
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            'id': 99999,
            'login': 'testgithubuser',
            'name': 'Test GitHub User',
            'email': 'testgh@example.com',
            'avatar_url': 'https://avatars.githubusercontent.com/u/99999'
        }
        mock_get.return_value = mock_user_response
        
        # Étape 3: Appeler le callback avec un code
        response = self.client.get(
            reverse('github-callback'),
            {'code': 'abc123def456'}
        )
        
        # Vérifier la redirect vers le frontend
        self.assertEqual(response.status_code, 302)
        self.assertIn('/projects', response.url)
        
        # Vérifier que l'utilisateur a été créé
        self.assertTrue(User.objects.filter(username='testgithubuser').exists())
        
        # Vérifier que le profil GitHub a été créé
        user = User.objects.get(username='testgithubuser')
        self.assertTrue(hasattr(user, 'github_profile'))
        self.assertEqual(user.github_profile.github_id, 99999)
        self.assertEqual(user.github_profile.github_login, 'testgithubuser')
        self.assertEqual(user.github_profile.github_access_token, 'gho_test_token_123')
    
    @patch('apps.users.views.requests.post')
    @patch('apps.users.views.requests.get')
    def test_update_existing_user(self, mock_get, mock_post):
        """Test que les infos utilisateur sont mises à jour si l'utilisateur existe"""
        
        # Créer un utilisateur existant
        user = User.objects.create_user(
            username='existinguser',
            email='old@example.com'
        )
        from apps.users.models import GitHubProfile
        github_profile = GitHubProfile.objects.create(
            user=user,
            github_id=99999,
            github_login='testgithubuser',
            github_name='Old Name',
            github_email='old@github.com',
            github_avatar_url='https://old.example.com/avatar.jpg',
            github_access_token='old_token'
        )
        
        # Mock les réponses
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            'access_token': 'gho_new_token_456'
        }
        mock_post.return_value = mock_token_response
        
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            'id': 99999,  # Même ID
            'login': 'testgithubuser',
            'name': 'Updated Name',  # Nom changé
            'email': 'new@github.com',  # Email changé
            'avatar_url': 'https://new.example.com/avatar.jpg'
        }
        mock_get.return_value = mock_user_response
        
        # Appeler le callback
        response = self.client.get(
            reverse('github-callback'),
            {'code': 'abc123'}
        )
        
        # Vérifier que le profil a été mis à jour
        github_profile.refresh_from_db()
        self.assertEqual(github_profile.github_name, 'Updated Name')
        self.assertEqual(github_profile.github_email, 'new@github.com')
        self.assertEqual(github_profile.github_access_token, 'gho_new_token_456')
    
    def test_missing_code_parameter(self):
        """Test que l'absence de code retourne une erreur"""
        response = self.client.get(reverse('github-callback'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
    
    @patch('apps.users.views.requests.post')
    def test_token_exchange_failure(self, mock_post):
        """Test que les erreurs d'échange de token sont gérées"""
        
        # Mock une réponse d'erreur
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            'error': 'invalid_request',
            'error_description': 'The code passed is incorrect or expired.'
        }
        mock_post.return_value = mock_token_response
        
        # Appeler le callback
        response = self.client.get(
            reverse('github-callback'),
            {'code': 'invalid_code'}
        )
        
        # Vérifier l'erreur
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
    
    @patch('apps.users.views.requests.post')
    @patch('apps.users.views.requests.get')
    def test_github_profile_fetch_failure(self, mock_get, mock_post):
        """Test que les erreurs lors de la récupération du profil sont gérées"""
        
        # Mock le token
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            'access_token': 'valid_token'
        }
        mock_post.return_value = mock_token_response
        
        # Mock une erreur lors de la récupération du profil
        mock_user_response = MagicMock()
        mock_user_response.status_code = 401  # Unauthorized
        mock_get.return_value = mock_user_response
        
        # Appeler le callback
        response = self.client.get(
            reverse('github-callback'),
            {'code': 'valid_code'}
        )
        
        # Vérifier l'erreur
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
    
    def test_authenticated_user_can_access_me_endpoint(self):
        """Test que les utilisateurs authentifiés peuvent accéder à /me/"""
        
        # Créer un utilisateur connecté
        user = User.objects.create_user(username='testuser')
        from apps.users.models import GitHubProfile
        GithubProfile.objects.create(
            user=user,
            github_id=1,
            github_login='testuser',
            github_name='Test User',
            github_email='test@example.com',
            github_avatar_url='https://example.com/avatar.jpg',
            github_access_token='test_token'
        )
        
        # Connecter l'utilisateur
        self.client.force_login(user)
        
        # Accéder à /me/
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, 200)
        
        # Vérifier les données retournées
        data = response.json()
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['github_login'], 'testuser')
        self.assertEqual(data['github_name'], 'Test User')
    
    def test_unauthenticated_user_cannot_access_me_endpoint(self):
        """Test que les utilisateurs non authentifiés ne peuvent pas accéder à /me/"""
        response = self.client.get(reverse('me'))
        self.assertEqual(response.status_code, 401)
    
    def test_duplicate_username_handling(self):
        """Test que les noms d'utilisateur dupliqués sont gérés"""
        
        # Créer un utilisateur avec le même username
        User.objects.create_user(username='testgithubuser')
        
        from apps.users.models import GitHubProfile
        
        # Mock les réponses
        mock_post = MagicMock()
        mock_post.return_value.json.return_value = {
            'access_token': 'token'
        }
        
        mock_get = MagicMock()
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'id': 99999,
            'login': 'testgithubuser',  # Même que l'utilisateur existant
            'name': 'Test User',
            'email': 'test@github.com',
            'avatar_url': 'https://example.com/avatar.jpg'
        }
        
        with patch('apps.users.views.requests.post', mock_post):
            with patch('apps.users.views.requests.get', mock_get):
                response = self.client.get(
                    reverse('github-callback'),
                    {'code': 'abc123'}
                )
        
        # Vérifier que le nouvel utilisateur a un username différent
        new_user = User.objects.get(github_profile__github_id=99999)
        self.assertEqual(new_user.username, 'testgithubuser_1')
