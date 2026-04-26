"""
GitHub App Service — Gestion des tokens, création de workflows et secrets.

Flow:
  1. generate_jwt()            → JWT signé avec la clé privée de l'App
  2. get_installation_token()  → Token temporaire pour agir sur le repo
  3. create_workflow_file()    → Crée .github/workflows/vulnops-scan.yml
  4. set_repo_secrets()        → Configure API_TOKEN + BACKEND_URL dans GitHub Secrets
  5. setup_repository()        → Orchestrateur (1 → 2 → 3 → 4)
"""

import time
import base64
import logging
import requests

from django.conf import settings

logger = logging.getLogger(__name__)


class GitHubAppService:
    """Service principal pour interagir avec l'API GitHub via GitHub App."""

    GITHUB_API_URL = "https://api.github.com"

    def __init__(self):
        self.app_id = getattr(settings, 'GITHUB_APP_ID', '')
        self.private_key = self._load_private_key()
        self.app_name = getattr(settings, 'GITHUB_APP_NAME', 'vulnops-security')

    def _load_private_key(self) -> str:
        """Charge la clé privée depuis un fichier .pem ou depuis les settings."""
        key_path = getattr(settings, 'GITHUB_APP_PRIVATE_KEY_PATH', '')
        key_content = getattr(settings, 'GITHUB_APP_PRIVATE_KEY', '')

        if key_content:
            return key_content

        if key_path:
            try:
                with open(key_path, 'r') as f:
                    return f.read()
            except FileNotFoundError:
                logger.warning(f"GitHub App private key not found at: {key_path}")
        return ''

    def generate_jwt(self) -> str:
        """Génère un JWT GitHub App (valable 10 minutes)."""
        if not self.app_id or not self.private_key:
            raise ValueError("GitHub App ID et Private Key sont requis.")

        try:
            import jwt as pyjwt
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend

            # Charger la clé privée
            private_key = serialization.load_pem_private_key(
                self.private_key.encode() if isinstance(self.private_key, str) else self.private_key,
                password=None,
                backend=default_backend()
            )

            now = int(time.time())
            payload = {
                'iat': now - 60,        # issued at (60s dans le passé pour éviter les décalages d'horloge)
                'exp': now + (10 * 60), # expire dans 10 minutes
                'iss': self.app_id,     # issuer = App ID
            }

            token = pyjwt.encode(payload, private_key, algorithm='RS256')
            return token if isinstance(token, str) else token.decode('utf-8')

        except ImportError:
            raise ImportError("Installez PyJWT et cryptography: pip install PyJWT cryptography")
        except Exception as e:
            logger.error(f"Erreur génération JWT: {e}")
            raise

    def get_installation_token(self, installation_id: int) -> str:
        """Échange le JWT contre un token d'installation temporaire (1h)."""
        jwt_token = self.generate_jwt()

        response = requests.post(
            f"{self.GITHUB_API_URL}/app/installations/{installation_id}/access_tokens",
            headers={
                'Authorization': f'Bearer {jwt_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
            },
            timeout=15
        )

        if response.status_code != 201:
            logger.error(f"Erreur obtention token d'installation: {response.status_code} - {response.text}")
            raise Exception(f"Impossible d'obtenir le token d'installation: {response.text}")

        return response.json().get('token')

    def get_installation_repos(self, installation_id: int) -> list:
        """Liste les repos accessibles par une installation."""
        token = self.get_installation_token(installation_id)

        response = requests.get(
            f"{self.GITHUB_API_URL}/installation/repositories",
            headers={
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github+json',
            },
            params={'per_page': 100},
            timeout=15
        )

        if response.status_code != 200:
            return []

        return response.json().get('repositories', [])

    def create_workflow_file(self, installation_id: int, repo_full_name: str) -> bool:
        """
        Crée .github/workflows/vulnops-scan.yml dans le repo via l'API GitHub Contents.
        Retourne True si succès, False sinon.
        """
        token = self.get_installation_token(installation_id)
        owner, repo = repo_full_name.split('/', 1)

        # Contenu du workflow YAML
        workflow_content = self._get_workflow_yaml()
        content_b64 = base64.b64encode(workflow_content.encode()).decode()

        # Vérifier si le fichier existe déjà
        check_response = requests.get(
            f"{self.GITHUB_API_URL}/repos/{owner}/{repo}/contents/.github/workflows/vulnops-scan.yml",
            headers={
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github+json',
            },
            timeout=10
        )

        payload = {
            'message': '🔒 Add VulnOps automated security scanning pipeline',
            'content': content_b64,
        }

        if check_response.status_code == 200:
            # Fichier existe → mettre à jour
            payload['sha'] = check_response.json().get('sha')
            payload['message'] = '🔒 Update VulnOps security scanning pipeline'

        response = requests.put(
            f"{self.GITHUB_API_URL}/repos/{owner}/{repo}/contents/.github/workflows/vulnops-scan.yml",
            headers={
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github+json',
            },
            json=payload,
            timeout=15
        )

        if response.status_code in (200, 201):
            logger.info(f"✅ Workflow créé dans {repo_full_name}")
            return True
        else:
            logger.error(f"❌ Erreur création workflow dans {repo_full_name}: {response.status_code} - {response.text}")
            return False

    def get_repo_public_key(self, token: str, owner: str, repo: str) -> tuple:
        """Récupère la clé publique du repo pour chiffrer les secrets."""
        response = requests.get(
            f"{self.GITHUB_API_URL}/repos/{owner}/{repo}/actions/secrets/public-key",
            headers={
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github+json',
            },
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"Impossible d'obtenir la clé publique: {response.text}")

        data = response.json()
        return data['key_id'], data['key']

    def encrypt_secret(self, public_key_b64: str, secret_value: str) -> str:
        """Chiffre un secret avec la clé publique du repo (libsodium/nacl)."""
        try:
            from nacl import encoding, public
            public_key_bytes = base64.b64decode(public_key_b64)
            pk = public.PublicKey(public_key_bytes)
            box = public.SealedBox(pk)
            encrypted = box.encrypt(secret_value.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
        except ImportError:
            raise ImportError("Installez PyNaCl: pip install PyNaCl")

    def set_repo_secret(self, token: str, owner: str, repo: str, key_id: str, public_key_b64: str, secret_name: str, secret_value: str) -> bool:
        """Configure un secret GitHub Actions sur le repo."""
        encrypted_value = self.encrypt_secret(public_key_b64, secret_value)

        response = requests.put(
            f"{self.GITHUB_API_URL}/repos/{owner}/{repo}/actions/secrets/{secret_name}",
            headers={
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github+json',
            },
            json={
                'encrypted_value': encrypted_value,
                'key_id': key_id,
            },
            timeout=10
        )
        return response.status_code in (201, 204)

    def set_repo_secrets(self, installation_id: int, repo_full_name: str) -> dict:
        """
        Configure les secrets VulnOps dans le repo:
        - VULNOPS_API_TOKEN
        - VULNOPS_BACKEND_URL
        Retourne un dict {secret_name: bool}
        """
        from django.conf import settings as django_settings

        token = self.get_installation_token(installation_id)
        owner, repo = repo_full_name.split('/', 1)

        try:
            key_id, public_key = self.get_repo_public_key(token, owner, repo)
        except Exception as e:
            logger.error(f"Impossible de récupérer la clé publique de {repo_full_name}: {e}")
            return {'VULNOPS_API_TOKEN': False, 'VULNOPS_BACKEND_URL': False}

        api_token = getattr(django_settings, 'GITHUB_CICD_TOKEN', '') or \
                    getattr(django_settings, 'API_TOKEN', 'vulnops-cicd-token')
        backend_url = getattr(django_settings, 'BACKEND_PUBLIC_URL', 'http://localhost:8000')

        results = {}
        results['VULNOPS_API_TOKEN'] = self.set_repo_secret(
            token, owner, repo, key_id, public_key,
            'VULNOPS_API_TOKEN', api_token
        )
        results['VULNOPS_BACKEND_URL'] = self.set_repo_secret(
            token, owner, repo, key_id, public_key,
            'VULNOPS_BACKEND_URL', backend_url
        )

        logger.info(f"Secrets configurés dans {repo_full_name}: {results}")
        return results

    def setup_repository(self, installation_id: int, repo_full_name: str) -> dict:
        """
        Orchestrateur complet : crée le workflow + configure les secrets.
        Retourne un dict de statut.
        """
        result = {
            'repo': repo_full_name,
            'workflow_created': False,
            'secrets_configured': {},
            'success': False,
            'error': None,
        }

        try:
            result['workflow_created'] = self.create_workflow_file(installation_id, repo_full_name)
            result['secrets_configured'] = self.set_repo_secrets(installation_id, repo_full_name)
            result['success'] = result['workflow_created']
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Erreur setup repo {repo_full_name}: {e}")

        return result

    def _get_workflow_yaml(self) -> str:
        """Retourne le contenu YAML du pipeline VulnOps."""
        backend_url = getattr(settings, 'BACKEND_PUBLIC_URL', 'http://localhost:8000')
        return f"""name: 🔒 VulnOps Security Scan

on:
  push:
    branches: ["main", "master", "develop"]
  pull_request:
    branches: ["main", "master"]

jobs:
  vulnops-security-scan:
    name: Security Analysis (SAST & SCA)
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write

    steps:
      - name: 📥 Checkout code
        uses: actions/checkout@v4

      - name: 🐍 Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 📦 Install reporting dependencies
        run: pip install requests

      - name: 🔍 Run SAST (Semgrep)
        run: |
          python3 -m pip install semgrep
          semgrep scan --json --config=auto --output=semgrep-report.json . || true
        continue-on-error: true

      - name: 📦 Run SCA (npm audit)
        run: |
          if [ -f package.json ]; then
            npm install --package-lock-only --ignore-scripts || true
            npm audit --json > sca-report.json || true
          else
            echo '{{"vulnerabilities": {{}}}}' > sca-report.json
          fi
        continue-on-error: true

      - name: 🚀 Send results to VulnOps Platform
        env:
          API_TOKEN: ${{{{ secrets.VULNOPS_API_TOKEN }}}}
          BACKEND_URL: ${{{{ secrets.VULNOPS_BACKEND_URL }}}}
        run: |
          python3 - <<'EOF'
          import json, os, requests, sys

          def load_json(path):
              if os.path.exists(path):
                  try:
                      with open(path) as f:
                          return json.load(f)
                  except:
                      return {{}}
              return {{}}

          sast_data = load_json('semgrep-report.json')
          sca_data = load_json('sca-report.json')

          payload = {{
              "repo_full_name": os.environ.get('GITHUB_REPOSITORY'),
              "repo_owner": os.environ.get('GITHUB_REPOSITORY_OWNER'),
              "repo_name": os.environ.get('GITHUB_REPOSITORY', '/').split('/')[-1],
              "branch": os.environ.get('GITHUB_REF_NAME'),
              "commit_sha": os.environ.get('GITHUB_SHA'),
              "triggered_by": "github-app",
              "reports": {{}}
          }}

          if sast_data:
              payload["reports"]["sast"] = {{"scanner": "semgrep", "data": sast_data}}
          if sca_data and sca_data.get('vulnerabilities'):
              payload["reports"]["sca"] = {{"scanner": "npm-audit", "data": sca_data}}

          backend_url = os.environ.get('BACKEND_URL', '').rstrip('/')
          if not backend_url:
              print("⚠️  BACKEND_URL not set, skipping report.")
              sys.exit(0)

          url = f"{{backend_url}}/api/scans/github/"
          headers = {{
              "Content-Type": "application/json",
              "Authorization": f"Bearer {{os.environ.get('API_TOKEN', '')}}"
          }}

          print(f"📤 Sending results to {{url}}...")
          try:
              resp = requests.post(url, json=payload, headers=headers, timeout=60)
              print(f"Status: {{resp.status_code}}")
              if resp.status_code >= 400:
                  print(f"Error: {{resp.text}}")
          except Exception as e:
              print(f"Connection error: {{e}}")
          EOF
"""
