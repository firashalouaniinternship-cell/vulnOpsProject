import os
import shutil
import subprocess
import tempfile
import json
from core.utils.repo_utils import clone_repo


def run_psalm(repo_path: str) -> dict:
    """
    Exécute Psalm via Docker sur un répertoire et retourne les résultats JSON.
    """
    print(f"Exécution de Psalm (Docker) sur : {repo_path}")
    
    # Vérifie si Docker est installé
    if not shutil.which('docker'):
        return {'results': [], 'errors': "Docker n'est pas installé."}

    abs_repo_path = os.path.abspath(repo_path)
    
    try:
        if os.name == 'nt':
            drive = abs_repo_path[0].lower()
            normalized_path = '/' + drive + abs_repo_path[2:].replace('\\', '/')
            volume_mapping = f"{normalized_path}:/app"
        else:
            volume_mapping = f"{abs_repo_path}:/app"

        # On utilise ghcr.io/danog/psalm qui est optimisé
        # L'image officielle Psalm est ghcr.io/danog/psalm:latest
        docker_cmd = [
            'docker', 'run', '--rm', 
            '-v', volume_mapping, 
            '-w', '/app', 
            'ghcr.io/danog/psalm:latest', 
            '/composer/vendor/bin/psalm', '--output-format=json', '--no-cache'
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
        
        # Psalm retourne souvent les résultats sur stdout en JSON même avec un code de sortie non-zéro (car erreurs trouvées)
        try:
            json_data = json.loads(output)
            return {'json': json_data}
        except json.JSONDecodeError:
            if result.returncode != 0:
                detailed_error = result.stderr or "Erreur inconnue"
                return {'results': [], 'errors': f"Psalm a échoué (code {result.returncode}): {detailed_error[:200]}"}
            return {'json': []}
            
    except subprocess.TimeoutExpired:
        return {'results': [], 'errors': "Psalm timeout (dépassé 15 minutes)"}
    except Exception as e:
        return {'results': [], 'errors': str(e)}


def parse_psalm_results(json_data: list, repo_path: str) -> list:
    """
    Transforme la sortie JSON de Psalm en liste de vulnérabilités au format VulnOps.
    """
    vulnerabilities = []
    
    for issue in json_data:
        severity_raw = issue.get('severity', 'info')
        
        if severity_raw == 'error':
            severity = 'HIGH'
        elif severity_raw == 'warning':
            severity = 'MEDIUM'
        else:
            severity = 'LOW'
            
        filename = issue.get('file_name', '')
        line_number = issue.get('line_from', 0)

        vuln = {
            'test_id': issue.get('type', 'PSALM'),
            'test_name': 'Psalm',
            'issue_text': issue.get('message', ''),
            'severity': severity,
            'confidence': 'HIGH',
            'filename': filename,
            'line_number': line_number,
            'line_range': [issue.get('line_from', 0), issue.get('line_to', 0)],
            'code_snippet': issue.get('snippet', '').strip(),
            'cwe': '',  # Psalm ne fournit pas de CWE par défaut
            'more_info': f"https://psalm.dev/docs/issues/{issue.get('type', '')}/",
        }
        vulnerabilities.append(vuln)
        
    return vulnerabilities


def run_full_psalm_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    """
    Scan complet Psalm pour PHP.
    """
    base_tmp = os.path.abspath('tmp')
    if not os.path.exists(base_tmp):
        os.makedirs(base_tmp)
        
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_psalm_', dir=base_tmp)
    
    try:
        # 1. Clone
        print(f"1. Clonage de {repo_owner}/{repo_name} dans {tmp_dir}...")
        clone_repo(clone_url, access_token, tmp_dir)
        
        # 2. Check for Psalm config
        psalm_config = os.path.join(tmp_dir, "psalm.xml")
        psalm_config_dist = os.path.join(tmp_dir, "psalm.xml.dist")
        
        if not os.path.exists(psalm_config) and not os.path.exists(psalm_config_dist):
            print("Psalm config not found. Creating a default one...")
            default_config = """<?xml version="1.0"?>
<psalm
    errorLevel="4"
    resolveFromConfigFile="true"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns="https://getpsalm.org/schema/config"
>
    <projectFiles>
        <directory name="." />
    </projectFiles>
</psalm>
"""
            # On ajoute l'ignoreFiles seulement si vendor existe
            if os.path.exists(os.path.join(tmp_dir, "vendor")):
                 default_config = default_config.replace("</projectFiles>", "    <ignoreFiles><directory name=\"vendor\" /></ignoreFiles>\n    </projectFiles>")

            with open(psalm_config, "w") as f:
                f.write(default_config)

        # 3. Psalm execution
        print("3. Analyse avec Psalm...")
        psalm_result = run_psalm(tmp_dir)
        
        if 'errors' in psalm_result:
            return {'success': False, 'error': psalm_result['errors']}
        
        # 3. Parsing
        print("3. Parsing des résultats...")
        vulnerabilities = parse_psalm_results(psalm_result.get('json', []), tmp_dir)
        
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
            'data': psalm_result.get('json', []),
            'raw_output': json.dumps(psalm_result.get('json', [])),
        }


    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Psalm exception: {error_detail}")
        return {'success': False, 'error': f'Erreur inattendue (Psalm): {str(e)}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
