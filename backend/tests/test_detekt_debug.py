"""Test de debug pour Detekt"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from apps.scans.models import ScanResult
from scanners.sast.detekt_runner import run_full_detekt_scan

# Paramètres
clone_url = "https://github.com/firasHalouani/test-kotlin.git"
repo_owner = "firasHalouani"
repo_name = "test-kotlin"
access_token = "test_token"  # Token sera récupéré depuis le test

# Lancer le scan
print("Lancement du scan Detekt...")
result = run_full_detekt_scan(clone_url, access_token, repo_owner, repo_name)

print("\n=== RÉSULTAT DU SCAN ===")
print(f"Success: {result.get('success')}")
print(f"Error: {result.get('error')}")
print(f"Vulnerabilities count: {len(result.get('vulnerabilities', []))}")
print(f"Metrics: {result.get('metrics')}")

if result.get('vulnerabilities'):
    print("\nPremières vulnérabilités:")
    for vuln in result.get('vulnerabilities', [])[:3]:
        print(f"  - {vuln['test_name']}: {vuln['issue_text']}")
else:
    print("\nAucune vulnérabilité trouvée")

print(f"\nRaw output: {result.get('raw_output')}")
