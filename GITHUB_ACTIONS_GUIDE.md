# 🚀 Guide Complet : CI/CD avec GitHub Actions

Ce guide vous explique comment automatiser les tests, la sécurité et le déploiement de votre projet **VulnOps**.

## 1. Concepts de Base
GitHub Actions utilise des fichiers **YAML** situés dans `.github/workflows/`.
- **Workflow** : Le processus global (ex: "Pipeline de CI").
- **Event** : Ce qui déclenche le workflow (ex: `push`, `pull_request`).
- **Jobs** : Des groupes d'étapes qui s'exécutent sur un serveur (Runner).
- **Steps** : Les commandes individuelles (ex: `npm install`).

## 2. Structure de votre Pipeline
Puisque votre projet est un "Monorepo" (Frontend et Backend séparés), nous utilisons des jobs parallèles pour gagner du temps.

### A. Pipeline Frontend
- **Linting** : Vérifie que le code suit les règles de style (`eslint`).
- **Build** : Vérifie que le projet compile correctement avec Vite/TypeScript.
- **Tests** : (À ajouter) Vérifie la logique des composants.

### B. Pipeline Backend
- **Tests Django** : Exécute `python manage.py test`.
- **Flake8** : Vérifie la qualité du code Python.

### C. Pipeline Sécurité (DevSecOps)
- **SAST (Semgrep)** : Analyse statique du code pour trouver des failles.
- **SCA (npm audit)** : Vérifie les vulnérabilités dans vos dépendances.

## 3. Configuration des Secrets 🔒
Pour que le pipeline puisse communiquer avec votre backend ou d'autres services, vous devez configurer des **Secrets** sur GitHub :
1. Allez dans votre dépôt sur GitHub.
2. Cliquez sur **Settings** > **Secrets and variables** > **Actions**.
3. Ajoutez les secrets suivants :
   - `BACKEND_URL` : L'URL de votre API (ex: `https://api.votre-domaine.com`).
   - `API_TOKEN` : Le token d'authentification pour envoyer les rapports de scan.

## 4. Exemple de fichier Workflow
Voici à quoi ressemble un workflow complet qui gère tout en tenant compte de vos sous-répertoires :

```yaml
name: VulnOps CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  # --- JOB FRONTEND ---
  frontend-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'npm'
          cache-dependency-path: './frontend/package-lock.json'
      - name: Install dependencies
        run: npm ci
        working-directory: ./frontend
      - name: Lint
        run: npm run lint
        working-directory: ./frontend
      - name: Build
        run: npm run build
        working-directory: ./frontend

  # --- JOB BACKEND ---
  backend-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          cache: 'pip'
          cache-dependency-path: './backend/requirements.txt'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest flake8
        working-directory: ./backend
      - name: Lint
        run: flake8 .
        working-directory: ./backend
      - name: Run Tests
        run: python manage.py test
        working-directory: ./backend

  # --- JOB SÉCURITÉ ---
  security-scan:
    needs: [frontend-ci, backend-ci] # Attend que les tests de base passent
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Semgrep
        run: |
          pip install semgrep
          semgrep scan --json --config=auto --output=semgrep-report.json
      # ... (Envoi des résultats au backend) ...
```

## 5. Bonnes Pratiques
1. **Échouer tôt** : Si le Linting échoue, n'exécutez pas les tests lourds.
2. **Cacher les dépendances** : Utilisez les options de cache pour accélérer le pipeline.
3. **Protection de Branche** : Configurez GitHub pour interdire le "Merge" si le pipeline échoue.
