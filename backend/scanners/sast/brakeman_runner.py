import os
import shutil
import subprocess
import tempfile
import json
from core.utils.repo_utils import clone_repo


def run_brakeman(repo_path: str) -> dict:
    """
    Exécute Brakeman via Docker sur un répertoire et retourne les résultats JSON.
    """
    print(f"Exécution de Brakeman (Docker) sur : {repo_path}")
    
    # Vérifie si Docker est installé
    if not shutil.which('docker'):
        return {'results': [], 'errors': "Docker n'est pas installé."}

    abs_repo_path = os.path.abspath(repo_path)
    
    try:
        if os.name == 'nt':
            drive = abs_repo_path[0].lower()
            normalized_path = '/' + drive + abs_repo_path[2:].replace('\\', '/')
            volume_mapping = f"{normalized_path}:/code"
        else:
            volume_mapping = f"{abs_repo_path}:/code"

        # Image officielle de Brakeman
        docker_cmd = [
            'docker', 'run', '--rm', 
            '-v', volume_mapping, 
            '-w', '/code', 
            'presidentbeef/brakeman', 
            '--format', 'json', '--force'
        ]
        
        print(f"Running Docker command: {' '.join(docker_cmd)}")
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=900,
            encoding='utf-8'
        )

        output = result.stdout or ""
        
        if not output.strip() and result.stderr:
            if "docker: Error" in result.stderr:
                return {'results': [], 'errors': f"Erreur Docker: {result.stderr[:200]}"}

        try:
            json_data = json.loads(output)
            return {'json': json_data}
        except json.JSONDecodeError:
            if result.returncode != 0:
                detailed_error = result.stderr or "Erreur inconnue"
                # Brakeman retourne souvent des erreurs si ce n'est pas un projet Rails
                if "Not a Rails application" in detailed_error:
                    return {'results': [], 'errors': "Ce projet n'est pas une application Ruby on Rails valide."}
                return {'results': [], 'errors': f"Brakeman a échoué (code {result.returncode}): {detailed_error[:200]}"}
            return {'json': {'warnings': []}}
            
    except subprocess.TimeoutExpired:
        return {'results': [], 'errors': "Brakeman timeout (dépassé 15 minutes)"}
    except Exception as e:
        return {'results': [], 'errors': str(e)}


def parse_brakeman_results(json_data: dict, repo_path: str) -> list:
    """
    Transforme la sortie JSON de Brakeman en liste de vulnérabilités au format VulnOps.
    """
    vulnerabilities = []
    warnings = json_data.get('warnings', [])
    
    for warning in warnings:
        severity_raw = warning.get('confidence', 'Low').upper()
        
        # Mapping des sévérités Brakeman (High, Medium, Weak)
        if severity_raw == 'HIGH':
            severity = 'HIGH'
        elif severity_raw == 'MEDIUM' or severity_raw == 'WEAK':
            severity = 'MEDIUM'
        else:
            severity = 'LOW'
            
        vuln = {
            'test_id': warning.get('check_name', 'BRAKEMAN'),
            'test_name': f"Brakeman ({warning.get('warning_type', 'Security')})",
            'issue_text': warning.get('message', ''),
            'severity': severity,
            'confidence': warning.get('confidence', 'High').upper(),
            'filename': warning.get('file', ''),
            'line_number': warning.get('line', 0),
            'line_range': [warning.get('line', 0), warning.get('line', 0)],
            'code_snippet': warning.get('code', '').strip() if warning.get('code') else '',
            'cwe': '',  # Brakeman ne link pas toujours les CWE
            'more_info': warning.get('link', 'https://brakemanscanner.org/docs/warning_types/'),
        }
        vulnerabilities.append(vuln)
        
    return vulnerabilities


def run_full_brakeman_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    """
    Scan complet Brakeman pour Ruby on Rails.
    """
    base_tmp = os.path.abspath('tmp')
    if not os.path.exists(base_tmp):
        os.makedirs(base_tmp)
        
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_brakeman_', dir=base_tmp)
    
    try:
        # 1. Clone
        print(f"1. Clonage de {repo_owner}/{repo_name} dans {tmp_dir}...")
        clone_repo(clone_url, access_token, tmp_dir)
        
        # 2. Brakeman execution
        print("2. Analyse avec Brakeman...")
        brakeman_result = run_brakeman(tmp_dir)
        
        if 'errors' in brakeman_result:
            return {'success': False, 'error': brakeman_result['errors']}
        
        # 3. Parsing
        print("3. Parsing des résultats...")
        json_data = brakeman_result.get('json', {})
        vulnerabilities = parse_brakeman_results(json_data, tmp_dir)
        
        high = sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')
        medium = sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM')
        low = sum(1 for v in vulnerabilities if v['severity'] == 'LOW')
        
        files_analyzed = json_data.get('scan_info', {}).get('number_of_files', 0)
        
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
            'data': json_data,
            'raw_output': json.dumps(json_data),
        }


    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Brakeman exception: {error_detail}")
        return {'success': False, 'error': f'Erreur inattendue (Brakeman): {str(e)}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
