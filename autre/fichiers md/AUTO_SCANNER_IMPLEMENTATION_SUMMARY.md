# Auto-Scanner Selection Implementation - Complete Summary

## 📋 Objectif

Implémenter un système d'auto-détection qui choisit automatiquement les outils de scanning appropriés selon les langages et frameworks du projet, en utilisant OpenRouter (un modèle LLM) pour la sélection intelligente.

## ✅ Implémentation Complète

### 1️⃣ Backend Python Modules

**Créé 3 modules Python principaux :**

#### `backend/scanner/project_analyzer.py`
- Classe `ProjectAnalyzer`: Analyse la structure d'un projet cloné
- Détecte les langages par extensions de fichiers
- Détecte les frameworks par dépendances
- Supporte 11 langages: Python, JS/TS, Java, Kotlin, Go, Rust, PHP, Ruby, C/C++

**Fonctionnalités:**
- `analyze()`: Analyse complète du projet
- `get_scan_candidates()`: Liste les scanners candidats
- Ignore les dossiers courants (node_modules, .git, __pycache__, etc.)

#### `backend/scanner/openrouter_selector.py`
- Classe `OpenRouterSelector`: Utilise OpenRouter API pour la sélection intelligente
- Envoie un prompt structuré au modèle LLM
- Parse la réponse JSON
- Fallback automatique si OpenRouter indisponible

**Modèles supportés:**
- mistral/mistral-7b-instruct (gratuit, recommandé)
- mistral/mistral-medium
- openai/gpt-3.5-turbo, openai/gpt-4 (payant)
- Et 50+ autres modèles OpenRouter

**Scanners gérés:**
All 10 scanners VulnOps: Bandit, ESLint, SonarCloud, Semgrep, Cppcheck, Gosec, Psalm, Brakeman, Clippy, Detekt

#### `backend/scanner/scanner_orchestrator.py`
- Classe `AutoScannerOrchestrator`: Orchestre le flux complet
- Clone les repos GitHub (shallow clone pour performance)
- Coordonne l'analyse et la sélection
- Gère les erreurs et fallbacks

**Méthodes principales:**
- `auto_select_scanners()`: Clone + analyse + sélection intelligente
- `analyze_existing_project()`: Analyse sans clôner
- `batch_analyze_projects()`: Analyse plusieurs projets

### 2️⃣ Nouveaux Endpoints API

**3 endpoints REST ajoutés à `views.py` :**

#### 1. `POST /api/scanner/auto-select/`
**Recommande les scanners sans les lancer**

Request:
```json
{
  "repo_full_name": "django/django",
  "clone_url": "https://github.com/django/django.git",
  "repo_name": "django",
  "repo_owner": "django"
}
```

Response:
```json
{
  "success": true,
  "analysis": {
    "languages": ["python"],
    "frameworks": {"python": ["django"]},
    "file_counts": {"python": 450},
    "structure_summary": "..."
  },
  "suggested_scanners": ["bandit", "semgrep"],
  "reasoning": "Django project requires Python security scanner...",
  "confidence": 0.92,
  "source": "openrouter"
}
```

#### 2. `POST /api/scanner/auto-scan/`
**Auto-détecte ET lance les scans automatiquement**

Même request que auto-select, retourne les résultats des scans:
```json
{
  "success": true,
  "auto_selected_scanners": ["bandit", "semgrep"],
  "scan_results": [
    {
      "scanner": "bandit",
      "status": "COMPLETED",
      "metrics": {"total_issues": 42, "high_count": 5},
      "scan_id": 123
    }
  ],
  "total_scans": 2
}
```

#### 3. `POST /api/scanner/analyze/`
**Analyse un projet existant sur le disque**

Request:
```json
{
  "project_path": "/var/projects/myapp"
}
```

Response: (même format que auto-select)

### 3️⃣ Configuration

**Fichiers créés/modifiés :**

- **`.env.example`** - Template pour configuration OpenRouter
- **`backend/scanner/urls.py`** - Ajout des 3 nouveaux endpoints
- **`backend/requirements.txt`** - (Dépendances déjà présentes)

**Variables d'environnement nécessaires:**
```env
OPENROUTER_API_KEY=sk-or-v1-xxxxx...
OPENROUTER_MODEL=mistral/mistral-7b-instruct
```

### 4️⃣ Frontend React/TypeScript

**2 fichiers créés:**

#### `frontend/src/hooks/useAutoScannerSelection.ts`
- Hook React réutilisable
- Exposes: `selectScanners()`, `autoScan()`, `analyzeProject()`
- Gestion du loading/error/progress
- Utilise Axios pour les appels API

#### `frontend/src/components/AutoScannerButton.tsx`
- Composant React complet
- UI avec analyse et recommandations
- Affiche langages, frameworks, confiance
- Boutons d'action avec résultats
- Styling complet en CSS-in-JS

**Utilisation dans un composant:**
```tsx
import { AutoScannerButton } from '@/components/AutoScannerButton';

<AutoScannerButton
  repoFullName="facebook/react"
  cloneUrl="https://github.com/facebook/react.git"
  repoName="react"
  repoOwner="facebook"
  variant="scan"
  onAutoScan={(results) => console.log(results)}
/>
```

### 5️⃣ Documentation et Tests

**Documentation créée:**

