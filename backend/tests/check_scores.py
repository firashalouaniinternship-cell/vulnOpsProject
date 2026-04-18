import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.scans.models import Vulnerability

print("--- VERIFICATION DES SCORES IA ---")
vulns = Vulnerability.objects.order_by('-id')[:3]

if not vulns:
    print("Aucune vulnérabilité trouvée en base.")
else:
    for v in vulns:
        print(f"ID: {v.id}")
        print(f"Test: {v.test_name}")
        print(f"Score: {v.llm_score}")
        print(f"Explication (Reasoning): {v.llm_explanation}")
        print("-" * 30)
