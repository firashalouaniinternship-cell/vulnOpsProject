# ✅ Checklist Production - Authentification GitHub OAuth

## 🔐 Phase 1: Sécurité (CRITIQUE)

### Secrets et Clés
- [ ] Générer une nouvelle `SECRET_KEY` complexe (min 50 caractères)
  ```python
  from django.core.management.utils import get_random_secret_key
  print(get_random_secret_key())
  ```
- [ ] Ne JAMAIS commiter `.env` (vérifier `.gitignore`)
- [ ] Utiliser les variables d'environnement système pour les secrets
- [ ] `GITHUB_CLIENT_SECRET` stocké de manière sécurisée (gestionnaire de secrets)
- [ ] Rotation des tokens d'accès GitHub chaque 90 jours

### HTTPS et SSL/TLS
- [ ] Certificat SSL/TLS valide (Let's Encrypt recommandé)
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] `HSTS` configuré (min 31536000 secondes)
  ```python
  SECURE_HSTS_SECONDS = 31536000
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  ```

### Authentification
- [ ] `DEBUG = False` (mode production)
- [ ] `ALLOWED_HOSTS` configuré correctement
- [ ] CORS restreint aux domaines autorisés uniquement
- [ ] `CORS_ALLOW_CREDENTIALS = True`
- [ ] CSRF tokens obligatoires pour POST/PUT/DELETE

### Tokens GitHub
- [ ] Tokens d'accès chiffrés en base de données
- [ ] Tokens jamais loggés (audit logs)
- [ ] Tokens révoqués lors de la déconnexion
- [ ] Expiration des tokens implémentée

## 📊 Phase 2: Performance

