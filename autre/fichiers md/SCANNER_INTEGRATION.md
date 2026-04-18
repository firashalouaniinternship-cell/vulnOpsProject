# Intégration des Scanners ESLint et Semgrep

## Vue d'ensemble
Le système VulnOps supporte maintenant **4 scanners** différents pour analyser les vulnérabilités dans les projets:

### Scanners disponibles

| Scanner | Technologie | Cas d'usage | Type |
|---------|-----------|----------|------|
| **Bandit** | Python | Détection de vulnérabilités en Python | SAST |
| **SonarCloud** | Multi-langage | Analyse qualité et sécurité (cloud) | SAST/QA |
| **ESLint** | JavaScript/TypeScript | Linting et détection d'erreurs JS/TS | Linting |
| **Semgrep** | Multi-langage | Patterns de sécurité OWASP Top 10 | SAST |

## Modifications du Backend

### Nouveaux fichiers créés

#### 1. [backend/scanner/eslint_runner.py](eslint_runner.py)
- Exécute ESLint sur un dépôt
- Parse la sortie JSON d'ESLint
- Convertit les résultats au format VulnOps
- **Dépendance CLI** : `eslint` (déjà installé v8.34.0)

#### 2. [backend/scanner/semgrep_runner.py](semgrep_runner.py)
- Exécute Semgrep avec config OWASP Top 10
- Parse la sortie JSON de Semgrep
- Convertit les résultats au format VulnOps
- **Dépendance** : `semgrep==1.45.0` (ajoutée à requirements.txt)

### Modifications existantes

#### [backend/scanner/views.py](views.py)
- Ajout des imports pour eslint_runner et semgrep_runner
- Mise à jour de `trigger_scan()` pour gérer les 4 scanners:
  - `scanner_type == 'eslint'` → appelle `run_full_eslint_scan()`
  - `scanner_type == 'semgrep'` → appelle `run_full_semgrep_scan()`
  - `scanner_type == 'sonarcloud'` → appelle `run_full_sonar_scan()`
  - `scanner_type == 'bandit'` → appelle `run_bandit_scan()` (défaut)

#### [backend/requirements.txt](requirements.txt)
```
+ semgrep==1.45.0
```

## Modifications du Frontend

### [frontend/src/pages/AnalysisPage.tsx](AnalysisPage.tsx)

1. **Type `ScannerType` mise à jour**:
   ```typescript
   type ScannerType = 'bandit' | 'sonarcloud' | 'eslint' | 'semgrep';
   ```

2. **Nouvel état `selectedScanner`**:
   - Valeur par défaut: `'sonarcloud'`
   - Permet la sélection parmi 4 scanners

3. **Interface de sélection** (2x2 grid):
   - Boutons avec descriptions (tooltips)
   - Styles adaptatifs selon sélection
   - Boutons désactivés pendant le scan

4. **Logique dynamique `scannerName`**:
   ```typescript
   'sonarcloud' → 'SonarCloud'
   'eslint' → 'ESLint'
   'semgrep' → 'Semgrep'
   'bandit' → 'Bandit'
   ```

5. **Historique des scans** affiche déjà le scanner utilisé:
   ```
   Scan #123 • ESLint • 07/04/2026 • 5 issues
   ```

## Flux d'utilisation

1. **Utilisateur accède à la page d'analyse** d'un dépôt
2. **Sélectionne un scanner** parmi les 4 options (interface 2x2)
3. **Clique sur "Analyser avec [Scanner]"**
4. **Backend**:
   - Clone le dépôt
   - Exécute le scanner sélectionné
   - Parse les résultats
   - Sauvegarde en base de données
5. **Frontend affiche les résultats** avec métriques et vulnerabilités
6. **Historique conserve le scanner utilisé** pour consultation future

## Formats de résultats standardisés

Tous les scanners retournent un objet uniforme:
```json
{
  "success": true,
  "vulnerabilities": [
    {
      "test_id": "rule_id",
      "test_name": "Scanner name",
      "issue_text": "Description",
      "severity": "HIGH|MEDIUM|LOW",
      "confidence": "HIGH",
      "filename": "path/to/file",
      "line_number": 42,
      "line_range": [42, 45],
      "code_snippet": "...",
      "cwe": "",
      "more_info": "link"
    }
  ],
  "metrics": {
    "total_issues": 10,
    "high_count": 2,
    "medium_count": 5,
    "low_count": 3,
    "files_analyzed": 15
  },
  "raw_output": "..."
}
```

## Vérification des dépendances

✅ **CLI Tools**:
- ESLint: v8.34.0 - Dans le PATH
- Semgrep: 1.157.0 - Installé

✅ **Python Packages**:
- semgrep==1.45.0 - Ajouté à requirements.txt

## Prochaines étapes

1. Tester chaque scanner avec un dépôt test
2. Valider le parsing des résultats
3. Vérifier l'interface de sélection (2x2 grid)
4. Monitorer les logs pour les erreurs

## Notes de développement

- ESLint nécessite que le dépôt cible soit un projet JS/TS
- Semgrep utilise la config `p/owasp-top-ten` (peut être étendue)
- Les timeouts sont configurés à 5-10 minutes par scanner
- Tous les répertoires temporaires sont nettoyés après le scan
