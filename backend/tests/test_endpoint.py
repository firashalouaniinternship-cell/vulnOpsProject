#!/usr/bin/env python
"""Test endpoint apps.scans"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.users.models import GitHubProfile
from rest_framework.test import APIClient

# Create test user and GitHub profile
try:
    user = User.objects.create_user(username='testuser', password='testpass')
except:
    user = User.objects.get(username='testuser')

try:
    profile = GitHubProfile.objects.create(
        user=user,
        github_id=123456,
        github_login='testuser',
        github_access_token='ghp_test_token_' + 'x' * 50
    )
except:
    profile = user.github_profile

# Test the endpoint with ESLint
client = APIClient()
client.force_authenticate(user=user)

payload = {
    'repo_full_name': 'facebook/react',
    'repo_owner': 'facebook',
    'repo_name': 'react',
    'clone_url': 'https://github.com/facebook/react.git',
    'scanner_type': 'eslint'
}

print("Testing ESLint endpoint...")
try:
    response = client.post('/api/apps.scans/scan/', payload, format='json')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.data}")
except Exception as e:
    print(f"Error: {e}")
