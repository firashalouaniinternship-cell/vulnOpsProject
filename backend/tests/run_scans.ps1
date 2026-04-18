# Script d'Automatisation DevSecOps (PowerShell)
# Ce script lance les outils de sécurité et envoie les rapports vers DefectDojo.

echo "[*] Création du dossier reports..."
if (!(Test-Path -Path "reports")) {
    New-Item -ItemType Directory -Path "reports"
}

echo "[*] Lancement de Bandit (SAST)..."
# Assurez-vous que bandit est installé via pip
bandit -r . -f json -o reports/bandit.json

echo "[*] Lancement de Trivy (SCA)..."
# Assurez-vous que trivy est installé (binaire windows ou Docker)
trivy fs . --format json --output reports/trivy.json

echo "[*] Lancement de OWASP ZAP (DAST)..."
# Exemple utilisant zap-baseline (nécessite Docker)
docker run -v ${PWD}:/zap/wrk/:rw -t owasp/zap2docker-stable zap-baseline.py -t http://localhost:5173 -J zap.json
Move-Item -Path "zap.json" -Destination "reports/zap.json" -Force

echo "[*] Envoi des rapports vers DefectDojo..."
python scripts/dojo_upload.py

echo "[+] Terminé ! Consultez votre dashboard sur http://localhost:8080"
