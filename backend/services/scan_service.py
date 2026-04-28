import logging
import tempfile
import os
import shutil
from django.utils import timezone
from apps.scans.models import ScanResult, Vulnerability
from services.orchestrator_service import OrchestratorService
from rag.llm_scoring import get_direct_llm_score
from apps.scans.risk_scorer import compute_risk_score


logger = logging.getLogger(__name__)

class ScanService:
    @staticmethod
    def start_scan(user, repo_data: dict, scanner_type: str, run_sca: bool = False):
        """
        Initialise et lance un scan.
        """
        repo_full_name = repo_data.get('repo_full_name')
        repo_owner = repo_data.get('repo_owner')
        repo_name = repo_data.get('repo_name')
        
        # 1. Création du record en base
        scan = ScanResult.objects.create(
            user=user if user and user.is_authenticated else None,
            repo_owner=repo_owner,
            repo_name=repo_name,
            repo_full_name=repo_full_name,
            scanner_type=scanner_type,
            status='RUNNING',
            run_sca=run_sca,
            sca_status='PENDING' if run_sca else 'FAILED',
        )
        
        # Dans une archi PRO, on lancerait ici une tâche Celery
        # Pour l'instant on garde le flow pour terminer la structure
        return scan

    @staticmethod
    def process_scan_results(scan_id, result_data, sca_data=None):
        """
        Traite les résultats bruts, les normalise, les score et les sauvegarde.
        """
        scan = ScanResult.objects.get(id=scan_id)
        
        try:
            findings = result_data.get('vulnerabilities', [])
            all_findings = findings + (sca_data or [])
            
            # 1. Mise à jour des compteurs
            scan.critical_count = sum(1 for v in all_findings if v.get('severity', '').upper() == 'CRITICAL')
            scan.high_count = sum(1 for v in all_findings if v.get('severity', '').upper() == 'HIGH')
            scan.medium_count = sum(1 for v in all_findings if v.get('severity', '').upper() == 'MEDIUM')
            scan.low_count = sum(1 for v in all_findings if v.get('severity', '').upper() == 'LOW')
            scan.total_issues = len(all_findings)
            scan.status = 'COMPLETED'
            scan.completed_at = timezone.now()
            scan.save()
            
            # 2. Sauvegarde des vulns individuelles (avec scoring AI)
            vuln_objects = []
            context_summary = f"Dépôt {scan.repo_full_name}. Scanner: {scan.scanner_type}. Total: {scan.total_issues}"
            
            for i, v in enumerate(all_findings):
                llm_fb_score = 0.0
                llm_fb_reasoning = ""
                
                # Fetch AI Score for ALL vulnerabilities, skip for SCA unless we want basic scoring
                if not v.get('is_sca', False):
                    try:
                        ai_res = get_direct_llm_score(
                            test_name=v['test_name'],
                            issue_text=v['issue_text'],
                            severity=v['severity'],
                            context_summary=context_summary,
                            code_snippet=v.get('code_snippet')
                        )
                        llm_fb_score = ai_res.get('score', 0.5)
                        llm_fb_reasoning = ai_res.get('reasoning', 'Analyse IA réussie')
                    except Exception as e:
                        logger.warning(f"AI Scoring failed for {v['test_id']}: {e}")
                        llm_fb_score = 0.5
                        llm_fb_reasoning = f'Erreur technique IA: {str(e)}'
                else:
                    llm_fb_score = 0.5
                    llm_fb_reasoning = "SCA"

                vuln_objects.append(Vulnerability(
                    scan=scan,
                    test_id=v['test_id'],
                    test_name=v['test_name'],
                    issue_text=v['issue_text'],
                    severity=v['severity'],
                    confidence=v.get('confidence', 'MEDIUM'),
                    filename=v.get('filename',''),
                    line_number=v.get('line_number', 0),
                    line_range=v.get('line_range', []),
                    code_snippet=v.get('code_snippet', ''),
                    cwe=v.get('cwe', ''),
                    llm_score=llm_fb_score,
                    risk_score=compute_risk_score(v),
                    llm_explanation=llm_fb_reasoning,
                    is_sca=v.get('is_sca', False),
                    is_container=v.get('is_container', False),
                    is_dast=v.get('is_dast', False)
                ))

            
            Vulnerability.objects.bulk_create(vuln_objects)
            
            return True
        except Exception as e:
            logger.error(f"Erreur processing scan {scan_id}: {str(e)}")
            scan.status = 'FAILED'
            scan.error_message = str(e)
            scan.save()
            return False

