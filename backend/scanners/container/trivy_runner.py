import subprocess
import json
import logging
import os
from ..base import BaseScanner

logger = logging.getLogger(__name__)


class TrivyRunner(BaseScanner):
    def __init__(self):
        super().__init__("Trivy")

    def run(self, target_path_or_url, **kwargs):
        targets = kwargs.get('targets', [])
        result = run_trivy_fs(target_path_or_url, targets=targets)
        if result['success']:
            return parse_trivy_results(result['data'], target_path_or_url)
        return []


# ------------------------------------------------------------------ #
# SCA — filesystem dependency scan                                     #
# ------------------------------------------------------------------ #

def run_trivy_fs(repo_path: str, targets: list = None) -> dict:
    """
    SCA mode: scans dependency files (package.json, requirements.txt, go.mod…)
    using `trivy fs`.
    """
    if not repo_path or not os.path.exists(repo_path):
        return {'success': False, 'error': f"Chemin invalide : {repo_path}"}

    scan_targets = []
    if targets:
        for t in targets:
            full_path = os.path.join(repo_path, t)
            if os.path.exists(full_path):
                scan_targets.append(full_path)

    if not scan_targets:
        scan_targets = [os.path.abspath(repo_path)]

    abs_repo_path = os.path.abspath(repo_path)
    all_results = []

    try:
        for t in scan_targets:
            rel_path = os.path.relpath(t, abs_repo_path)
            container_path = "/app" if rel_path == "." else f"/app/{rel_path.replace(os.sep, '/')}"

            cmd = [
                'docker', 'run', '--rm',
                '-v', f"{abs_repo_path}:/app:ro",
                'aquasec/trivy', 'fs',
                '--format', 'json',
                '--quiet',
                '--no-progress',
                container_path,
            ]

            logger.info(f"Trivy fs scan on: {t}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                encoding='utf-8',
                errors='replace',
            )

            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    if 'Results' in data:
                        all_results.extend(data['Results'])
                except Exception as e:
                    logger.error(f"Failed to parse Trivy fs JSON for {t}: {e}")

        return {'success': True, 'data': {'Results': all_results}}

    except subprocess.TimeoutExpired:
        return {'success': False, 'error': "Trivy fs scan timed out after 300s"}
    except FileNotFoundError:
        return {'success': False, 'error': "Docker not found. Please ensure Docker Desktop is running."}
    except Exception as e:
        logger.error(f"Unexpected error running Trivy fs: {e}")
        return {'success': False, 'error': str(e)}


# ------------------------------------------------------------------ #
# Container — Docker image scan                                        #
# ------------------------------------------------------------------ #

def run_trivy_image(image_name: str) -> dict:
    """
    Container mode: scans a Docker image (OS packages, installed libs…)
    using `trivy image`.
    Requires Docker socket access so Trivy can pull/inspect the image.
    """
    if not image_name:
        return {'success': False, 'error': "image_name est requis pour le container scan"}

    # Docker Desktop on Windows exposes the daemon via a named pipe;
    # mounting /var/run/docker.sock works through the WSL2 backend.
    docker_sock = _docker_socket_mount()

    cmd = [
        'docker', 'run', '--rm',
        '-v', docker_sock,
        'aquasec/trivy', 'image',
        '--format', 'json',
        '--quiet',
        '--no-progress',
        image_name,
    ]

    logger.info(f"Trivy image scan on: {image_name}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            encoding='utf-8',
            errors='replace',
        )

        if result.returncode not in (0, 1):
            err = result.stderr.strip() or f"exit code {result.returncode}"
            return {'success': False, 'error': f"Trivy image scan failed: {err}"}

        if not result.stdout.strip():
            return {'success': True, 'data': {'Results': []}}

        data = json.loads(result.stdout)
        return {'success': True, 'data': data}

    except subprocess.TimeoutExpired:
        return {'success': False, 'error': "Trivy image scan timed out after 600s"}
    except FileNotFoundError:
        return {'success': False, 'error': "Docker not found. Please ensure Docker Desktop is running."}
    except json.JSONDecodeError as e:
        return {'success': False, 'error': f"Failed to parse Trivy image output: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error running Trivy image: {e}")
        return {'success': False, 'error': str(e)}


def _docker_socket_mount() -> str:
    """Returns the correct Docker socket mount string for the current OS."""
    if os.name == 'nt':
        # Windows — Docker Desktop named pipe
        return r'\\.\pipe\docker_engine:\\.\pipe\docker_engine'
    return '/var/run/docker.sock:/var/run/docker.sock'


# ------------------------------------------------------------------ #
# Backward-compat alias                                               #
# ------------------------------------------------------------------ #

def run_trivy(repo_path: str, targets: list = None) -> dict:
    """Kept for backward compatibility — delegates to run_trivy_fs."""
    return run_trivy_fs(repo_path, targets=targets)


# ------------------------------------------------------------------ #
# Shared result parser                                                 #
# ------------------------------------------------------------------ #

def parse_trivy_results(trivy_data: dict, source_label: str = '') -> list:
    """Parse Trivy JSON output (fs or image) into the standard vulnerability format."""
    vulnerabilities = []
    severity_map = {
        'CRITICAL': 'CRITICAL',
        'HIGH': 'HIGH',
        'MEDIUM': 'MEDIUM',
        'LOW': 'LOW',
        'UNKNOWN': 'LOW',
    }

    for res in trivy_data.get('Results', []):
        target = res.get('Target', source_label)
        for v in (res.get('Vulnerabilities') or []):
            raw_severity = v.get('Severity', 'LOW').upper()
            severity = severity_map.get(raw_severity, 'LOW')

            fixed_version = v.get('FixedVersion', '')
            fix_text = f" Fix available in version {fixed_version}." if fixed_version else ""

            vulnerabilities.append({
                'test_id':      v.get('VulnerabilityID', 'TRIVY-VULN'),
                'test_name':    v.get('PkgName', 'Unknown Package'),
                'issue_text':   (v.get('Description') or v.get('Title') or 'No description available.') + fix_text,
                'severity':     severity,
                'confidence':   'HIGH',
                'filename':     target,
                'line_number':  0,
                'line_range':   [],
                'code_snippet': f"{v.get('PkgName', '')}@{v.get('InstalledVersion', 'unknown')}",
                'cwe':          (v.get('CweIDs') or [''])[0],
                'more_info':    (v.get('References') or [''])[0],
                'solution':     f"Upgrade to {fixed_version}" if fixed_version else '',
                'is_sca':       False,
                'is_container': False,
            })

    logger.info(f"Trivy parsed {len(vulnerabilities)} vulnerabilities from '{source_label}'")
    return vulnerabilities
