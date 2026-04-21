import json
import logging
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from ..models import ScanResult, Vulnerability
from rag.llm_scoring import get_direct_llm_score

logger = logging.getLogger(__name__)

def parse_semgrep_report(data):
    """Parse Semgrep JSON output."""
    vulnerabilities = []
    results = data.get('results', [])
    
    severity_map = {
        'ERROR': 'HIGH',
        'WARNING': 'MEDIUM',
        'INFO': 'LOW',
    }
    
    for issue in results:
        severity = severity_map.get(issue.get('severity', 'INFO'), 'LOW')
        vuln = {
            'test_id': issue.get('check_id', 'SEMGREP'),
            'test_name': 'Semgrep (CI/CD)',
            'issue_text': issue.get('extra', {}).get('message', ''),
            'severity': severity,
            'confidence': 'HIGH',
            'filename': issue.get('path', ''),
            'line_number': issue.get('start', {}).get('line', 0),
            'line_range': [
                issue.get('start', {}).get('line', 0),
                issue.get('end', {}).get('line', 0)
            ],
            'code_snippet': issue.get('extra', {}).get('lines', ''),
            'cwe': issue.get('extra', {}).get('metadata', {}).get('cwe', [''])[0] if issue.get('extra', {}).get('metadata', {}).get('cwe') else '',
            'more_info': issue.get('extra', {}).get('metadata', {}).get('references', [''])[0] if issue.get('extra', {}).get('metadata', {}).get('references') else '',
            'is_sca': False
        }
        vulnerabilities.append(vuln)
    return vulnerabilities

def parse_npm_audit_report(data):
    """Parse npm audit --json output (v2+ format)."""
    vulnerabilities = []
    vulns_dict = data.get('vulnerabilities', {})
    
    severity_map = {
        'critical': 'CRITICAL',
        'high': 'HIGH',
        'moderate': 'MEDIUM',
        'low': 'LOW',
        'info': 'LOW',
    }
    
    for pkg_name, info in vulns_dict.items():
        #npm audit can have multiple advisories via the 'via' field
        vias = info.get('via', [])
        for via in vias:
            if isinstance(via, dict): # actual vulnerability, not just a dependent package
                severity = severity_map.get(via.get('severity', 'low'), 'LOW')
                vuln = {
                    'test_id': f"NPM-{via.get('source', 'VULN')}",
                    'test_name': pkg_name,
                    'issue_text': via.get('title', 'NPM Vulnerability'),
                    'severity': severity,
                    'confidence': 'HIGH',
                    'filename': 'package.json',
                    'line_number': 0,
                    'line_range': [],
                    'code_snippet': f"{pkg_name}@{info.get('range', 'unknown')}",
                    'cwe': via.get('cwe', [''])[0] if via.get('cwe') else '',
                    'more_info': via.get('url', ''),
                    'is_sca': True
                }
                vulnerabilities.append(vuln)
    return vulnerabilities

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def github_cicd_webhook(request):
    """
    Endpoint for GitHub Actions to send scan results.
    Payload:
    {
        "repo_full_name": "owner/repo",
        "repo_owner": "owner",
        "repo_name": "repo",
        "branch": "main",
        "commit_sha": "...",
        "reports": {
            "sast": { "scanner": "semgrep", "data": { ... } },
            "sca": { "scanner": "npm-audit", "data": { ... } }
        }
    }
    """
    # Simple token authentication
    auth_header = request.headers.get('Authorization', '')
    expected_token = getattr(settings, 'GITHUB_CICD_TOKEN', 'fallback-secret-token')
    
    if not auth_header.startswith('Bearer ') or auth_header.split(' ')[1] != expected_token:
        # Check against environment variable if not in settings explicitly
        import os
        env_token = os.environ.get('API_TOKEN', 'fallback-secret-token')
        if auth_header.split(' ')[-1] != env_token:
             return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

    data = request.data
    repo_full_name = data.get('repo_full_name')
    repo_owner = data.get('repo_owner')
    repo_name = data.get('repo_name')
    reports = data.get('reports', {})

    if not repo_full_name:
        return Response({'error': 'repo_full_name is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Create ScanResult
    scan = ScanResult.objects.create(
        repo_full_name=repo_full_name,
        repo_owner=repo_owner or repo_full_name.split('/')[0],
        repo_name=repo_name or repo_full_name.split('/')[-1],
        scanner_type='github-actions',
        status='RUNNING',
        run_sast='sast' in reports,
        run_sca='sca' in reports,
        started_at=timezone.now()
    )

    all_vulns_data = []
    
    # Process SAST
    if 'sast' in reports:
        sast_report = reports['sast']
        if sast_report.get('scanner') == 'semgrep':
            all_vulns_data.extend(parse_semgrep_report(sast_report.get('data', {})))

    # Process SCA
    if 'sca' in reports:
        sca_report = reports['sca']
        if sca_report.get('scanner') == 'npm-audit':
            all_vulns_data.extend(parse_npm_audit_report(sca_report.get('data', {})))

    # Save to database and AI Scoring
    vuln_objects = []
    context_summary = f"GitHub CI/CD Scan for {repo_full_name}. Tools: {', '.join(reports.keys())}"
    
    for v_data in all_vulns_data:
        # AI Scoring
        try:
            ai_res = get_direct_llm_score(
                test_name=v_data['test_name'],
                issue_text=v_data['issue_text'],
                severity=v_data['severity'],
                context_summary=context_summary,
                code_snippet=v_data.get('code_snippet', '')
            )
            llm_score = ai_res.get('score', 0.5)
            llm_explanation = ai_res.get('reasoning', 'Analyse CI/CD réussie')
        except Exception as e:
            logger.warning(f"AI Scoring failed for CI/CD vuln: {e}")
            llm_score = 0.5
            llm_explanation = f"Erreur IA: {str(e)}"

        vuln_objects.append(Vulnerability(
            scan=scan,
            test_id=v_data['test_id'],
            test_name=v_data['test_name'],
            issue_text=v_data['issue_text'],
            severity=v_data['severity'],
            confidence=v_data['confidence'],
            filename=v_data['filename'],
            line_number=v_data['line_number'],
            line_range=v_data['line_range'],
            code_snippet=v_data['code_snippet'],
            cwe=v_data.get('cwe', ''),
            more_info=v_data.get('more_info', ''),
            llm_score=llm_score,
            llm_explanation=llm_explanation,
            is_sca=v_data.get('is_sca', False)
        ))

    Vulnerability.objects.bulk_create(vuln_objects)

    # Update scan metrics
    scan.status = 'COMPLETED'
    scan.completed_at = timezone.now()
    scan.total_issues = len(vuln_objects)
    scan.high_count = sum(1 for v in vuln_objects if v.severity == 'HIGH')
    scan.medium_count = sum(1 for v in vuln_objects if v.severity == 'MEDIUM')
    scan.low_count = sum(1 for v in vuln_objects if v.severity == 'LOW')
    scan.critical_count = sum(1 for v in vuln_objects if v.severity == 'CRITICAL')
    
    if scan.run_sca:
        scan.sca_status = 'COMPLETED'
        scan.sca_high_count = sum(1 for v in vuln_objects if v.is_sca and v.severity in ['HIGH', 'CRITICAL'])
        scan.sca_medium_count = sum(1 for v in vuln_objects if v.is_sca and v.severity == 'MEDIUM')
        scan.sca_low_count = sum(1 for v in vuln_objects if v.is_sca and v.severity == 'LOW')

    scan.save()

    return Response({
        'success': True,
        'scan_id': scan.id,
        'vulns_found': len(vuln_objects)
    }, status=status.HTTP_201_CREATED)
