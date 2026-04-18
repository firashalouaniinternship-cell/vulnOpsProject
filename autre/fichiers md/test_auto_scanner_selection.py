"""
Script de test pour le système d'auto-sélection des scanners.
Démontre comment utiliser les endpoints auto-select/auto-scan/analyze.
"""

import requests
import json
from typing import Optional


class VulnOpsClient:
    """Client pour l'API VulnOps avec support de l'auto-sélection."""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: Optional[str] = None):
        """
        Initialise le client.
        
        :param base_url: URL de base de l'API
        :param token: Token d'authentification
        """
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Content-Type": "application/json",
        }
        if token:
            self.headers["Authorization"] = f"Token {token}"
    
    def auto_select_scanners(self, repo_full_name: str, clone_url: str, 
                            repo_name: str, repo_owner: str) -> dict:
        """
        Auto-détecte les langages et recommande les scanners.
        
        :param repo_full_name: Nom complet du repo (owner/name)
        :param clone_url: URL de clone du repo
        :param repo_name: Nom du repo
        :param repo_owner: Propriétaire du repo
        :return: Réponse de l'API
        """
        url = f"{self.base_url}/api/scanner/auto-select/"
        
        payload = {
            "repo_full_name": repo_full_name,
            "clone_url": clone_url,
            "repo_name": repo_name,
            "repo_owner": repo_owner
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()
    
    def auto_trigger_scan(self, repo_full_name: str, clone_url: str,
                         repo_name: str, repo_owner: str) -> dict:
        """
        Auto-détecte et lance automatiquement les scans.
        
        :param repo_full_name: Nom complet du repo
        :param clone_url: URL de clone du repo
        :param repo_name: Nom du repo
        :param repo_owner: Propriétaire du repo
        :return: Réponse de l'API avec résultats des scans
        """
        url = f"{self.base_url}/api/scanner/auto-scan/"
        
        payload = {
            "repo_full_name": repo_full_name,
            "clone_url": clone_url,
            "repo_name": repo_name,
            "repo_owner": repo_owner
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()
    
    def analyze_project(self, project_path: str) -> dict:
        """
        Analyse un projet existant sans le clôner.
        
        :param project_path: Chemin du projet
        :return: Réponse de l'API avec analyse
        """
        url = f"{self.base_url}/api/scanner/analyze/"
        
        payload = {
            "project_path": project_path
        }
        
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()


def print_response(title: str, response: dict):
    """Affiche une réponse formatée."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(json.dumps(response, indent=2, ensure_ascii=False))


def test_auto_select():
    """Test : Auto-sélection sans lancer les scans."""
    print("\n" + "▶"*30)
    print("TEST 1: AUTO-SELECT (Recommandation)")
    print("▶"*30)
    
    client = VulnOpsClient(
        base_url="http://localhost:8000",
        token="YOUR_AUTH_TOKEN"
    )
    
    # Exemple avec un repo TypeScript/JavaScript
    result = client.auto_select_scanners(
        repo_full_name="facebook/react",
        clone_url="https://github.com/facebook/react.git",
        repo_name="react",
        repo_owner="facebook"
    )
    
    print_response("Résultats auto-sélection React", result)
    
    if result.get('success'):
        print("\n✓ Auto-sélection réussie!")
        print(f"  Langages détectés: {result['analysis']['languages']}")
        print(f"  Scanners recommandés: {result['suggested_scanners']}")
        print(f"  Confiance: {result['confidence']:.0%}")
        print(f"  Raisonnement: {result['reasoning']}")
    else:
        print("\n✗ Auto-sélection échouée!")


def test_auto_scan():
    """Test : Auto-détection et lancement des scans."""
    print("\n" + "▶"*30)
    print("TEST 2: AUTO-SCAN (Auto-détection + Lancement)")
    print("▶"*30)
    
    client = VulnOpsClient(
        base_url="http://localhost:8000",
        token="YOUR_AUTH_TOKEN"
    )
    
    # Exemple avec un repo Python (Django)
    result = client.auto_trigger_scan(
        repo_full_name="django/django",
        clone_url="https://github.com/django/django.git",
        repo_name="django",
        repo_owner="django"
    )
    
    print_response("Résultats auto-scan Django", result)
    
    if result.get('success'):
        print("\n✓ Auto-scan lancé avec succès!")
        print(f"  Scanners lancés: {result['auto_selected_scanners']}")
        print(f"  Nombre de scans: {result['total_scans']}")
        
        for scan in result['scan_results']:
            print(f"\n  Scanner: {scan['scanner']}")
            print(f"    Status: {scan['status']}")
            if scan['status'] == 'COMPLETED':
                print(f"    Vulnérabilités: {scan['vulnerabilities_count']}")
                print(f"    High: {scan['metrics']['high_count']}")
    else:
        print("\n✗ Auto-scan échoué!")


def test_analyze_existing():
    """Test : Analyse d'un projet existant."""
    print("\n" + "▶"*30)
    print("TEST 3: ANALYZE (Analyse d'un projet existant)")
    print("▶"*30)
    
    client = VulnOpsClient(
        base_url="http://localhost:8000",
        token="YOUR_AUTH_TOKEN"
    )
    
    result = client.analyze_project(
        project_path="/home/user/my-python-project"
    )
    
    print_response("Résultats analyse projet", result)
    
    if result.get('success'):
        print("\n✓ Analyse réussie!")
        print(f"  Chemin: {result['project_path']}")
        print(f"  Langages: {result['analysis']['languages']}")
        print(f"  Scanners recommandés: {result['suggested_scanners']}")
    else:
        print("\n✗ Analyse échouée!")


def test_with_various_repos():
    """Test avec différents types de repos."""
    print("\n" + "="*60)
    print("TESTS DE REPOS VARIÉS")
    print("="*60)
    
    client = VulnOpsClient(
        base_url="http://localhost:8000",
        token="YOUR_AUTH_TOKEN"
    )
    
    test_cases = [
        {
            "name": "Python/Django",
            "repo": "django/django",
            "url": "https://github.com/django/django.git"
        },
        {
            "name": "JavaScript/React",
            "repo": "facebook/react",
            "url": "https://github.com/facebook/react.git"
        },
        {
            "name": "Go/Kubernetes",
            "repo": "kubernetes/kubernetes",
            "url": "https://github.com/kubernetes/kubernetes.git"
        },
        {
            "name": "Rust/Tokio",
            "repo": "tokio-rs/tokio",
            "url": "https://github.com/tokio-rs/tokio.git"
        },
        {
            "name": "Ruby/Rails",
            "repo": "rails/rails",
            "url": "https://github.com/rails/rails.git"
        },
    ]
    
    for test in test_cases:
        print(f"\n▶ Analysing {test['name']}...")
        
        result = client.auto_select_scanners(
            repo_full_name=test['repo'],
            clone_url=test['url'],
            repo_name=test['repo'].split('/')[-1],
            repo_owner=test['repo'].split('/')[0]
        )
        
        if result.get('success'):
            langs = result['analysis']['languages']
            scanners = result['suggested_scanners']
            confidence = result['confidence']
            print(f"  ✓ Langages: {', '.join(langs)}")
            print(f"  ✓ Scanners: {', '.join(scanners)}")
            print(f"  ✓ Confiance: {confidence:.0%}")
        else:
            print(f"  ✗ Erreur: {result.get('error')}")


def main():
    """Fonction principale pour exécuter tous les tests."""
    print("\n" + "="*60)
    print("   VulnOps Auto-Scanner Selection - Tests")
    print("="*60)
    print("\nNote: Assurez-vous que le serveur Django tourne sur localhost:8000")
    print("      et que vous avez remplacé YOUR_AUTH_TOKEN par un token réel")
    print("      (obtenez-le avec: python manage.py drf_create_token <username>)")
    
    try:
        # Test 1: Auto-select
        test_auto_select()
        
        # Test 2: Auto-scan
        test_auto_scan()
        
        # Test 3: Analyze existing
        test_analyze_existing()
        
        # Test 4: Repos variés
        test_with_various_repos()
        
        print("\n" + "="*60)
        print("  Tous les tests sont terminés!")
        print("="*60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ ERREUR DE CONNEXION!")
        print("  Assurez-vous que le serveur Django tourne sur localhost:8000")
        print("  Commande: python manage.py runserver")
    except Exception as e:
        print(f"\n✗ ERREUR: {e}")


if __name__ == "__main__":
    main()
