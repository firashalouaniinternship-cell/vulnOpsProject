import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from services.scan_service import ScanService
from tasks.scan_tasks import run_scan_task

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_scan(request):
    """
    Lance un scan de manière asynchrone via Celery.
    """
    repo_full_name = request.data.get('repo_full_name', '')
    clone_url = request.data.get('clone_url', '')
    scanner_type = request.data.get('scanner_type', 'bandit').lower()
    run_sca = request.data.get('run_sca', False) or scanner_type == 'trivy'

    if not repo_full_name or not clone_url:
        return Response(
            {'error': 'repo_full_name et clone_url sont requis'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Récupération du token
    custom_token = request.data.get('custom_token')
    access_token = custom_token
    if not access_token and request.user.is_authenticated:
        try:
            access_token = request.user.github_profile.github_access_token
        except Exception:
            pass

    # 1. Pipeline via Service
    scan = ScanService.start_scan(
        user=request.user,
        repo_data={
            'repo_full_name': repo_full_name,
            'repo_owner': request.data.get('repo_owner', ''),
            'repo_name': request.data.get('repo_name', ''),
        },
        scanner_type=scanner_type,
        run_sca=run_sca
    )

    # 2. Appel Celery asynchrone
    run_scan_task.delay(
        scan_id=scan.id,
        repo_data={'clone_url': clone_url, 'repo_full_name': repo_full_name},
        scanner_type=scanner_type,
        access_token=access_token
    )

    return Response({
        'scan_id': scan.id,
        'status': 'PENDING',
        'message': 'Scan lancé avec succès en arrière-plan.'
    }, status=status.HTTP_202_ACCEPTED)

