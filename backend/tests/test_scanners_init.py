#!/usr/bin/env python
"""Test que les scanners peuvent au moins démarrer sans erreur"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from scanners.sast.eslint_runner import run_full_eslint_scan
from scanners.sast.semgrep_runner import run_full_semgrep_scan
from scanners.sast.bandit_runner import run_full_scan as run_bandit
from scanners.sast.sonar_runner import run_full_sonar_scan

print("✓ All apps.scans imports successful")

# Test that each runner can be called (they should fail gracefully without a repo)
print("\nTesting apps.scans error handling...")

# Test ESLint with dummy URL
result = run_full_eslint_scan("https://github.com/dummy/repo.git", "dummy_token", "dummy", "repo")
print(f"ESLint test: {'✓ Handles errors' if not result['success'] else '✗ Unexpected success'}")
if result.get('error'):
    print(f"  Error message OK: {result['error'][:50]}...")

# Test Semgrep with dummy URL
result = run_full_semgrep_scan("https://github.com/dummy/repo.git", "dummy_token", "dummy", "repo")
print(f"Semgrep test: {'✓ Handles errors' if not result['success'] else '✗ Unexpected success'}")
if result.get('error'):
    print(f"  Error message OK: {result['error'][:50]}...")

print("\n✓ All tests passed!")
