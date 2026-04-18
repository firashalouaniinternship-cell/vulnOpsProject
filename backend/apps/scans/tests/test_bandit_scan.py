import os
import sys
import json
import django

# Configuration Django
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from scanners.sast.bandit_runner import run_bandit, parse_bandit_results, get_metrics

def create_vulnerable_file():
    """Crée un fichier Python avec des vulnérabilités connues (Bandit)"""
    content = """
import os
import subprocess

# Vulnerability: os.system with user input (Shell Injection)
def run_command(cmd):
    os.system(cmd)

# Vulnerability: subprocess with shell=True
def run_sub(cmd):
    subprocess.call(cmd, shell=True)

# Vulnerability: MD5 is insecure
import hashlib
def get_hash(data):
    return hashlib.md5(data.encode()).hexdigest()

# Vulnerability: Hardcoded password
PASSWORD = "admin123"

# Vulnerability: Flask with debug=True (if flask was here)
# app.run(debug=True)
"""
    file_path = "vulnerable_sample.py"
    with open(file_path, "w") as f:
        f.write(content)
    return os.path.abspath(file_path)

def test_scan():
    print("--- Test de scan Bandit local ---")
    
    vuln_file = create_vulnerable_file()
    repo_dir = os.path.dirname(vuln_file)
    
    try:
        # 1. Run Bandit
        print(f"Lancement du scan sur {vuln_file}...")
        bandit_output = run_bandit(repo_dir)
        
        # 2. Parse results
        vulnerabilities = parse_bandit_results(bandit_output, repo_dir)
        metrics = get_metrics(bandit_output)
        
        # 3. Print summaries
        print("\n--- Résumé du Scan ---")
        print(f"Fichiers analysés : {metrics.get('files_analyzed')}")
        print(f"Total des issues : {metrics.get('total_issues')}")
        print(f" - Haute : {metrics.get('high_count')}")
        print(f" - Moyenne : {metrics.get('medium_count')}")
        print(f" - Basse : {metrics.get('low_count')}")
        
        print("\n--- Détails des Vulnérabilités ---")
        for v in vulnerabilities:
            if v['filename'] == "vulnerable_sample.py":
                print(f"[{v['severity']}] {v['test_name']} (Ligne {v['line_number']})")
                print(f" > {v['issue_text']}")
                print("-" * 20)

        if metrics.get('total_issues', 0) > 0:
            print("\nSUCCÈS : Le apps.scans a détecté des vulnérabilités.")
        else:
            print("\nÉCHEC : Aucune vulnérabilité n'a été détectée.")
            
    finally:
        # Cleanup
        if os.path.exists(vuln_file):
            os.remove(vuln_file)

if __name__ == "__main__":
    test_scan()
