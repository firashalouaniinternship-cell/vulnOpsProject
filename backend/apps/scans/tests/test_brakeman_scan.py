import os
import sys
import json
import shutil
import tempfile

# Configuration paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scanners.sast.brakeman_runner import run_brakeman, parse_brakeman_results

def create_mock_rails_project(repo_dir):
    """Crée une structure Rails minimale pour que Brakeman accepte de apps.scans"""
    
    # 1. Dossiers de base
    os.makedirs(os.path.join(repo_dir, "config"))
    os.makedirs(os.path.join(repo_dir, "app", "controllers"))
    os.makedirs(os.path.join(repo_dir, "app", "models"))
    
    # 2. Fichier config/environment.rb (Brakeman le cherche souvent)
    with open(os.path.join(repo_dir, "config", "environment.rb"), "w") as f:
        f.write("# Minimal Rails environment\n")

    # 3. Fichier config/application.rb
    with open(os.path.join(repo_dir, "config", "application.rb"), "w") as f:
        f.write("module MockApp; class Application; end; end\n")

    # 4. Un contrôleur vulnérable (SQL Injection)
    controller_content = """class UsersController < ApplicationController
  def search
    # SQL Injection Vulnerability
    @users = User.where("name = '#{params[:name]}'")
    
    # XSS Vulnerability
    render html: "<h1>Hello #{params[:name]}</h1>".html_safe
  end
end
"""
    with open(os.path.join(repo_dir, "app", "controllers", "users_controller.rb"), "w") as f:
        f.write(controller_content)

def test_brakeman_scan():
    print("--- Test de scan Brakeman via Docker ---")
    
    tmp_dir = tempfile.mkdtemp(prefix='test_brakeman_')
    
    try:
        # 1. Create Mock Rails project
        create_mock_rails_project(tmp_dir)
        print(f"Mini-projet Rails créé dans : {tmp_dir}")
        
        # 2. Run Brakeman (Docker required)
        print("Lancement du scan Brakeman (Docker : presidentbeef/brakeman)...")
        brakeman_output = run_brakeman(tmp_dir)
        
        if 'errors' in brakeman_output:
            print(f"ERREUR : {brakeman_output['errors']}")
            return

        # 3. Parse results
        json_data = brakeman_output.get('json', {})
        vulnerabilities = parse_brakeman_results(json_data, tmp_dir)
        
        # 4. Print summaries
        print("\n--- Résumé du Scan Brakeman ---")
        issues_count = len(vulnerabilities)
        print(f"Total des issues : {issues_count}")
        
        high = sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')
        medium = sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM')
        low = sum(1 for v in vulnerabilities if v['severity'] == 'LOW')
        
        print(f" - Haute : {high}")
        print(f" - Moyenne : {medium}")
        print(f" - Basse : {low}")
        
        print("\n--- Détails des Vulnérabilités ---")
        for v in vulnerabilities:
            print(f"[{v['severity']}] {v['test_id']}: {v['test_name']} (Ligne {v['line_number']})")
            print(f" > {v['issue_text']}")
            if v['code_snippet']:
                print(f" Code: {v['code_snippet']}")
            print("-" * 20)

        if issues_count > 0:
            print("\nSUCCÈS : Brakeman a détecté des vulnérabilités Rails.")
        else:
            print("\nAVERTISSEMENT : Aucune vulnérabilité trouvée. Vérifiez la structure du projet.")
            
    finally:
        # Cleanup
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    test_brakeman_scan()
