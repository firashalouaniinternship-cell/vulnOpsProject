import os
import json
import shutil
import subprocess
import tempfile
import logging

from core.utils.repo_utils import clone_repo

logger = logging.getLogger(__name__)


def run_eslint(repo_path: str, targets: list = None) -> dict:
    """
    Exécute ESLint sur un répertoire ou des cibles spécifiques et retourne les résultats JSON.
    """
    scan_targets = []
    if targets:
        for t in targets:
            if os.path.exists(os.path.join(repo_path, t)):
                scan_targets.append(t)

    if not scan_targets:
        scan_targets = ['.']

    eslint_config_path = os.path.join(repo_path, 'eslint.config.cjs')
    config_created = False

    if not os.path.exists(eslint_config_path):
        try:
            with open(eslint_config_path, 'w') as f:
                f.write(
                    'module.exports = [{\n'
                    '  files: ["**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx"],\n'
                    '  rules: {\n'
                    '    "no-eval": "error",\n'
                    '    "no-implied-eval": "error",\n'
                    '    "no-new-func": "error",\n'
                    '    "no-debugger": "error",\n'
                    '    "no-unused-vars": "warn",\n'
                    '    "no-undef": "warn"\n'
                    '  }\n'
                    '}];\n'
                )
            config_created = True
        except Exception as e:
            logger.warning(f"Could not create ESLint config: {e}")

    eslint_cmd = _find_eslint_executable()
    if not eslint_cmd:
        if config_created and os.path.exists(eslint_config_path):
            os.remove(eslint_config_path)
        return {'error': "ESLint n'est pas installé. Installez avec: npm install -g eslint"}

    try:
        cmd_args = (eslint_cmd if isinstance(eslint_cmd, list) else [eslint_cmd])
        cmd_args = cmd_args + scan_targets + ['--format', 'json', '--no-warn-ignored']

        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=repo_path,
            encoding='utf-8',
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode not in [0, 1]:
            if not stdout.strip():
                return {'error': f"ESLint failed (code {result.returncode}): {stderr.strip() or 'Unknown error'}"}

        if not stdout.strip():
            return {}

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            start_idx = stdout.find('[')
            if start_idx != -1:
                try:
                    return json.loads(stdout[start_idx:])
                except json.JSONDecodeError:
                    pass
            logger.error(f"ESLint JSON decode error. stderr: {stderr[:200]}")
            return {'error': f"JSON parse error from ESLint output"}

    except subprocess.TimeoutExpired:
        return {'error': "ESLint timeout (exceeded 5 minutes)"}
    except Exception as e:
        logger.exception("ESLint subprocess failed")
        return {'error': f"System error: {e}"}
    finally:
        if config_created and os.path.exists(eslint_config_path):
            try:
                os.remove(eslint_config_path)
            except Exception:
                pass


def _find_eslint_executable():
    """Locates the ESLint executable using standard PATH lookup, then Windows fallbacks."""
    import shutil as _shutil

    # 1. Standard PATH lookup (works on Linux, Mac, properly-configured Windows)
    if _shutil.which('eslint'):
        return 'eslint'

    # 2. Windows npm global install fallback
    npm_cmd = os.path.expanduser('~\\AppData\\Roaming\\npm\\eslint.cmd')
    if os.path.exists(npm_cmd):
        try:
            subprocess.run([npm_cmd, '--version'], capture_output=True, check=True, timeout=10)
            return npm_cmd
        except Exception:
            pass

    # 3. node + eslint.js fallback
    eslint_js = os.path.expanduser('~\\AppData\\Roaming\\npm\\node_modules\\eslint\\bin\\eslint.js')
    if os.path.exists(eslint_js):
        return ['node', eslint_js]

    return None


def parse_eslint_results(eslint_output, repo_path: str) -> list:
    vulnerabilities = []

    if isinstance(eslint_output, dict):
        file_results = eslint_output.get('results', [])
    else:
        file_results = eslint_output if isinstance(eslint_output, list) else []

    for file_result in file_results:
        if not isinstance(file_result, dict):
            continue

        filename = file_result.get('filePath', '')
        if repo_path in filename:
            filename = filename.replace(repo_path, '').lstrip('/').lstrip('\\')

        for issue in file_result.get('messages', []):
            severity = 'HIGH' if issue.get('severity') == 2 else 'MEDIUM'
            vulnerabilities.append({
                'test_id': issue.get('ruleId', 'ESLINT'),
                'test_name': 'ESLint',
                'issue_text': issue.get('message', ''),
                'severity': severity,
                'confidence': 'HIGH',
                'filename': filename,
                'line_number': issue.get('line', 0),
                'line_range': [issue.get('line', 0), issue.get('endLine', issue.get('line', 0))],
                'code_snippet': '',
                'cwe': '',
                'more_info': f"https://eslint.org/docs/rules/{issue.get('ruleId', '')}",
            })

    return vulnerabilities


def run_full_eslint_scan(
    clone_url: str,
    access_token: str,
    repo_owner: str,
    repo_name: str,
    repo_path: str = None,
    targets: list = None,
) -> dict:
    """
    Clone (si repo_path est None) → ESLint → parse → cleanup.
    Si repo_path est fourni, le clone est ignoré et le répertoire n'est pas supprimé.
    """
    is_temp = repo_path is None
    if is_temp:
        repo_path = tempfile.mkdtemp(prefix='vulnops_eslint_')

    try:
        if is_temp:
            logger.info(f"Cloning {repo_owner}/{repo_name} for ESLint scan")
            clone_repo(clone_url, access_token, repo_path)

        logger.info(f"Running ESLint on {repo_path}")
        eslint_result = run_eslint(repo_path, targets=targets)

        if 'error' in eslint_result:
            return {'success': False, 'error': eslint_result['error']}

        vulnerabilities = parse_eslint_results(eslint_result, repo_path)

        if isinstance(eslint_result, list):
            files_analyzed = len(eslint_result)
        elif isinstance(eslint_result, dict):
            files_analyzed = len(eslint_result.get('results', []))
        else:
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
            'raw_output': json.dumps(eslint_result),
        }

    except Exception as e:
        logger.exception("ESLint scan failed unexpectedly")
        return {'success': False, 'error': f'Erreur inattendue (ESLint): {e}'}
    finally:
        if is_temp and os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)
