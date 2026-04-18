#!/usr/bin/env python
"""Test complet du scan ESLint avec endpoint Django"""
import os
import sys
import django
import json

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from scanners.sast.eslint_runner import run_full_eslint_scan
from apps.scans.models import ScanResult, Vulnerability
from django.contrib.auth.models import User
from django.utils import timezone
from apps.users.models import GitHubProfile

# Create test user
try:
    user = User.objects.create_user(username='testuser_eslint', password='testpass')
except:
    user = User.objects.get(username='testuser_eslint')

try:
    profile = GitHubProfile.objects.create(
        user=user,
        github_id=999,
        github_login='testuser',
        github_access_token='ghp_test_token_' + 'x' * 50
    )
except:
    profile = user.github_profile

print("Testing full ESLint scan pipeline...")
print("=" * 60)

# Test with facebook/react which is a JS project
result = run_full_eslint_scan(
    'https://github.com/facebook/react.git',
    profile.github_access_token,
    'facebook',
    'react'
)

print(f"\n1. Scan result success: {result.get('success')}")
if not result.get('success'):
    print(f"   Error: {result.get('error')}")
    sys.exit(1)

vulnerabilities_data = result.get('vulnerabilities', [])
metrics = result.get('metrics', {})

print(f"2. Vulnerabilities found: {len(vulnerabilities_data)}")
print(f"   Metrics: {metrics}")

if vulnerabilities_data:
    print(f"\n3. First vulnerability structure:")
    v = vulnerabilities_data[0]
    print(f"   Keys: {list(v.keys())}")
    for key in v.keys():
        print(f"   - {key}: {type(v[key]).__name__}")

    # Test creating database entries
    print(f"\n4. Testing database storage...")
    scan = ScanResult.objects.create(
        user=user,
        repo_owner='facebook',
        repo_name='react',
        repo_full_name='facebook/react',
        scanner_type='eslint',
        status='RUNNING',
    )
    
    # Try to create vulnerability entries
    try:
        vuln_objects = []
        for v in vulnerabilities_data[:3]:  # Test with first 3
            vuln = Vulnerability(
                scan=scan,
                test_id=v.get('test_id', ''),
                test_name=v.get('test_name', ''),
                issue_text=v.get('issue_text', ''),
                severity=v.get('severity', 'LOW'),
                confidence=v.get('confidence', 'HIGH'),
                filename=v.get('filename', ''),
                line_number=v.get('line_number', 0),
                line_range=v.get('line_range', []),
                code_snippet=v.get('code_snippet', ''),
                cwe=v.get('cwe', ''),
                more_info=v.get('more_info', ''),
            )
            vuln_objects.append(vuln)
        
        Vulnerability.objects.bulk_create(vuln_objects)
        print(f"   Successfully created {len(vuln_objects)} vulnerabilities in DB")
        
    except Exception as e:
        print(f"   Error creating vulnerabilities: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
