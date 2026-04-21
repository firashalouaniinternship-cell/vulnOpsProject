import os
import json
import shutil
import subprocess
import tempfile
import git
from django.conf import settings
from core.utils.repo_utils import clone_repo
def run_bandit(repo_path: str, targets: list = None) -> dict:
    """
    Exécute Bandit sur un répertoire ou des cibles spécifiques et retourne les résultats JSON.
    """
    print(f"Exécution de Bandit sur : {repo_path} (targets: {targets})")
    
    # Prépare les cibles du scan
    scan_targets = []
    if targets:
        for t in targets:
            full_path = os.path.join(repo_path, t)
            if os.path.exists(full_path):
                scan_targets.append(full_path)
    
    if not scan_targets:
        scan_targets = [repo_path] # Fallback sur le repo complet if nothing valid selected
    
    # Vérifie si bandit est installé
    try:
        subprocess.run(['bandit', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {'results': [], 'metrics': {}, 'errors': "Bandit n'est pas installé sur le système."}

    result = subprocess.run(
        [
            'bandit',
            '-r',              # récursif
            '-f', 'json',      # format JSON
            '-ll',             # niveau minimum LOW
            '--exit-zero',     # ne pas échouer même si des issues trouvées
        ] + scan_targets,
        capture_output=True,
        text=True,
        timeout=300  # 5 minutes max pour les gros repos
    )

    if not result.stdout.strip():
        # Pas de sortie stdout, possible erreur
        return {
            'results': [],
            'metrics': {},
            'errors': result.stderr or "Aucune sortie reçue de Bandit.",
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Erreur de décodage JSON Bandit: {str(e)}")
        return {
            'results': [],
            'metrics': {},
            'errors': f"Erreur lors du parsing des résultats : {str(e)}",
        }


def parse_bandit_results(bandit_output: dict, repo_path: str) -> list:
    """
    Transforme la sortie JSON de Bandit en liste de vulnérabilités.
    Nettoie les chemins absolus pour n'afficher que le chemin relatif.
    """
    vulnerabilities = []
    results = bandit_output.get('results', [])

    for issue in results:
        # Nettoie le chemin du fichier (enlève le préfixe du répertoire temporaire)
        filename = issue.get('filename', '')
        if repo_path in filename:
            filename = filename.replace(repo_path, '').lstrip('/').lstrip('\\')

        cwe_info = issue.get('issue_cwe', {})
        cwe = f"CWE-{cwe_info.get('id', '')}" if cwe_info.get('id') else ''

        vuln = {
            'test_id': issue.get('test_id', ''),
            'test_name': issue.get('test_name', ''),
            'issue_text': issue.get('issue_text', ''),
            'severity': issue.get('issue_severity', 'LOW').upper(),
            'confidence': issue.get('issue_confidence', 'LOW').upper(),
            'filename': filename,
            'line_number': issue.get('line_number', 0),
            'line_range': issue.get('line_range', []),
            'code_snippet': issue.get('code', '').strip(),
            'cwe': cwe,
            'more_info': issue.get('more_info', ''),
        }
        vulnerabilities.append(vuln)

    return vulnerabilities


def get_metrics(bandit_output: dict) -> dict:
    """Retourne les métriques globales du scan"""
    metrics = bandit_output.get('metrics', {}).get('_totals', {})
    return {
        'total_issues': metrics.get('SEVERITY.HIGH', 0) + metrics.get('SEVERITY.MEDIUM', 0) + metrics.get('SEVERITY.LOW', 0),
        'high_count': int(metrics.get('SEVERITY.HIGH', 0)),
        'medium_count': int(metrics.get('SEVERITY.MEDIUM', 0)),
        'low_count': int(metrics.get('SEVERITY.LOW', 0)),
        'files_analyzed': int(metrics.get('loc', 0)),
    }


from ..base import BaseScanner

class BanditRunner(BaseScanner):
    def __init__(self):
        super().__init__("Bandit")

    def run(self, target_path_or_url, **kwargs):
        access_token = kwargs.get('access_token')
        targets = kwargs.get('targets', [])
        # On utilise la fonction existante run_full_scan pour conserver la logique
        result = run_full_scan(target_path_or_url, access_token, targets=targets)
        if result['success']:
            return result['vulnerabilities']
        return []

def run_full_scan(clone_url: str, access_token: str, repo_path: str = None, targets: list = None) -> dict:
    """
    Lance un scan complet :
    1. Clone le dépôt (si repo_path est None)
    2. Exécute Bandit
    3. Parse les résultats
    4. Nettoie les fichiers temporaires (uniquement si crée par cette fonction)
    """
    is_temp = False
    if not repo_path:
        repo_path = tempfile.mkdtemp(prefix='vulnops_')
        is_temp = True
        
    try:
        # Clone if needed
        if is_temp:
            clone_repo(clone_url, access_token, repo_path)

        # Scan
        bandit_output = run_bandit(repo_path, targets=targets)

        # Parse
        vulnerabilities = parse_bandit_results(bandit_output, repo_path)
        metrics = get_metrics(bandit_output)

        return {
            'success': True,
            'vulnerabilities': vulnerabilities,
            'metrics': metrics,
            'raw_output': json.dumps(bandit_output),
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Le scan a dépassé le délai de 2 minutes'}
    except git.GitCommandError as e:
        return {'success': False, 'error': f'Erreur de clonage Git: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Erreur inattendue: {str(e)}'}
    finally:
        # Toujours nettoyer le répertoire temporaire s'il a été créé ici
        if is_temp and os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)
