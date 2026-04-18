# Configuration GitHub OAuth pour VulnOps

Ce guide explique comment configurer l'authentification GitHub OAuth pour l'application VulnOps.

## Étapes de configuration

### 1. Créer une OAuth App sur GitHub

1. Allez sur [GitHub Developer Settings](https://github.com/settings/developers)
2. Cliquez sur **"New OAuth App"**
3. Remplissez les informations suivantes :
   - **Application name**: `VulnOps` (ou le nom que vous préférez)
   - **Homepage URL**: `http://localhost:5173`
   - **Authorization callback URL**: `http://localhost:8000/api/accounts/github/callback/`
   - **Application description**: `Application SAST pour analyser la sécurité des dépôts GitHub`

4. Cliquez sur **"Register application"**

### 2. Récupérer les credentials

Une fois l'application créée, vous verrez :
- **Client ID**: Une chaîne alphanumérique
- **Client Secret**: Un secret à générer en cliquant sur "Generate a new client secret"

### 3. Configurer le fichier .env

Dans le dossier `backend/`, modifiez le fichier `.env` :

```env
# GitHub OAuth - Créer sur https://github.com/settings/developers
GITHUB_CLIENT_ID=votre_client_id_ici
GITHUB_CLIENT_SECRET=votre_client_secret_ici
GITHUB_REDIRECT_URI=http://localhost:8000/api/accounts/github/callback/

# Django
SECRET_KEY=change-moi-par-une-cle-secrete-tres-longue-et-aleatoire
DEBUG=True

# Frontend URL
FRONTEND_URL=http://localhost:5173
```

Remplacez `votre_client_id_ici` et `votre_client_secret_ici` par les valeurs reçues de GitHub.

### 4. Démarrer les serveurs

#### Backend (Django)
```bash
cd backend
python manage.py runserver
```

#### Frontend (React/Vite)
```bash
cd frontend
npm install
npm run dev
```

### 5. Tester la connexion

1. Ouvrez `http://localhost:5173`
2. Cliquez sur **"Se connecter avec GitHub"**
3. Vous serez redirigé vers GitHub pour autoriser l'application
4. Après autorisation, vous serez redirigé vers votre compte dans VulnOps

## Scopes demandés

L'application demande les scopes suivants :
- `repo`: Accès aux dépôts
- `user:email`: Accès à l'email de l'utilisateur

## Mode Démo (développement)

Si vous n'avez pas configuré les credentials GitHub, vous pouvez utiliser le **Mode Démo** pour tester :
1. Cliquez sur **"Accéder au Mode Démo (Test)"**
2. Un utilisateur de test sera créé automatiquement

Pour utiliser le mode démo, assurez-vous que :
- `DEBUG=True` dans `.env`
- Le script `create_test_user.py` a été exécuté

```bash
cd backend
python create_test_user.py
```

## Dépannage

### Erreur "GitHub OAuth credentials not configured"
- Vérifiez que `GITHUB_CLIENT_ID` et `GITHUB_CLIENT_SECRET` sont configurés dans `.env`
- Assurez-vous d'avoir relancé le serveur Django après la modification de `.env`

### Erreur "Invalid callback URL"
- Vérifiez que `GITHUB_REDIRECT_URI` dans `.env` correspond exactement à celui configuré sur GitHub
- Par défaut : `http://localhost:8000/api/accounts/github/callback/`

### Erreur "CORS"
- Assurez-vous que `FRONTEND_URL` dans `.env` est correct
- Vérifiez que `CORS_ALLOWED_ORIGINS` dans `settings.py` inclut votre URL frontend

## Structure de l'authentification

### Backend (Django)
- **Endpoint de connexion**: `GET /api/accounts/github/login/`
  - Retourne l'URL d'authentification GitHub
- **Callback OAuth**: `GET /api/accounts/github/callback/?code=...`
  - Reçoit le code de GitHub
  - Échange contre un token d'accès
  - Crée ou met à jour l'utilisateur
  - Redirige vers le frontend

- **Info utilisateur**: `GET /api/accounts/me/` (authentifié)
  - Retourne les informations de l'utilisateur connecté
- **Déconnexion**: `POST /api/accounts/logout/` (authentifié)
  - Déconnecte l'utilisateur

### Frontend (React)
- Page de connexion: `src/pages/LoginPage.tsx`
- Client API: `src/api/client.ts`

## Modèle de données

### GitHubProfile
Stocke les informations du profil GitHub :
- `github_id`: ID unique GitHub
- `github_login`: Nom d'utilisateur GitHub
- `github_name`: Nom complet
- `github_email`: Email GitHub
- `github_avatar_url`: URL de l'avatar
- `github_access_token`: Token d'accès OAuth
- `user`: Lien vers l'utilisateur Django

## Sécurité

- Les tokens d'accès sont stockés en base de données (chiffrez-les en production)
- Les sessions sont configurées avec `SESSION_COOKIE_AGE = 86400` (24 heures)
- CSRF est activé et configuré pour accepter les origines de confiance
- CORS est restreint aux URL autorisées

## Production

Pour déployer en production :

1. **Changez `DEBUG=False`** dans `.env`
2. **Générez une nouvelle `SECRET_KEY`** complexe
3. **Configurez HTTPS** et mettez à jour les URLs de redirection
4. **Utilisez les variables d'environnement** pour les secrets (ne pas les commiter)
5. **Chiffrez les tokens d'accès** en base de données
6. **Configurez les CSRF et CORS** pour les domaines de production
