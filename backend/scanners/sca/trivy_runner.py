import subprocess
import json
import logging
import os
import stat
from ..base import BaseScanner

logger = logging.getLogger(__name__)

class TrivyRunner(BaseScanner):
    def __init__(self):
        super().__init__("Trivy")
    
    def run(self, target_path_or_url, **kwargs):
        result = run_trivy(target_path_or_url)
        if result['success']:
            return parse_trivy_results(result['data'], target_path_or_url)
        return []

def run_trivy(repo_path: str) -> dict:
    """
    Exécute Trivy sur un répertoire et retourne les résultats JSON bruts.
    Fonctionne via Docker sur Windows avec gestion correcte des chemins.
    """
    if not repo_path or not os.path.exists(repo_path):
        return {'success': False, 'error': f"Chemin invalide : {repo_path}"}

    try:
        abs_repo_path = os.path.abspath(repo_path)
        
        # Sur Windows, Docker Desktop accepte les chemins en format /c/Users/...
        # ou directement le chemin Windows avec guillemets
        # On utilise le format Windows natif que Docker Desktop convertit automatiquement
        
        logger.info(f"Running Trivy via Docker on: {abs_repo_path}")
        
        result = subprocess.run(
            [
                'docker', 'run', '--rm',
                '-v', f"{abs_repo_path}:/app:ro",
                'aquasec/trivy', 'fs',
                '--format', 'json',
                '--quiet',
                '--no-progress',
                '/app'
            ],
            capture_output=True,
            text=True,
            timeout=300,
            encoding='utf-8',
            errors='replace'
        )
        
        logger.info(f"Trivy returncode: {result.returncode}")
        
        if result.returncode != 0:
            logger.error(f"Trivy stderr: {result.stderr[:500]}")
            return {'success': False, 'error': result.stderr or "Erreur inconnue Trivy"}
        
        if not result.stdout.strip():
            logger.warning("Trivy returned empty output — no vulnerabilities found")
            return {'success': True, 'data': {'Results': []}}
        
        try:
            data = json.loads(result.stdout)
            return {'success': True, 'data': data}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Trivy JSON output: {e}")
            logger.error(f"Raw output (first 500): {result.stdout[:500]}")
            return {'success': False, 'error': f"Invalid JSON from Trivy: {str(e)}"}
        
    except subprocess.TimeoutExpired:
        logger.error("Trivy scan timed out after 300s")
        return {'success': False, 'error': "Trivy scan timed out"}
    except FileNotFoundError:
        logger.error("Docker not found — Trivy requires Docker to be installed and running")
        return {'success': False, 'error': "Docker not found. Please ensure Docker Desktop is running."}
    except Exception as e:
        logger.error(f"Unexpected error running Trivy: {e}")
        return {'success': False, 'error': str(e)}

def parse_trivy_results(trivy_data, repo_path):
    """Parse les résultats de Trivy en format standard."""
    vulnerabilities = []
    results = trivy_data.get('Results', [])
    
    severity_map = {
        'CRITICAL': 'CRITICAL',
        'HIGH': 'HIGH',
        'MEDIUM': 'MEDIUM',
        'LOW': 'LOW',
        'UNKNOWN': 'LOW',
    }
    
    for res in results:
        target = res.get('Target', '')
        vulns = res.get('Vulnerabilities') or []
        for v in vulns:
            raw_severity = v.get('Severity', 'LOW').upper()
            severity = severity_map.get(raw_severity, 'LOW')
            
            fixed_version = v.get('FixedVersion', '')
            fix_text = f" Fix available in version {fixed_version}." if fixed_version else ""
            
            vulnerabilities.append({
                'test_id': v.get('VulnerabilityID', 'SCA-VULN'),
                'test_name': v.get('PkgName', 'Unknown Package'),
                'issue_text': v.get('Description') or v.get('Title') or 'No description available.' + fix_text,
                'severity': severity,
                'confidence': 'HIGH',
                'filename': target,
                'line_number': 0,            # Required by model but not applicable for SCA
                'line_range': [],            # Required by model but not applicable for SCA
                'code_snippet': f"{v.get('PkgName', '')}@{v.get('InstalledVersion', 'unknown')}",
                'cwe': v.get('CweIDs', [''])[0] if v.get('CweIDs') else '',
                'more_info': (v.get('References') or [''])[0],
                'is_sca': True
            })
    
    logger.info(f"Trivy found {len(vulnerabilities)} vulnerabilities")
    return vulnerabilities
