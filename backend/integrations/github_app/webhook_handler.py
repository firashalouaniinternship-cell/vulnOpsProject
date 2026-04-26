"""
Webhook Handler — Traite les événements GitHub App (installation, push, PR).

GitHub envoie des webhooks quand:
- Un utilisateur installe l'App (installation.created)
- Un utilisateur désinstalle (installation.deleted)
- Un push est fait sur un repo connecté
"""

import hashlib
import hmac
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """Vérifie la signature HMAC-SHA256 du webhook GitHub."""
    webhook_secret = getattr(settings, 'GITHUB_APP_WEBHOOK_SECRET', '')
    if not webhook_secret:
        logger.warning("GITHUB_APP_WEBHOOK_SECRET non configuré — vérification ignorée.")
        return True  # Permissif en dev si pas de secret configuré

    if not signature_header or not signature_header.startswith('sha256='):
        return False

    expected = hmac.new(
        webhook_secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    received = signature_header.split('sha256=', 1)[1]
    return hmac.compare_digest(expected, received)


def handle_installation_event(payload: dict, user=None) -> dict:
    """
    Gère les événements 'installation' et 'installation_repositories'.
    
    Actions:
    - created: Stocke l'installation + setup automatique des repos
    - deleted: Marque l'installation comme supprimée
    - added (installation_repositories): Setup les nouveaux repos
    """
    from apps.scans.models import GitHubAppInstallation
    from integrations.github_app.service import GitHubAppService

    action = payload.get('action')
    installation_data = payload.get('installation', {})
    installation_id = installation_data.get('id')
    account = installation_data.get('account', {})

    if not installation_id:
        return {'error': 'No installation_id in payload'}

    logger.info(f"📦 GitHub App event: {payload.get('event', 'installation')}.{action} — installation #{installation_id}")

    if action == 'created':
        # Récupérer ou créer l'installation en DB
        repos_from_payload = payload.get('repositories', [])
        repo_list = [
            {
                'id': r.get('id'),
                'full_name': r.get('full_name'),
                'name': r.get('name'),
                'private': r.get('private', False),
                'pipeline_status': 'pending',
            }
            for r in repos_from_payload
        ]

        installation, created = GitHubAppInstallation.objects.update_or_create(
            installation_id=installation_id,
            defaults={
                'user': user,
                'github_account_login': account.get('login', ''),
                'github_account_id': account.get('id', 0),
                'github_account_type': account.get('type', 'User'),
                'repositories': repo_list,
                'status': 'active',
                'setup_completed': False,
            }
        )

        # Setup automatique de chaque repo
        service = GitHubAppService()
        results = []
        for repo in repos_from_payload:
            repo_full_name = repo.get('full_name')
            if repo_full_name:
                try:
                    result = service.setup_repository(installation_id, repo_full_name)
                    results.append(result)
                    # Mettre à jour le statut dans la liste
                    for r in repo_list:
                        if r['full_name'] == repo_full_name:
                            r['pipeline_status'] = 'installed' if result['success'] else 'error'
                            r['setup_result'] = result
                except Exception as e:
                    logger.error(f"Erreur setup {repo_full_name}: {e}")
                    for r in repo_list:
                        if r['full_name'] == repo_full_name:
                            r['pipeline_status'] = 'error'
                            r['error'] = str(e)

        # Sauvegarder les statuts mis à jour
        installation.repositories = repo_list
        installation.setup_completed = all(r.get('pipeline_status') == 'installed' for r in repo_list)
        installation.save()

        return {
            'action': 'created',
            'installation_id': installation_id,
            'repos_processed': len(results),
            'results': results,
        }

    elif action == 'deleted':
        GitHubAppInstallation.objects.filter(installation_id=installation_id).update(status='deleted')
        logger.info(f"🗑️ Installation #{installation_id} supprimée.")
        return {'action': 'deleted', 'installation_id': installation_id}

    elif action in ('added', 'repositories_added'):
        # Des repos ont été ajoutés à une installation existante
        new_repos = payload.get('repositories_added', [])
        try:
            installation = GitHubAppInstallation.objects.get(installation_id=installation_id)
            current_repos = installation.repositories or []

            service = GitHubAppService()
            for repo in new_repos:
                repo_full_name = repo.get('full_name')
                repo_entry = {
                    'id': repo.get('id'),
                    'full_name': repo_full_name,
                    'name': repo.get('name'),
                    'private': repo.get('private', False),
                    'pipeline_status': 'pending',
                }
                # Éviter les doublons
                if not any(r.get('full_name') == repo_full_name for r in current_repos):
                    current_repos.append(repo_entry)

                if repo_full_name:
                    try:
                        result = service.setup_repository(installation_id, repo_full_name)
                        repo_entry['pipeline_status'] = 'installed' if result['success'] else 'error'
                    except Exception as e:
                        repo_entry['pipeline_status'] = 'error'
                        repo_entry['error'] = str(e)

            installation.repositories = current_repos
            installation.save()
        except GitHubAppInstallation.DoesNotExist:
            logger.warning(f"Installation #{installation_id} inconnue pour l'event 'added'.")

        return {'action': 'added', 'repos_added': len(new_repos)}

    elif action in ('removed', 'repositories_removed'):
        removed_repos = payload.get('repositories_removed', [])
        try:
            installation = GitHubAppInstallation.objects.get(installation_id=installation_id)
            removed_names = {r.get('full_name') for r in removed_repos}
            installation.repositories = [
                r for r in (installation.repositories or [])
                if r.get('full_name') not in removed_names
            ]
            installation.save()
        except GitHubAppInstallation.DoesNotExist:
            pass
        return {'action': 'removed', 'repos_removed': len(removed_repos)}

    return {'action': action, 'ignored': True}
