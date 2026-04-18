import os
import json
import shutil
import subprocess
import tempfile
from core.utils.repo_utils import clone_repo


def run_eslint(repo_path: str) -> dict:
    """
    Exécute ESLint sur un répertoire et retourne les résultats JSON.
    """
    print(f"Exécution d'ESLint sur : {repo_path}")
    
    # Crée une config ESLint minimal si elle n'existe pas
    # Utilise .cjs pour garantir le support CommonJS même si le projet est en mode ESM
    eslint_config_path = os.path.join(repo_path, 'eslint.config.cjs')
    config_created = False
    
    if not os.path.exists(eslint_config_path):
        try:
            with open(eslint_config_path, 'w') as f:
                f.write('module.exports = [{ \n'
                        '  files: ["**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx"], \n'
                        '  rules: { \n'
                        '    "no-eval": "error", \n'
                        '    "no-implied-eval": "error", \n'
                        '    "no-new-func": "error", \n'
                        '    "no-debugger": "error", \n'
                        '    "no-unused-vars": "warn", \n'
                        '    "no-undef": "warn" \n'
                        '  } \n'
                        '}];\n')
            config_created = True
        except Exception as e:
            print(f"Erreur lors de la création de la config ESLint: {e}")
    
    # Cherche ESLint - essaie plusieurs approches
    eslint_cmd = None
    
    # 1. Essaie direct eslint
    try:
        subprocess.run(['eslint', '--version'], capture_output=True, check=True, timeout=10)
        eslint_cmd = 'eslint'
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # 2. Essaie eslint.cmd sur Windows (npm global installations)
    if not eslint_cmd:
        eslint_cmd_path = os.path.expanduser('~\\AppData\\Roaming\\npm\\eslint.cmd')
        if os.path.exists(eslint_cmd_path):
            try:
                subprocess.run([eslint_cmd_path, '--version'], capture_output=True, check=True, timeout=10)
                eslint_cmd = eslint_cmd_path
            except:
                pass
    
    # 3. Essaie node vers eslint bin
    if not eslint_cmd:
        eslint_js = os.path.expanduser('~\\AppData\\Roaming\\npm\\node_modules\\eslint\\bin\\eslint.js')
        if os.path.exists(eslint_js):
            eslint_cmd = ['node', eslint_js]
    
    if not eslint_cmd:
        if config_created and os.path.exists(eslint_config_path):
            os.remove(eslint_config_path)
        return {'results': [], 'errors': "ESLint n'est pas installé. Installez avec: npm install -g eslint"}

    try:
        # On exécute avec '.' comme cible
        if isinstance(eslint_cmd, list):
            cmd_args = eslint_cmd + ['.', '--format', 'json', '--no-warn-ignored']
        else:
            cmd_args = [eslint_cmd, '.', '--format', 'json', '--no-warn-ignored']
            
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=repo_path,
            encoding='utf-8'  # IMPORTANT : évite les UnicodeDecodeError sur Windows
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode not in [0, 1]:
            print(f"ESLint error (code {result.returncode}): {stderr}")
            if not stdout.strip():
                return {'results': [], 'errors': f"ESLint failed (code {result.returncode}): {stderr.strip() or 'Unknown error'}"}

        if not stdout.strip():
            return {'results': []}

        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            print(f"Erreur de décodage JSON ESLint: {str(e)}")
            start_idx = stdout.find('[')
            if start_idx != -1:
                try:
                    return json.loads(stdout[start_idx:])
                except:
                    pass
            return {'results': [], 'errors': f"JSON parse error: {str(e)}"}
    
    except subprocess.TimeoutExpired:
        return {'results': [], 'errors': "ESLint timeout (exceeded 5 minutes)"}
    except Exception as e:
        import traceback
        print(f"ESLint subprocess exception: {traceback.format_exc()}")
        return {'results': [], 'errors': f"System error: {str(e)}"}
    finally:
        # Nettoie la config créée
        if config_created and os.path.exists(eslint_config_path):
            try:
                os.remove(eslint_config_path)
            except:
                pass


