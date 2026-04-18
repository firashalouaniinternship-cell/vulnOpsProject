import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from core.utils.repo_utils import clone_repo
from core.utils.docker_utils import get_docker_path_mapping, ensure_docker_image, run_docker_container


def run_cppcheck(repo_path: str) -> dict:
    """
    Exécute Cppcheck via Docker sur un répertoire et retourne les résultats XML.
    """
    print(f"Exécution de Cppcheck (Docker) sur : {repo_path}")
    
    # 1. S'assurer que l'image est présente
    image_name = 'facthunder/cppcheck'
    success, error_msg = ensure_docker_image(image_name)
    if not success:
        return {'results': [], 'errors': error_msg}

    # 2. Préparer le mapping de volume
    volume_mapping = get_docker_path_mapping(repo_path)
    working_dir = '/src'
    
    try:
        # On ajoute un 'ls' de débug pour voir ce que Docker voit réellement
        command = [
            'sh', '-c', 'ls -la /src && cppcheck --xml --xml-version=2 --enable=all --inconclusive .'
        ]
        
        result = run_docker_container(
            image_name=image_name,
            volume_mapping=volume_mapping,
            working_dir=working_dir,
            command=command,
            timeout=1200
        )
        
        output = (result.stdout or "") + (result.stderr or "")
        
        xml_start = output.find('<?xml')
        if xml_start == -1:
            xml_start = output.find('<results')
            
        if xml_start != -1:
            xml_data = output[xml_start:]
        else:
            xml_data = ""
        
        if result.returncode != 0 and not xml_data.strip():
            # Retourne le début de l'output pour aider au débug
            detailed_error = output.strip() or result.stderr.strip() or "Aucun message d'erreur Docker"
            print(f"Docker failed: {detailed_error}")
            return {'results': [], 'errors': f"Erreur Docker ({result.returncode}): {detailed_error[:200]}"}

        if not xml_data.strip():
            return {'results': []}

        return {'xml': xml_data}
    
    except subprocess.TimeoutExpired:
        return {'results': [], 'errors': "Cppcheck timeout (exceeded 10 minutes)"}
    except Exception as e:
        return {'results': [], 'errors': str(e)}


def parse_cppcheck_results(xml_data: str, repo_path: str) -> list:
    """
    Transforme la sortie XML de Cppcheck en liste de vulnérabilités.
    """
    vulnerabilities = []
    
    try:
        root = ET.fromstring(xml_data)
        errors = root.find('errors')
        if errors is None:
            return []
            
        for error in errors.findall('error'):
            severity_raw = error.get('severity', 'info')
            
            # Mapping des sévérités
            if severity_raw == 'error':
                severity = 'HIGH'
            elif severity_raw == 'warning':
                severity = 'MEDIUM'
            else:
                severity = 'LOW'
                
            location = error.find('location')
            filename = ""
            line_number = 0
            
            if location is not None:
                filename = location.get('file', '')
                line_str = location.get('line', '0')
                line_number = int(line_str) if line_str.isdigit() else 0
                
                # Nettoyage du chemin (Cppcheck retourne des chemins relatifs au CWD)
                filename = filename.lstrip('./').lstrip('.\\')

            vuln = {
                'test_id': error.get('id', 'CPPCHECK'),
                'test_name': 'Cppcheck',
                'issue_text': error.get('msg', ''),
                'severity': severity,
                'confidence': 'MEDIUM' if error.get('inconclusive') else 'HIGH',
                'filename': filename,
                'line_number': line_number,
                'line_range': [line_number, line_number],
                'code_snippet': error.get('verbose', ''),
                'cwe': error.get('cwe', ''),
                'more_info': f"https://cwe.mitre.org/data/definitions/{error.get('cwe')}.html" if error.get('cwe') else "",
            }
            vulnerabilities.append(vuln)
            
    except Exception as e:
        print(f"Erreur lors du parsing XML Cppcheck: {e}")
        
    return vulnerabilities


def run_full_cppcheck_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    """
    Lance un scan complet Cppcheck pour un projet C/C++:
    1. Clone le dépôt
    2. Lance Cppcheck
    3. Parse les résultats
    4. Nettoie les fichiers temporaires
    """
    # On utilise un dossier tmp LOCAL au projet plutôt que le temp système
    # car Docker a parfois du mal à monter des dossiers de AppData\Local\Temp sur Windows
    base_tmp = os.path.abspath('tmp')
    if not os.path.exists(base_tmp):
        os.makedirs(base_tmp)
        
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_cppcheck_', dir=base_tmp)
    
    try:
        # 1. Clone
        print(f"1. Clonage dans {tmp_dir}...")
        clone_repo(clone_url, access_token, tmp_dir)
        
        # 2. Cppcheck execution
        print("2. Analyse avec Cppcheck...")
        cppcheck_result = run_cppcheck(tmp_dir)
        
        # Check for error messages returned in dict
        if 'errors' in cppcheck_result:
            return {'success': False, 'error': cppcheck_result['errors']}
        
        if 'xml' not in cppcheck_result:
            return {
                'success': True,
                'vulnerabilities': [],
                'metrics': {'total_issues': 0, 'high_count': 0, 'medium_count': 0, 'low_count': 0, 'files_analyzed': 0},
                'raw_output': "No XML output from Cppcheck"
            }

        # 3. Parsing
        print("3. Parsing et formatage...")
        vulnerabilities = parse_cppcheck_results(cppcheck_result['xml'], tmp_dir)
        
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
            'data': cppcheck_result.get('xml', ''),
            'raw_output': cppcheck_result.get('xml', ''),
        }


    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Cppcheck exception: {error_detail}")
        return {'success': False, 'error': f'Erreur inattendue(Cppcheck): {str(e)}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
