import os
import shutil
import subprocess
import tempfile
import json
import logging

from core.utils.repo_utils import clone_repo
from core.utils.docker_utils import get_docker_path_mapping, ensure_docker_image, run_docker_container

logger = logging.getLogger(__name__)


def run_gosec(repo_path: str) -> dict:
    image_name = 'securego/gosec'
    success, error_msg = ensure_docker_image(image_name)
    if not success:
        return {'error': error_msg}

    volume_mapping = get_docker_path_mapping(repo_path)
    try:
        result = run_docker_container(
            image_name=image_name,
            volume_mapping=volume_mapping,
            working_dir='/src',
            command=['-fmt=json', './...'],
            timeout=900,
        )

        output = result.stdout or ""

        if not output.strip() and result.stderr:
            if "docker: Error" in result.stderr:
                return {'error': f"Erreur Docker: {result.stderr[:200]}"}

        try:
            return {'json': json.loads(output)}
        except json.JSONDecodeError:
            if result.returncode != 0 and not output.strip():
                return {'error': f"Gosec a échoué (code {result.returncode}): {result.stderr[:200]}"}
            return {'json': {'Issues': []}}

    except subprocess.TimeoutExpired:
        return {'error': "Gosec timeout (exceeded 15 minutes)"}
    except Exception as e:
        logger.exception("Gosec Docker execution failed")
        return {'error': str(e)}


def parse_gosec_results(json_data: dict, repo_path: str) -> list:
    vulnerabilities = []
    for issue in json_data.get('Issues', []):
        filename = issue.get('file', '')
        if filename.startswith('/src/'):
            filename = filename[5:]

        line_str = issue.get('line', '0')
        line_number = int(line_str) if str(line_str).isdigit() else 0

        cwe_info = issue.get('cwe') or {}
        vulnerabilities.append({
            'test_id': issue.get('rule_id', 'GOSEC'),
            'test_name': 'Gosec',
            'issue_text': issue.get('details', ''),
            'severity': issue.get('severity', 'LOW').upper(),
            'confidence': issue.get('confidence', 'HIGH'),
            'filename': filename,
            'line_number': line_number,
            'line_range': [line_number, line_number],
            'code_snippet': issue.get('code', ''),
            'cwe': cwe_info.get('id', ''),
            'more_info': cwe_info.get('url', '') or f"https://securego.io/docs/rules/{issue.get('rule_id', '').lower()}.html",
        })
    return vulnerabilities


def run_full_gosec_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    base_tmp = os.path.abspath('tmp')
    os.makedirs(base_tmp, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_gosec_', dir=base_tmp)

    try:
        logger.info(f"Cloning {repo_owner}/{repo_name} for Gosec scan")
        clone_repo(clone_url, access_token, tmp_dir)

        logger.info(f"Running Gosec on {tmp_dir}")
        gosec_result = run_gosec(tmp_dir)

        if 'error' in gosec_result:
            return {'success': False, 'error': gosec_result['error']}

        vulnerabilities = parse_gosec_results(gosec_result.get('json', {}), tmp_dir)
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
            'raw_output': json.dumps(gosec_result.get('json', {})),
        }

    except Exception as e:
        logger.exception("Gosec scan failed unexpectedly")
        return {'success': False, 'error': f'Erreur inattendue (Gosec): {e}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
