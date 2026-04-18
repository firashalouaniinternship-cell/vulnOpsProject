#!/usr/bin/env python
"""
Script de validation de la configuration OAuth GitHub pour VulnOps
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
env_path = Path(__file__).parent / 'backend' / '.env'
load_dotenv(env_path)

def check_env_vars():
    """Vérifie si toutes les variables d'environnement requises sont configurées"""
    print("=" * 60)
    print("Vérification de la configuration OAuth GitHub")
    print("=" * 60)
    
    required_vars = {
        'GITHUB_CLIENT_ID': 'Client ID de l\'application GitHub',
        'GITHUB_CLIENT_SECRET': 'Secret de l\'application GitHub',
        'GITHUB_REDIRECT_URI': 'URI de redirection OAuth',
        'FRONTEND_URL': 'URL du frontend React',
        'SECRET_KEY': 'Clé secrète Django',
    }
    
    all_configured = True
    
    for var, description in required_vars.items():
        value = os.getenv(var, '').strip()
        
        if not value:
            print(f"❌ {var}: NON CONFIGURÉ")
            print(f"   Description: {description}")
            all_configured = False
        else:
            # Masquer les valeurs sensibles
            if 'SECRET' in var or 'TOKEN' in var:
                masked_value = value[:10] + '...' if len(value) > 10 else '***'
            else:
                masked_value = value
            print(f"✓ {var}: {masked_value}")
    
    print("\n" + "=" * 60)
    
    # Vérifications supplémentaires
    print("\nVérifications supplémentaires:")
    
    # Vérifier le fichier .env
    if env_path.exists():
        print(f"✓ Fichier .env trouvé: {env_path}")
    else:
        print(f"❌ Fichier .env non trouvé: {env_path}")
        all_configured = False
    
    # Vérifier la validité de GITHUB_REDIRECT_URI
    redirect_uri = os.getenv('GITHUB_REDIRECT_URI', '')
    if 'github/callback' in redirect_uri:
        print(f"✓ GITHUB_REDIRECT_URI format correct")
    elif redirect_uri:
        print(f"⚠ GITHUB_REDIRECT_URI format suspects (devrait contenir 'github/callback')")
    
    # Vérifier la configuration Django
    django_settings = Path(__file__).parent / 'backend' / 'vulnops' / 'settings.py'
    if django_settings.exists():
        print(f"✓ Fichier settings.py trouvé")
    else:
        print(f"❌ Fichier settings.py non trouvé")
        all_configured = False
    
    print("\n" + "=" * 60)
    
    if all_configured:
        print("✓ Configuration complète!")
        print("\nProchaines étapes:")
        print("1. Démarrer le backend Django: python backend/manage.py runserver")
        print("2. Démarrer le frontend React: cd frontend && npm run dev")
        print("3. Ouvrir http://localhost:5173 dans votre navigateur")
        return 0
    else:
        print("❌ Configuration incomplète!")
        print("\nVeuillez suivre le guide de configuration: GITHUB_OAUTH_SETUP.md")
        return 1

if __name__ == '__main__':
    sys.exit(check_env_vars())
