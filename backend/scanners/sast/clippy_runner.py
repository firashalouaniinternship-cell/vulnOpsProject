import os
import shutil
import subprocess
import tempfile
import json
from core.utils.repo_utils import clone_repo
from core.utils.docker_utils import get_docker_path_mapping, ensure_docker_image, run_docker_container


def run_clippy(repo_path: str) -> dict:
    """
    Exécute Cargo Clippy via Docker sur un répertoire et retourne les résultats JSON (NDJSON).
    """
    print(f"Exécution de Clippy (Docker) sur : {repo_path}")
    
    # 1. S'assurer que l'image est présente
    image_name = 'rust:latest'
    success, error_msg = ensure_docker_image(image_name)
    if not success:
        return {'results': [], 'errors': error_msg}

    # 2. Préparer le mapping de volume
    volume_mapping = get_docker_path_mapping(repo_path)
    working_dir = '/usr/src/myapp'
    
    try:
        # Image officielle Rust
        # On s'assure que Clippy est bien installé dans le conteneur
        command = [
            'sh', '-c', 'rustup component add clippy && cargo clippy --message-format=json -- -D warnings'
        ]
        
        result = run_docker_container(
            image_name=image_name,
            volume_mapping=volume_mapping,
            working_dir=working_dir,
            command=command,
            timeout=1800 # Les compilations Rust peuvent être longues
        )

        output = result.stdout or ""
        stderr = result.stderr or ""
        
        # Clippy renvoie du JSON-L (un objet par ligne)
        json_lines = []
        for line in output.splitlines():
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    json_lines.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        if not json_lines and result.returncode != 0:
            detailed_error = result.stderr or "Erreur inconnue"
            if "Cargo.toml" in detailed_error or "Cargo.toml" in detailed_error.lower():
                 return {'results': [], 'errors': "Fichier Cargo.toml introuvable. Ce projet ne semble pas être un projet Rust valide."}
            elif "error: could not compile" in detailed_error.lower():
                return {'results': [], 'errors': "Le projet Rust contient des erreurs de compilation qui empêchent l'analyse Clippy."}
            elif "rustc" in detailed_error.lower() or "rust" in detailed_error.lower() and "not found" in detailed_error.lower():
                return {'results': [], 'errors': "Environnement Rust non correctement configuré dans le conteneur Docker."}
            return {'results': [], 'errors': f"Clippy a échoué (code {result.returncode}): {detailed_error[:200]}"}

        return {'json_lines': json_lines}
            
    except subprocess.TimeoutExpired:
        return {'results': [], 'errors': "Clippy timeout (dépassé 20 minutes)"}
    except Exception as e:
        return {'results': [], 'errors': str(e)}


def parse_clippy_results(json_lines: list, repo_path: str) -> list:
    """
    Transforme la sortie JSON de Clippy en liste de vulnérabilités au format VulnOps.
    """
    vulnerabilities = []
    
    for entry in json_lines:
        # On ne s'intéresse qu'aux messages du compilateur
        if entry.get('reason') != 'compiler-message':
            continue
            
        message_obj = entry.get('message', {})
        level_raw = message_obj.get('level', 'warning')
        
        if level_raw == 'error':
            severity = 'HIGH'
        elif level_raw == 'warning':
            severity = 'MEDIUM'
        else:
            severity = 'LOW'
            
        code_obj = message_obj.get('code')
        test_id = code_obj.get('code', 'CLIPPY') if code_obj else 'CLIPPY'
        
        # On récupère le span primaire
        spans = message_obj.get('spans', [])
        primary_span = next((s for s in spans if s.get('is_primary')), None)
        
        if not primary_span:
            continue
            
        filename = primary_span.get('file_name', '')
        line_number = primary_span.get('line_start', 0)

        vuln = {
            'test_id': test_id,
            'test_name': f"Clippy ({test_id})",
            'issue_text': message_obj.get('message', ''),
            'severity': severity,
            'confidence': 'HIGH',
            'filename': filename,
            'line_number': line_number,
            'line_range': [primary_span.get('line_start', 0), primary_span.get('line_end', 0)],
            'code_snippet': primary_span.get('text', [{}])[0].get('text', '').strip() if primary_span.get('text') else '',
            'cwe': '',
            'more_info': f"https://rust-lang.github.io/rust-clippy/master/index.html#{test_id.replace('clippy::', '')}",
        }
        vulnerabilities.append(vuln)
        
    return vulnerabilities


def run_full_clippy_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    """
    Scan complet Clippy pour Rust.
    """
    base_tmp = os.path.abspath('tmp')
    if not os.path.exists(base_tmp):
        os.makedirs(base_tmp)
        
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_clippy_', dir=base_tmp)
    
    try:
        # 1. Clone
        print(f"1. Clonage de {repo_owner}/{repo_name} dans {tmp_dir}...")
        clone_repo(clone_url, access_token, tmp_dir)
        
        # 2. Clippy execution
        print("2. Analyse avec Clippy...")
        clippy_result = run_clippy(tmp_dir)
        
        if 'errors' in clippy_result:
            return {'success': False, 'error': clippy_result['errors']}
        
        # 3. Parsing
        print("3. Parsing des messages Clippy...")
        vulnerabilities = parse_clippy_results(clippy_result.get('json_lines', []), tmp_dir)
        
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
            'data': clippy_result.get('json_lines', []),
            'raw_output': json.dumps(clippy_result.get('json_lines', [])),
        }


    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Clippy exception: {error_detail}")
        return {'success': False, 'error': f'Erreur inattendue (Clippy): {str(e)}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
