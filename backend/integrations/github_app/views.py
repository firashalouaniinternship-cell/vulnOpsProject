"""
API Views pour la GitHub App Integration.

Endpoints:
  GET  /api/github-app/install/       → URL d'installation de l'App
  POST /api/github-app/webhook/       → Reçoit les webhooks GitHub
  GET  /api/github-app/callback/      → Callback post-installation
  GET  /api/github-app/status/        → Statut installation de l'utilisateur
  GET  /api/github-app/repos/         → Liste repos connectés
  POST /api/github-app/setup/<repo>/  → Setup manuel d'un repo
"""

import json
import logging

from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.scans.models import GitHubAppInstallation
from integrations.github_app.service import GitHubAppService
from integrations.github_app.webhook_handler import verify_webhook_signature, handle_installation_event

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_install_url(request):
    """
    Retourne l'URL d'installation de la GitHub App.
    Le frontend redirige l'utilisateur vers cette URL.
    """
    app_name = getattr(settings, 'GITHUB_APP_NAME', '')
    if not app_name:
        return Response(
            {'error': 'GitHub App non configurée. Ajoutez GITHUB_APP_NAME dans les settings.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    install_url = f"https://github.com/apps/{app_name}/installations/new"
    return Response({
        'install_url': install_url,
        'app_name': app_name,
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def github_app_webhook(request):
    """
    Reçoit les webhooks de la GitHub App.
    GitHub signe chaque requête avec HMAC-SHA256.
    """
    # Vérifier la signature
    signature = request.headers.get('X-Hub-Signature-256', '')
    if not verify_webhook_signature(request.body, signature):
        logger.warning("Webhook reçu avec signature invalide!")
        return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)

    event_type = request.headers.get('X-GitHub-Event', '')
    payload = request.data

    logger.info(f"📨 Webhook reçu: {event_type} — action: {payload.get('action', 'N/A')}")

    # Traiter selon le type d'événement
    if event_type in ('installation', 'installation_repositories'):
        # Essayer de trouver l'utilisateur VulnOps lié au compte GitHub
        user = _find_user_from_installation(payload)
        result = handle_installation_event(payload, user=user)
        return Response(result, status=status.HTTP_200_OK)

    elif event_type == 'push':
        # Un push sur un repo connecté — on peut logger ou déclencher un scan
        repo_full_name = payload.get('repository', {}).get('full_name')
        logger.info(f"📤 Push reçu sur {repo_full_name} — scan CI/CD attendu via GitHub Actions")
        return Response({'received': True, 'event': 'push', 'repo': repo_full_name})

    elif event_type == 'pull_request':
        repo_full_name = payload.get('repository', {}).get('full_name')
        logger.info(f"🔀 Pull request reçu sur {repo_full_name}")
        return Response({'received': True, 'event': 'pull_request', 'repo': repo_full_name})

    # Événement non géré — on retourne quand même 200 pour ne pas déclencher des retry GitHub
    return Response({'received': True, 'event': event_type, 'handled': False})


def _find_user_from_installation(payload: dict):
    """Essaie de retrouver l'utilisateur VulnOps correspondant au compte GitHub de l'installation."""
    try:
        from apps.users.models import GitHubProfile
        account = payload.get('installation', {}).get('account', {})
        github_login = account.get('login', '')
        if github_login:
            profile = GitHubProfile.objects.get(github_login=github_login)
            return profile.user
    except Exception:
        pass
    return None


@api_view(['GET'])
@permission_classes([AllowAny])
def github_app_callback(request):
    """
    Callback appelé par GitHub après l'installation.
    GitHub ajoute ?installation_id=xxx&setup_action=install
    """
    installation_id = request.GET.get('installation_id')
    setup_action = request.GET.get('setup_action', 'install')

    logger.info(f"✅ GitHub App callback: installation_id={installation_id}, action={setup_action}")

    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')

    if installation_id:
        # Redirige vers la page CI/CD du frontend avec le paramètre
        return HttpResponseRedirect(
            f"{frontend_url}/cicd?installed=true&installation_id={installation_id}"
        )

    return HttpResponseRedirect(f"{frontend_url}/cicd?error=no_installation_id")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_app_status(request):
    """
    Retourne le statut de l'installation GitHub App pour l'utilisateur connecté.
    Inclut la liste des repos connectés et leur statut de pipeline.
    """
    try:
        installations = GitHubAppInstallation.objects.filter(
            user=request.user,
            status='active'
        ).order_by('-created_at')

        if not installations.exists():
            app_name = getattr(settings, 'GITHUB_APP_NAME', '')
            return Response({
                'installed': False,
                'installations': [],
                'install_url': f"https://github.com/apps/{app_name}/installations/new" if app_name else None,
            })

        data = []
        for inst in installations:
            data.append({
                'installation_id': inst.installation_id,
                'github_account': inst.github_account_login,
                'account_type': inst.github_account_type,
                'repositories': inst.repositories or [],
                'setup_completed': inst.setup_completed,
                'status': inst.status,
                'created_at': inst.created_at.isoformat(),
            })

        return Response({
            'installed': True,
            'installations': data,
        })

    except Exception as e:
        logger.error(f"Erreur get_app_status: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_connected_repos(request):
    """Liste tous les repos connectés via la GitHub App pour l'utilisateur."""
    installations = GitHubAppInstallation.objects.filter(
        user=request.user,
        status='active'
    )

    all_repos = []
    for inst in installations:
        for repo in (inst.repositories or []):
            all_repos.append({
                **repo,
                'installation_id': inst.installation_id,
                'github_account': inst.github_account_login,
            })

    return Response({'repos': all_repos, 'count': len(all_repos)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_repo(request, repo_owner, repo_name):
    """
    Déclenche manuellement le setup d'un repo (création workflow + secrets).
    Utile si le webhook n'a pas pu s'exécuter, ou pour un retry.
    """
    repo_full_name = f"{repo_owner}/{repo_name}"

    # Trouver l'installation qui a accès à ce repo
    installation = None
    for inst in GitHubAppInstallation.objects.filter(user=request.user, status='active'):
        repos = inst.repositories or []
        if any(r.get('full_name') == repo_full_name for r in repos):
            installation = inst
            break

    if not installation:
        return Response(
            {'error': f"Aucune installation GitHub App trouvée avec accès à {repo_full_name}. Vérifiez que l'App est installée sur ce repo."},
            status=status.HTTP_404_NOT_FOUND
        )

    service = GitHubAppService()
    try:
        result = service.setup_repository(installation.installation_id, repo_full_name)

        # Mettre à jour le statut dans la DB
        repos = installation.repositories or []
        for repo in repos:
            if repo.get('full_name') == repo_full_name:
                repo['pipeline_status'] = 'installed' if result['success'] else 'error'
                repo['setup_result'] = {
                    'workflow_created': result.get('workflow_created'),
                    'secrets_configured': result.get('secrets_configured'),
                }
        installation.repositories = repos
        installation.save()

        return Response(result)
    except Exception as e:
        logger.error(f"Erreur setup manuel {repo_full_name}: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def link_installation(request):
    """
    Lie une installation GitHub App à l'utilisateur connecté.
    Appelé depuis le frontend après le callback avec installation_id.
    """
    installation_id = request.data.get('installation_id')
    if not installation_id:
        return Response({'error': 'installation_id requis'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        installation_id = int(installation_id)
    except (ValueError, TypeError):
        return Response({'error': 'installation_id doit être un entier'}, status=status.HTTP_400_BAD_REQUEST)

    # Vérifier si l'installation existe déjà (créée par webhook)
    try:
        inst = GitHubAppInstallation.objects.get(installation_id=installation_id)
        if not inst.user and request.user.is_authenticated:
            inst.user = request.user
            inst.save()
        return Response({
            'linked': True,
            'installation_id': installation_id,
            'repos': inst.repositories,
            'setup_completed': inst.setup_completed,
        })
    except GitHubAppInstallation.DoesNotExist:
        pass

    # L'installation n'existe pas encore (webhook pas encore reçu) → on la crée via API
    if not request.user.is_authenticated:
        return Response({'error': 'Authentification requise'}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        service = GitHubAppService()
        repos = service.get_installation_repos(installation_id)

        repo_list = [{
            'id': r.get('id'),
            'full_name': r.get('full_name'),
            'name': r.get('name'),
            'private': r.get('private', False),
            'pipeline_status': 'pending',
        } for r in repos]

        account_login = repos[0].get('owner', {}).get('login', '') if repos else ''

        inst, _ = GitHubAppInstallation.objects.update_or_create(
            installation_id=installation_id,
            defaults={
                'user': request.user,
                'github_account_login': account_login,
                'github_account_id': 0,
                'github_account_type': 'User',
                'repositories': repo_list,
                'status': 'active',
                'setup_completed': False,
            }
        )

        # Setup automatique des repos
        for repo in repos:
            repo_full_name = repo.get('full_name')
            if repo_full_name:
                try:
                    result = service.setup_repository(installation_id, repo_full_name)
                    for r in repo_list:
                        if r['full_name'] == repo_full_name:
                            r['pipeline_status'] = 'installed' if result['success'] else 'error'
                except Exception as e:
                    logger.error(f"Erreur setup {repo_full_name}: {e}")

        inst.repositories = repo_list
        inst.setup_completed = all(r.get('pipeline_status') == 'installed' for r in repo_list)
        inst.save()

        return Response({
            'linked': True,
            'installation_id': installation_id,
            'repos': repo_list,
            'setup_completed': inst.setup_completed,
        })

    except Exception as e:
        logger.error(f"Erreur link_installation: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
