"""
Central scanner registry — single source of truth for all scanner metadata
and language-to-scanner mappings. Every other module imports from here;
no duplicate mapping tables anywhere else.
"""
import shutil
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScannerMeta:
    name: str
    language: str           # primary language, or 'multi' for polyglot scanners
    description: str
    requires_docker: bool
    frameworks: tuple = ()
    docker_image: Optional[str] = None
    local_executable: Optional[str] = None  # used by is_scanner_available()


SCANNER_REGISTRY: dict[str, ScannerMeta] = {
    'bandit': ScannerMeta(
        name='Bandit',
        language='python',
        description='Security linter for Python code. Finds common security issues.',
        requires_docker=False,
        frameworks=('django', 'flask', 'fastapi'),
        local_executable='bandit',
    ),
    'eslint': ScannerMeta(
        name='ESLint',
        language='javascript',
        description='Linter for JavaScript and TypeScript. Finds code quality and security issues.',
        requires_docker=False,
        frameworks=('react', 'vue', 'angular', 'nodejs'),
        local_executable='eslint',
    ),
    'sonarcloud': ScannerMeta(
        name='SonarCloud',
        language='multi',
        description='Cloud-based code quality and security platform. Supports 30+ languages.',
        requires_docker=False,
        # API-based — no local executable required
    ),
    'semgrep': ScannerMeta(
        name='Semgrep',
        language='multi',
        description='Pattern-based static analysis with OWASP rules. Supports 17+ languages.',
        requires_docker=False,
        local_executable='semgrep',
    ),
    'gosec': ScannerMeta(
        name='Gosec',
        language='go',
        description='Security scanner for Go code.',
        requires_docker=True,
        docker_image='securego/gosec',
    ),
    'clippy': ScannerMeta(
        name='Clippy',
        language='rust',
        description='Official Rust linter. Catches common mistakes and security issues.',
        requires_docker=True,
        docker_image='rust:latest',
    ),
    'psalm': ScannerMeta(
        name='Psalm',
        language='php',
        description='Static analysis tool for PHP code.',
        requires_docker=True,
        frameworks=('laravel', 'symfony'),
        docker_image='ghcr.io/danog/psalm:latest',
    ),
    'brakeman': ScannerMeta(
        name='Brakeman',
        language='ruby',
        description='Security scanner for Ruby on Rails applications.',
        requires_docker=True,
        frameworks=('rails',),
        docker_image='presidentbeef/brakeman',
    ),
    'detekt': ScannerMeta(
        name='Detekt',
        language='kotlin',
        description='Static analysis tool for Kotlin code.',
        requires_docker=True,
        frameworks=('android',),
        docker_image='gradle:latest',
    ),
    'cppcheck': ScannerMeta(
        name='Cppcheck',
        language='cpp',
        description='Static analysis tool for C and C++ code.',
        requires_docker=True,
        docker_image='facthunder/cppcheck',
    ),
}

# Single source of truth: language name → scanner key
LANGUAGE_TO_SCANNER: dict[str, str] = {
    'python':     'bandit',
    'javascript': 'eslint',
    'typescript': 'eslint',
    'java':       'sonarcloud',
    'kotlin':     'detekt',
    'go':         'gosec',
    'rust':       'clippy',
    'php':        'psalm',
    'ruby':       'brakeman',
    'cpp':        'cppcheck',
    'c':          'cppcheck',
}


def get_scanner_for_language(language: str) -> Optional[str]:
    """Returns the primary scanner key for a given language, or None."""
    return LANGUAGE_TO_SCANNER.get(language.lower())


def is_scanner_available(scanner_name: str) -> bool:
    """
    Returns True if the scanner can be used on the current system.
    Docker-based scanners require Docker to be running.
    Local scanners require the executable to be in PATH.
    API-based scanners (sonarcloud) are always considered available.
    """
    meta = SCANNER_REGISTRY.get(scanner_name)
    if not meta:
        return False
    if meta.requires_docker:
        return shutil.which('docker') is not None
    if meta.local_executable:
        return shutil.which(meta.local_executable) is not None
    return True


def get_available_scanners() -> list[str]:
    """Returns scanner keys that are usable on the current system."""
    return [name for name in SCANNER_REGISTRY if is_scanner_available(name)]
