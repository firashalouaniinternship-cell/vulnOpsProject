import os
import sys
import json
import shutil
import tempfile

# Configuration paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scanners.sast.gosec_runner import run_gosec, parse_gosec_results

def create_vulnerable_go_file(repo_dir):
    """Crée un fichier Go avec des vulnérabilités connues (Gosec)"""
    content = """
package main

import (
	"crypto/md5"
	"fmt"
	"io/ioutil"
	"os"
)

func main() {
	// G101: Password hardcoded
	password := "p@ssword123"
	fmt.Println("Password is:", password)

	// G401: Use of weak cryptographic primitive (MD5)
	h := md5.New()
	h.Write([]byte("secret"))
	fmt.Printf("%x\\n", h.Sum(nil))

	// G304: Potential file inclusion via variable
	filename := os.Args[1]
	data, _ := ioutil.ReadFile(filename)
	fmt.Println(string(data))
}
"""
    file_path = os.path.join(repo_dir, "main.go")
    with open(file_path, "w") as f:
        f.write(content)
    return file_path

def test_gosec_scan():
    print("--- Test de scan Gosec via Docker ---")
    
    # Create a temp directory for the test
    tmp_dir = tempfile.mkdtemp(prefix='test_gosec_')
    
    try:
        # 1. Create vulnerable Go file
        vuln_file = create_vulnerable_go_file(tmp_dir)
        print(f"Fichier de test créé : {vuln_file}")
        
        # 2. Run Gosec (Docker required)
        print("Lancement du scan Gosec (Docker)...")
        gosec_output = run_gosec(tmp_dir)
        
        if 'errors' in gosec_output:
            print(f"ERREUR : {gosec_output['errors']}")
            return

        # 3. Parse results
        json_data = gosec_output.get('json', {})
        vulnerabilities = parse_gosec_results(json_data, tmp_dir)
        
        # 4. Print summaries
        print("\n--- Résumé du Scan Gosec ---")
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
                print(f" Code: {v['code_snippet'].strip()}")
            print("-" * 20)

        if issues_count > 0:
            print("\nSUCCÈS : Gosec a détecté des vulnérabilités.")
        else:
            print("\nAVERTISSEMENT : Aucune vulnérabilité n'a été détectée. Vérifiez si Gosec est bien installé et si l'image Docker est accessible.")
            
    finally:
        # Cleanup
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    test_gosec_scan()
