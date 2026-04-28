import os
import json
import shutil
import subprocess
import tempfile
import logging

from core.utils.repo_utils import clone_repo

logger = logging.getLogger(__name__)


def run_semgrep(repo_path: str, targets: list = None) -> dict:
    scan_targets = []
    if targets:
        for t in targets:
            full_path = os.path.join(repo_path, t)
            if os.path.exists(full_path):
                scan_targets.append(full_path)

    if not scan_targets:
        scan_targets = [repo_path]

    try:
        subprocess.run(['semgrep', '--version'], capture_output=True, check=True, timeout=10)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return {'error': "Semgrep n'est pas installé ou n'est pas dans le PATH."}

    try:
        result = subprocess.run(
            ['semgrep', 'scan', '--json', '--config=p/owasp-top-ten'] + scan_targets,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode not in [0, 1]:
            if not result.stdout.strip():
                return {'error': result.stderr or "Semgrep returned no output"}

        if not result.stdout.strip():
            return {}

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Semgrep JSON decode error: {e}")
            return {'error': f"JSON parse error: {e}"}

    except subprocess.TimeoutExpired:
        return {'error': "Semgrep timeout (exceeded 10 minutes)"}
    except Exception as e:
        logger.exception("Semgrep subprocess failed")
        return {'error': str(e)}


def parse_semgrep_results(semgrep_output: dict, repo_path: str) -> list:
    severity_map = {'ERROR': 'HIGH', 'WARNING': 'MEDIUM', 'INFO': 'LOW'}
    vulnerabilities = []

    for issue in semgrep_output.get('results', []):
        filename = issue.get('path', '')
        if repo_path in filename:
            filename = filename.replace(repo_path, '').lstrip('/').lstrip('\\')

        references = issue.get('extra', {}).get('metadata', {}).get('references', [])
        vulnerabilities.append({
            'test_id': issue.get('check_id', 'SEMGREP'),
            'test_name': 'Semgrep',
            'issue_text': issue.get('extra', {}).get('message', ''),
            'severity': severity_map.get(issue.get('severity', 'INFO'), 'LOW'),
            'confidence': 'HIGH',
            'filename': filename,
            'line_number': issue.get('start', {}).get('line', 0),
            'line_range': [issue.get('start', {}).get('line', 0), issue.get('end', {}).get('line', 0)],
            'code_snippet': issue.get('extra', {}).get('lines', ''),
            'cwe': '',
            'more_info': references[0] if references else '',
        })

    return vulnerabilities


def run_full_semgrep_scan(
    clone_url: str,
    access_token: str,
    repo_owner: str,
    repo_name: str,
    repo_path: str = None,
    targets: list = None,
) -> dict:
    """
    Clone (si repo_path est None) → Semgrep → parse → cleanup.
    Si repo_path est fourni, le clone est ignoré et le répertoire n'est pas supprimé.
    """
    is_temp = repo_path is None
    if is_temp:
        repo_path = tempfile.mkdtemp(prefix='vulnops_semgrep_')

    try:
        if is_temp:
            logger.info(f"Cloning {repo_owner}/{repo_name} for Semgrep scan")
            clone_repo(clone_url, access_token, repo_path)

        logger.info(f"Running Semgrep on {repo_path}")
        semgrep_result = run_semgrep(repo_path, targets=targets)

        if 'error' in semgrep_result:
            return {'success': False, 'error': semgrep_result['error']}

        vulnerabilities = parse_semgrep_results(semgrep_result, repo_path)
        files_analyzed = len(set(v['filename'] for v in vulnerabilities)) if vulnerabilities else 0

        return {
            'success': True,
            'vulnerabilities': vulnerabilities,
            'metrics': {
                'total_issues': len(vulnerabilities),
                'high_count': sum(1 for v in vulnerabilities if v['severity'] == 'HIGH'),
                'medium_count': sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM'),
                'low_count': sum(1 for v in vulnerabilities if v['severity'] == 'LOW'),
                'files_analyzed': files_analyzed,
            },
            'raw_output': json.dumps(semgrep_result),
        }

    except Exception as e:
        logger.exception("Semgrep scan failed unexpectedly")
        return {'success': False, 'error': f'Erreur inattendue (Semgrep): {e}'}
    finally:
        if is_temp and os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)
