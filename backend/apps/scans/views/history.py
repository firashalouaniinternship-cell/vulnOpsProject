from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from ..models import ScanResult, ApiUsage
from ..risk_scorer import compute_risk_score

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
        'scanner_type', 'error_message', 'run_sast', 'run_sca', 'run_container', 'run_dast'
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

    vulns_data = []
    for v in scan.vulnerabilities.all():
        vulns_data.append({
            'id':              v.id,
            'test_id':         v.test_id,
            'test_name':       v.test_name,
            'issue_text':      v.issue_text,
            'severity':        v.severity,
            'confidence':      v.confidence,
            'filename':        v.filename,
            'line_number':     v.line_number,
            'line_range':      v.line_range,
            'code_snippet':    v.code_snippet,
            'cwe':             v.cwe,
            'more_info':       v.more_info,
            'llm_score':       v.llm_score,
            'llm_explanation': v.llm_explanation,
            'is_sca':          v.is_sca,
            'is_container':    v.is_container,
            'is_dast':         v.is_dast,
            'solution':        v.solution,
            'risk_score':      compute_risk_score({
                'severity': v.severity,
                'confidence': v.confidence,
                'filename': v.filename,
                'is_dast': v.is_dast,
                'llm_score': v.llm_score
            }),
        })

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
        'run_container': scan.run_container,
        'container_status': scan.container_status,
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
            'container_critical_count': scan.container_critical_count,
            'container_high_count': scan.container_high_count,
            'container_medium_count': scan.container_medium_count,
            'container_low_count': scan.container_low_count,
        },
        'vulnerabilities': vulns_data,
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

@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_scan(request, scan_id):
    """Supprime un scan spécifique"""
    user_filter = request.user if request.user.is_authenticated else None
    scan = get_object_or_404(ScanResult, id=scan_id, user=user_filter)
    scan.delete()
    return Response({'message': 'Scan supprimé avec succès'}, status=status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_all_scans(request, owner, repo):
    """Supprime tout l'historique des scans d'un dépôt"""
    user_filter = request.user if request.user.is_authenticated else None
    scans = ScanResult.objects.filter(
        user=user_filter,
        repo_owner=owner,
        repo_name=repo
    )
    count = scans.count()
    scans.delete()
    return Response({'message': f'{count} scans supprimés'}, status=status.HTTP_200_OK)
