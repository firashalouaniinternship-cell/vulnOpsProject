# Guide de Configuration Rapide - Auto-Scanner Selection

Guide étape par étape pour démarrer avec le système d'auto-sélection des scanners.

## Prerequisites

- Python 3.8+
- Django 4.2+
- Git
- OpenRouter API key (gratuit) - https://openrouter.io/

## Step 1: Installation

### 1.1 Clôner le projet (si pas encore fait)
```bash
git clone https://github.com/yourrepo/vulnops.git
cd vulnops
```

### 1.2 Installer les dépendances Python
```bash
cd backend
pip install -r requirements.txt
```

### 1.3 Créer ou mettre à jour le fichier .env
```bash
# Copier le fichier d'exemple
cp ../.env.example ../.env

# Éditer .env et ajouter votre clé OpenRouter
# OPENROUTER_API_KEY=sk-or-v1-xxxxx...
```

### 1.4 Vérifier que les modules sont importés correctement
```bash
python manage.py shell
>>> from scanner.scanner_orchestrator import AutoScannerOrchestrator
>>> from scanner.project_analyzer import ProjectAnalyzer
>>> from scanner.openrouter_selector import OpenRouterSelector
>>> print("✓ Tous les modules chargés correctement")
```

## Step 2: Configuration OpenRouter

### 2.1 Créer un compte OpenRouter
1. Allez sur https://openrouter.io/
2. Cliquez sur "Sign Up"
3. Créez un compte

### 2.2 Obtenir votre API Key
1. Allez dans https://openrouter.io/keys
2. Cliquez sur "Create Key"
3. Copiez la clé générée

### 2.3 Configurer dans .env
```bash
# Dans backend/.env ou à la racine du projet
OPENROUTER_API_KEY=sk-or-v1-votre_cle_ici

# Optionnel - choisir le modèle
OPENROUTER_MODEL=mistral/mistral-7b-instruct
```

### 2.4 Tester la configuration (optionnel)
```bash
cd backend
python manage.py shell
```

```python
from scanner.openrouter_selector import OpenRouterSelector
import os

# Vérifier que la clé est chargée
api_key = os.getenv('OPENROUTER_API_KEY')
print(f"API Key set: {bool(api_key)}")
print(f"API Key (masked): {api_key[:20]}..." if api_key else "No API key")

# Tester un appel
selector = OpenRouterSelector()
result = selector.suggest_scanners(
    languages=['python', 'javascript'],
    frameworks={'python': ['django']},
    file_counts={'python': 100, 'javascript': 50},
    structure_summary="Django + React project"
)

print("\nAPI Response:")
print(result)
```

## Step 3: Démarrer le serveur Django

```bash
cd backend
python manage.py runserver
```

Vous devriez voir :
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

## Step 4: Tester l'API

### Via cURL

```bash
# 1. D'abord, obtenir un token d'authentification
# (créer un compte utilisateur dans l'admin si nécessaire)

# 2. Tester auto-select (scanner recommendation)
curl -X POST http://localhost:8000/api/scanner/auto-select/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_full_name": "django/django",
    "clone_url": "https://github.com/django/django.git",
    "repo_name": "django",
    "repo_owner": "django"
  }'
```

### Via Python script
```bash
cd /path/to/project
python test_auto_scanner_selection.py
```

(Éditez le script pour remplacer `YOUR_AUTH_TOKEN` par un token réel)

### Avant de lancer les tests

Vous avez besoin d'un token d'authentification. Voici comment l'obtenir :

```bash
cd backend

# Créer un superuser s'il n'existe pas
python manage.py createsuperuser

# Générer un token pour l'utilisateur
python manage.py shell
```

```python
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User

user = User.objects.get(username='your_username')  # Remplacez par votre username
token = Token.objects.get(user=user)
print(f"Token: {token.key}")
```

## Step 5: Intégration Frontend

Le système devrait être prêt à être utilisé depuis le frontend.

Les nouveaux endpoints d'API disponibles:

- `POST /api/scanner/auto-select/` - Recommander des scanners
- `POST /api/scanner/auto-scan/` - auto-détecter et lancer les scans
- `POST /api/scanner/analyze/` - Analyser un projet existant

Mettez à jour votre frontend React/TypeScript pour appeler ces endpoints.

## Modèles OpenRouter disponibles

### Gratuit/Performant
- `mistral/mistral-7b-instruct` - recommandé pour commencer

### Équilibré
- `mistral/mistral-medium`
- `meta-llama/llama-2-70b-chat`

### Haute qualité (payant)
- `openai/gpt-3.5-turbo`
- `openai/gpt-4` - meilleur mais plus coûteux

Changez le modèle en editant `OPENROUTER_MODEL` dans `.env`.

## Commandes útiles

### Créer un test user avec token
```bash
cd backend

python manage.py shell
```

```python
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

# Créer un utilisateur
user = User.objects.create_user('testuser', 'test@example.com', 'testpass')

# Générer un token
token, created = Token.objects.get_or_create(user=user)
print(f"Token: {token.key}")
```

### Tester l'API avec le token
```bash
TOKEN=your_token_from_above

curl -X POST http://localhost:8000/api/scanner/auto-select/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_full_name": "torvalds/linux",
    "clone_url": "https://github.com/torvalds/linux.git",
    "repo_name": "linux",
    "repo_owner": "torvalds"
  }' | python -m json.tool
```

### Voir les logs Django
```bash
# Terminal 1 - Django server avec logs verbeux
cd backend
DJANGO_LOG_LEVEL=DEBUG python manage.py runserver
```

## Troubleshooting

### Error: "OPENROUTER_API_KEY not set"
- Vérifiez que `.env` existe
- Vérifiez que la variable est correctement définie
- Redémarrez Django après modification du `.env`

### Error: "Failed to clone repository"
- Vérifiez que Git est installé
- Vérifiez que l'URL du repo est correcte
- Vérifiez votre connexion internet

### Error: "OpenRouter connection timeout"
- Vérifiez votre connexion internet
- Vérifiez que `OPENROUTER_API_KEY` est valide
- Essayez avec un modèle différent

### Error: "No languages detected"
- Le repo peut être vide
- Les fichiers source peuvent être dans un sous-dossier

## Documentation complète

Pour une documentation plus détaillée, consultez :
- [AUTO_SCANNER_SELECTION.md](AUTO_SCANNER_SELECTION.md) - Architecture et utilisation complète
- [backend/scanner/project_analyzer.py](backend/scanner/project_analyzer.py) - Code source commenté
- [backend/scanner/openrouter_selector.py](backend/scanner/openrouter_selector.py) - Code source commenté

## Prochaines étapes

1. ✅ Configuration de base terminée
2. 📝 Intégrer auto-select dans le frontend
3. 🚀 Déployer en production
4. 📊 Monitor et optimiser les sélections

## Support

Pour toute question :
1. Consultez les logs Django
2. Consultez la documentation complète
3. Ouvrez une issue sur GitHub
4. Contactez l'équipe de support

---

**Last updated**: 2024
**Version**: 1.0