"""Vérifier les données sauvegardées en base"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from apps.scans.models import ScanResult, Vulnerability

print("=== SCANS DETEKT EN BASE DE DONNÉES ===")
scans = ScanResult.objects.filter(scanner_type='detekt').order_by('-id')[:5]

print(f"Total scans Detekt: {scans.count()}\n")

for scan in scans:
    vulns = Vulnerability.objects.filter(scan=scan)
    print(f"Scan ID: {scan.id}")
    print(f"  Repo: {scan.repo_full_name}")
    print(f"  Status: {scan.status}")
    print(f"  Total Issues: {scan.total_issues}")
    print(f"  High: {scan.high_count}, Medium: {scan.medium_count}, Low: {scan.low_count}")
    print(f"  Error Message: {scan.error_message}")
    print(f"  Vulnerabilities in DB: {vulns.count()}")
    if vulns.count() > 0:
        for v in vulns[:2]:
            print(f"    - {v.test_name}: {v.issue_text[:60]}")
    print()
