import logging
import os
import shutil
import tempfile

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from ..models import ScanResult, Vulnerability
from ..scanner_orchestrator import AutoScannerOrchestrator
from ..risk_scorer import compute_risk_score
from core.utils.repo_utils import clone_repo

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
from scanners.container.trivy_runner import run_trivy_fs, run_trivy_image, parse_trivy_results
from scanners.dast.zaproxy_runner import run_zap_baseline_scan

from rag.llm_scoring import get_batch_llm_scores

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

SAST_RUNNER_MAP = {
    'bandit':     run_bandit_scan,
    'sonarcloud': run_full_sonar_scan,
    'eslint':     run_full_eslint_scan,
    'semgrep':    run_full_semgrep_scan,
    'cppcheck':   run_full_cppcheck_scan,
    'gosec':      run_full_gosec_scan,
    'psalm':      run_full_psalm_scan,
    'brakeman':   run_full_brakeman_scan,
    'clippy':     run_full_clippy_scan,
    'detekt':     run_full_detekt_scan,
}


def _get_token(request) -> str:
    token = request.data.get('custom_token')
    if not token and request.user.is_authenticated:
        try:
            token = request.user.github_profile.github_access_token
        except Exception:
            pass
    return token or ''


def _build_vuln_objects(scan, vulns: list, context_summary: str, is_sca=False, is_container=False, is_dast=False):
    if not vulns:
        return []

    try:
        scores = get_batch_llm_scores(vulns, context_summary)
    except Exception as e:
        logger.warning(f"Batch LLM scoring failed, using defaults: {e}")
        scores = [{"score": 0.5, "reasoning": f"Erreur IA: {e}"}] * len(vulns)

    objects = []
    for v, ai in zip(vulns, scores):
        score = float(ai.get("score", 0.5))
        reasoning = ai.get("reasoning", "Analyse IA")
        risk = compute_risk_score({
            'severity': v.get('severity', 'LOW'),
            'confidence': v.get('confidence', 'MEDIUM'),
            'filename': v.get('filename', ''),
            'is_dast': is_dast,
            'llm_score': score,
        })
        objects.append(Vulnerability(
            scan=scan,
            test_id=v.get('test_id', ''),
            test_name=v.get('test_name', ''),
            issue_text=v.get('issue_text', ''),
            severity=v.get('severity', 'LOW'),
            confidence=v.get('confidence', 'MEDIUM'),
            filename=v.get('filename', ''),
            line_number=v.get('line_number', 0),
            line_range=v.get('line_range', []),
            code_snippet=v.get('code_snippet', ''),
            cwe=v.get('cwe', ''),
            more_info=(v.get('more_info') or '')[:1000],
            llm_score=score,
            llm_explanation=reasoning,
            risk_score=risk,
            is_sca=is_sca,
            is_container=is_container,
            is_dast=is_dast,
            solution=v.get('solution', ''),
        ))
    return objects


def _run_sast(scanner_type: str, clone_url: str, access_token: str,
              repo_owner: str, repo_name: str, repo_path: str, targets: list) -> dict:
    """Dispatches the SAST runner with the correct argument signature."""
    fn = SAST_RUNNER_MAP.get(scanner_type)
    if not fn:
        return {'success': False, 'error': f"Scanner '{scanner_type}' inconnu"}

    if scanner_type == 'bandit':
        return fn(clone_url, access_token, repo_path=repo_path, targets=targets)
    if scanner_type in ('semgrep', 'eslint'):
        return fn(clone_url, access_token, repo_owner, repo_name, repo_path=repo_path, targets=targets)
    return fn(clone_url, access_token, repo_owner, repo_name)


