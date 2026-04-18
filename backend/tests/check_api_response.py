"""Simuler une requête API pour récupérer les détails du scan"""
import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth.models import User
from apps.scans.models import ScanResult
from rest_framework.test import APIRequestFactory
from apps.scans.views import get_scan_detail

# Créer un user de test s'il n'existe pas
user, _ = User.objects.get_or_create(username='testuser', defaults={'first_name': 'Test'})

# Récupérer le dernier scan Detekt
scan = ScanResult.objects.filter(scanner_type='detekt').order_by('-id').first()

if not scan:
    print("Aucun scan Detekt trouvé!")
    sys.exit(1)

print(f"=== TEST API RESPONSE POUR SCAN {scan.id} ===\n")

# Créer une requête API
factory = APIRequestFactory()
request = factory.get(f'/api/apps.scans/detail/{scan.id}/')
request.user = scan.user

# Appeler la view
response = get_scan_detail(request, scan.id)

print(f"Status Code: {response.status_code}")
print(f"\nResponse Data:")
print(json.dumps(response.data, indent=2, default=str))

print(f"\nVulnerabilities count in response: {len(response.data.get('vulnerabilities', []))}")
print(f"Metrics: {response.data.get('metrics')}")
