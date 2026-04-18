import os
import json
import shutil
import subprocess
import tempfile
from core.utils.repo_utils import clone_repo


def run_semgrep(repo_path: str) -> dict:
    """
    Exécute Semgrep sur un répertoire et retourne les résultats JSON.
    """
    print(f"Exécution de Semgrep sur : {repo_path}")
    
    # Vérifie si semgrep est installé
    try:
        subprocess.run(['semgrep', '--version'], capture_output=True, check=True, timeout=10)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return {'results': [], 'errors': "Semgrep n'est pas installé ou n'est pas dans le PATH."}

    try:
        # Utilise le subcommand 'scan' avec le config p/owasp-top-ten
        result = subprocess.run(
            [
                'semgrep',
                'scan',
                '--json',
                '--config=p/owasp-top-ten',
                repo_path,
            ],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes max
        )

        if result.returncode not in [0, 1]:  # 0=success, 1=findings found
            print(f"Semgrep stderr: {result.stderr}")
            if not result.stdout.strip():
                return {'results': [], 'errors': result.stderr or "Semgrep returned no output"}

        if not result.stdout.strip():
            return {'results': []}

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            print(f"Erreur de décodage JSON Semgrep: {str(e)}")
            return {'results': [], 'errors': f"JSON parse error: {str(e)}"}

    except subprocess.TimeoutExpired:
        return {'results': [], 'errors': "Semgrep timeout (exceeded 10 minutes)"}
    except Exception as e:
        return {'results': [], 'errors': str(e)}


def parse_semgrep_results(semgrep_output: dict, repo_path: str) -> list:
    """
    Transforme la sortie JSON de Semgrep en liste de vulnérabilités.
    Semgrep retourne un objet avec structure:
    { "results": [...], "errors": [...] }
    """
    vulnerabilities = []
    
    results = semgrep_output.get('results', [])
    
    # Mapping des sévérités Semgrep
    severity_map = {
        'ERROR': 'HIGH',
        'WARNING': 'MEDIUM',
        'INFO': 'LOW',
    }
    
    for issue in results:
        # Nettoie le chemin du fichier
        filename = issue.get('path', '')
        if repo_path in filename:
            filename = filename.replace(repo_path, '').lstrip('/').lstrip('\\')
        
        severity = severity_map.get(issue.get('severity', 'INFO'), 'LOW')
        
        vuln = {
            'test_id': issue.get('check_id', 'SEMGREP'),
            'test_name': 'Semgrep',
            'issue_text': issue.get('extra', {}).get('message', ''),
            'severity': severity,
            'confidence': 'HIGH',
            'filename': filename,
            'line_number': issue.get('start', {}).get('line', 0),
            'line_range': [
                issue.get('start', {}).get('line', 0),
                issue.get('end', {}).get('line', 0)
            ],
            'code_snippet': issue.get('extra', {}).get('lines', ''),
            'cwe': '',
            'more_info': issue.get('extra', {}).get('metadata', {}).get('references', [''])[0] if issue.get('extra', {}).get('metadata', {}).get('references') else '',
        }
        vulnerabilities.append(vuln)
    
    return vulnerabilities


def run_full_semgrep_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str, repo_path: str = None) -> dict:
    """
    Lance un scan complet Semgrep pour un projet:
    1. Clone le dépôt (si repo_path est None)
    2. Lance Semgrep avec config OWASP top 10
    3. Parse les résultats
    4. Nettoie les fichiers temporaires (uniquement si crée par cette fonction)
    """
    is_temp = False
    if not repo_path:
        repo_path = tempfile.mkdtemp(prefix='vulnops_semgrep_')
        is_temp = True
    
    try:
        # 1. Clone
        if is_temp:
            print("1. Clonage...")
            clone_repo(clone_url, access_token, repo_path)
        
        # 2. Semgrep execution
        print("2. Analyse avec Semgrep...")
        semgrep_result = run_semgrep(repo_path)
        
        # Check for errors
        if 'errors' in semgrep_result:
            return {'success': False, 'error': semgrep_result['errors']}
        
        # 3. Parsing
        print("3. Parsing et formatage...")
        vulnerabilities = parse_semgrep_results(semgrep_result, repo_path)
        
        high = sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')
        medium = sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM')
        low = sum(1 for v in vulnerabilities if v['severity'] == 'LOW')
        
        # Count unique files analyzed
        files_analyzed = len(set(v['filename'] for v in vulnerabilities)) if vulnerabilities else 0
        
        metrics = {
            'total_issues': len(vulnerabilities),
            'high_count': high,
            'medium_count': medium,
            'low_count': low,
            'files_analyzed': files_analyzed
        }

        return {
            'success': True,
            'vulnerabilities': vulnerabilities,
            'metrics': metrics,
            'data': semgrep_result,
            'raw_output': json.dumps(semgrep_result),
        }


    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Semgrep exception: {error_detail}")
        return {'success': False, 'error': f'Erreur inattendue(Semgrep): {str(e)}'}
    finally:
        if is_temp and os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)
