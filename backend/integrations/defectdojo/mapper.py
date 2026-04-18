import requests
import os
import logging
import json
import tempfile
from django.conf import settings

logger = logging.getLogger(__name__)

class DojoMapper:
    # Mapping between our internal scanner types and DefectDojo scan types
    SCAN_TYPE_MAPPING = {
        'bandit': 'Bandit Scan',
        'trivy': 'Trivy Scan',
        'zap': 'ZAP Scan',
        'sonarcloud': 'SonarQube Scan',
        'eslint': 'ESLint Scan',
        'semgrep': 'Semgrep JSON Report',
        'cppcheck': 'Cppcheck Scan',
        'gosec': 'Gosec Scan',
        'psalm': 'Psalm Scan',
        'brakeman': 'Brakeman Scan',
        'clippy': 'Clippy Scan',
        'detekt': 'Detekt Scan',
    }

    @staticmethod
    def push_to_defectdojo(file_path, scanner_type, engagement_id=None):
        if not os.path.exists(file_path):
            logger.error(f"DefectDojo: Fichier introuvable : {file_path}")
            return False

        dd_url = os.getenv('DEFECTDOJO_URL', 'http://localhost:8080')
        dd_api_key = os.getenv('DEFECTDOJO_API_KEY')
        engagement_id = engagement_id or os.getenv('DEFECTDOJO_ENGAGEMENT_ID', '1')

        if not dd_api_key:
            logger.warning("DefectDojo: API Key non configure. Upload annul.")
            return False

        scan_type = DojoMapper.SCAN_TYPE_MAPPING.get(scanner_type.lower(), f"{scanner_type.capitalize()} Scan")
        
        url = f"{dd_url.rstrip('/')}/api/v2/import-scan/"
        headers = {"Authorization": f"Token {dd_api_key}"}

        data = {
            "scan_type": scan_type,
            "engagement": engagement_id,
            "active": True,
            "verified": True,
            "close_old_findings": True,
            "push_to_jira": False,
            "minimum_severity": "Info"
        }

        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                response = requests.post(url, headers=headers, data=data, files=files, timeout=30)

            if response.status_code == 201:
                logger.info(f"DefectDojo: Succs ! Rapport {scanner_type} import.")
                return True
            else:
                logger.error(f"DefectDojo: Erreur lors de l'import ({response.status_code}) : {response.text}")
                return False
        except Exception as e:
            logger.error(f"DefectDojo: Exception lors de l'upload : {str(e)}")
            return False

    @staticmethod
    def save_and_push_to_dojo(raw_data_dict, scanner_type, engagement_id=None):
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w', encoding='utf-8') as tf:
            json.dump(raw_data_dict, tf)
            temp_path = tf.name
        
        try:
            return DojoMapper.push_to_defectdojo(temp_path, scanner_type, engagement_id)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
