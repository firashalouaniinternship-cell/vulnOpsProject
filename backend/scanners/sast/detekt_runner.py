import os
import shutil
import subprocess
import tempfile
import json
from core.utils.repo_utils import clone_repo
from core.utils.docker_utils import get_docker_path_mapping, ensure_docker_image, run_docker_container


def run_detekt(repo_path: str) -> dict:
    """
    Exécute Detekt via Docker sur un répertoire Kotlin et retourne les résultats JSON.
    Détekt est un analyseur statique pour Kotlin.
    """
    print(f"Exécution de Detekt (Docker) sur : {repo_path}")
    
    # 1. S'assurer que l'image est présente
    image_name = 'gradle:latest'
    success, error_msg = ensure_docker_image(image_name)
    if not success:
        return {'results': [], 'errors': error_msg}

    # 2. Préparer le mapping de volume
    volume_mapping = get_docker_path_mapping(repo_path)
    working_dir = '/workspace'
    
    try:
        # Commande pour exécuter Detekt via gradle
        # -x test : saute les tests (optionnel, peut être commenté)
        # La sortie est générée dans build/reports/detekt/detekt.json
        command = [
            'sh', '-c', 
            'gradle detekt --no-daemon 2>/dev/null || true && cat build/reports/detekt/detekt.json 2>/dev/null || echo "{}"'
        ]
        
        result = run_docker_container(
            image_name=image_name,
            volume_mapping=volume_mapping,
            working_dir=working_dir,
            command=command,
            timeout=3600  # Les builds gradle peuvent être longs, 1 heure
        )

        output = result.stdout or ""
        stderr = result.stderr or ""
        
        # Nettoie la sortie en extrayant uniquement le JSON valide
        # Gradle affiche beaucoup de logs avant le JSON
        json_output = output.strip()
        
        # Cherche le JSON valide (commence par {)
        json_start = json_output.find('{')
        if json_start != -1:
            json_output = json_output[json_start:]
        
        try:
            # Essaie parsing du JSON
            json_data = json.loads(json_output)
            return {'json': json_data}
        except json.JSONDecodeError:
            # Si on n'a pas de JSON valide, c'est une erreur
            if not json_output or json_output == '{}':
                detailed_error = stderr or "Detekt n'a pas généré de rapport JSON"
                if "Gradle" in detailed_error or "gradle" in detailed_error.lower():
                    return {'results': [], 'errors': "Gradle n'est pas configuré ou build.gradle est invalide."}
                elif "Kotlin" in detailed_error or "kotlin" in detailed_error.lower():
                    return {'results': [], 'errors': "Pas de code Kotlin détecté ou projet non configuré pour Kotlin."}
                return {'results': [], 'errors': f"Detekt a échoué: {detailed_error[:200]}"}
            return {'json': {}}  # JSON vide = aucun problème trouvé
            
    except subprocess.TimeoutExpired:
        return {'results': [], 'errors': "Detekt timeout (dépassé 1 heure)"}
    except Exception as e:
        return {'results': [], 'errors': str(e)}


def parse_detekt_results(json_data: dict, repo_path: str) -> list:
    """
    Transforme la sortie JSON de Detekt en liste de vulnérabilités au format VulnOps.
    """
    vulnerabilities = []
    
    # Détekt structure: { "version": "...", "statistics": {...}, "issues": [...] }
    issues = json_data.get('issues', [])
    
    for issue in issues:
        # Détekt severity: MAJOR, MINOR, WARNING, STYLE, INFO
        severity_raw = issue.get('severity', 'INFO')
        
        if severity_raw == 'MAJOR' or severity_raw == 'CRITICAL':
            severity = 'HIGH'
        elif severity_raw == 'MINOR' or severity_raw == 'WARNING':
            severity = 'MEDIUM'
        else:
            severity = 'LOW'
        
        filename = issue.get('filename', '')
        # Les chemins dans Docker commencent par /workspace/
        if filename.startswith('/workspace/'):
            filename = filename[11:]
        
        line_number = issue.get('startLine', 0)
        end_line = issue.get('endLine', line_number)

        # Détekt fournit aussi le message et les détails
        message = issue.get('message', '')
        rule_id = issue.get('ruleId', 'DETEKT')
        rule_set = issue.get('ruleSetId', 'style')

        vuln = {
            'test_id': rule_id,
            'test_name': f"Detekt ({rule_set})",
            'issue_text': message,
            'severity': severity,
            'confidence': 'HIGH',
            'filename': filename,
            'line_number': line_number,
            'line_range': [line_number, end_line],
            'code_snippet': issue.get('snippet', '').strip() if issue.get('snippet') else '',
            'cwe': '',  # Detekt ne fournit pas de CWE par défaut
            'more_info': f"https://detekt.dev/docs/rules/{rule_set.lower()}#{rule_id.lower()}",
        }
        vulnerabilities.append(vuln)
    
    return vulnerabilities


def run_full_detekt_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    """
    Scan complet Detekt pour Kotlin.
    """
    base_tmp = os.path.abspath('tmp')
    if not os.path.exists(base_tmp):
        os.makedirs(base_tmp)
        
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_detekt_', dir=base_tmp)
    
    try:
        # 1. Clone
        print(f"1. Clonage de {repo_owner}/{repo_name} dans {tmp_dir}...")
        clone_repo(clone_url, access_token, tmp_dir)
        
        # 2. Detekt execution
        print("2. Analyse avec Detekt...")
        detekt_result = run_detekt(tmp_dir)
        
        if 'errors' in detekt_result:
            return {'success': False, 'error': detekt_result['errors']}
        
        # 3. Parsing
        print("3. Parsing des résultats Detekt...")
        json_data = detekt_result.get('json', {})
        vulnerabilities = parse_detekt_results(json_data, tmp_dir)
        
        high = sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')
        medium = sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM')
        low = sum(1 for v in vulnerabilities if v['severity'] == 'LOW')
        
        statistics = json_data.get('statistics', {})
        files_analyzed = statistics.get('file', 0)
        
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
        print(f"Detekt exception: {error_detail}")
        return {'success': False, 'error': f'Erreur inattendue (Detekt): {str(e)}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
