import logging
from typing import List, Dict
from scanners.sast.bandit_runner import BanditRunner
from scanners.sca.trivy_runner import TrivyRunner
from scanners.dast.zaproxy_runner import ZapRunner
# Import other runners as they are converted...

logger = logging.getLogger(__name__)

class OrchestratorService:
    @staticmethod
    def run_full_scan(target_path: str, scanners: List[str], **kwargs) -> List[Dict]:
        """
        Orchestre lexcution de plusieurs scanners sur une cible.
        """
        all_findings = []
        
        # Mapping simple pour lexemple -  affiner avec une registry
        runner_map = {
            'bandit': BanditRunner,
            'trivy': TrivyRunner,
            'zap': ZapRunner,
        }
        
        for scanner_name in scanners:
            try:
                runner_class = runner_map.get(scanner_name.lower())
                if not runner_class:
                    logger.warning(f"Scanner inconnu : {scanner_name}")
                    continue
                
                logger.info(f"Lancement du scanner : {scanner_name}")
                runner = runner_class()
                findings = runner.run(target_path, **kwargs)
                
                # Ajout de mtadonnes sur la source
                for f in findings:
                    f['scanner_source'] = scanner_name
                
                all_findings.extend(findings)
            except Exception as e:
                logger.error(f"Erreur lors de lexcution de {scanner_name}: {str(e)}")
        
        return all_findings
