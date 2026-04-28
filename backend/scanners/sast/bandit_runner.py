import os
import json
import shutil
import subprocess
import tempfile
import logging

import git
from django.conf import settings
from core.utils.repo_utils import clone_repo
from ..base import BaseScanner

logger = logging.getLogger(__name__)


def run_bandit(repo_path: str, targets: list = None) -> dict:
    """
    Exécute Bandit sur un répertoire ou des cibles spécifiques et retourne les résultats JSON.
    """
    scan_targets = []
    if targets:
        for t in targets:
            full_path = os.path.join(repo_path, t)
            if os.path.exists(full_path):
                scan_targets.append(full_path)

    if not scan_targets:
        scan_targets = [repo_path]

    try:
        subprocess.run(['bandit', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {'error': "Bandit n'est pas installé sur le système."}

    result = subprocess.run(
        ['bandit', '-r', '-f', 'json', '-ll', '--exit-zero'] + scan_targets,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if not result.stdout.strip():
        return {'error': result.stderr or "Aucune sortie reçue de Bandit."}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.error(f"Bandit JSON decode error: {e}")
        return {'error': f"Erreur lors du parsing des résultats : {e}"}


def parse_bandit_results(bandit_output: dict, repo_path: str) -> list:
    vulnerabilities = []
    for issue in bandit_output.get('results', []):
        filename = issue.get('filename', '')
        if repo_path in filename:
            filename = filename.replace(repo_path, '').lstrip('/').lstrip('\\')

        cwe_info = issue.get('issue_cwe', {})
        cwe = f"CWE-{cwe_info.get('id', '')}" if cwe_info.get('id') else ''

        vulnerabilities.append({
            'test_id': issue.get('test_id', ''),
            'test_name': issue.get('test_name', ''),
            'issue_text': issue.get('issue_text', ''),
            'severity': issue.get('issue_severity', 'LOW').upper(),
            'confidence': issue.get('issue_confidence', 'LOW').upper(),
            'filename': filename,
            'line_number': issue.get('line_number', 0),
            'line_range': issue.get('line_range', []),
            'code_snippet': issue.get('code', '').strip(),
            'cwe': cwe,
            'more_info': issue.get('more_info', ''),
        })
    return vulnerabilities


def get_metrics(bandit_output: dict) -> dict:
    metrics = bandit_output.get('metrics', {}).get('_totals', {})
    return {
        'total_issues': int(metrics.get('SEVERITY.HIGH', 0) + metrics.get('SEVERITY.MEDIUM', 0) + metrics.get('SEVERITY.LOW', 0)),
        'high_count': int(metrics.get('SEVERITY.HIGH', 0)),
        'medium_count': int(metrics.get('SEVERITY.MEDIUM', 0)),
        'low_count': int(metrics.get('SEVERITY.LOW', 0)),
        'files_analyzed': int(metrics.get('loc', 0)),
    }


class BanditRunner(BaseScanner):
    def __init__(self):
        super().__init__("Bandit")

    def run(self, target_path_or_url, **kwargs):
        result = run_full_scan(target_path_or_url, kwargs.get('access_token', ''), targets=kwargs.get('targets', []))
        return result['vulnerabilities'] if result['success'] else []


def run_full_scan(clone_url: str, access_token: str, repo_path: str = None, targets: list = None) -> dict:
    """
    Clone (si repo_path est None) → Bandit → parse → cleanup.
    Si repo_path est fourni, le clone est ignoré et le répertoire n'est pas supprimé.
    """
    is_temp = repo_path is None
    if is_temp:
        repo_path = tempfile.mkdtemp(prefix='vulnops_bandit_')

    try:
        if is_temp:
            clone_repo(clone_url, access_token, repo_path)

        bandit_output = run_bandit(repo_path, targets=targets)

        if 'error' in bandit_output:
            return {'success': False, 'error': bandit_output['error']}

        vulnerabilities = parse_bandit_results(bandit_output, repo_path)
        metrics = get_metrics(bandit_output)

        return {
            'success': True,
            'vulnerabilities': vulnerabilities,
            'metrics': metrics,
            'raw_output': json.dumps(bandit_output),
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Le scan a dépassé le délai de 5 minutes'}
    except git.GitCommandError as e:
        return {'success': False, 'error': f'Erreur de clonage Git: {e}'}
    except Exception as e:
        logger.exception("Bandit scan failed unexpectedly")
        return {'success': False, 'error': f'Erreur inattendue: {e}'}
    finally:
        if is_temp and os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)
