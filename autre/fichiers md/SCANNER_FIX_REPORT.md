# Fix pour les erreurs 500 des scanners ESLint et Semgrep

## Problèmes identifiés et corrigés

### 1. **Semgrep utilise un modèle de subcommandes** ✓
**Problème**: Semgrep ne s'exécute pas directement - il nécessite la commande `semgrep scan`
**Solution**: Mise à jour de `semgrep_runner.py` pour utiliser le subcommand correct

```bash
# Avant (incorrect):
semgrep --json --config=p/owasp-top-ten <path>

# Après (correct):
semgrep scan --json --config=p/owasp-top-ten <path>
```

### 2. **Gestion des erreurs et timeouts** ✓
**Problème**: Les erreurs des scanners n'étaient pas bien gérées, les timeouts n'étaient pas configurés
**Solution**: Ajout de try/except robustes et timeouts appropriés:
- ESLint: 5 minutes timeout
- Semgrep: 10 minutes timeout

### 3. **Parsing des résultats robuste** ✓
**Problème**: Les fonctions `parse_eslint_results` et `parse_semgrep_results` ne géraient pas tous les formats de sortie
**Solution**: Amélioration de la gestion des structures de données pour éviter les KeyError

### 4. **Logging des exceptions** ✓
**Problème**: Les exceptions n'étaient pas loggées, rendant le débogage difficile
**Solution**: Ajout de `traceback` logging dans les espaces try/except

## Fichiers modifiés

### [backend/scanner/eslint_runner.py](eslint_runner.py)
- Meilleure gestion des exceptions dans `run_eslint()`
- Amélioration du parsing dans `parse_eslint_results()` 
- Logging détaillé des erreurs dans `run_full_eslint_scan()`

### [backend/scanner/semgrep_runner.py](semgrep_runner.py)
- Correction du subcommand: ajout de `'scan'` dans la liste des arguments
- Meilleure gestion des timeouts et erreurs
- Logging détaillé des exceptions

### [backend/scanner/views.py](views.py)
- Support pour les 4 scanners: bandit, sonarcloud, eslint, semgrep
- Logging amélioré des opérations de scan

## Comportement attendu après les corrections

### Cas 1: Scan réussi
```
POST /api/scanner/scan/
→ 200 OK avec résultats
{
  "scan_id": 123,
  "status": "COMPLETED",
  "metrics": { "total_issues": 5, ... },
  "vulnerabilities": [...]
}
```

### Cas 2: Erreur lors du scan (outil non installé, timeout, etc.)
```
POST /api/scanner/scan/
→ 500 Internal Server Error
{
  "error": "Description claire de l'erreur",
  "scan_id": 123
}
```

Le scan sera marqué comme FAILED en base de données avec le message d'erreur.

## Points importants

### ESLint
- ✅ Analyse les fichiers JavaScript et TypeScript
- ⚠️ Peut nécessiter une configuration ESLint dans le projet (.eslintrc.js, etc.)
- ⚠️ Peut nécessiter l'installation des dépendances npm du projet
- Timeout: 5 minutes

### Semgrep
- ✅ Analyse multi-langage avec config OWASP Top 10
- ✅ Pas de dépendances du projet nécessaires
- ⚠️ Nécessite de bonnes ressources (peut être lent sur gros repos)
- Timeout: 10 minutes

### Bandit
- ✅ Analyse la sécurité Python rapidement
- ✅ Pas de dépendances supplémentaires
- Timeout: 5 minutes

### SonarCloud
- ✅ Plateforme cloud multi-langage
- ✅ Analyse profonde avec métriques
- ⚠️ Nécessite SONAR_TOKEN et SONAR_ORG configurés
- Timeout: 10 minutes

## Commandes de test

```bash
# Vérifier que les outils CLI sont installés
eslint --version         # v8.34.0
semgrep --version       # 1.157.0
sonar-scanner --version # 3.1.0
bandit --version        # OK (si Python)

# Tester les imports Python
python -c "from scanner.eslint_runner import run_full_eslint_scan; print('✓')"
python -c "from scanner.semgrep_runner import run_full_semgrep_scan; print('✓')"

# Exécuter le test complet
python test_scanners_init.py
```

## Troubleshooting

**Problème**: ESLint retourne "No files matching"
- Ca peut arriver si le repo n'a pas de fichiers .js/.ts à la racine

**Problème**: Semgrep timeout
- Les gros repos peuvent dépasser 10 minutes avec OWASP Top 10
- Solution: Augmenter le timeout ou utiliser une config plus légère

**Problème**: SonarCloud ne démarre pas
- Vérifier que SONAR_TOKEN et SONAR_ORG sont configurés dans .env

**Problème**: Authentification GitHub échoue
- Certains tokens/repos peuvent ne pas fonctionner en clonage
- C'est attendu pour les dummies URLs de test