### Caching
- [ ] Cache Redis configuré (au minimum 5 minutes pour les URLs d'auth)
- [ ] Cache des profils utilisateur (1 heure)
- [ ] Eviction policy: `allkeys-lru`
- [ ] TTL approprié pour chaque type de données

### Base de Données
- [ ] Index sur `github_id` pour requêtes rapides
- [ ] Index sur `user_id` pour OneToOne
- [ ] Backups quotidiens automatisés
- [ ] Read replicas pour les lectures intensives

### API GitHub
- [ ] Rate limiting implémenté (60 req/heure)
- [ ] Circuit breaker si l'API est down
- [ ] Fallback au mode démo en cas d'erreur
- [ ] Timeout sur les requêtes (10 secondes max)

## 🧪 Phase 3: Tests et QA

### Tests Automatisés
- [ ] Tests unitaires passent: `python manage.py test accounts`
- [ ] Tests d'intégration passent: `python manage.py test accounts.integration_tests`
- [ ] Coverage > 80%: `python manage.py coverage report`
- [ ] Tous les linters passent: `flake8`, `black`, `isort`

### Tests Manuel
- [ ] Test complet du flux OAuth
- [ ] Test avec l'API GitHub réelle
- [ ] Test mode démo (DEBUG=True)
- [ ] Test déconnexion
- [ ] Test accès /me/ authentifié
- [ ] Test accès /me/ non authentifié (401)

### Tests de Sécurité
- [ ] CSRF token validé
- [ ] CORS headers corrects
- [ ] Pas d'injection XSS
- [ ] Pas d'injection SQL
- [ ] Pas de secrets exposés
- [ ] Pas de tokens en logs

### Tests de Performance
- [ ] Temps réponse initial: < 2 secondes
- [ ] Temps réponse /me/: < 500ms
- [ ] Support 1000 utilisateurs simultanés
- [ ] Support 10,000 tokens actifs

## 📝 Phase 4: Configuration

### Django Settings
- [ ] `DEBUG = False`
- [ ] `ALLOWED_HOSTS` complète
- [ ] `SECURE_BROWSER_XSS_FILTER = True`
- [ ] `SECURE_CONTENT_SECURITY_POLICY` configuré
- [ ] `SESSION_ENGINE` configuré (pas 'db')
- [ ] `SESSION_CACHE_ALIAS` configuré

### URLs et CORS
- [ ] `FRONTEND_URL` correct (production)
- [ ] `GITHUB_REDIRECT_URI` correspond à GitHub Settings
- [ ] `CORS_ALLOWED_ORIGINS` configuré pour production
- [ ] `CSRF_TRUSTED_ORIGINS` configuré
- [ ] Tous les domaines en HTTPS

### Variables d'Environnement
- [ ] Toutes les variables requises dans `.env` ou système
- [ ] Aucune variable manquante
- [ ] Secrets sécurisés (pas en plain text)
- [ ] Format correcte pour chaque variable

## 🔍 Phase 5: Monitoring et Logs

### Logs
- [ ] Logs OAuth configurés (level INFO minimum)
- [ ] Logs centralisés (Elasticsearch, Stackdriver, etc.)
- [ ] Logs PII masqués (pas de tokens, emails, etc.)
- [ ] Rotation des logs (24h, max 100MB)

### Monitoring
- [ ] Alertes sur taux d'erreur OAuth > 5%
- [ ] Alertes sur temps réponse > 5 secondes
- [ ] Alertes sur rate limit GitHub atteint
- [ ] Dashboard de monitoring mis en place

### Error Tracking
- [ ] Sentry configuré (ou équivalent)
- [ ] Alertes sur nouveau type d'erreur
- [ ] Source maps uploadées pour JavaScript
- [ ] Erreurs groupées par type/endpoint

### Métriques
- [ ] Nombre de connexions/jour
- [ ] Nombre d'erreurs OAuth/jour
- [ ] Temps moyen de connexion
- [ ] Région des utilisateurs (si applicable)

## 🚀 Phase 6: Déploiement

### Avant le déploiement
- [ ] Tous les tests passent en CI/CD
- [ ] Code review approuvé
- [ ] Documentation à jour
- [ ] Changelog mis à jour
- [ ] Version taggée et releasée

### Déploiement Progressive
- [ ] Déployer en staging d'abord
- [ ] Tests de smoke en staging
- [ ] Canary deployment (5% du traffic)
- [ ] Monitoring pendant le déploiement
- [ ] Rollback plan prêt
- [ ] Déploiement complet si OK

### Post-Déploiement
- [ ] Vérifier connexion OAuth en production
- [ ] Vérifier logs pour erreurs
- [ ] Vérifier métriques (pas de dégradation)
- [ ] Tester depuis plusieurs navigateurs
- [ ] Tester depuis différentes régions
- [ ] Contacter un utilisateur pour tester

## 🔄 Phase 7: Maintenance Continue

### Hebdomadaire
- [ ] Vérifier les logs d'erreur
- [ ] Vérifier les métriques de performance
- [ ] Vérifier les alertes Sentry
- [ ] Vérifier les mises à jour de sécurité

### Mensuel
- [ ] Audit des accès (qui s'est connecté)
- [ ] Vérifier les quotas GitHub API
- [ ] Nettoyer les tokens expirés
- [ ] Vérifier la capacité de stockage
- [ ] Backup + restore test

### Trimestriel
- [ ] Audit de sécurité complet
- [ ] Vérifier les pratiques de sécurité
- [ ] Rotation des API credentials
- [ ] Mise à jour des dépendances
- [ ] Tests de charge

### Annuel
- [ ] Renouveler les certificats SSL
- [ ] Audit de sécurité externe
- [ ] Planifier les améliorations
- [ ] Vérifier la compliance (GDPR, etc.)

## 🆘 Rollback Plan

En cas de problème en production:

```bash
# 1. Arrêter le nouveau déploiement
docker-compose down  # ou votre système de déploiement

# 2. Redéployer la version stable précédente
git checkout <previous-tag>
docker-compose up -d

# 3. Vérifier les logs
docker-compose logs -f backend

# 4. Alerter l'équipe
# Notifier Slack, email, etc.

# 5. Analyser le problème
# Créer une issue GitHub
# Discuter de la solution

# 6. Chercher la correction
# Code review rigoureuse
# Tests avant re-déploiement
```

## 📋 Documentation à Préparer

- [ ] Runbook de déploiement
- [ ] Procédure de rollback
- [ ] Guide dépannage en production
- [ ] Escalade d'incidents
- [ ] Contacts d'urgence
- [ ] SLA et uptime targets

## ✔️ Sign-off Final

- [ ] Product Owner approuve
- [ ] Security Team approuve
- [ ] DevOps approuve
- [ ] Tech Lead approuve
- [ ] QA certifie tous les tests passent

---

**Prêt pour production**: ________________________  
**Date**: ________________________  
**Approuvé par**: ________________________  
**Notes**: ________________________
