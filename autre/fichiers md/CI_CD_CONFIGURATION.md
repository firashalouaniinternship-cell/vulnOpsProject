# Configuration CI/CD pour l'Authentification GitHub OAuth

## GitHub Actions Example

Créez `.github/workflows/test-oauth.yml`:

```yaml
name: Test OAuth Authentication

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.8', '3.9', '3.10']

    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
    
    - name: Run migrations
      run: |
        cd backend
        python manage.py migrate
    
    - name: Run tests
      run: |
        cd backend
        python manage.py test accounts
    
    - name: Run integration tests
      run: |
        cd backend
        python manage.py test accounts.integration_tests
    
    - name: Check OAuth config
      run: |
        python check_oauth_config.py
```

## Configuration Environnement de Test

Pour les tests CI/CD, configurez les secrets GitHub:

1. Allez dans **Settings** → **Secrets and variables** → **Actions**
2. Ajoutez les secrets:
   - `GITHUB_CLIENT_ID`: ID de test
   - `GITHUB_CLIENT_SECRET`: Secret de test
   - `GITHUB_REDIRECT_URI`: http://localhost:8000/api/accounts/github/callback/

Utilisez les secrets dans le workflow:

```yaml
env:
  GITHUB_CLIENT_ID: ${{ secrets.GITHUB_CLIENT_ID }}
  GITHUB_CLIENT_SECRET: ${{ secrets.GITHUB_CLIENT_SECRET }}
  GITHUB_REDIRECT_URI: ${{ secrets.GITHUB_REDIRECT_URI }}
```

## GitLab CI Configuration

Créez `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - deploy

test_oauth:
  stage: test
  image: python:3.10
  services:
    - postgres:13
  before_script:
    - cd backend
    - pip install -r requirements.txt
  script:
    - python manage.py migrate
    - python manage.py test accounts
    - python manage.py test accounts.integration_tests
  variables:
    GITHUB_CLIENT_ID: $GITHUB_CLIENT_ID
    GITHUB_CLIENT_SECRET: $GITHUB_CLIENT_SECRET
    GITHUB_REDIRECT_URI: "http://localhost:8000/api/accounts/github/callback/"
    DATABASE_URL: "postgresql://postgres:postgres@postgres:5432/vulnops_test"
```

## Azure Pipelines Configuration

Créez `azure-pipelines.yml`:

```yaml
trigger:
  - main
  - develop

pool:
  vmImage: 'ubuntu-latest'

strategy:
  matrix:
    Python_38:
      python.version: '3.8'
    Python_39:
      python.version: '3.9'
    Python_310:
      python.version: '3.10'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '$(python.version)'
  displayName: 'Use Python $(python.version)'

- script: |
    cd backend
    pip install -r requirements.txt
  displayName: 'Install dependencies'

- script: |
    cd backend
    python manage.py migrate
  displayName: 'Run migrations'

- script: |
    cd backend
    python manage.py test accounts
    python manage.py test accounts.integration_tests
  displayName: 'Run tests'
  env:
    GITHUB_CLIENT_ID: $(GITHUB_CLIENT_ID)
    GITHUB_CLIENT_SECRET: $(GITHUB_CLIENT_SECRET)
```

## Checklist Pre-Deployment

- [ ] Tests unitaires passent: `python manage.py test accounts`
- [ ] Tests d'intégration passent: `python manage.py test accounts.integration_tests`
- [ ] Validation de config: `python check_oauth_config.py`
- [ ] Environnement de production configuré
- [ ] HTTPS activé (en production)
- [ ] Secrets non exposés dans repos
- [ ] Logs configurés
- [ ] Monitoring d'erreurs configuré (Sentry, etc.)

## Variables d'Environnement pour Production

```env
# Settings
DJANGO_SETTINGS_MODULE=vulnops.settings
PYTHONUNBUFFERED=1

# Security
SECRET_KEY=your-very-long-and-random-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# GitHub OAuth
GITHUB_CLIENT_ID=your_production_client_id
GITHUB_CLIENT_SECRET=your_production_client_secret
GITHUB_REDIRECT_URI=https://yourdomain.com/api/accounts/github/callback/

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Frontend
FRONTEND_URL=https://yourdomain.com

# CORS and CSRF
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com

# SSL/TLS
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## Monitoring et Alertes

Configurez les alertes pour:

- Taux d'erreur OAuth > 5%
- Temps de réponse OAuth > 5s
- Nombre d'utilisateurs uniques connectés chaque jour
- Tentatives d'authentification échouées

Exemple avec Sentry:

```python
# backend/vulnops/settings.py
import sentry_sdk

sentry_sdk.init(
    dsn="https://your-sentry-dsn@sentry.io/project-id",
    traces_sample_rate=1.0,
    environment='production'
)
```

## Logs et Debugging

Pour les logs en production, configurez:

```python
# backend/vulnops/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/vulnops/oauth.log',
        },
    },
    'loggers': {
        'accounts': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Checklists de Sécurité

### OAuth Tokens
- [ ] Tokens stockés chiffrés en base de données
- [ ] Tokens jamais loggés
- [ ] Tokens expirés après un délai raisonnable
- [ ] Refresh tokens implémentés
- [ ] Tokens révoqués à la déconnexion

### Cookies de Session
- [ ] SESSION_COOKIE_SECURE = True (production)
- [ ] SESSION_COOKIE_HTTPONLY = True
- [ ] SESSION_COOKIE_SAMESITE = 'Lax'
- [ ] SESSION_COOKIE_AGE = 86400 (24 heures)

### CSRF Protection
- [ ] CSRF tokens générés pour chaque session
- [ ] Tokens validés pour chaque POST/PUT/DELETE
- [ ] CSRF_TRUSTED_ORIGINS configurés correctement

### CORS
- [ ] CORS restreint aux domaines autorisés
- [ ] CORS_ALLOW_CREDENTIALS = True
- [ ] En-têtes CORS validés

## Performance

Optimisations OAuth:

1. **Cache les URLs d'authentification** (5 minutes)
2. **Cache les profils utilisateur** (1 heure)
3. **Limiter les appels à l'API GitHub** avec rate-limiting
4. **Connection pooling** pour les requêtes HTTP
5. **Compression GZIP** pour les réponses

Exemple avec caching:

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # 5 minutes
def github_login(request):
    # ...
```

## Disaster Recovery

Plan de récupération:

1. **Backup régulier** des utilisateurs et tokens
2. **Rate limiting** pour prévenir les abus
3. **Circuit break** si l'API GitHub est down
4. **Fallback** au mode démo si l'API GitHub est down
5. **Logs détaillés** pour audit et debugging

---

**Dernière mise à jour**: April 7, 2026
