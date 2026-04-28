import logging
from typing import List, Dict, Callable

from scanners.base import BaseScanner
from scanners.sast.bandit_runner import BanditRunner
from scanners.container.trivy_runner import TrivyRunner
from scanners.sca.dependency_check_runner import DependencyCheckRunner
from scanners.dast.zaproxy_runner import ZapRunner

from scanners.sast.eslint_runner import run_full_eslint_scan
from scanners.sast.semgrep_runner import run_full_semgrep_scan
from scanners.sast.gosec_runner import run_full_gosec_scan
from scanners.sast.clippy_runner import run_full_clippy_scan
from scanners.sast.psalm_runner import run_full_psalm_scan
from scanners.sast.brakeman_runner import run_full_brakeman_scan
from scanners.sast.detekt_runner import run_full_detekt_scan
from scanners.sast.cppcheck_runner import run_full_cppcheck_scan
from scanners.sast.sonar_runner import run_full_sonar_scan

logger = logging.getLogger(__name__)


class _FunctionRunner(BaseScanner):
    """
    Adapts a run_full_* function to the BaseScanner interface so that
    OrchestratorService can treat all scanners uniformly.
    """
    def __init__(self, name: str, fn: Callable):
        super().__init__(name)
        self._fn = fn

    def run(self, target_path_or_url: str, **kwargs) -> List[Dict]:
        result = self._fn(
            target_path_or_url,
            kwargs.get('access_token', ''),
            kwargs.get('repo_owner', ''),
            kwargs.get('repo_name', ''),
        )
        if result.get('success'):
            return result.get('vulnerabilities', [])
        logger.error(f"[{self.name}] scan failed: {result.get('error', 'unknown error')}")
        return []


# All available scanners — class-based and function-based are unified here.
_RUNNER_MAP: dict[str, Callable] = {
    # Class-based (already implement BaseScanner)
    'bandit':           BanditRunner,
    'dependency-check': DependencyCheckRunner,
    'trivy':            TrivyRunner,
    'zap':              ZapRunner,
    # Function-based (wrapped transparently)
    'eslint':           lambda: _FunctionRunner('ESLint',      run_full_eslint_scan),
    'semgrep':          lambda: _FunctionRunner('Semgrep',     run_full_semgrep_scan),
    'gosec':            lambda: _FunctionRunner('Gosec',       run_full_gosec_scan),
    'clippy':           lambda: _FunctionRunner('Clippy',      run_full_clippy_scan),
    'psalm':            lambda: _FunctionRunner('Psalm',       run_full_psalm_scan),
    'brakeman':         lambda: _FunctionRunner('Brakeman',    run_full_brakeman_scan),
    'detekt':           lambda: _FunctionRunner('Detekt',      run_full_detekt_scan),
    'cppcheck':         lambda: _FunctionRunner('Cppcheck',    run_full_cppcheck_scan),
    'sonarcloud':       lambda: _FunctionRunner('SonarCloud',  run_full_sonar_scan),
}


class OrchestratorService:
    @staticmethod
    def run_full_scan(target_path: str, scanners: List[str], **kwargs) -> List[Dict]:
        """
        Runs multiple scanners against a target and aggregates findings.

        :param target_path: Local repo path or URL
        :param scanners: List of scanner keys (from SCANNER_REGISTRY)
        :param kwargs: Forwarded to each runner (access_token, repo_owner, repo_name, targets…)
        :return: Combined list of normalized vulnerability dicts
        """
        all_findings: List[Dict] = []

        for scanner_name in scanners:
            factory = _RUNNER_MAP.get(scanner_name.lower())
            if not factory:
                logger.warning(f"Unknown scanner requested: '{scanner_name}' — skipping")
                continue

            try:
                logger.info(f"Running scanner: {scanner_name}")
                runner = factory()
                findings = runner.run(target_path, **kwargs)
                for f in findings:
                    f['scanner_source'] = scanner_name
                all_findings.extend(findings)
            except Exception as e:
                logger.error(f"Scanner '{scanner_name}' raised an exception: {e}", exc_info=True)

        return all_findings
