import logging
import os
import shutil
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from ..models import ScanResult, Vulnerability
from ..scanner_orchestrator import AutoScannerOrchestrator
from scanners.sast.bandit_runner import run_full_scan as run_bandit_scan
from scanners.sast.sonar_runner import run_full_sonar_scan
from scanners.sast.eslint_runner import run_full_eslint_scan
from scanners.sast.semgrep_runner import run_full_semgrep_scan
from scanners.sast.cppcheck_runner import run_full_cppcheck_scan
from scanners.sast.gosec_runner import run_full_gosec_scan
from scanners.sast.psalm_runner import run_full_psalm_scan
from scanners.sast.brakeman_runner import run_full_brakeman_scan
from scanners.sast.clippy_runner import run_full_clippy_scan
from scanners.sast.detekt_runner import run_full_detekt_scan
from scanners.sca.dependency_check_runner import run_dependency_check, parse_dependency_check_results
from scanners.container.trivy_runner import run_trivy, parse_trivy_results
from rag.llm_scoring import get_direct_llm_score
from integrations.defectdojo.mapper import DojoMapper

logger = logging.getLogger(__name__)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def auto_select_scanners(request):
    """
    Auto-détecte les langages et frameworks d'un projet.
    """
    clone_url = request.data.get('clone_url', '')
    repo_full_name = request.data.get('repo_full_name', '')
    repo_name = request.data.get('repo_name', '')
    repo_owner = request.data.get('repo_owner', '')
    
    if not clone_url or not repo_full_name:
        return Response(
            {'error': 'clone_url et repo_full_name sont requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    custom_token = request.data.get('custom_token')
    access_token = custom_token
    if not access_token and request.user.is_authenticated:
        try:
            access_token = request.user.github_profile.github_access_token
        except Exception:
            pass
    
    try:
        orchestrator = AutoScannerOrchestrator()
        result = orchestrator.auto_select_scanners(
            clone_url=clone_url,
            github_token=access_token,
            repo_owner=repo_owner,
            repo_name=repo_name
        )
        
        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'repo_full_name': repo_full_name,
            'analysis': result['analysis'],
            'suggested_scanners': result['suggested_scanners'],
            'reasoning': result['reasoning'],
            'confidence': result['confidence'],
            'source': result['source'],
            'message': f"Auto-selected {len(result['suggested_scanners'])} scanner(s) for {repo_full_name}"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Auto-selection error: {e}", exc_info=True)
        return Response(
            {'error': f"Auto-selection failed: {str(e)}", 'suggested_scanners': ['sonarcloud'], 'fallback': True},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def auto_trigger_scan(request):
    """
    Auto-détecte les langages et lance automatiquement les scans.
    """
    clone_url = request.data.get('clone_url', '')
    repo_full_name = request.data.get('repo_full_name', '')
    repo_name = request.data.get('repo_name', '')
    repo_owner = request.data.get('repo_owner', '')
    run_sca = request.data.get('run_sca', False)
    run_container = request.data.get('run_container', False)
    run_sast = request.data.get('run_sast', True)
    targets = request.data.get('targets', [])
    
    if not clone_url or not repo_full_name:
        return Response(
            {'error': 'clone_url et repo_full_name sont requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    custom_token = request.data.get('custom_token')
    access_token = custom_token
    if not access_token and request.user.is_authenticated:
        try:
            access_token = request.user.github_profile.github_access_token
        except Exception:
            pass
    
    repo_path = None
    is_temp_managed_here = False
    try:
        orchestrator = AutoScannerOrchestrator()
        selection_result = orchestrator.auto_select_scanners(
            clone_url=clone_url,
            github_token=access_token,
            repo_owner=repo_owner,
            repo_name=repo_name,
            cleanup=False
        )
        
        if selection_result['success']:
            repo_path = selection_result.get('temp_dir')
            is_temp_managed_here = True
        
        suggested = selection_result.get('suggested_scanners', ['sonarcloud'])
        if suggested:
            suggested = [suggested[0]]
        else:
            suggested = ['sonarcloud']
        
        scan_results = []
        scanner_functions = {
            'bandit': run_bandit_scan,
            'sonarcloud': run_full_sonar_scan,
            'eslint': run_full_eslint_scan,
            'semgrep': run_full_semgrep_scan,
            'cppcheck': run_full_cppcheck_scan,
            'gosec': run_full_gosec_scan,
            'psalm': run_full_psalm_scan,
            'brakeman': run_full_brakeman_scan,
            'clippy': run_full_clippy_scan,
            'detekt': run_full_detekt_scan,
        }
        
        dojo_uploads = []

        for scanner_type in suggested:
            if scanner_type not in scanner_functions:
                continue
            
            scan = ScanResult.objects.create(
                user=request.user if request.user.is_authenticated else None,
                repo_owner=repo_owner,
                repo_name=repo_name,
                repo_full_name=repo_full_name,
                scanner_type=scanner_type,
                status='RUNNING' if run_sast else 'COMPLETED',
                run_sast=run_sast,
                run_sca=run_sca,
                sca_status='PENDING' if run_sca else 'FAILED',
                run_container=run_container,
                container_status='PENDING' if run_container else 'FAILED',
            )

            current_repo_path = repo_path
            
            try:
                if run_sast:
                    if scanner_type == 'bandit':
                        result = scanner_functions[scanner_type](clone_url, access_token, repo_path=current_repo_path, targets=targets)
                    elif scanner_type == 'semgrep':
                        result = scanner_functions[scanner_type](clone_url, access_token, repo_owner, repo_name, repo_path=current_repo_path, targets=targets)
                    elif scanner_type == 'eslint':
                        result = scanner_functions[scanner_type](clone_url, access_token, repo_owner, repo_name, targets=targets)
                    else:
                        result = scanner_functions[scanner_type](clone_url, access_token, repo_owner, repo_name)
                else:
                    result = {'success': True, 'vulnerabilities': []}
                
                sca_vulnerabilities = []
                if run_sca and result['success']:
                    try:
                        scan.sca_status = 'RUNNING'
                        scan.save()
                        
                        dc_result = run_dependency_check(repo_path, targets=targets)
                        if dc_result['success']:
                            sca_vulnerabilities = parse_dependency_check_results(dc_result['data'], repo_path)
                            scan.sca_status = 'COMPLETED'
                            scan.sca_high_count = sum(1 for v in sca_vulnerabilities if v.get('severity') == 'HIGH')
                            scan.sca_medium_count = sum(1 for v in sca_vulnerabilities if v.get('severity') == 'MEDIUM')
                            scan.sca_low_count = sum(1 for v in sca_vulnerabilities if v.get('severity') == 'LOW')
                        else:
                            scan.sca_status = 'FAILED'
                    except Exception as e:
                        logger.error(f"SCA (Dependency-Check) failed: {e}")
                        scan.sca_status = 'FAILED'
                    scan.save()

                container_vulnerabilities = []
                if run_container and result['success']:
                    try:
                        scan.container_status = 'RUNNING'
                        scan.save()
                        
                        trivy_result = run_trivy(repo_path, targets=targets)
                        if trivy_result['success']:
                            container_vulnerabilities = parse_trivy_results(trivy_result['data'], repo_path)
                            # Marquer comme container au lieu de SCA
                            for v in container_vulnerabilities:
                                v['is_sca'] = False
                                v['is_container'] = True
                            
                            scan.container_status = 'COMPLETED'
                            scan.container_critical_count = sum(1 for v in container_vulnerabilities if v.get('severity') == 'CRITICAL')
                            scan.container_high_count = sum(1 for v in container_vulnerabilities if v.get('severity') == 'HIGH')
                            scan.container_medium_count = sum(1 for v in container_vulnerabilities if v.get('severity') == 'MEDIUM')
                            scan.container_low_count = sum(1 for v in container_vulnerabilities if v.get('severity') == 'LOW')
                        else:
                            scan.container_status = 'FAILED'
                    except Exception as e:
                        logger.error(f"Container scan (Trivy) failed: {e}")
                        scan.container_status = 'FAILED'
                    scan.save()
                
                if not result['success']:
                    error_msg = result.get('error', 'Erreur inconnue')
                    scan.status = 'FAILED'
                    scan.error_message = error_msg
                    scan.completed_at = timezone.now()
                    scan.save()
                    
                    scan_results.append({
                        'apps.scans': scanner_type,
                        'status': 'FAILED',
                        'error': error_msg,
                        'scan_id': scan.id
                    })
                else:
                    vulnerabilities_data = result['vulnerabilities']
                    all_vulns = vulnerabilities_data + sca_vulnerabilities + container_vulnerabilities
                    total_issues = len(all_vulns)
                    
                    scan.status = 'COMPLETED'
                    scan.completed_at = timezone.now()
                    scan.total_issues = total_issues
                    scan.save()
                    
                    context_summary = f"Dépôt {repo_full_name}. Scanner: {scanner_type}. Total: {total_issues}"

                    vuln_objects = []
                    for i, v in enumerate(vulnerabilities_data):
                        # Score direct pour l'ensemble des vulnérabilités SAST
                        # Note: Une version asynchrone via Celery serait préférable pour éviter les Timeouts HTTP
                        try:
                            ai_res = get_direct_llm_score(
                                test_name=v['test_name'],
                                issue_text=v['issue_text'],
                                severity=v['severity'],
                                context_summary=context_summary,
                                code_snippet=v.get('code_snippet')
                            )
                            llm_fb_score = ai_res.get('score', 0.5)
                            llm_fb_reasoning = ai_res.get('reasoning', 'Analyse IA réussie')
                        except Exception as e:
                            logger.warning(f"AI Scoring failed for {v['test_id']}: {e}")
                            llm_fb_score = 0.5
                            llm_fb_reasoning = f'Erreur technique IA: {str(e)}'
                        
                        vuln_objects.append(Vulnerability(
                            scan=scan,
                            test_id=v['test_id'],
                            test_name=v['test_name'],
                            issue_text=v['issue_text'],
                            severity=v['severity'],
                            confidence=v['confidence'],
                            filename=v.get('filename'),
                            line_number=v.get('line_number'),
                            line_range=v.get('line_range'),
                            code_snippet=v.get('code_snippet'),
                            cwe=v.get('cwe'),
                            llm_score=llm_fb_score,
                            llm_explanation=llm_fb_reasoning,
                            more_info=v.get('more_info'),
                            is_sca=False,
                            is_dast=False
                        ))
                    
                    for v in sca_vulnerabilities:
                        # Scoring IA pour les vulnérabilités SCA
                        try:
                            ai_res = get_direct_llm_score(
                                test_name=v['test_name'],
                                issue_text=v['issue_text'],
                                severity=v['severity'],
                                context_summary=context_summary,
                                code_snippet=v.get('code_snippet', '')
                            )
                            llm_fb_score = ai_res.get('score', 0.5)
                            llm_fb_reasoning = ai_res.get('reasoning', 'Analyse SCA IA réussie')
                        except Exception as e:
                            logger.warning(f"AI Scoring failed for SCA {v['test_id']}: {e}")
                            llm_fb_score = 0.5
                            llm_fb_reasoning = f'Erreur technique IA (SCA): {str(e)}'

                        vuln_objects.append(Vulnerability(
                            scan=scan,
                            test_id=v['test_id'],
                            test_name=v['test_name'],
                            issue_text=v['issue_text'],
                            severity=v['severity'],
                            confidence=v['confidence'],
                            filename=v.get('filename', ''),
                            line_number=v.get('line_number', 0),
                            line_range=v.get('line_range', []),
                            code_snippet=v.get('code_snippet', ''),
                            cwe=v.get('cwe', ''),
                            more_info=v.get('more_info', ''),
                            llm_score=llm_fb_score,
                            llm_explanation=llm_fb_reasoning,
                            is_sca=True,
                            is_container=False
                        ))

                    for v in container_vulnerabilities:
                        # Scoring IA pour Container Scanning
                        try:
                            ai_res = get_direct_llm_score(
                                test_name=v['test_name'],
                                issue_text=v['issue_text'],
                                severity=v['severity'],
                                context_summary=context_summary,
                                code_snippet=v.get('code_snippet', '')
                            )
                            llm_fb_score = ai_res.get('score', 0.5)
                            llm_fb_reasoning = ai_res.get('reasoning', 'Analyse Container IA réussie')
                        except Exception as e:
                            logger.warning(f"AI Scoring failed for Container {v['test_id']}: {e}")
                            llm_fb_score = 0.5
                            llm_fb_reasoning = f'Erreur technique IA (Container): {str(e)}'

                        vuln_objects.append(Vulnerability(
                            scan=scan,
                            test_id=v['test_id'],
                            test_name=v['test_name'],
                            issue_text=v['issue_text'],
                            severity=v['severity'],
                            confidence=v['confidence'],
                            filename=v.get('filename', ''),
                            line_number=v.get('line_number', 0),
                            line_range=v.get('line_range', []),
                            code_snippet=v.get('code_snippet', ''),
                            cwe=v.get('cwe', ''),
                            more_info=v.get('more_info', ''),
                            llm_score=llm_fb_score,
                            llm_explanation=llm_fb_reasoning,
                            is_sca=False,
                            is_container=True
                        ))
                    
                    Vulnerability.objects.bulk_create(vuln_objects)

                    dojo_uploads.append({
                        'type': 'sast',
                        'data': result.get('raw_output'),
                        'apps.scans': scanner_type
                    })
                    if run_sca and 'dc_result' in locals() and dc_result.get('success'):
                        dojo_uploads.append({
                            'type': 'sca',
                            'data': json.dumps(dc_result['data']),
                            'apps.scans': 'dependency-check'
                        })
                    if run_container and 'trivy_result' in locals() and trivy_result.get('success'):
                        dojo_uploads.append({
                            'type': 'container',
                            'data': json.dumps(trivy_result['data']),
                            'apps.scans': 'trivy'
                        })

                    scan_results.append({
                        'apps.scans': scanner_type,
                        'status': 'COMPLETED',
                        'metrics': {'total': total_issues},
                        'scan_id': scan.id
                    })
            except Exception as e:
                error_msg = str(e)
                scan.status = 'FAILED'
                scan.error_message = error_msg
                scan.completed_at = timezone.now()
                scan.save()
                
                scan_results.append({
                    'apps.scans': scanner_type,
                    'status': 'FAILED',
                    'error': error_msg,
                    'scan_id': scan.id
                })
        
        if dojo_uploads:
            # Envoi Dojo différé
            pass
        
        return Response({
            'success': True,
            'repo_full_name': repo_full_name,
            'auto_selected_scanners': suggested,
            'scan_results': scan_results,
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f"Auto-triggered scan failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        if is_temp_managed_here and repo_path and os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_project(request):
    """
    Analyse un projet existant et recommande les scanners.
    """
    project_path = request.data.get('project_path', '')
    
    if not project_path:
        return Response(
            {'error': 'project_path est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        orchestrator = AutoScannerOrchestrator()
        result = orchestrator.analyze_existing_project(project_path)
        
        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'project_path': project_path,
            'analysis': result['analysis'],
            'suggested_scanners': result['suggested_scanners'],
            'reasoning': result['reasoning'],
            'confidence': result['confidence'],
            'source': result['source']
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f"Analysis failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
