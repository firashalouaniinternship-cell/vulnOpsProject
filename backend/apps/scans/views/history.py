from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from ..models import ScanResult, ApiUsage

@api_view(['GET'])
@permission_classes([AllowAny])
def get_scan_history(request, owner, repo):
    """Retourne l'historique des scans d'un dépôt"""
    user_filter = request.user if request.user.is_authenticated else None
    scans = ScanResult.objects.filter(
        user=user_filter,
        repo_owner=owner,
        repo_name=repo,
    ).values(
        'id', 'status', 'started_at', 'completed_at',
        'total_issues', 'critical_count', 'high_count', 'medium_count', 'low_count',
        'scanner_type', 'error_message', 'run_sast', 'run_sca', 'run_dast'
    )
    return Response(list(scans))

@api_view(['GET'])
@permission_classes([AllowAny])
def get_scan_detail(request, scan_id):
    """Retourne le détail d'un scan avec toutes les vulnérabilités"""
    user_filter = request.user if request.user.is_authenticated else None
    try:
        scan = ScanResult.objects.get(id=scan_id, user=user_filter)
    except ScanResult.DoesNotExist:
        return Response({'error': 'Scan non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    vulns = scan.vulnerabilities.values(
        'id', 'test_id', 'test_name', 'issue_text',
        'severity', 'confidence', 'filename', 'line_number',
        'line_range', 'code_snippet', 'cwe', 'more_info',
        'llm_score', 'llm_explanation', 'is_sca', 'is_dast', 'solution'
    )

    return Response({
        'id': scan.id,
        'repo_full_name': scan.repo_full_name,
        'status': scan.status,
        'scanner_type': scan.scanner_type,
        'started_at': scan.started_at,
        'completed_at': scan.completed_at,
        'run_sast': scan.run_sast,
        'run_sca': scan.run_sca,
        'sca_status': scan.sca_status,
        'run_dast': scan.run_dast,
        'dast_status': scan.dast_status,
        'metrics': {
            'total_issues': scan.total_issues,
            'critical_count': scan.critical_count,
            'high_count': scan.high_count,
            'medium_count': scan.medium_count,
            'low_count': scan.low_count,
            'sca_critical_count': scan.sca_critical_count,
            'sca_high_count': scan.sca_high_count,
            'sca_medium_count': scan.sca_medium_count,
            'sca_low_count': scan.sca_low_count,
        },
        'vulnerabilities': list(vulns),
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_stats(request):
    """Retourne les statistiques globales pour le dashboard utilisateur"""
    # 5 derniers dépôts scannés (un seul scan par dépôt)
    recent_scans_raw = ScanResult.objects.filter(
        user=request.user
    ).order_by('-started_at')[:50].values(
        'id', 'repo_full_name', 'scanner_type', 'status', 'started_at', 'total_issues'
    )
    
    recent_scans = []
    seen_repos = set()
    for s in recent_scans_raw:
        if s['repo_full_name'] not in seen_repos:
            recent_scans.append(s)
            seen_repos.add(s['repo_full_name'])
        if len(recent_scans) >= 5:
            break
    
    # Utilisation de l'API
    api_usage, created = ApiUsage.objects.get_or_create(user=request.user)
    
    return Response({
        'recent_scans': list(recent_scans),
        'api_usage': {
            'rag_calls_count': api_usage.rag_calls_count,
            'rag_calls_limit': api_usage.rag_calls_limit
        }
    }, status=status.HTTP_200_OK)
