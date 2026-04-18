import os
import sys
import json
import shutil
import tempfile

# Configuration paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scanners.sast.psalm_runner import run_psalm, parse_psalm_results

def create_psalm_test_project(repo_dir):
    """Crée un projet PHP avec des erreurs pour Psalm"""
    
    # 1. psalm.xml (Minimal config)
    psalm_xml = """<?xml version="1.0"?>
<psalm
    errorLevel="3"
    resolveFromConfigFile="true"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns="https://getpsalm.org/schema/config"
    xsi:schemaLocation="https://getpsalm.org/schema/config vendor/vimeo/psalm/config.xsd"
>
    <projectFiles>
        <directory name="src" />
    </projectFiles>
</psalm>
"""
    with open(os.path.join(repo_dir, "psalm.xml"), "w") as f:
        f.write(psalm_xml)

    # 2. src directory
    src_dir = os.path.join(repo_dir, "src")
    os.makedirs(src_dir)

    # 3. vulnerable.php
    php_content = """<?php

function sayHello(string $name): string {
    return "Hello " . $name;
}

// Error 1: Wrong type passed (array instead of string)
echo sayHello(["not", "a", "string"]);

// Error 2: Possibly undefined variable
echo $undefined_var;

// Error 3: Calling non-existent method
$obj = new stdClass();
$obj->nonExistentMethod();
"""
    with open(os.path.join(src_dir, "vulnerable.php"), "w") as f:
        f.write(php_content)

def test_psalm_scan():
    print("--- Test de scan Psalm via Docker ---")
    
    tmp_dir = tempfile.mkdtemp(prefix='test_psalm_')
    
    try:
        # 1. Create PHP project
        create_psalm_test_project(tmp_dir)
        print(f"Projet de test PHP créé dans : {tmp_dir}")
        
        # 2. Run Psalm (Docker required)
        print("Lancement du scan Psalm (Docker : ghcr.io/danog/psalm)...")
        psalm_output = run_psalm(tmp_dir)
        
        if 'errors' in psalm_output:
            print(f"ERREUR : {psalm_output['errors']}")
            return

        # 3. Parse results
        json_data = psalm_output.get('json', [])
        vulnerabilities = parse_psalm_results(json_data, tmp_dir)
        
        # 4. Print summaries
        print("\n--- Résumé du Scan Psalm ---")
        issues_count = len(vulnerabilities)
        print(f"Total des issues : {issues_count}")
        
        high = sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')
        medium = sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM')
        low = sum(1 for v in vulnerabilities if v['severity'] == 'LOW')
        
        print(f" - Haute : {high}")
        print(f" - Moyenne : {medium}")
        print(f" - Basse : {low}")
        
        print("\n--- Détails des Issues ---")
        for v in vulnerabilities:
            print(f"[{v['severity']}] {v['test_id']}: {v['test_name']} (Ligne {v['line_number']})")
            print(f" > {v['issue_text']}")
            if v['code_snippet']:
                print(f" Code: {v['code_snippet']}")
            print("-" * 20)

        if issues_count > 0:
            print("\nSUCCÈS : Psalm a détecté des problèmes de type/sécurité.")
        else:
            print("\nAVERTISSEMENT : Aucun problème détecté. Vérifiez la configuration.")
            
    finally:
        # Cleanup
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    test_psalm_scan()
