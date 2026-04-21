import subprocess
import json
import logging
import os
import tempfile
import shutil
from ..base import BaseScanner

logger = logging.getLogger(__name__)

class DependencyCheckRunner(BaseScanner):
    def __init__(self):
        super().__init__("OWASP Dependency-Check")
    
    def run(self, target_path_or_url, **kwargs):
        targets = kwargs.get('targets', [])
        result = run_dependency_check(target_path_or_url, targets=targets)
        if result['success']:
            return parse_dependency_check_results(result['data'], target_path_or_url)
        return []

def run_dependency_check(repo_path: str, targets: list = None) -> dict:
    """
    Exécute OWASP Dependency-Check sur un répertoire ou des cibles spécifiques et retourne les résultats JSON bruts.
    """
    if not repo_path or not os.path.exists(repo_path):
        return {'success': False, 'error': f"Chemin invalide : {repo_path}"}

    # Prépare les cibles du scan
    scan_targets = []
    if targets:
        for t in targets:
            full_path = os.path.join(repo_path, t)
            if os.path.exists(full_path):
                scan_targets.append(full_path)
    
    if not scan_targets:
        scan_targets = [os.path.abspath(repo_path)]

    # Créer un répertoire temporaire pour le rapport
    report_dir = tempfile.mkdtemp(prefix='depcheck_report_')
    report_file = os.path.join(report_dir, 'dependency-check-report.json')

    try:
        abs_repo_path = os.path.abspath(repo_path)
        
        logger.info(f"Running Dependency-Check on: {abs_repo_path}")
        
        # Commande simplifiée. Note: Dependency-Check peut être long au premier run (téléchargement NVD)
        # On utilise --format JSON
        # On suppose que 'dependency-check.bat' ou 'dependency-check.sh' est dans le PATH
        cmd = [
            'dependency-check',
            '--project', 'VulnOpsProject',
            '--format', 'JSON',
            '--out', report_dir,
            '--prettyPrint'
        ]
        for t in scan_targets:
            cmd.extend(['--scan', t])

        # Sur Windows, on peut avoir besoin d'appeler l'exécutable spécifiquement
        if os.name == 'nt':
            # Tenter avec .bat si la commande directe échoue, ou utiliser 'shell=True'
            pass

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900, # 15 minutes car le scan NVD peut être long
            encoding='utf-8',
            errors='replace'
        )
        
        logger.info(f"Dependency-Check returncode: {result.returncode}")
        
        if not os.path.exists(report_file):
            logger.error(f"Dependency-Check report not found: {report_file}")
            logger.error(f"Stderr: {result.stderr}")
            return {'success': False, 'error': "Rapport Dependency-Check non généré."}
        
        with open(report_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {'success': True, 'data': data}
        
    except subprocess.TimeoutExpired:
        logger.error("Dependency-Check scan timed out")
        return {'success': False, 'error': "Dependency-Check scan timed out"}
    except FileNotFoundError:
        logger.error("Dependency-Check not found in PATH")
        return {'success': False, 'error': "Dependency-Check non trouvé. Assurez-vous qu'il est installé et dans le PATH."}
    except Exception as e:
        logger.error(f"Unexpected error running Dependency-Check: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        if os.path.exists(report_dir):
            shutil.rmtree(report_dir, ignore_errors=True)

def parse_dependency_check_results(dc_data, repo_path):
    """Parse les résultats de Dependency-Check en format standard."""
    vulnerabilities = []
    dependencies = dc_data.get('dependencies', [])
    
    severity_map = {
        'CRITICAL': 'CRITICAL',
        'HIGH': 'HIGH',
        'MEDIUM': 'MEDIUM',
        'LOW': 'LOW',
        'INFO': 'LOW',
    }
    
    for dep in dependencies:
        file_path = dep.get('filePath', '')
        vulns = dep.get('vulnerabilities') or []
        for v in vulns:
            raw_severity = v.get('severity', 'LOW').upper()
            severity = severity_map.get(raw_severity, 'LOW')
            
            name = v.get('name', 'N/A')
            cvss = v.get('cvssv3', {}).get('baseScore') or v.get('cvssv2', {}).get('score')
            
            vulnerabilities.append({
                'test_id': name,
                'test_name': f"Dependency: {dep.get('fileName', 'Unknown')}",
                'issue_text': v.get('description', 'No description available.'),
                'severity': severity,
                'confidence': 'HIGH',
                'filename': file_path.replace(repo_path, '').lstrip(os.sep),
                'line_number': 0,
                'line_range': [],
                'code_snippet': f"CVSS Score: {cvss}" if cvss else "N/A",
                'cwe': v.get('cwes', [''])[0] if v.get('cwes') else '',
                'more_info': (v.get('references', [{}])[0].get('url', '')),
                'is_sca': True
            })
    
    logger.info(f"Dependency-Check found {len(vulnerabilities)} vulnerabilities")
    return vulnerabilities
