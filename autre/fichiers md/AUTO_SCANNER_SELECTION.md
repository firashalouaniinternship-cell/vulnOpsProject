# VulnOps Auto-Scanner Selection System

Documentation complète du système d'auto-détection et sélection automatique des scanners utilisant OpenRouter.

## Vue d'ensemble

Le système d'auto-sélection des scanners automatise les tâches suivantes :

1. **Détection de langages** : Analyse la structure du projet pour identifier les langages de programmation utilisés
2. **Détection de frameworks** : Identifie les frameworks et dépendances
3. **Sélection intelligente** : Utilise OpenRouter (LLM) pour choisir les scanners les plus appropriés
4. **Lancement automatique** : Lance les scans avec les outils recommandés sans intervention manuelle

## Architecture

### Composants

#### 1. ProjectAnalyzer (`project_analyzer.py`)
- Analyse un projet cloné localement
- Détecte les langages par extensions de fichiers et fichiers de configuration
- Détecte les frameworks en analysant les dépendances
- Retourne un rapport structuré

**Langages supportés** :
- Python (Django, Flask, FastAPI)
- JavaScript/TypeScript (React, Vue, Angular)
- Java (Spring)
- Kotlin
- Go
- Rust
- PHP (Laravel, Symfony)
- Ruby (Rails)
- C/C++

#### 2. OpenRouterSelector (`openrouter_selector.py`)
- Appelle l'API OpenRouter pour consulter un modèle LLM
- Fournit un contexte détaillé sur les scanners disponibles
- Demande au modèle de sélectionner les scanners optimaux
- Parse la réponse JSON structurée

**Scanners disponibles** :
- **Bandit** - Python security
- **ESLint** - JavaScript/TypeScript
- **SonarCloud** - Multi-language
- **Semgrep** - Pattern-based multi-language
- **Cppcheck** - C/C++
- **Gosec** - Go
- **Psalm** - PHP
- **Brakeman** - Ruby on Rails
- **Clippy** - Rust
- **Detekt** - Kotlin

#### 3. AutoScannerOrchestrator (`scanner_orchestrator.py`)
- Orchestre le flux complet d'auto-sélection
- Clone les repos GitHub
- Coordonne l'analyse et la sélection
- Gère les erreurs et fallbacks

### Flux d'exécution

```
User Request
    ↓
[GitHub Clone] → Clone du repo (shallow clone pour performance)
    ↓
[Project Analysis] → ProjectAnalyzer détecte langages/frameworks
    ↓
[LLM Selection] → OpenRouter choisit les meilleurs scanners
    ↓
[Scan Execution] → Lance les scanners s'électionnés
    ↓
[Store Results] → Sauvegarde les vulnérabilités en base
```

## Installation et Configuration

### 1. Installation des dépendances

Les dépendances requises sont déjà dans `requirements.txt`:
- `requests` - pour appeler l'API OpenRouter
- `GitPython` - pour clôner les repos
- `python-dotenv` - pour les variables d'environnement

Si vous n'aviez pas encore installé, faites :
```bash
pip install -r backend/requirements.txt
```

### 2. Configuration OpenRouter

1. **Créer un compte OpenRouter**
   - Allez sur https://openrouter.io/
   - Créez un compte
   - Obtenez votre clé API

2. **Définir les variables d'environnement**
   - Copiez `.env.example` en `.env` :
     ```bash
     cp .env.example .env
     ```
   - Remplissez `OPENROUTER_API_KEY` avec votre clé
   - (Optionnel) Changez `OPENROUTER_MODEL` selon vos préférences

3. **Modèles disponibles** (gratuit et payant)
   - `mistral/mistral-7b-instruct` - Gratuit et rapide (recommandé)
   - `mistral/mistral-medium` - Plus puissant
   - `openai/gpt-3.5-turbo` - ChatGPT 3.5
   - `openai/gpt-4` - ChatGPT 4 (le meilleur)
   - Plus de modèles disponibles sur le site OpenRouter

## Utilisation

### API Endpoints

#### 1. Auto-select Scanners (Recommandation sans lancer les scans)

**Endpoint** : `POST /api/scanner/auto-select/`

Détecte le projet et recommande les scanners sans les lancer.

**Request** :
```json
{
  "repo_full_name": "facebook/react",
  "clone_url": "https://github.com/facebook/react.git",
  "repo_name": "react",
  "repo_owner": "facebook"
}
```

**Response** :
```json
{
  "success": true,
  "repo_full_name": "facebook/react",
  "analysis": {
    "languages": ["typescript", "javascript"],
    "frameworks": {
      "typescript": [],
      "javascript": []
    },
    "file_counts": {
      "typescript": 245,
      "javascript": 89
    },
    "structure_summary": "Languages: javascript, typescript | Files: typescript: 245 files; javascript: 89 files"
  },
  "suggested_scanners": ["eslint", "semgrep"],
  "reasoning": "The project is primarily TypeScript/JavaScript, so ESLint is the best choice for linting and security checks. Semgrep adds pattern-based analysis.",
  "confidence": 0.89,
  "source": "openrouter",
  "message": "Auto-selected 2 scanner(s) for facebook/react"
}
```

#### 2. Auto-trigger Scans (Auto-détection + Lancement des scans)

**Endpoint** : `POST /api/scanner/auto-scan/`

Détecte le projet, sélectionne les scanners et les lance automatiquement.

**Request** :
```json
{
  "repo_full_name": "torvalds/linux",
  "clone_url": "https://github.com/torvalds/linux.git",
  "repo_name": "linux",
  "repo_owner": "torvalds"
}
```

