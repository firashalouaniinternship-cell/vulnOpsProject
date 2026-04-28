import os
import shutil
import subprocess
import tempfile
import json
import logging

from core.utils.repo_utils import clone_repo
from core.utils.docker_utils import get_docker_path_mapping, ensure_docker_image, run_docker_container

logger = logging.getLogger(__name__)


def run_detekt(repo_path: str) -> dict:
    image_name = 'gradle:latest'
    success, error_msg = ensure_docker_image(image_name)
    if not success:
        return {'error': error_msg}

    volume_mapping = get_docker_path_mapping(repo_path)
    try:
        result = run_docker_container(
            image_name=image_name,
            volume_mapping=volume_mapping,
            working_dir='/workspace',
            command=[
                'sh', '-c',
                'gradle detekt --no-daemon 2>/dev/null || true && cat build/reports/detekt/detekt.json 2>/dev/null || echo "{}"',
            ],
            timeout=3600,
        )

        output = (result.stdout or "").strip()

        # Gradle produces logs before the JSON — find where it starts
        json_start = output.find('{')
        if json_start != -1:
            output = output[json_start:]

        try:
            return {'json': json.loads(output)}
        except json.JSONDecodeError:
            stderr = result.stderr or ""
            if 'gradle' in stderr.lower():
                return {'error': "Gradle n'est pas configuré ou build.gradle est invalide."}
            if 'kotlin' in stderr.lower():
                return {'error': "Pas de code Kotlin détecté ou projet non configuré pour Kotlin."}
            return {'error': f"Detekt a échoué: {stderr[:200]}"}

    except subprocess.TimeoutExpired:
        return {'error': "Detekt timeout (exceeded 1 hour)"}
    except Exception as e:
        logger.exception("Detekt Docker execution failed")
        return {'error': str(e)}


def parse_detekt_results(json_data: dict, repo_path: str) -> list:
    severity_map = {'MAJOR': 'HIGH', 'CRITICAL': 'HIGH', 'MINOR': 'MEDIUM', 'WARNING': 'MEDIUM'}
    vulnerabilities = []
    for issue in json_data.get('issues', []):
        severity = severity_map.get(issue.get('severity', 'INFO'), 'LOW')
        filename = issue.get('filename', '')
        if filename.startswith('/workspace/'):
            filename = filename[11:]
        line_number = issue.get('startLine', 0)
        rule_id = issue.get('ruleId', 'DETEKT')
        rule_set = issue.get('ruleSetId', 'style')
        vulnerabilities.append({
            'test_id': rule_id,
            'test_name': f"Detekt ({rule_set})",
            'issue_text': issue.get('message', ''),
            'severity': severity,
            'confidence': 'HIGH',
            'filename': filename,
            'line_number': line_number,
            'line_range': [line_number, issue.get('endLine', line_number)],
            'code_snippet': (issue.get('snippet') or '').strip(),
            'cwe': '',
            'more_info': f"https://detekt.dev/docs/rules/{rule_set.lower()}#{rule_id.lower()}",
        })
    return vulnerabilities


def run_full_detekt_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    base_tmp = os.path.abspath('tmp')
    os.makedirs(base_tmp, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_detekt_', dir=base_tmp)

    try:
        logger.info(f"Cloning {repo_owner}/{repo_name} for Detekt scan")
        clone_repo(clone_url, access_token, tmp_dir)

        logger.info(f"Running Detekt on {tmp_dir}")
        detekt_result = run_detekt(tmp_dir)

        if 'error' in detekt_result:
            return {'success': False, 'error': detekt_result['error']}

        json_data = detekt_result.get('json', {})
        vulnerabilities = parse_detekt_results(json_data, tmp_dir)
        files_analyzed = json_data.get('statistics', {}).get('file', 0)

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
            'raw_output': json.dumps(json_data),
        }

    except Exception as e:
        logger.exception("Detekt scan failed unexpectedly")
        return {'success': False, 'error': f'Erreur inattendue (Detekt): {e}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
