import os
import sys
import json
import shutil
import tempfile

# Configuration paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scanners.sast.clippy_runner import run_clippy, parse_clippy_results

def create_mock_rust_project(repo_dir):
    """Crée un projet Rust minimal pour tester Clippy"""
    
    # 1. Cargo.toml
    cargo_toml = """[package]
name = "mock_rust_project"
version = "0.1.0"
edition = "2021"

[dependencies]
"""
    with open(os.path.join(repo_dir, "Cargo.toml"), "w") as f:
        f.write(cargo_toml)

    # 2. src/main.rs avec des lint issues
    os.makedirs(os.path.join(repo_dir, "src"))
    main_rs = """fn main() {
    let x = 5;
    // Issue 1: Needless return
    return hello(x);
}

fn hello(val: i32) -> i32 {
    // Issue 2: Redundant closure
    let _ = Some(5).map(|x| x);
    val
}
"""
    with open(os.path.join(repo_dir, "src", "main.rs"), "w") as f:
        f.write(main_rs)

def test_clippy_scan():
    print("--- Test de scan Clippy via Docker ---")
    
    tmp_dir = tempfile.mkdtemp(prefix='test_clippy_')
    
    try:
        # 1. Create Mock Rust project
        create_mock_rust_project(tmp_dir)
        print(f"Mini-projet Rust créé dans : {tmp_dir}")
        
        # 2. Run Clippy (Docker required)
        print("Lancement du scan Clippy (Docker : rust:latest)...")
        print("Note: Cela peut être long si l'image doit être téléchargée.")
        clippy_output = run_clippy(tmp_dir)
        
        if 'errors' in clippy_output:
            print(f"ERREUR : {clippy_output['errors']}")
            return

        # 3. Parse results
        json_lines = clippy_output.get('json_lines', [])
        vulnerabilities = parse_clippy_results(json_lines, tmp_dir)
        
        # 4. Print summaries
        print("\n--- Résumé du Scan Clippy ---")
        issues_count = len(vulnerabilities)
        print(f"Total des issues : {issues_count}")
        
        high = sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')
        medium = sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM')
        low = sum(1 for v in vulnerabilities if v['severity'] == 'LOW')
        
        print(f" - Haute : {high}")
        print(f" - Moyenne : {medium}")
        print(f" - Basse : {low}")
        
        print("\n--- Détails des Lints ---")
        for v in vulnerabilities:
            print(f"[{v['severity']}] {v['test_id']}: {v['test_name']} (Ligne {v['line_number']})")
            print(f" > {v['issue_text']}")
            if v['code_snippet']:
                print(f" Code: {v['code_snippet']}")
            print("-" * 20)

        if issues_count > 0:
            print("\nSUCCÈS : Clippy a détecté des problèmes de qualité/lint.")
        else:
            print("\nAVERTISSEMENT : Aucun problème détecté. Vérifiez la structure du projet.")
            
    finally:
        # Cleanup
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    test_clippy_scan()