# ------------------------------------------------------------------ #
# Endpoint: auto-select only (preview, no scan)                        #
# ------------------------------------------------------------------ #

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def auto_select_scanners(request):
    """
    Clones a repo, detects languages and returns which scanners would be selected.
    Does NOT run any scan.

    Body:
      clone_url, repo_full_name, repo_owner, repo_name
      scan_mode  (fast | standard | deep)  — default: standard
      branch     (optional)
    """
    clone_url = request.data.get('clone_url', '')
    repo_full_name = request.data.get('repo_full_name', '')
    repo_name = request.data.get('repo_name', '')
    repo_owner = request.data.get('repo_owner', '')
    scan_mode = request.data.get('scan_mode', 'standard')
    branch = request.data.get('branch')

    if not clone_url or not repo_full_name:
        return Response({'error': 'clone_url et repo_full_name sont requis'}, status=status.HTTP_400_BAD_REQUEST)

    if scan_mode not in ('fast', 'standard', 'deep'):
        return Response({'error': "scan_mode doit être 'fast', 'standard' ou 'deep'"}, status=status.HTTP_400_BAD_REQUEST)

    access_token = _get_token(request)

    try:
        orchestrator = AutoScannerOrchestrator()
        result = orchestrator.auto_select_scanners(
            clone_url=clone_url,
            github_token=access_token,
            repo_owner=repo_owner,
            repo_name=repo_name,
            branch=branch,
            scan_mode=scan_mode,
        )

        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'repo_full_name': repo_full_name,
            'scan_mode': scan_mode,
            'analysis': result['analysis'],
            'suggested_scanners': result['suggested_scanners'],
            'reasoning': result['reasoning'],
            'confidence': result['confidence'],
            'source': result['source'],
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Auto-selection error: {e}", exc_info=True)
        return Response(
            {'error': f"Auto-selection failed: {e}", 'suggested_scanners': ['semgrep'], 'fallback': True},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ------------------------------------------------------------------ #
# Endpoint: auto-trigger (detect + run)                                #
# ------------------------------------------------------------------ #

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def auto_trigger_scan(request):
    """
    Detects the project language and runs the selected scan types.

    Body:
      clone_url        (required)
      repo_full_name   (required)
      repo_owner, repo_name
      branch           (optional)

      scan_mode        fast | standard | deep   (default: fast)
                       → controls which SAST scanners are chosen

      run_sast         bool  (default: true)
      run_sca          bool  (default: false)  — filesystem dependency scan via Trivy
      run_container    bool  (default: false)  — container/image scan via Trivy
      run_dast         bool  (default: false)  — dynamic scan via OWASP ZAP
      dast_target_url  str   (required if run_dast=true)

      targets          list  (optional)  — subdirectories to limit the scan
    """
    # ── Input parsing ──────────────────────────────────────────────
    clone_url      = request.data.get('clone_url', '')
    repo_full_name = request.data.get('repo_full_name', '')
    repo_name      = request.data.get('repo_name', '')
    repo_owner     = request.data.get('repo_owner', '')
    branch         = request.data.get('branch')
    targets        = request.data.get('targets', [])

    scan_mode        = request.data.get('scan_mode', 'fast')
    run_sast         = bool(request.data.get('run_sast', True))
    run_sca          = bool(request.data.get('run_sca', False))
    run_container    = bool(request.data.get('run_container', False))
    run_dast         = bool(request.data.get('run_dast', False))
    dast_target_url  = request.data.get('dast_target_url', '').strip()
    container_image  = request.data.get('container_image', '').strip()

    # ── Validation ─────────────────────────────────────────────────
    if not clone_url or not repo_full_name:
        return Response({'error': 'clone_url et repo_full_name sont requis'}, status=status.HTTP_400_BAD_REQUEST)

    if scan_mode not in ('fast', 'standard', 'deep'):
        return Response({'error': "scan_mode doit être 'fast', 'standard' ou 'deep'"}, status=status.HTTP_400_BAD_REQUEST)

    if run_dast and not dast_target_url:
        return Response({'error': 'dast_target_url est requis quand run_dast=true'}, status=status.HTTP_400_BAD_REQUEST)

    if run_container and not container_image:
        return Response({'error': 'container_image est requis quand run_container=true (ex: "myapp:latest")'}, status=status.HTTP_400_BAD_REQUEST)

    if not run_sast and not run_sca and not run_container and not run_dast:
        return Response({'error': 'Au moins un type de scan doit être activé'}, status=status.HTTP_400_BAD_REQUEST)

    access_token = _get_token(request)

    # ── Step 1: Determine SAST scanners & clone repo ───────────────
    repo_path = None
    is_temp = False
    suggested_scanners = []
    detection_info = {}

    try:
        if run_sast:
            if scan_mode == 'fast':
                # Fast mode: always semgrep, skip LLM — clone directly
                suggested_scanners = ['semgrep']
                detection_info = {
                    'source': 'mode:fast',
                    'reasoning': 'Fast mode — Semgrep selected automatically',
                    'confidence': 1.0,
                }
                repo_path = tempfile.mkdtemp(prefix='vulnops_fast_')
                is_temp = True
                clone_repo(clone_url, access_token, repo_path)

            else:
                # Standard / Deep: LLM detection
                orchestrator = AutoScannerOrchestrator()
                sel = orchestrator.auto_select_scanners(
                    clone_url=clone_url,
                    github_token=access_token,
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    branch=branch,
                    cleanup=False,
                    scan_mode=scan_mode,
                )
                suggested_scanners = sel.get('suggested_scanners', ['semgrep'])
                detection_info = {
                    'source': sel.get('source', 'fallback'),
                    'reasoning': sel.get('reasoning', ''),
                    'confidence': sel.get('confidence', 0.7),
                    'analysis': sel.get('analysis', {}),
                }
                if sel.get('success'):
                    repo_path = sel.get('temp_dir')
                    is_temp = True

        elif run_sca or run_container:
            # No SAST but SCA/Container needs a repo
            repo_path = tempfile.mkdtemp(prefix='vulnops_sca_')
            is_temp = True
            clone_repo(clone_url, access_token, repo_path)

        # ── Step 2: SAST scans ─────────────────────────────────────
        scan_results = []

        for scanner_type in suggested_scanners:
            if scanner_type not in SAST_RUNNER_MAP:
                logger.warning(f"Scanner '{scanner_type}' not in runner map — skipping")
                continue

            scan = ScanResult.objects.create(
                user=request.user if request.user.is_authenticated else None,
                repo_owner=repo_owner,
                repo_name=repo_name,
                repo_full_name=repo_full_name,
                scanner_type=scanner_type,
                status='RUNNING',
                run_sast=True,
                run_sca=run_sca,
                sca_status='PENDING' if run_sca else 'SKIPPED',
                run_container=run_container,
                container_status='PENDING' if run_container else 'SKIPPED',
            )

            try:
                sast_result = _run_sast(scanner_type, clone_url, access_token,
                                        repo_owner, repo_name, repo_path, targets)

                # ── SCA via Trivy fs (dependency files) ───────────
                sca_vulns = []
                if run_sca:
                    scan.sca_status = 'RUNNING'
                    scan.save()
                    try:
                        trivy = run_trivy_fs(repo_path, targets=targets)
                        if trivy['success']:
                            sca_vulns = parse_trivy_results(trivy['data'], repo_path)
                            for v in sca_vulns:
                                v['is_sca'] = True
                                v['is_container'] = False
                            scan.sca_status = 'COMPLETED'
                            scan.sca_high_count   = sum(1 for v in sca_vulns if v['severity'] == 'HIGH')
                            scan.sca_medium_count = sum(1 for v in sca_vulns if v['severity'] == 'MEDIUM')
                            scan.sca_low_count    = sum(1 for v in sca_vulns if v['severity'] == 'LOW')
                        else:
                            scan.sca_status = 'FAILED'
                    except Exception as e:
                        logger.error(f"SCA (Trivy fs) failed: {e}")
                        scan.sca_status = 'FAILED'
                    scan.save()

                # ── Container via Trivy image ──────────────────────
                container_vulns = []
                if run_container:
                    scan.container_status = 'RUNNING'
                    scan.save()
                    try:
                        trivy = run_trivy_image(container_image)
                        if trivy['success']:
                            container_vulns = parse_trivy_results(trivy['data'], container_image)
                            for v in container_vulns:
                                v['is_sca'] = False
                                v['is_container'] = True
                            scan.container_status = 'COMPLETED'
                            scan.container_critical_count = sum(1 for v in container_vulns if v['severity'] == 'CRITICAL')
                            scan.container_high_count     = sum(1 for v in container_vulns if v['severity'] == 'HIGH')
                            scan.container_medium_count   = sum(1 for v in container_vulns if v['severity'] == 'MEDIUM')
                            scan.container_low_count      = sum(1 for v in container_vulns if v['severity'] == 'LOW')
                        else:
                            scan.container_status = 'FAILED'
                    except Exception as e:
                        logger.error(f"Container scan (Trivy image) failed: {e}")
                        scan.container_status = 'FAILED'
                    scan.save()

                # ── Finalise SAST scan record ──────────────────────
                if not sast_result['success']:
                    scan.status = 'FAILED'
                    scan.error_message = sast_result.get('error', 'Erreur inconnue')
                    scan.completed_at = timezone.now()
                    scan.save()
                    scan_results.append({'scanner': scanner_type, 'status': 'FAILED',
                                         'error': scan.error_message, 'scan_id': scan.id})
                else:
                    sast_vulns = sast_result['vulnerabilities']
                    all_vulns = sast_vulns + sca_vulns + container_vulns
                    scan.total_issues = len(all_vulns)
                    scan.status = 'COMPLETED'
                    scan.completed_at = timezone.now()
                    scan.save()

                    ctx = f"Dépôt {repo_full_name}. Scanner: {scanner_type}. Total: {len(all_vulns)}"
                    vuln_objects = (
                        _build_vuln_objects(scan, sast_vulns, ctx)
                        + _build_vuln_objects(scan, sca_vulns, ctx, is_sca=True)
                        + _build_vuln_objects(scan, container_vulns, ctx, is_container=True)
                    )
                    Vulnerability.objects.bulk_create(vuln_objects)
                    scan_results.append({'scanner': scanner_type, 'status': 'COMPLETED',
                                         'metrics': {'total': len(all_vulns)}, 'scan_id': scan.id})

            except Exception as e:
                logger.exception(f"Scanner '{scanner_type}' raised an unexpected error")
                scan.status = 'FAILED'
                scan.error_message = str(e)
                scan.completed_at = timezone.now()
                scan.save()
                scan_results.append({'scanner': scanner_type, 'status': 'FAILED',
                                     'error': str(e), 'scan_id': scan.id})

        # ── Step 3: SCA/Container only (no SAST requested) ─────────
        if not run_sast and (run_sca or run_container):
            scan = ScanResult.objects.create(
                user=request.user if request.user.is_authenticated else None,
                repo_owner=repo_owner,
                repo_name=repo_name,
                repo_full_name=repo_full_name,
                scanner_type='trivy',
                status='RUNNING',
                run_sast=False,
                run_sca=run_sca,
                sca_status='PENDING' if run_sca else 'SKIPPED',
                run_container=run_container,
                container_status='PENDING' if run_container else 'SKIPPED',
            )
            try:
                trivy_vulns = []
                if run_sca:
                    scan.sca_status = 'RUNNING'
                    scan.save()
                    trivy = run_trivy_fs(repo_path, targets=targets)
                    if trivy['success']:
                        v_list = parse_trivy_results(trivy['data'], repo_path)
                        for v in v_list:
                            v['is_sca'] = True
                            v['is_container'] = False
                        trivy_vulns += v_list
                        scan.sca_status = 'COMPLETED'
                        scan.sca_high_count   = sum(1 for v in v_list if v['severity'] == 'HIGH')
                        scan.sca_medium_count = sum(1 for v in v_list if v['severity'] == 'MEDIUM')
                        scan.sca_low_count    = sum(1 for v in v_list if v['severity'] == 'LOW')
                    else:
                        scan.sca_status = 'FAILED'
                    scan.save()

                if run_container:
                    scan.container_status = 'RUNNING'
                    scan.save()
                    trivy = run_trivy_image(container_image)
                    if trivy['success']:
                        v_list = parse_trivy_results(trivy['data'], container_image)
                        for v in v_list:
                            v['is_sca'] = False
                            v['is_container'] = True
                        trivy_vulns += v_list
                        scan.container_status = 'COMPLETED'
                        scan.container_critical_count = sum(1 for v in v_list if v['severity'] == 'CRITICAL')
                        scan.container_high_count     = sum(1 for v in v_list if v['severity'] == 'HIGH')
                        scan.container_medium_count   = sum(1 for v in v_list if v['severity'] == 'MEDIUM')
                        scan.container_low_count      = sum(1 for v in v_list if v['severity'] == 'LOW')
                    else:
                        scan.container_status = 'FAILED'
                    scan.save()

                scan.total_issues = len(trivy_vulns)
                scan.status = 'COMPLETED'
                scan.completed_at = timezone.now()
                scan.save()

                ctx = f"Dépôt {repo_full_name}. Scanner: Trivy. Total: {len(trivy_vulns)}"
                Vulnerability.objects.bulk_create(
                    _build_vuln_objects(scan, trivy_vulns, ctx,
                                        is_sca=run_sca, is_container=run_container)
                )
                scan_results.append({'scanner': 'trivy', 'status': 'COMPLETED',
                                     'metrics': {'total': len(trivy_vulns)}, 'scan_id': scan.id})
            except Exception as e:
                logger.exception("Trivy-only scan failed")
                scan.status = 'FAILED'
                scan.error_message = str(e)
                scan.completed_at = timezone.now()
                scan.save()
                scan_results.append({'scanner': 'trivy', 'status': 'FAILED',
                                     'error': str(e), 'scan_id': scan.id})

        # ── Step 4: DAST via OWASP ZAP ─────────────────────────────
        dast_result_summary = None
        if run_dast:
            dast_scan = ScanResult.objects.create(
                user=request.user if request.user.is_authenticated else None,
                repo_owner=repo_owner,
                repo_name=repo_name,
                repo_full_name=repo_full_name,
                scanner_type='zap',
                status='RUNNING',
                run_sast=False,
                run_dast=True,
                dast_status='RUNNING',
                dast_target_url=dast_target_url,
            )
            try:
                logger.info(f"Starting DAST scan (ZAP) against {dast_target_url}")
                zap = run_zap_baseline_scan(dast_target_url)

                if not zap['success']:
                    dast_scan.status = 'FAILED'
                    dast_scan.dast_status = 'FAILED'
                    dast_scan.error_message = zap.get('error', 'ZAP scan failed')
                    dast_scan.completed_at = timezone.now()
                    dast_scan.save()
                    scan_results.append({'scanner': 'zap', 'status': 'FAILED',
                                         'error': dast_scan.error_message, 'scan_id': dast_scan.id})
                else:
                    alerts = zap['data']
                    dast_scan.status = 'COMPLETED'
                    dast_scan.dast_status = 'COMPLETED'
                    dast_scan.completed_at = timezone.now()
                    dast_scan.total_issues = len(alerts)
                    dast_scan.dast_high_count   = sum(1 for a in alerts if a['severity'] == 'HIGH')
                    dast_scan.dast_medium_count = sum(1 for a in alerts if a['severity'] == 'MEDIUM')
                    dast_scan.dast_low_count    = sum(1 for a in alerts if a['severity'] == 'LOW')
                    dast_scan.save()

                    ctx = f"Dépôt {repo_full_name}. Scanner: ZAP (DAST). Total: {len(alerts)}"
                    Vulnerability.objects.bulk_create(
                        _build_vuln_objects(dast_scan, alerts, ctx, is_dast=True)
                    )
                    dast_result_summary = {
                        'scanner': 'zap', 'status': 'COMPLETED',
                        'metrics': {'total': len(alerts),
                                    'high': dast_scan.dast_high_count,
                                    'medium': dast_scan.dast_medium_count,
                                    'low': dast_scan.dast_low_count},
                        'scan_id': dast_scan.id,
                    }
                    scan_results.append(dast_result_summary)

            except Exception as e:
                logger.exception(f"DAST scan failed for {dast_target_url}")
                dast_scan.status = 'FAILED'
                dast_scan.dast_status = 'FAILED'
                dast_scan.error_message = str(e)
                dast_scan.completed_at = timezone.now()
                dast_scan.save()
                scan_results.append({'scanner': 'zap', 'status': 'FAILED',
                                     'error': str(e), 'scan_id': dast_scan.id})

        # ── Response ────────────────────────────────────────────────
        return Response({
            'success': True,
            'repo_full_name': repo_full_name,
            'scan_mode': scan_mode,
            'scan_types': {
                'sast': run_sast,
                'sca': run_sca,
                'container': run_container,
                'dast': run_dast,
            },
            'selected_sast_scanners': suggested_scanners,
            'detection': detection_info,
            'scan_results': scan_results,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(f"auto_trigger_scan failed for {repo_full_name}")
        return Response(
            {'error': f"Scan failed: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        if is_temp and repo_path and os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)


# ------------------------------------------------------------------ #
# Endpoint: analyze existing project path (local, admin use)           #
# ------------------------------------------------------------------ #

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_project(request):
    """
    Analyzes a project already on disk and recommends scanners.
    Body: { "project_path": "/abs/path", "scan_mode": "standard" }
    """
    project_path = request.data.get('project_path', '')
    scan_mode = request.data.get('scan_mode', 'standard')

    if not project_path:
        return Response({'error': 'project_path est requis'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        orchestrator = AutoScannerOrchestrator()
        result = orchestrator.analyze_existing_project(project_path)

        if not result['success']:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'success': True,
            'project_path': project_path,
            'scan_mode': scan_mode,
            'analysis': result['analysis'],
            'suggested_scanners': result['suggested_scanners'],
            'reasoning': result['reasoning'],
            'confidence': result['confidence'],
            'source': result['source'],
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f"Analysis failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
