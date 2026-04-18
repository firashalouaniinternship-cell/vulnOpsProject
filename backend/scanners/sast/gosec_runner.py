import os
import shutil
import subprocess
import tempfile
import json
from core.utils.repo_utils import clone_repo
from core.utils.docker_utils import get_docker_path_mapping, ensure_docker_image, run_docker_container


def run_gosec(repo_path: str) -> dict:
    """
    Exécute Gosec via Docker sur un répertoire et retourne les résultats JSON.
    """
    print(f"Exécution de Gosec (Docker) sur : {repo_path}")
    
    # 1. S'assurer que l'image est présente
    image_name = 'securego/gosec'
    success, error_msg = ensure_docker_image(image_name)
    if not success:
        return {'results': [], 'errors': error_msg}

    # 2. Préparer le mapping de volume
    volume_mapping = get_docker_path_mapping(repo_path)
    working_dir = '/src'
    
    try:
        # Gosec command
        # -fmt=json for JSON output
        # /src/... to scan all subdirectories
        command = ['-fmt=json', './...']
        
        result = run_docker_container(
            image_name=image_name,
            volume_mapping=volume_mapping,
            working_dir=working_dir,
            command=command,
            timeout=900
        )

        # Gosec returns non-zero if issues are found, so we check stdout for JSON
        output = result.stdout or ""
        
        if not output.strip() and result.stderr:
            print(f"Gosec error: {result.stderr}")
            # If it's a real Docker error (not just findings)
            if "docker: Error" in result.stderr:
                return {'results': [], 'errors': f"Erreur Docker: {result.stderr[:200]}"}

        try:
            json_data = json.loads(output)
            return {'json': json_data}
        except json.JSONDecodeError:
            if result.returncode != 0 and not output.strip():
                return {'results': [], 'errors': f"Gosec a échoué (code {result.returncode}): {result.stderr[:200]}"}
            return {'json': {'Issues': []}} # No issues found / empty output
            
    except subprocess.TimeoutExpired:
        return {'results': [], 'errors': "Gosec timeout (dépassé 15 minutes)"}
    except Exception as e:
        return {'results': [], 'errors': str(e)}


def parse_gosec_results(json_data: dict, repo_path: str) -> list:
    """
    Transforme la sortie JSON de Gosec en liste de vulnérabilités au format VulnOps.
    """
    vulnerabilities = []
    issues = json_data.get('Issues', [])
    
    for issue in issues:
        severity_raw = issue.get('severity', 'LOW')
        # Gosec uses HIGH, MEDIUM, LOW
        severity = severity_raw.upper()
        
        filename = issue.get('file', '')
        # Les chemins dans Docker commencent par /src/
        if filename.startswith('/src/'):
            filename = filename[5:]
        
        line_str = issue.get('line', '0')
        line_number = int(line_str) if str(line_str).isdigit() else 0

        cwe_info = issue.get('cwe') or {}
        cwe_id = cwe_info.get('id', '')
        cwe_url = cwe_info.get('url', '')

        vuln = {
            'test_id': issue.get('rule_id', 'GOSEC'),
            'test_name': 'Gosec',
            'issue_text': issue.get('details', ''),
            'severity': severity,
            'confidence': issue.get('confidence', 'HIGH'),
            'filename': filename,
            'line_number': line_number,
            'line_range': [line_number, line_number],
            'code_snippet': issue.get('code', ''),
            'cwe': cwe_id,
            'more_info': cwe_url or f"https://securego.io/docs/rules/{issue.get('rule_id', '').lower()}.html",
        }
        vulnerabilities.append(vuln)
        
    return vulnerabilities


def run_full_gosec_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    """
    Lance un scan complet Gosec pour un projet Go:
    1. Clone le dépôt
    2. Lance Gosec via Docker
    3. Parse les résultats
    4. Nettoie les fichiers temporaires
    """
    base_tmp = os.path.abspath('tmp')
    if not os.path.exists(base_tmp):
        os.makedirs(base_tmp)
        
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_gosec_', dir=base_tmp)
    
    try:
        # 1. Clone
        print(f"1. Clonage de {repo_owner}/{repo_name} dans {tmp_dir}...")
        clone_repo(clone_url, access_token, tmp_dir)
        
        # 2. Gosec execution
        print("2. Analyse avec Gosec...")
        gosec_result = run_gosec(tmp_dir)
        
        if 'errors' in gosec_result:
            return {'success': False, 'error': gosec_result['errors']}
        
        # 3. Parsing
        print("3. Parsing et formatage des résultats...")
        vulnerabilities = parse_gosec_results(gosec_result.get('json', {}), tmp_dir)
        
        high = sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')
        medium = sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM')
        low = sum(1 for v in vulnerabilities if v['severity'] == 'LOW')
        
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
            'data': gosec_result.get('json', {}),
            'raw_output': json.dumps(gosec_result.get('json', {})),
        }


    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Gosec exception: {error_detail}")
        return {'success': False, 'error': f'Erreur inattendue (Gosec): {str(e)}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
