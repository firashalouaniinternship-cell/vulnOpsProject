# Guide d'Installation Rapide - VulnOps

## Prérequis
- Python 3.8+
- Node.js 16+
- npm ou yarn
- Un compte GitHub

## 1. Configuration GitHub OAuth (5 minutes)

### Étape 1: Créer l'OAuth App
1. Allez sur https://github.com/settings/developers
2. Cliquez **"New OAuth App"**
3. Remplissez:
   - **Application name**: `VulnOps`
   - **Homepage URL**: `http://localhost:5173`
   - **Authorization callback URL**: `http://localhost:8000/api/accounts/github/callback/`

### Étape 2: Configurer le .env
```bash
# Créez/modifiez backend/.env
GITHUB_CLIENT_ID=votre_client_id
GITHUB_CLIENT_SECRET=votre_client_secret
GITHUB_REDIRECT_URI=http://localhost:8000/api/accounts/github/callback/
FRONTEND_URL=http://localhost:5173
SECRET_KEY=votre-clé-secrète-longue-et-complexe
DEBUG=True
```

## 2. Installation Backend (5 minutes)

```bash
cd backend

# Installer les dépendances
pip install -r requirements.txt

# Appliquer les migrations
python manage.py migrate

# Créer un utilisateur de test (optionnel)
python manage.py createsuperuser

# Lancer le serveur
python manage.py runserver
```

Le backend tourne sur `http://localhost:8000`

## 3. Installation Frontend (5 minutes)

```bash
cd frontend

# Installer les dépendances
npm install

# Lancer le serveur de développement
npm run dev
```

Le frontend tourne sur `http://localhost:5173`

## 4. Tester la connexion

1. Ouvrez `http://localhost:5173`
2. Cliquez **"Se connecter avec GitHub"**
3. Autorisez l'application GitHub
4. Vous serez redirigé vers l'application

## 5. Mode Démo (test sans GitHub)

Si vous n'avez pas GitHub configuré:

```bash
cd backend
python create_test_user.py  # Crée testuser/testpass
python manage.py runserver
```

Puis cliquez sur **"Mode Démo"** depuis la page de login.

## Dépannage Rapide

### Erreur "CORS"
```bash
# Vérifiez dans backend/.env:
FRONTEND_URL=http://localhost:5173
```

### Erreur "OAuth credentials not configured"
```bash
# Vérifiez que GITHUB_CLIENT_ID et SECRET sont dans .env
# Relancez le serveur: python manage.py runserver
```

### API ne répond pas
```bash
# Assurez-vous que le backend est lancé
cd backend
python manage.py runserver
```

## Endpoints clés

- `GET /api/accounts/github/login/` - Retourne l'URL OAuth
- `GET /api/accounts/github/callback/?code=...` - Callback OAuth
- `GET /api/accounts/me/` - Infos utilisateur (authentifié)
- `POST /api/accounts/logout/` - Déconnexion (authentifié)

## Questions/Problèmes?

Voir le fichier détaillé: `GITHUB_OAUTH_SETUP.md`
