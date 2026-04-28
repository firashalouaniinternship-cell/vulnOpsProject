import os
import shutil
import subprocess
import tempfile
import logging
import xml.etree.ElementTree as ET

from core.utils.repo_utils import clone_repo
from core.utils.docker_utils import get_docker_path_mapping, ensure_docker_image, run_docker_container

logger = logging.getLogger(__name__)


def run_cppcheck(repo_path: str) -> dict:
    image_name = 'facthunder/cppcheck'
    success, error_msg = ensure_docker_image(image_name)
    if not success:
        return {'error': error_msg}

    volume_mapping = get_docker_path_mapping(repo_path)
    try:
        # cppcheck writes XML to stderr; combine both streams to capture it
        result = run_docker_container(
            image_name=image_name,
            volume_mapping=volume_mapping,
            working_dir='/src',
            command=['sh', '-c', 'cppcheck --xml --xml-version=2 --enable=all --inconclusive .'],
            timeout=1200,
        )

        output = (result.stdout or "") + (result.stderr or "")

        xml_start = output.find('<?xml')
        if xml_start == -1:
            xml_start = output.find('<results')

        if xml_start == -1:
            if result.returncode != 0:
                return {'error': f"Cppcheck Docker error ({result.returncode}): {output[:200]}"}
            return {}

        return {'xml': output[xml_start:]}

    except subprocess.TimeoutExpired:
        return {'error': "Cppcheck timeout (exceeded 20 minutes)"}
    except Exception as e:
        logger.exception("Cppcheck Docker execution failed")
        return {'error': str(e)}


def parse_cppcheck_results(xml_data: str, repo_path: str) -> list:
    vulnerabilities = []
    severity_map = {'error': 'HIGH', 'warning': 'MEDIUM'}
    try:
        root = ET.fromstring(xml_data)
        errors = root.find('errors')
        if errors is None:
            return []

        for error in errors.findall('error'):
            severity = severity_map.get(error.get('severity', 'info'), 'LOW')
            location = error.find('location')
            filename, line_number = '', 0
            if location is not None:
                filename = location.get('file', '').lstrip('./').lstrip('.\\')
                line_str = location.get('line', '0')
                line_number = int(line_str) if line_str.isdigit() else 0

            cwe = error.get('cwe', '')
            vulnerabilities.append({
                'test_id': error.get('id', 'CPPCHECK'),
                'test_name': 'Cppcheck',
                'issue_text': error.get('msg', ''),
                'severity': severity,
                'confidence': 'MEDIUM' if error.get('inconclusive') else 'HIGH',
                'filename': filename,
                'line_number': line_number,
                'line_range': [line_number, line_number],
                'code_snippet': error.get('verbose', ''),
                'cwe': cwe,
                'more_info': f"https://cwe.mitre.org/data/definitions/{cwe}.html" if cwe else '',
            })
    except ET.ParseError as e:
        logger.error(f"Cppcheck XML parse error: {e}")
    return vulnerabilities


def run_full_cppcheck_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    base_tmp = os.path.abspath('tmp')
    os.makedirs(base_tmp, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_cppcheck_', dir=base_tmp)

    try:
        logger.info(f"Cloning {repo_owner}/{repo_name} for Cppcheck scan")
        clone_repo(clone_url, access_token, tmp_dir)

        logger.info(f"Running Cppcheck on {tmp_dir}")
        cppcheck_result = run_cppcheck(tmp_dir)

        if 'error' in cppcheck_result:
            return {'success': False, 'error': cppcheck_result['error']}

        if 'xml' not in cppcheck_result:
            return {
                'success': True,
                'vulnerabilities': [],
                'metrics': {'total_issues': 0, 'high_count': 0, 'medium_count': 0, 'low_count': 0, 'files_analyzed': 0},
                'raw_output': '',
            }

        vulnerabilities = parse_cppcheck_results(cppcheck_result['xml'], tmp_dir)
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
            'raw_output': cppcheck_result['xml'],
        }

    except Exception as e:
        logger.exception("Cppcheck scan failed unexpectedly")
        return {'success': False, 'error': f'Erreur inattendue (Cppcheck): {e}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