1. **`AUTO_SCANNER_SELECTION.md`** (15KB)
   - Architecture complète
   - Guide d'utilisation
   - Exemples cURL
   - Troubleshooting

2. **`QUICK_SETUP_AUTO_SCANNER.md`** (8KB)
   - Setup instruction étape par étape
   - Configuration OpenRouter
   - Commandes de test
   - Prochaines étapes

3. **`test_auto_scanner_selection.py`** (10KB)
   - Script test complet avec classe `VulnOpsClient`
   - 4 fonctions de test
   - Teste différents types de repos

4. **`backend/validate_auto_scanner_setup.py`** (8KB)
   - Validation de la configuration
   - Tests des imports
   - Tests de connexion OpenRouter
   - Diagnostic détaillé

## 🔄 Architecture du Flux

```
User Request
    ↓
[Auto-select Endpoint] ← GitHub repo URL
    ↓
[Git Clone] → Shallow clone (performance)
    ↓
[ProjectAnalyzer] → Détecte languages/frameworks
    ↓
[OpenRouterSelector] → Appelle LLM pour sélection intelligente
    ↓
[Response]
    └─ Success: Retourne scanners recommandés ✅
    └─ Error: Utilise fallback (règles par défaut) ⚙️
```

## 📊 Langages et Frameworks Supportés

| Langage | Frameworks | Scanner |
|---------|-----------|---------|
| Python | Django, Flask, FastAPI | Bandit |
| JavaScript/TypeScript | React, Vue, Angular | ESLint |
| Java | Spring | SonarCloud |
| Kotlin | Android | Detekt |
| Go | - | Gosec |
| Rust | - | Clippy |
| PHP | Laravel, Symfony | Psalm |
| Ruby | Rails | Brakeman |
| C++ | - | Cppcheck |
| C | - | Cppcheck |

## 🚀 Utilisation Rapide

### 1. Configuration (5 min)
```bash
# Obtenir clé OpenRouter
# https://openrouter.io → Sign up → Get API Key

# Configurer .env
cp .env.example .env
# Éditer .env avec votre OPENROUTER_API_KEY
```

### 2. Valider l'installation
```bash
cd backend
python validate_auto_scanner_setup.py
```

### 3. Démarrer le serveur
```bash
cd backend
python manage.py runserver
```

### 4. Tester via cURL
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

## 🗂️ Fichiers Modifiés/Créés

### Créés:
- ✅ `backend/scanner/project_analyzer.py` (200 lignes)
- ✅ `backend/scanner/openrouter_selector.py` (300 lignes)
- ✅ `backend/scanner/scanner_orchestrator.py` (250 lignes)
- ✅ `backend/validate_auto_scanner_setup.py` (200 lignes)
- ✅ `frontend/src/hooks/useAutoScannerSelection.ts` (150 lignes)
- ✅ `frontend/src/components/AutoScannerButton.tsx` (380 lignes)
- ✅ `test_auto_scanner_selection.py` (280 lignes)
- ✅ `AUTO_SCANNER_SELECTION.md` (comprehensive docs)
- ✅ `QUICK_SETUP_AUTO_SCANNER.md` (setup guide)
- ✅ `.env.example` (updated with OpenRouter config)

### Modifiés:
- ✅ `backend/scanner/views.py` (3 nouveaux endpoints + imports)
- ✅ `backend/scanner/urls.py` (3 nouvelles routes)

## 🛡️ Robustesse et Sécurité

✅ **Gestion d'erreurs complète:**
- Fallback si OpenRouter indisponible
- Gestion des erreurs de clonage
- Logs détaillés pour debug

✅ **Performance:**
- Shallow clone des repos
- Timeout 30s sur les appels API
- Ignore les gros dossiers (.git, node_modules)

✅ **Sécurité:**
- Token GitHub protégé
- Variables sensibles dans .env
- Validation des entrées

## 📈 Confiance et Qualité

Les résultats incluent:
- **Confiance**: 0.3-0.95 (basé sur le modèle ou règles)
- **Source**: "openrouter" ou "fallback"
- **Raisonnement**: Explication textuelle du choix

## 🔮 Améliorations Futures

- [ ] Cacher les résultats d'analyse
- [ ] Paralléliser l'exécution des scans
- [ ] Webhooks pour déclencheur auto
- [ ] Dashboard d'analytics
- [ ] Fine-tuning du modèle

## 📝 Notes Importantes

1. **OpenRouter est gratuit**: Le modèle Mistral 7B est gratuit
2. **Fallback automatique**: Si OpenRouter indisponible, utilise règles par défaut
3. **Shallow clone**: Pour performance (peut être changé)
4. **Langage agnostique**: Fonctionne avec n'importe quel langage supporté

## ✨ Résumé

Vous avez maintenant un système **complet et prêt à la production** qui:

1. ✅ Détecte automatiquement les langages/frameworks d'un projet
2. ✅ Utilise un LLM (OpenRouter) pour choisir intelligemment les scanners
3. ✅ Lance automatiquement les scans sans intervention manuelle
4. ✅ Inclut des fallbacks pour robustesse
5. ✅ A une API REST bien documentée
6. ✅ A des composants React réutilisables
7. ✅ Inclut des scripts de test et validation

**Prêt à utiliser!** 🚀
