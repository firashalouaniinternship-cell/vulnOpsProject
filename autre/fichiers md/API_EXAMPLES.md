"""
Exemples d'utilisation de l'API d'authentification GitHub OAuth
"""

# ============================================================================
# 1. EXEMPLE: Connecter un utilisateur via GitHub (Frontend)
# ============================================================================

import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true  // Important pour les sessions
});

// 1. Récupérer l'URL d'authentification GitHub
async function initiateGitHubLogin() {
  try {
    const response = await api.get('/accounts/github/login/');
    const { auth_url } = response.data;
    
    // Rediriger vers GitHub
    window.location.href = auth_url;
  } catch (error) {
    console.error('Erreur lors de la connexion:', error);
  }
}

// 2. Après retour de GitHub (callback automatique)
// Le backend redirige automatiquement vers /projects

// ============================================================================
// 2. EXEMPLE: Récupérer les informations de l'utilisateur connecté
// ============================================================================

async function getCurrentUser() {
  try {
    const response = await api.get('/accounts/me/');
    const user = response.data;
    
    console.log('Utilisateur connecté:', {
      id: user.id,
      username: user.username,
      github_login: user.github_login,
      github_name: user.github_name,
      github_email: user.github_email,
      github_avatar_url: user.github_avatar_url
    });
    
    return user;
  } catch (error) {
    if (error.response?.status === 401) {
      console.log('Utilisateur non connecté');
    }
  }
}

// ============================================================================
// 3. EXEMPLE: Déconnecter l'utilisateur
// ============================================================================

async function logoutUser() {
  try {
    const response = await api.post('/accounts/logout/');
    console.log('Utilisateur déconnecté:', response.data);
    
    // Rediriger vers la page de login
    window.location.href = '/';
  } catch (error) {
    console.error('Erreur lors de la déconnexion:', error);
  }
}

// ============================================================================
// 4. EXEMPLE: Hook React pour l'authentification
// ============================================================================

import { useState, useEffect } from 'react';

function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await api.get('/accounts/me/');
        setUser(response.data);
      } catch (err) {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, []);

  return { user, loading, error };
}

// Utilisation:
// const { user, loading } = useAuth();
// if (loading) return <div>Chargement...</div>;
// if (!user) return <div>Non connecté</div>;
// return <div>Bienvenue {user.github_name}</div>;

// ============================================================================
// 5. EXEMPLE: Requête authentifiée vers une autre API
// ============================================================================

async function fetchUserRepositories() {
  try {
    // Le token GitHub est stocké en base de données
    // Vous pouvez faire une requête vers votre backend
    // qui accédera aux repos via le GitHub API
    
    const response = await api.get('/projects/repos/');
    
    // Le backend utilise le token stocké pour:
    // 1. Récupérer la liste des repos de l'utilisateur
    // 2. Filtrer les repos accessibles
    // 3. Retourner les données au frontend
    
    return response.data;
  } catch (error) {
    console.error('Erreur lors de la récupération des repos:', error);
  }
}

// ============================================================================
// 6. EXEMPLE: Vérifier l'authentification au démarrage
// ============================================================================

function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuthentication = async () => {
      try {
        await api.get('/accounts/me/');
        setAuthenticated(true);
      } catch (error) {
        setAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuthentication();
  }, []);

  if (loading) {
    return <div>Chargement...</div>;
  }

  return authenticated ? <Dashboard /> : <LoginPage />;
}

// ============================================================================
# EXEMPLE BACKEND: Réception du callback OAuth
# ============================================================================

# Automatique via Django, mais voici le flux:

# 1. URL de callback: /api/accounts/github/callback/?code=abc123&state=xyz

# 2. Le backend reçoit:
#    - code: Code d'autorisation de GitHub
#    - state: Token de sécurité (CSRF)

# 3. Backend échange le code contre un token:
#    POST https://github.com/login/oauth/access_token
#    {
#      "client_id": "...",
#      "client_secret": "...",
#      "code": "abc123",
#      "redirect_uri": "http://localhost:8000/..."
#    }

# 4. GitHub retourne:
#    {
#      "access_token": "gho_xyz...",
#      "scope": "repo,user:email",
#      "token_type": "bearer"
#    }

# 5. Backend récupère le profil utilisateur:
#    GET https://api.github.com/user
#    Headers: Authorization: token gho_xyz...

# 6. GitHub retourne:
#    {
#      "id": 12345,
#      "login": "username",
#      "name": "Full Name",
#      "email": "user@example.com",
#      "avatar_url": "https://avatars.githubusercontent.com/...",
#      ...
#    }

# 7. Backend crée ou met à jour:
#    - User (djangouser)
#    - GitHubProfile (avec token stocké)

# 8. Backend crée une session Django
#    - Cookie de session = "sessionid=..."

# 9. Backend redirige vers le frontend
#    - Location: http://localhost:5173/projects

# 10. Le frontend a maintenant un cookie de session valide
#     - Toutes les requêtes API incluent ce cookie automatiquement

# ============================================================================
# EXEMPLE: Requête cURL pour tester l'API
# ============================================================================

# 1. Récupérer l'URL d'authentification
curl -X GET "http://localhost:8000/api/accounts/github/login/" \
  -H "Accept: application/json"

# Réponse:
# {
#   "auth_url": "https://github.com/login/oauth/authorize?client_id=...&redirect_uri=...&scope=repo,user:email"
# }

# 2. Récupérer les infos utilisateur (après connexion)
curl -b "sessionid=your_session_id" \
  "http://localhost:8000/api/accounts/me/" \
  -H "Accept: application/json"

# Réponse:
# {
#   "id": 1,
#   "username": "github_username",
#   "github_login": "github_username",
#   "github_name": "User's Full Name",
#   "github_email": "user@example.com",
#   "github_avatar_url": "https://avatars.githubusercontent.com/u/123/..."
# }

# 3. Se déconnecter
curl -X POST "http://localhost:8000/api/accounts/logout/" \
  -b "sessionid=your_session_id" \
  -H "Accept: application/json"

# ============================================================================
# CONFIGURATION REQUISE DANS .env
# ============================================================================

# GITHUB_CLIENT_ID=your_app_id_from_github
# GITHUB_CLIENT_SECRET=your_app_secret_from_github
# GITHUB_REDIRECT_URI=http://localhost:8000/api/accounts/github/callback/
# FRONTEND_URL=http://localhost:5173
# SECRET_KEY=a-very-long-and-random-secret-key
# DEBUG=True

# ============================================================================
# ERREURS COURANTES ET SOLUTIONS
# ============================================================================

# 1. Erreur: "CORS error"
#    Solution: Vérifier CORS_ALLOWED_ORIGINS dans settings.py
#    Vérifier que FRONTEND_URL est correct dans .env

# 2. Erreur: "OAuth credentials not configured"
#    Solution: Vérifier que GITHUB_CLIENT_ID et SECRET sont dans .env
#    Relancer le serveur Django

# 3. Erreur: "Redirect URI mismatch"
#    Solution: GITHUB_REDIRECT_URI dans .env doit matcher
#    celle configurée dans GitHub Developer Settings

# 4. Erreur: "Session not found"
#    Solution: Assurez-vous que withCredentials: true
#    est configuré dans le client axios

# 5. Erreur: "Unauthorized" (401)
#    Solution: L'utilisateur n'est pas connecté
#    Rediriger vers LoginPage
