# Architecture du Backend VulnOps

Ce document explique l'organisation du dossier `backend/` après sa restructuration modulaire. L'architecture suit les principes de séparation des responsabilités (separation of concerns) pour garantir la scalabilité et la maintenabilité.

## 📁 Structure Globale

Voici l'arborescence simplifiée et le rôle de chaque dossier :

### 1. `apps/` (Applications Django)
Contient le cœur métier découpé en modules Django indépendants.
*   **`users/`** : Gestion des utilisateurs, profils et authentification via GitHub OAuth.
*   **`projects/`** : Gestion des projets, des dépôts GitHub et de l'arborescence des fichiers.
*   **`scans/`** : Moteur principal de scan, modèles de résultats (`ScanResult`, `Vulnerability`) et historique.

### 2. `config/` (Configuration Globale)
Le "quartier général" de Django.
*   **`settings/`** : Paramètres du projet (Base, PostgreSQL, Celery).
*   **`urls.py`** : Routage principal de l'API.
*   **`celery.py`** : Configuration du worker pour les tâches asynchrones.

### 3. `services/` (Couche Métier)
Contient la logique complexe qui n'a pas sa place dans les vues (views.py).
*   **`scan_service.py`** : Gère le cycle de vie d'un scan (création, exécution, sauvegarde).
*   **`orchestrator_service.py`** : Coordonne l'exécution de multiples scanners sur un même projet.

### 4. `scanners/` (Exécuteurs d'Outils)
Regroupe les scripts (runners) qui pilotent les outils de sécurité externes.
*   **`sast/`** : Analyse statique de code (Bandit, Sonar, ESLint, Semgrep, etc.).
*   **`sca/`** : Analyse des dépendances (Trivy).
*   **`dast/`** : Analyse dynamique (OWASP ZAP).
*   **`base.py`** : Classe de base `BaseScanner` dont héritent tous les runners.

### 5. `rag/` (Intelligence Artificielle)
Couche d'intégration avec les modèles de langage (LLM).
*   **`rag_utils.py`** : Interface avec le système RAG externe pour les recommandations.
*   **`llm_scoring.py`** : Logique de priorité des vulnérabilités calculée par l'IA.

### 6. `core/` (Noyau Transversal)
Utilitaires et briques partagées par tout le backend.
*   **`utils/`** : Helpers pour Docker, Git (`repo_utils.py`) et l'analyse de structure projet.

### 7. `integrations/` (Connecteurs Externes)
Modules de communication avec des plateformes tierces.
*   **`defectdojo/`** : Code pour exporter les résultats vers une instance DefectDojo.

### 8. `tasks/` (Tâches Asynchrones)
Définitions des tâches Celery qui s'exécutent en arrière-plan (ex: `run_scan_task`).

### 9. `processor/` (Traitement des Données)
Normalisation et enrichment des résultats bruts avant leur enregistrement en base de données.

---

## 📄 Fichiers Clés à la Racine du Backend

*   **`manage.py`** : Outil en ligne de commande de Django (migrations, lancement du serveur).
*   **`.env`** : Fichier contenant vos secrets et configurations locales (clés API, DB).
*   **`.env.example`** : Modèle du fichier `.env` pour les autres développeurs.
*   **`requirements.txt`** : Liste de toutes les dépendances Python du projet.

> [!TIP]
> **Règle d'or de cette architecture :**
> Si vous voulez ajouter une nouvelle fonctionnalité, demandez-vous : 
> - Est-ce une route API ? -> `apps/*/views/`
> - Est-ce une logique métier ? -> `services/`
> - Est-ce un nouvel outil de scan ? -> `scanners/`
