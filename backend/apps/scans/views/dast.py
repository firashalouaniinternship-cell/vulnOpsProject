import logging
import os
import shutil
import tempfile
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from ..models import ScanResult, Vulnerability
from scanners.dast.zaproxy_runner import (
    run_zap_baseline_scan,
    check_dast_prerequisites,
    build_and_run_container,
    stop_and_cleanup_container
)
from core.utils.repo_utils import clone_repo
from integrations.defectdojo.mapper import DojoMapper
from rag.llm_scoring import get_direct_llm_score

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def check_dast_prerequisites_view(request):
    """
    Checks if a repository has files required for DAST scanning.
    Clones the repo temporarily and checks for Dockerfile, docker-compose, openapi.yaml, etc.
    Body: { "clone_url": "https://...", "custom_token": "...(optional)" }
    """
    clone_url = request.data.get('clone_url', '')
    custom_token = request.data.get('custom_token')
    access_token = custom_token
    if not access_token and request.user.is_authenticated:
        try:
            access_token = request.user.github_profile.github_access_token
        except Exception:
            pass

    if not clone_url:
        return Response({'error': 'clone_url is required'}, status=status.HTTP_400_BAD_REQUEST)

    repo_path = None
    try:
        repo_path = tempfile.mkdtemp(prefix='vulnops_dast_check_')
        clone_repo(clone_url, access_token, repo_path)
        result = check_dast_prerequisites(repo_path)
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error checking DAST prerequisites: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        if repo_path and os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_dast_scan(request):
    """
    Launches an OWASP ZAP DAST baseline scan against a given target URL.
    Body: { "repo_full_name": "owner/repo", "target_url": "https://..." }
    """
    repo_full_name = request.data.get('repo_full_name', '')
    repo_owner = request.data.get('repo_owner', '')
    repo_name = request.data.get('repo_name', '')
    target_url = request.data.get('target_url', '').strip()

    if not target_url:
        return Response({'error': 'target_url is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not repo_full_name:
        return Response({'error': 'repo_full_name is required'}, status=status.HTTP_400_BAD_REQUEST)

    scan = ScanResult.objects.create(
        user=request.user if request.user.is_authenticated else None,
        repo_owner=repo_owner,
        repo_name=repo_name,
        repo_full_name=repo_full_name,
        scanner_type='zap',
        status='RUNNING',
        run_sast=False,
        run_dast=True,
        dast_status='RUNNING',
        dast_target_url=target_url,
    )

    try:
        logger.info(f"Starting ZAP DAST scan for {repo_full_name} -> {target_url}")
        result = run_zap_baseline_scan(target_url)

        if not result['success']:
            scan.status = 'FAILED'
            scan.dast_status = 'FAILED'
            scan.error_message = result.get('error', 'ZAP scan failed')
            scan.completed_at = timezone.now()
            scan.save()
            return Response(
                {'error': result['error'], 'scan_id': scan.id},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        alerts = result['data']
        high_count = sum(1 for a in alerts if a['severity'] == 'HIGH')
        medium_count = sum(1 for a in alerts if a['severity'] == 'MEDIUM')
        low_count = sum(1 for a in alerts if a['severity'] == 'LOW')

        scan.status = 'COMPLETED'
        scan.dast_status = 'COMPLETED'
        scan.completed_at = timezone.now()
        scan.total_issues = len(alerts)
        scan.high_count = high_count
        scan.medium_count = medium_count
        scan.low_count = low_count
        scan.dast_high_count = high_count
        scan.dast_medium_count = medium_count
        scan.dast_low_count = low_count
        scan.save()

        context_summary = f"Dépôt {repo_full_name}. Scanner: ZAP (DAST). Total: {len(alerts)}"
        vuln_objects = []
        for a in alerts:
            try:
                ai_res = get_direct_llm_score(
                    test_name=a['test_name'],
                    issue_text=a['issue_text'],
                    severity=a['severity'],
                    context_summary=context_summary,
                    code_snippet=a.get('code_snippet', '')
                )
                llm_fb_score = ai_res.get('score', 0.5)
                llm_fb_reasoning = ai_res.get('reasoning', 'Analyse DAST IA réussie')
            except Exception as e:
                logger.warning(f"AI Scoring failed for DAST {a['test_id']}: {e}")
                llm_fb_score = 0.5
                llm_fb_reasoning = f'Erreur technique IA (DAST): {str(e)}'

            vuln_objects.append(Vulnerability(
                scan=scan,
                test_id=a['test_id'],
                test_name=a['test_name'],
                issue_text=a['issue_text'],
                severity=a['severity'],
                confidence=a['confidence'],
                filename=a['filename'],
                line_number=a.get('line_number', 0),
                line_range=a.get('line_range', []),
                code_snippet=a.get('code_snippet', ''),
                cwe=a.get('cwe', ''),
                more_info=a.get('more_info', '')[:1000],
                llm_score=llm_fb_score,
                llm_explanation=llm_fb_reasoning,
                is_sca=False,
                is_dast=True,
                solution=a.get('solution', ''),
            ))
        
        Vulnerability.objects.bulk_create(vuln_objects)

        try:
            if result.get('raw'):
                DojoMapper.save_and_push_to_dojo(result['raw'], 'zap')
        except Exception as e:
            logger.error(f"Error triggering DefectDojo integration in DAST scan: {e}")

        metrics = {
            'total_issues': len(alerts),
            'high_count': high_count,
            'medium_count': medium_count,
            'low_count': low_count,
            'target_url': target_url,
        }

        return Response({
            'scan_id': scan.id,
            'status': 'COMPLETED',
            'repo': repo_full_name,
            'metrics': metrics,
            'vulnerabilities': alerts,
        })

    except Exception as e:
        scan.status = 'FAILED'
        scan.dast_status = 'FAILED'
        scan.error_message = str(e)
        scan.completed_at = timezone.now()
        scan.save()
        logger.exception(f"DAST scan error for {repo_full_name}: {e}")
        return Response(
            {'error': str(e), 'scan_id': scan.id},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_auto_build_dast_scan(request):
    """
    Automates the DAST process: Build & Scan.
    """
    clone_url = request.data.get('clone_url', '')
    repo_full_name = request.data.get('repo_full_name', '')
    repo_owner = request.data.get('repo_owner', '')
    repo_name = request.data.get('repo_name', '')
    custom_token = request.data.get('custom_token')
    start_command = request.data.get('start_command')
    target_port = request.data.get('target_port')
    parent_scan_id = request.data.get('parent_scan_id')
    
    if target_port:
        try:
            target_port = int(target_port)
        except (ValueError, TypeError):
            target_port = None
    
    access_token = custom_token
    if not access_token and request.user.is_authenticated:
        try:
            access_token = request.user.github_profile.github_access_token
        except Exception:
            pass

    if not clone_url or not repo_full_name:
        return Response({'error': 'clone_url and repo_full_name are required'}, status=status.HTTP_400_BAD_REQUEST)

    scan = None
    if parent_scan_id:
        try:
            scan = ScanResult.objects.get(id=parent_scan_id)
            scan.run_dast = True
            scan.dast_status = 'RUNNING'
            scan.save()
        except ScanResult.DoesNotExist:
            logger.warning(f"Parent scan {parent_scan_id} not found, creating new one.")

    if not scan:
        scan = ScanResult.objects.create(
            user=request.user if request.user.is_authenticated else None,
            repo_owner=repo_owner,
            repo_name=repo_name,
            repo_full_name=repo_full_name,
            scanner_type='zap',
            status='RUNNING',
            run_sast=False,
            run_dast=True,
            dast_status='RUNNING',
        )

    repo_path = None
    container_info = None
    try:
        repo_path = tempfile.mkdtemp(prefix='vulnops_autodast_')
        logger.info(f"Cloning {repo_full_name} for auto-DAST into {repo_path}")
        clone_repo(clone_url, access_token, repo_path)
        
        logger.info(f"Building and running container for {repo_name} (command: {start_command}, port: {target_port})")
        container_info = build_and_run_container(
            repo_path, 
            repo_name, 
            start_command=start_command, 
            manual_port=target_port
        )
        
        if not container_info['success']:
            raise Exception(f"Failed to start application: {container_info.get('error')}")
            
        target_url = container_info['url']
        scan.dast_target_url = target_url
        scan.save()
        
        logger.info(f"Starting ZAP scan against local app at {target_url}")
        result = run_zap_baseline_scan(target_url)

        if not result['success']:
            raise Exception(result.get('error', 'ZAP scan failed'))

        alerts = result['data']
        high_count = sum(1 for a in alerts if a['severity'] == 'HIGH')
        medium_count = sum(1 for a in alerts if a['severity'] == 'MEDIUM')
        low_count = sum(1 for a in alerts if a['severity'] == 'LOW')

        scan.status = 'COMPLETED'
        scan.dast_status = 'COMPLETED'
        scan.completed_at = timezone.now()
        scan.total_issues += len(alerts)
        scan.high_count += high_count
        scan.medium_count += medium_count
        scan.low_count += low_count
        scan.dast_high_count = high_count
        scan.dast_medium_count = medium_count
        scan.dast_low_count = low_count
        scan.save()

        context_summary = f"Dépôt {repo_full_name}. Scanner: ZAP (Auto-DAST). Total: {len(alerts)}"
        vuln_objects = []
        for a in alerts:
            try:
                ai_res = get_direct_llm_score(
                    test_name=a['test_name'],
                    issue_text=a['issue_text'],
                    severity=a['severity'],
                    context_summary=context_summary,
                    code_snippet=a.get('code_snippet', '')
                )
                llm_fb_score = ai_res.get('score', 0.5)
                llm_fb_reasoning = ai_res.get('reasoning', 'Analyse DAST IA réussie')
            except Exception as e:
                logger.warning(f"AI Scoring failed for DAST {a['test_id']}: {e}")
                llm_fb_score = 0.5
                llm_fb_reasoning = f'Erreur technique IA (DAST): {str(e)}'

            vuln_objects.append(Vulnerability(
                scan=scan,
                test_id=a['test_id'],
                test_name=a['test_name'],
                issue_text=a['issue_text'],
                severity=a['severity'],
                confidence=a['confidence'],
                filename=a['filename'],
                line_number=a.get('line_number', 0),
                code_snippet=a.get('code_snippet', ''),
                cwe=a.get('cwe', ''),
                more_info=a.get('more_info', '')[:1000],
                llm_score=llm_fb_score,
                llm_explanation=llm_fb_reasoning,
                is_dast=True,
                solution=a.get('solution', ''),
            ))
        Vulnerability.objects.bulk_create(vuln_objects)

        try:
            if result.get('raw'):
                DojoMapper.save_and_push_to_dojo(result['raw'], 'zap')
        except Exception as e:
            logger.error(f"Error triggering DefectDojo integration in Auto-DAST scan: {e}")

        return Response({
            'scan_id': scan.id,
            'status': 'COMPLETED',
            'target_url': target_url,
            'metrics': {'total_issues': len(alerts), 'high': high_count, 'medium': medium_count, 'low': low_count},
            'vulnerabilities': alerts,
        })

    except Exception as e:
        logger.exception(f"Auto-DAST failed for {repo_full_name}: {e}")
        scan.status = 'FAILED'
        scan.dast_status = 'FAILED'
        scan.error_message = str(e)
        scan.completed_at = timezone.now()
        scan.save()
        return Response({'error': str(e), 'scan_id': scan.id}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    finally:
        if container_info and container_info.get('container_name'):
            logger.info(f"Cleaning up container: {container_info['container_name']}")
            stop_and_cleanup_container(container_info['container_name'])
            
        if repo_path and os.path.exists(repo_path):
            logger.info(f"Cleaning up temporary repo: {repo_path}")
            shutil.rmtree(repo_path, ignore_errors=True)