**Response** :
```json
{
  "success": true,
  "repo_full_name": "torvalds/linux",
  "detection_source": "openrouter",
  "auto_selected_scanners": ["cppcheck", "semgrep"],
  "scan_results": [
    {
      "scanner": "cppcheck",
      "status": "COMPLETED",
      "metrics": {
        "total_issues": 42,
        "high_count": 5,
        "medium_count": 15,
        "low_count": 22
      },
      "scan_id": 123,
      "vulnerabilities_count": 42
    },
    {
      "scanner": "semgrep",
      "status": "COMPLETED",
      "metrics": {
        "total_issues": 18,
        "high_count": 2,
        "medium_count": 8,
        "low_count": 8
      },
      "scan_id": 124,
      "vulnerabilities_count": 18
    }
  ],
  "total_scans": 2,
  "message": "Auto-triggered 2 scan(s) for torvalds/linux"
}
```

#### 3. Analyze Existing Project

**Endpoint** : `POST /api/scanner/analyze/`

Analyse un projet existant sur le disque sans clôner.

**Request** :
```json
{
  "project_path": "/var/projects/myapp"
}
```

**Response** :
```json
{
  "success": true,
  "project_path": "/var/projects/myapp",
  "analysis": {
    "languages": ["python", "javascript"],
    "frameworks": {
      "python": ["django"]
    },
    "file_counts": {
      "python": 156,
      "javascript": 89
    },
    "structure_summary": "Languages: python, javascript | Frameworks: python: django | Files: python: 156 files; javascript: 89 files"
  },
  "suggested_scanners": ["bandit", "eslint"],
  "reasoning": "Django project detected - Bandit is required for Python security. ESLint for frontend JavaScript.",
  "confidence": 0.92,
  "source": "openrouter"
}
```

## Exemples d'utilisation avec cURL

### 1. Auto-détection sans scanner (recommandation)
```bash
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

### 2. Auto-détection + lancement des scans
```bash
curl -X POST http://localhost:8000/api/scanner/auto-scan/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_full_name": "rails/rails",
    "clone_url": "https://github.com/rails/rails.git",
    "repo_name": "rails",
    "repo_owner": "rails"
  }'
```

### 3. Analyse de projet existant
```bash
curl -X POST http://localhost:8000/api/scanner/analyze/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "/home/user/my-python-project"
  }'
```

## Options de Configuration

### Variables d'environnement (.env)

```env
# API Key for OpenRouter
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxx

# Model selection
OPENROUTER_MODEL=mistral/mistral-7b-instruct

# GitHub configuration
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
```

### Modèles OpenRouter recommandés par cas d'usage

**Pour performance** (gratuit/rapide):
- `mistral/mistral-7b-instruct`

**Performance équilibrée** (meilleur rapport qualité/prix):
- `mistral/mistral-medium`

**Meilleure qualité** (coût plus élevé):
- `openai/gpt-4`

## Gestion des erreurs et Fallback

Le système inclut une stratégie de fallback robuste :

1. **Si OpenRouter n'est pas accessible** → Utilise la sélection par défaut (logique métier)
2. **Si le clonage échoue** → Retourne une erreur avec scanners par défaut
3. **Si aucun langage détecté** → Recommande SonarCloud et Semgrep (multi-langages)
4. **Si un scanner échoue** → Continue avec les autres et rapporte les erreurs

## Performance et optimisations

- **Shallow clone** : Clône uniquement la branche par défaut, pas l'historique complet
- **Cache d'analyse** : Évite les ré-analyses identiques (à implémenter)
- **Timeout limité** : API calls avec timeout de 30 secondes
- **Parallélisation** : Les scans sont lancés séquentiellement mais peuvent être parallélisés

## Troubleshooting

### "OPENROUTER_API_KEY not set in environment variables"
- Vérifiez que `.env` existe et contient `OPENROUTER_API_KEY`
- Redémarrez Django après modification du `.env`

### "Failed to connect to OpenRouter"
- Vérifiez votre connexion internet
- Vérifiez que `OPENROUTER_API_KEY` est valide
- Consultez https://status.openrouter.io/

### "No languages detected"
- Le projet peut être vide
- Les fichiers peuvent être dans un dossier ignoré (`node_modules`, `.git`, etc.)
- Vérifiez que le clone s'est bien exécuté

### Scanners non-sélectionnés
- Vérifiez le `reasoning` retourné
- Consultez les logs Django pour plus de détails
- Essayez avec un modèle différent dans `OPENROUTER_MODEL`

## Logs et Debug

Activez les logs détaillés dans Django settings :

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'scanner': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

Puis consultez les logs pour voir :
- Langages détectés
- Frameworks détectés
- Prompt envoyé à OpenRouter
- Réponse du modèle
- Scanners sélectionnés

## Limitations actuelles

1. L'analyse du projet est faite en local - pour les très gros repos, cela peut être lent
2. La détection de framework est basée sur les dépendances - certains peuvent être manqués
3. Le modèle OpenRouter peut faire des choix différents selon le moment (température = 0.3)
4. Les scans sont lancés séquentiellement - peuvent être parallélisés pour plus de vitesse

## Améliorations futures

- [ ] Cacher les résultats d'analyse pour éviter les ré-analyses
- [ ] Paralléliser l'exécution des scans
- [ ] Support des webhooks pour déclencher les scans automatiquement
- [ ] Dashboard d'analytics sur les langages/frameworks les plus scanés
- [ ] Fine-tuning du modèle avec des données VulnOps

---

**Plus d'assistance** : Consultez les fichiers source en commentaires détaillés ou ouvrez une issue.
