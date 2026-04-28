import os
import shutil
import subprocess
import tempfile
import json
import logging

from core.utils.repo_utils import clone_repo

logger = logging.getLogger(__name__)


def run_brakeman(repo_path: str) -> dict:
    if not shutil.which('docker'):
        return {'error': "Docker n'est pas installé."}

    abs_repo_path = os.path.abspath(repo_path)
    if os.name == 'nt':
        drive = abs_repo_path[0].lower()
        normalized = '/' + drive + abs_repo_path[2:].replace('\\', '/')
        volume_mapping = f"{normalized}:/code"
    else:
        volume_mapping = f"{abs_repo_path}:/code"

    try:
        docker_cmd = [
            'docker', 'run', '--rm',
            '-v', volume_mapping,
            '-w', '/code',
            'presidentbeef/brakeman',
            '--format', 'json', '--force',
        ]

        logger.info(f"Running Brakeman Docker command: {' '.join(docker_cmd)}")
        result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=900, encoding='utf-8')
        output = result.stdout or ""

        if not output.strip() and result.stderr:
            if "docker: Error" in result.stderr:
                return {'error': f"Erreur Docker: {result.stderr[:200]}"}

        try:
            return {'json': json.loads(output)}
        except json.JSONDecodeError:
            if result.returncode != 0:
                stderr = result.stderr or "Erreur inconnue"
                if "Not a Rails application" in stderr:
                    return {'error': "Ce projet n'est pas une application Ruby on Rails valide."}
                return {'error': f"Brakeman a échoué (code {result.returncode}): {stderr[:200]}"}
            return {'json': {'warnings': []}}

    except subprocess.TimeoutExpired:
        return {'error': "Brakeman timeout (exceeded 15 minutes)"}
    except Exception as e:
        logger.exception("Brakeman Docker execution failed")
        return {'error': str(e)}


def parse_brakeman_results(json_data: dict, repo_path: str) -> list:
    severity_map = {'HIGH': 'HIGH', 'MEDIUM': 'MEDIUM', 'WEAK': 'MEDIUM'}
    vulnerabilities = []
    for warning in json_data.get('warnings', []):
        severity_raw = warning.get('confidence', 'Low').upper()
        severity = severity_map.get(severity_raw, 'LOW')
        vulnerabilities.append({
            'test_id': warning.get('check_name', 'BRAKEMAN'),
            'test_name': f"Brakeman ({warning.get('warning_type', 'Security')})",
            'issue_text': warning.get('message', ''),
            'severity': severity,
            'confidence': warning.get('confidence', 'High').upper(),
            'filename': warning.get('file', ''),
            'line_number': warning.get('line', 0),
            'line_range': [warning.get('line', 0), warning.get('line', 0)],
            'code_snippet': (warning.get('code') or '').strip(),
            'cwe': '',
            'more_info': warning.get('link', 'https://brakemanscanner.org/docs/warning_types/'),
        })
    return vulnerabilities


def run_full_brakeman_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    base_tmp = os.path.abspath('tmp')
    os.makedirs(base_tmp, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_brakeman_', dir=base_tmp)

    try:
        logger.info(f"Cloning {repo_owner}/{repo_name} for Brakeman scan")
        clone_repo(clone_url, access_token, tmp_dir)

        logger.info(f"Running Brakeman on {tmp_dir}")
        brakeman_result = run_brakeman(tmp_dir)

        if 'error' in brakeman_result:
            return {'success': False, 'error': brakeman_result['error']}

        json_data = brakeman_result.get('json', {})
        vulnerabilities = parse_brakeman_results(json_data, tmp_dir)

        return {
            'success': True,
            'vulnerabilities': vulnerabilities,
            'metrics': {
                'total_issues': len(vulnerabilities),
                'high_count': sum(1 for v in vulnerabilities if v['severity'] == 'HIGH'),
                'medium_count': sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM'),
                'low_count': sum(1 for v in vulnerabilities if v['severity'] == 'LOW'),
                'files_analyzed': json_data.get('scan_info', {}).get('number_of_files', 0),
            },
            'raw_output': json.dumps(json_data),
        }

    except Exception as e:
        logger.exception("Brakeman scan failed unexpectedly")
        return {'success': False, 'error': f'Erreur inattendue (Brakeman): {e}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
