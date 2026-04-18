import requests
import os
import sys

# Configuration DefectDojo
DD_URL = "http://localhost:8080"
DD_API_KEY = "VOTRE_CLÉ_API_ICI"  # Profil -> API Key v2
ENGAGEMENT_ID = 1               # À récupérer dans l'interface Dojo (URL de l'engagement)

def upload_to_dojo(file_path, scan_type):
    if not os.path.exists(file_path):
        print(f"[-] Fichier introuvable : {file_path}")
        return

    url = f"{DD_URL}/api/v2/import-scan/"
    headers = {
        "Authorization": f"Token {DD_API_KEY}"
    }

    data = {
        "scan_type": scan_type,
        "engagement": ENGAGEMENT_ID,
        "active": True,
        "verified": True,
        "close_old_findings": True,
        "push_to_jira": False,
        "minimum_severity": "Info"
    }

    files = {
        "file": open(file_path, "rb")
    }

    print(f"[*] Envoi de {file_path} ({scan_type}) vers DefectDojo...")
    response = requests.post(url, headers=headers, data=data, files=files)

    if response.status_code == 201:
        print(f"[+] Succès ! Rapport importé.")
    else:
        print(f"[-] Erreur lors de l'import : {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Liste des outils et leurs types correspondants dans Dojo
    tools = [
        {"path": "reports/bandit.json", "type": "Bandit Scan"},
        {"path": "reports/trivy.json", "type": "Trivy Scan"},
        {"path": "reports/zap.json", "type": "ZAP Scan"}
    ]

    for tool in tools:
        upload_to_dojo(tool["path"], tool["type"])
