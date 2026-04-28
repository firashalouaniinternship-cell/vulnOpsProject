import os
import shutil
import subprocess
import tempfile
import json
import logging

from core.utils.repo_utils import clone_repo

logger = logging.getLogger(__name__)


def run_psalm(repo_path: str) -> dict:
    if not shutil.which('docker'):
        return {'error': "Docker n'est pas installé."}

    abs_repo_path = os.path.abspath(repo_path)
    if os.name == 'nt':
        drive = abs_repo_path[0].lower()
        normalized = '/' + drive + abs_repo_path[2:].replace('\\', '/')
        volume_mapping = f"{normalized}:/app"
    else:
        volume_mapping = f"{abs_repo_path}:/app"

    try:
        docker_cmd = [
            'docker', 'run', '--rm',
            '-v', volume_mapping,
            '-w', '/app',
            'ghcr.io/danog/psalm:latest',
            '/composer/vendor/bin/psalm', '--output-format=json', '--no-cache',
        ]

        logger.info(f"Running Psalm Docker command: {' '.join(docker_cmd)}")
        result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=900, encoding='utf-8')
        output = result.stdout or ""

        try:
            return {'json': json.loads(output)}
        except json.JSONDecodeError:
            if result.returncode != 0:
                return {'error': f"Psalm a échoué (code {result.returncode}): {result.stderr[:200]}"}
            return {'json': []}

    except subprocess.TimeoutExpired:
        return {'error': "Psalm timeout (exceeded 15 minutes)"}
    except Exception as e:
        logger.exception("Psalm Docker execution failed")
        return {'error': str(e)}


def parse_psalm_results(json_data: list, repo_path: str) -> list:
    severity_map = {'error': 'HIGH', 'warning': 'MEDIUM'}
    vulnerabilities = []
    for issue in json_data:
        severity = severity_map.get(issue.get('severity', 'info'), 'LOW')
        vulnerabilities.append({
            'test_id': issue.get('type', 'PSALM'),
            'test_name': 'Psalm',
            'issue_text': issue.get('message', ''),
            'severity': severity,
            'confidence': 'HIGH',
            'filename': issue.get('file_name', ''),
            'line_number': issue.get('line_from', 0),
            'line_range': [issue.get('line_from', 0), issue.get('line_to', 0)],
            'code_snippet': issue.get('snippet', '').strip(),
            'cwe': '',
            'more_info': f"https://psalm.dev/docs/issues/{issue.get('type', '')}/",
        })
    return vulnerabilities


def run_full_psalm_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    base_tmp = os.path.abspath('tmp')
    os.makedirs(base_tmp, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_psalm_', dir=base_tmp)

    try:
        logger.info(f"Cloning {repo_owner}/{repo_name} for Psalm scan")
        clone_repo(clone_url, access_token, tmp_dir)

        psalm_config = os.path.join(tmp_dir, 'psalm.xml')
        if not os.path.exists(psalm_config) and not os.path.exists(psalm_config + '.dist'):
            logger.info("No psalm.xml found — creating default config")
            ignore_vendor = '<ignoreFiles><directory name="vendor" /></ignoreFiles>\n    ' \
                if os.path.exists(os.path.join(tmp_dir, 'vendor')) else ''
            with open(psalm_config, 'w') as f:
                f.write(
                    '<?xml version="1.0"?>\n'
                    '<psalm errorLevel="4" resolveFromConfigFile="true"\n'
                    '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
                    '  xmlns="https://getpsalm.org/schema/config">\n'
                    '    <projectFiles>\n'
                    f'        <directory name="." />\n'
                    f'    {ignore_vendor}</projectFiles>\n'
                    '</psalm>\n'
                )

        logger.info(f"Running Psalm on {tmp_dir}")
        psalm_result = run_psalm(tmp_dir)

        if 'error' in psalm_result:
            return {'success': False, 'error': psalm_result['error']}

        vulnerabilities = parse_psalm_results(psalm_result.get('json', []), tmp_dir)
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
            'raw_output': json.dumps(psalm_result.get('json', [])),
        }

    except Exception as e:
        logger.exception("Psalm scan failed unexpectedly")
        return {'success': False, 'error': f'Erreur inattendue (Psalm): {e}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
