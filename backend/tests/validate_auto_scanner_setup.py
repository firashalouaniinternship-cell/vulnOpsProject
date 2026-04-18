"""
Fichier de test simple pour valider que le système est configuré correctement.
Execute: python backend/validate_auto_scanner_setup.py
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, 'backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dotenv import load_dotenv
load_dotenv()

def validate_environment():
    """Valide que l'environnement est correctement configuré."""
    print("\n" + "="*60)
    print("  VALIDATION - Configuration Auto-Scanner Selection")
    print("="*60 + "\n")
    
    errors = []
    warnings = []
    checks = []
    
    # Check 1: OpenRouter API Key
    print("1️⃣  Vérification OpenRouter API Key...")
    api_key = os.getenv('OPENROUTER_API_KEY')
    if api_key:
        print(f"   ✅ API Key trouvée: {api_key[:20]}...")
        checks.append("OpenRouter API Key")
    else:
        print("   ❌ API Key non trouvée (optionnel)")
        warnings.append("OpenRouter API Key not set - fallback mode will be used")
    
    # Check 2: Model Configuration
    print("\n2️⃣  Vérification du modèle OpenRouter...")
    model = os.getenv('OPENROUTER_MODEL', 'mistral/mistral-7b-instruct')
    print(f"   ✅ Modèle configuré: {model}")
    checks.append("OpenRouter Model")
    
    # Check 3: Python Dependencies
    print("\n3️⃣  Vérification des dépendances Python...")
    try:
        import requests
        import git
        from pathlib import Path
        print("   ✅ requests: OK")
        print("   ✅ GitPython: OK")
        print("   ✅ pathlib: OK")
        checks.append("Python Dependencies")
    except ImportError as e:
        print(f"   ❌ Dépendance manquante: {e}")
        errors.append(f"Missing dependency: {e}")
    
    # Check 4: Django App Structure
    print("\n4️⃣  Vérification de la structure du projet...")
    files_to_check = [
        'backend/apps/scans/project_analyzer.py',
        'backend/rag/llm_selector.py',
        'backend/apps/scans/scanner_orchestrator.py',
    ]
    
    all_exist = True
    for file in files_to_check:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} NOT FOUND")
            all_exist = False
            errors.append(f"File not found: {file}")
    
    if all_exist:
        checks.append("Project Structure")
    
    # Check 5: Module Imports
    print("\n5️⃣  Vérification des imports des modules...")
    try:
        from apps.scans.project_analyzer import ProjectAnalyzer
        print("   ✅ ProjectAnalyzer: OK")
    except ImportError as e:
        print(f"   ❌ ProjectAnalyzer: {e}")
        errors.append(f"Cannot import ProjectAnalyzer: {e}")
    
    try:
        from rag.llm_selector import LLMSelector
        print("   ✅ LLMSelector: OK")
    except ImportError as e:
        print(f"   ❌ LLMSelector: {e}")
        errors.append(f"Cannot import LLMSelector: {e}")
    
    try:
        from apps.scans.scanner_orchestrator import AutoScannerOrchestrator
        print("   ✅ AutoScannerOrchestrator: OK")
    except ImportError as e:
        print(f"   ❌ AutoScannerOrchestrator: {e}")
        errors.append(f"Cannot import AutoScannerOrchestrator: {e}")
    
    if len(errors) == 0:
        checks.append("Module Imports")
    
    # Check 6: API Endpoints
    print("\n6️⃣  Vérification des endpoints API...")
    try:
        from django.urls import path, reverse
        from apps.scans import views
        
        endpoints = [
            ('auto-select-scanners', 'auto_select_scanners'),
            ('auto-trigger-scan', 'auto_trigger_scan'),
            ('analyze-project', 'analyze_project'),
        ]
        
        for endpoint_name, view_func_name in endpoints:
            if hasattr(views, view_func_name):
                print(f"   ✅ {endpoint_name}: OK")
            else:
                print(f"   ❌ {endpoint_name}: NOT FOUND")
                errors.append(f"Endpoint {endpoint_name} not found")
        
        if len(errors) == 0:
            checks.append("API Endpoints")
    
    except Exception as e:
        print(f"   ❌ Error checking endpoints: {e}")
        warnings.append(f"Could not verify endpoints: {e}")
    
    # Check 7: URL Configuration
    print("\n7️⃣  Vérification de la configuration des URLs...")
    try:
        with open('backend/apps/scans/urls.py', 'r') as f:
            urls_content = f.read()
            
        if 'auto-select' in urls_content and 'auto-scan' in urls_content:
            print("   ✅ URLs configurées: OK")
            checks.append("URL Configuration")
        else:
            print("   ❌ URLs non trouvées dans apps.scans/urls.py")
            errors.append("URLs not properly configured")
    
    except Exception as e:
        print(f"   ❌ Error reading urls.py: {e}")
        errors.append(f"Cannot read urls.py: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("  RÉSUMÉ")
    print("="*60)
    
    print(f"\n✅ Vérifications réussies: {len(checks)}")
    for check in checks:
        print(f"   • {check}")
    
    if warnings:
        print(f"\n⚠️  Avertissements: {len(warnings)}")
        for warning in warnings:
            print(f"   • {warning}")
    
    if errors:
        print(f"\n❌ Erreurs: {len(errors)}")
        for error in errors:
            print(f"   • {error}")
        
        print("\n" + "="*60)
        print("  Configuration INCOMPLÈTE ❌")
        print("="*60)
        return False
    else:
        print("\n" + "="*60)
        print("  Configuration COMPLÈTE ✅")
        print("="*60)
        print("\nLe système est prêt à être utilisé!")
        print("\nProchaines étapes:")
        print("1. Démarrer le serveur Django: python manage.py runserver")
        print("2. Obtenir un token d'authentification")
        print("3. Tester les endpoints auto-select/auto-scan")
        print("\nConsultez QUICK_SETUP_AUTO_SCANNER.md pour plus de détails.")
        return True


def test_ai_connection():
    """Teste la connexion à l'IA (Ollama ou OpenRouter)."""
    print("\n" + "="*60)
    print("  TEST - Connexion IA (Ollama/OpenRouter)")
    print("="*60 + "\n")
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("⚠️  OPENROUTER_API_KEY n'est pas configurée")
        print("   Test de connexion ignoré (mode fallback)")
        return
    
    try:
        from rag.llm_selector import LLMSelector
        
        print("Test: Appel à l'IA...")
        selector = LLMSelector()
        
        result = selector.suggest_scanners(
            languages=['python', 'javascript'],
            frameworks={'python': ['django'], 'javascript': []},
            file_counts={'python': 50, 'javascript': 30},
            structure_summary="Test project with Python and JavaScript"
        )
        
        print("\n✅ Connexion IA réussie!")
        print(f"\n   Scanners suggérés: {result['selected_scanners']}")
        print(f"   Confiance: {result['confidence']:.0%}")
        print(f"   Source: {result['source']}")
        
        if result['source'] == 'openrouter':
            print(f"\n   Raisonnement du modèle:")
            print(f"   {result['reasoning']}")
    
    except Exception as e:
        print(f"\n❌ Erreur de connexion: {e}")
        print("   Le système utilisera le mode fallback (sélection par défaut)")


if __name__ == '__main__':
    success = validate_environment()
    
    if success:
        test_ai_connection()
    
    sys.exit(0 if success else 1)