def parse_eslint_results(eslint_output, repo_path: str) -> list:
    """
    Transforme la sortie JSON d'ESLint en liste de vulnérabilités.
    ESLint retourne un tableau d'objets avec les fichiers et leurs issues.
    """
    vulnerabilities = []
    
    # Gère le cas où eslint_output est un dictionnaire avec 'results'
    if isinstance(eslint_output, dict):
        file_results = eslint_output.get('results', [])
    else:
        file_results = eslint_output if isinstance(eslint_output, list) else []
    
    # file_results est un tableau d'objets avec structure:
    # [{ filePath: "...", messages: [...] }, ...]
    for file_result in file_results:
        if not isinstance(file_result, dict):
            continue
            
        filename = file_result.get('filePath', '')
        
        # Nettoie le chemin du fichier
        if repo_path in filename:
            filename = filename.replace(repo_path, '').lstrip('/').lstrip('\\')
        
        messages = file_result.get('messages', [])
        
        for issue in messages:
            # Conversion des niveaux de sévérité ESLint en notre format
            severity = 'HIGH' if issue.get('severity') == 2 else 'MEDIUM'  # 2=error, 1=warning
            
            vuln = {
                'test_id': issue.get('ruleId', 'ESLINT'),
                'test_name': 'ESLint',
                'issue_text': issue.get('message', ''),
                'severity': severity,
                'confidence': 'HIGH',
                'filename': filename,
                'line_number': issue.get('line', 0),
                'line_range': [issue.get('line', 0), issue.get('endLine', issue.get('line', 0))],
                'code_snippet': '',
                'cwe': '',
                'more_info': f"https://eslint.org/docs/rules/{issue.get('ruleId', '')}",
            }
            vulnerabilities.append(vuln)
    
    return vulnerabilities


def run_full_eslint_scan(clone_url: str, access_token: str, repo_owner: str, repo_name: str) -> dict:
    """
    Lance un scan complet ESLint pour un projet JS/TS:
    1. Clone le dépôt
    2. Lance ESLint
    3. Parse les résultats
    4. Nettoie les fichiers temporaires
    """
    tmp_dir = tempfile.mkdtemp(prefix='vulnops_eslint_')
    
    try:
        # 1. Clone
        print("1. Clonage...")
        clone_repo(clone_url, access_token, tmp_dir)
        
        # 2. ESLint execution
        print("2. Analyse avec ESLint...")
        eslint_result = run_eslint(tmp_dir)
        
        # Check for errors
        if 'errors' in eslint_result:
            return {'success': False, 'error': eslint_result['errors']}
        
        # 3. Parsing
        print("3. Parsing et formatage...")
        vulnerabilities = parse_eslint_results(eslint_result, tmp_dir)
        
        high = sum(1 for v in vulnerabilities if v['severity'] == 'HIGH')
        medium = sum(1 for v in vulnerabilities if v['severity'] == 'MEDIUM')
        low = sum(1 for v in vulnerabilities if v['severity'] == 'LOW')

        # Count unique files analyzed from ESLint output
        if isinstance(eslint_result, list):
            files_analyzed = len(eslint_result)
        elif isinstance(eslint_result, dict):
            files_analyzed = len(eslint_result.get('results', []))
        else:
            files_analyzed = len(set(v['filename'] for v in vulnerabilities)) if vulnerabilities else 0
        
        metrics = {
            'total_issues': len(vulnerabilities),
            'high_count': high,
            'medium_count': medium,
            'low_count': low,
            'files_analyzed': files_analyzed
        }

        return {
            'success': True,
            'vulnerabilities': vulnerabilities,
            'metrics': metrics,
            'data': eslint_result,
            'raw_output': json.dumps(eslint_result), # Better for logging/Dojo
        }


    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"ESLint exception: {error_detail}")
        return {'success': False, 'error': f'Erreur inattendue(ESLint): {str(e)}'}
    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
