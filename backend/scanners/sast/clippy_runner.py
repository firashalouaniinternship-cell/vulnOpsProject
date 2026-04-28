import os
import shutil
import subprocess
import tempfile
import json
import logging

from core.utils.repo_utils import clone_repo
from core.utils.docker_utils import get_docker_path_mapping, ensure_docker_image, run_docker_container

logger = logging.getLogger(__name__)


def run_clippy(repo_path: str) -> dict:
    image_name = 'rust:latest'
    success, error_msg = ensure_docker_image(image_name)
    if not success:
        return {'error': error_msg}

    volume_mapping = get_docker_path_mapping(repo_path)
    try:
        result = run_docker_container(
            image_name=image_name,
            volume_mapping=volume_mapping,
            working_dir='/usr/src/myapp',
            command=['sh', '-c', 'rustup component add clippy && cargo clippy --message-format=json -- -D warnings'],
            timeout=1800,
        )

        output = result.stdout or ""

        json_lines = []
        for line in output.splitlines():
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    json_lines.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if not json_lines and result.returncode != 0:
            stderr = result.stderr or "Erreur inconnue"
            if "Cargo.toml" in stderr:
                return {'error': "Fichier Cargo.toml introuvable. Ce projet ne semble pas être un projet Rust valide."}
            if "error: could not compile" in stderr.lower():
                return {'error': "Le projet Rust contient des erreurs de compilation qui empêchent l'analyse Clippy."}
            return {'error': f"Clippy a échoué (code {result.returncode}): {stderr[:200]}"}

        return {'json_lines': json_lines}

    except subprocess.TimeoutExpired:
        return {'error': "Clippy timeout (exceeded 30 minutes)"}
    except Exception as e:
        logger.exception("Clippy Docker execution failed")
        return {'error': str(e)}


def parse_clippy_results(json_lines: list, repo_path: str) -> list:
    vulnerabilities = []
    for entry in json_lines:
        if entry.get('reason') != 'compiler-message':
            continue

        message_obj = entry.get('message', {})
        level_raw = message_obj.get('level', 'warning')
        severity = {'error': 'HIGH', 'warning': 'MEDIUM'}.get(level_raw, 'LOW')

        code_obj = message_obj.get('code')
        test_id = code_obj.get('code', 'CLIPPY') if code_obj else 'CLIPPY'

        spans = message_obj.get('spans', [])
        primary_span = next((s for s in spans if s.get('is_primary')), None)
        if not primary_span:
            continue

        line_number = primary_span.get('line_start', 0)
        text_list = primary_span.get('text', [])
        code_snippet = text_list[0].get('text', '').strip() if text_list else ''

        vulnerabilities.append({
            'test_id': test_id,
            'test_name': f"Clippy ({test_id})",
            'issue_text': message_obj.get('message', ''),
            'severity': severity,
            'confidence': 'HIGH',
            'filename': primary_span.get('file_name', ''),
            'line_number': line_number,
            'line_range': [line_number, primary_span.get('line_end', line_number)],
            'code_snippet': code_snippet,
            'cwe': '',
            'more_info': f"https://rust-lang.github.io/rust-clippy/master/index.html#{test_id.replace('clippy::', '')}",
        })
    return vulnerabilities


def run_full_clippy_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    base_tmp = os.path.abspath('tmp')
    os.makedirs(base_tmp, exist_ok=True)
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_clippy_', dir=base_tmp)

    try:
        logger.info(f"Cloning {repo_owner}/{repo_name} for Clippy scan")
        clone_repo(clone_url, access_token, tmp_dir)

        logger.info(f"Running Clippy on {tmp_dir}")
        clippy_result = run_clippy(tmp_dir)

        if 'error' in clippy_result:
            return {'success': False, 'error': clippy_result['error']}

        vulnerabilities = parse_clippy_results(clippy_result.get('json_lines', []), tmp_dir)
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
            'raw_output': json.dumps(clippy_result.get('json_lines', [])),
        }

    except Exception as e:
        logger.exception("Clippy scan failed unexpectedly")
        return {'success': False, 'error': f'Erreur inattendue (Clippy): {e}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
