"""Test de la réponse améliorée d'erreur SonarCloud"""
import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from scanners.sast.sonar_runner import run_sonar_scanner

# Test le scan SonarCloud sur un projet Java sans compilation
print("=== TEST SCAN SONARCLOUD ===\n")

# Créons un dossier de test simple
test_dir = "tmp/test_sonarcloud"
os.makedirs(test_dir, exist_ok=True)

# Crée un simple fichier Java
java_content = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}
"""
with open(f"{test_dir}/HelloWorld.java", "w") as f:
    f.write(java_content)

# Lance le scan (va échouer car pas de classes compilées)
result = run_sonar_scanner(os.path.abspath(test_dir), "test", "project")

print(f"Success: {result.get('success')}")
print(f"Error: {result.get('error')}")
print(f"Error length: {len(result.get('error', ''))}")
