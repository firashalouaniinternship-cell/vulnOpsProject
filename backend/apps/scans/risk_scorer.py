import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RiskScorer:
    """
    Calcule un score de risque dynamique pour les vulnérabilités.
    """
    
    SEVERITY_WEIGHTS = {
        'CRITICAL': 1.0,
        'HIGH': 0.8,
        'MEDIUM': 0.5,
        'LOW': 0.2,
        'INFO': 0.0
    }
    
    @classmethod
    def calculate_score(cls, vulnerability_data: Dict[str, Any], project_context: Dict[str, Any] = None) -> float:
        """
        Calcule le score de risque (0.0 à 1.0).
        Logic: severity * 0.4 + exposure * 0.3 + exploitability * 0.2 + business_impact * 0.1
        """
        project_context = project_context or {}
        
        # 1. Sévérité (40%)
        severity = vulnerability_data.get('severity', 'MEDIUM').upper()
        severity_score = cls.SEVERITY_WEIGHTS.get(severity, 0.5)
        
        # 2. Exposition (30%)
        # Par défaut 0.5, monte à 1.0 si c'est du DAST ou si le fichier est dans une route publique
        exposure_score = 0.5
        if vulnerability_data.get('is_dast', False):
            exposure_score = 1.0
        
        filename = vulnerability_data.get('filename', '').lower()
        if any(term in filename for term in ['api', 'route', 'controller', 'public', 'v1']):
            exposure_score = min(1.0, exposure_score + 0.2)
            
        # 3. Exploitabilité (20%)
        # Basée sur la confiance du scanner
        confidence = vulnerability_data.get('confidence', 'MEDIUM').upper()
        exploitability_score = 0.5
        if confidence == 'HIGH':
            exploitability_score = 0.9
        elif confidence == 'LOW':
            exploitability_score = 0.3
            
        # 4. Impact Business (10%)
        # Basé sur l'importance du fichier (auth, config, models)
        business_impact = 0.4
        critical_paths = ['auth', 'login', 'payment', 'user', 'config', 'settings', 'database', 'models']
        if any(path in filename for path in critical_paths):
            business_impact = 1.0
            
        # Calcul final
        final_score = (
            severity_score * 0.4 +
            exposure_score * 0.3 +
            exploitability_score * 0.2 +
            business_impact * 0.1
        )
        
        return round(min(1.0, final_score), 2)

def compute_risk_score(vulnerability_data: Dict[str, Any], project_context: Dict[str, Any] = None) -> float:
    """Fonction utilitaire pour calculer le score de risque."""
    return RiskScorer.calculate_score(vulnerability_data, project_context)

