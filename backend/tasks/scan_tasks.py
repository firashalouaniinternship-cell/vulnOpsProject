import logging
from celery import shared_task
from services.scan_service import ScanService
from services.orchestrator_service import OrchestratorService

logger = logging.getLogger(__name__)

@shared_task(name="tasks.scan_tasks.run_scan_task")
def run_scan_task(scan_id, repo_data, scanner_type, access_token=None):
    """
    Tche Celery asynchrone pour lancer un scan.
    """
    logger.info(f"Dmarrage de la tche de scan pour ID: {scan_id}")
    
    # 1. Orchestration (Lancement des runners)
    # Note: access_token est pass ici, mais devrait tre scurisé
    results = OrchestratorService.run_full_scan(
        target_path=repo_data.get('clone_url'),
        scanners=[scanner_type],
        access_token=access_token
    )
    
    # 2. Processing (Normalisation, Scoring, DB)
    ScanService.process_scan_results(scan_id, {'success': True, 'vulnerabilities': results})
    
    logger.info(f"Tche de scan pour ID: {scan_id} termine.")
