"""
Module pour détecter automatiquement les langages et frameworks d'un projet.
Utilise la structure du projet clôné pour identifier les technologies utilisées.
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Set, Tuple

logger = logging.getLogger(__name__)


class ProjectAnalyzer:
    """Analyse un projet cloné pour détecter les langages et frameworks."""
    
    # Extensions de fichiers par langage
    LANGUAGE_PATTERNS = {
        'python': {
            'extensions': ['.py'],
            'config_files': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile', 'poetry.lock'],
            'frameworks': {
                'django': ['django', 'Django'],
                'flask': ['flask', 'Flask'],
                'fastapi': ['fastapi', 'FastAPI'],
            }
        },
        'javascript': {
            'extensions': ['.js', '.jsx'],
            'config_files': ['package.json'],
            'frameworks': {}
        },
        'typescript': {
            'extensions': ['.ts', '.tsx'],
            'config_files': ['tsconfig.json', 'package.json'],
            'frameworks': {}
        },
        'java': {
            'extensions': ['.java'],
            'config_files': ['pom.xml', 'build.gradle', 'settings.gradle'],
            'frameworks': {
                'spring': ['org.springframework', 'spring-boot', 'spring-framework'],
            }
        },
        'kotlin': {
            'extensions': ['.kt', '.kts'],
            'config_files': ['pom.xml', 'build.gradle'],
            'frameworks': {}
        },
        'go': {
            'extensions': ['.go'],
            'config_files': ['go.mod', 'go.sum'],
            'frameworks': {}
        },
        'rust': {
            'extensions': ['.rs'],
            'config_files': ['Cargo.toml'],
            'frameworks': {}
        },
        'php': {
            'extensions': ['.php'],
            'config_files': ['composer.json', 'composer.lock'],
            'frameworks': {
                'laravel': ['laravel/framework'],
                'symfony': ['symfony/framework-bundle'],
                'wordpress': ['wordpress'],
            }
        },
        'ruby': {
            'extensions': ['.rb'],
            'config_files': ['Gemfile', 'Gemfile.lock'],
            'frameworks': {
                'rails': ['railties', 'actionpack'],
            }
        },
        'cpp': {
            'extensions': ['.cpp', '.cc', '.cxx', '.c++', '.h', '.hpp'],
            'config_files': ['CMakeLists.txt', 'Makefile'],
            'frameworks': {}
        },
        'c': {
            'extensions': ['.c', '.h'],
            'config_files': ['CMakeLists.txt', 'Makefile'],
            'frameworks': {}
        },
    }
    
    def __init__(self, project_path: str):
        """
        Initialise l'analyseur.
        
        :param project_path: Chemin du projet cloné
        """
        self.project_path = Path(project_path)
        self.detected_languages: Set[str] = set()
        self.detected_frameworks: Dict[str, List[str]] = {}
        self.file_count_by_language: Dict[str, int] = {}
    
    def analyze(self) -> Dict:
        """
        Analyse le projet et retourne les informations détectées.
        
        :return: Dictionnaire contenant:
            - languages: liste des langages détectés
            - frameworks: dictionnaire des frameworks par langage
            - file_counts: nombre de fichiers par langage
            - structure_summary: résumé de la structure du projet
        """
        if not self.project_path.exists():
            logger.error(f"Project path does not exist: {self.project_path}")
            return {
                'languages': [],
                'frameworks': {},
                'file_counts': {},
                'structure_summary': 'Project path does not exist',
                'error': 'Invalid project path'
            }
        
        # Détecte les langages et frameworks
        self._detect_languages()
        self._detect_frameworks()
        
        # Crée un résumé
        summary = self._create_structure_summary()
        
        return {
            'languages': sorted(list(self.detected_languages)),
            'frameworks': self.detected_frameworks,
            'file_counts': self.file_count_by_language,
            'structure_summary': summary,
        }
    
    def _detect_languages(self) -> None:
        """Détecte les langages utilisés basé sur les extensions de fichiers."""
        logger.info(f"Detecting languages in {self.project_path}")
        
        for language, patterns in self.LANGUAGE_PATTERNS.items():
            extensions = patterns['extensions']
            config_files = patterns['config_files']
            
            file_count = 0
            
            # Cherche les fichiers avec les bonnes extensions
            for ext in extensions:
                for file_path in self.project_path.rglob(f'*{ext}'):
                    # Ignore les dossiers communs qu'on veut skip
                    if self._should_ignore_path(file_path):
                        continue
                    file_count += 1
            
            # Cherche les fichiers de configuration
            for config in config_files:
                for file_path in self.project_path.rglob(config):
                    if self._should_ignore_path(file_path):
                        continue
                    file_count += 1
            
            # Ajoute le langage s'il y a au moins un fichier
            if file_count > 0:
                self.detected_languages.add(language)
                self.file_count_by_language[language] = file_count
                logger.info(f"Detected {language}: {file_count} files")
    
    def _detect_frameworks(self) -> None:
        """Détecte les frameworks basé sur le contenu des fichiers de configuration."""
        logger.info("Detecting frameworks")
        
        for language, patterns in self.LANGUAGE_PATTERNS.items():
            if language not in self.detected_languages:
                continue
            
            frameworks_dict = patterns['frameworks']
            detected = []
            
            # Analyse les fichiers de configuration
            for config_file in patterns['config_files']:
                content = self._read_config_file(config_file)
                if not content:
                    continue
                
                # Cherche les dépendances qui correspondent aux frameworks
                for framework, keywords in frameworks_dict.items():
                    for keyword in keywords:
                        if keyword.lower() in content.lower():
                            if framework not in detected:
                                detected.append(framework)
                            logger.info(f"Detected framework {framework} in {language}")
            
            if detected:
                self.detected_frameworks[language] = detected
    
    def _read_config_file(self, filename: str) -> str:
        """
        Lit le contenu d'un fichier de configuration.
        
        :param filename: Nom du fichier à chercher
        :return: Contenu du fichier ou chaîne vide
        """
        for file_path in self.project_path.rglob(filename):
            if self._should_ignore_path(file_path):
                continue
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
        return ""
    
    def _should_ignore_path(self, file_path: Path) -> bool:
        """
        Vérifie si le chemin doit être ignoré.
        
        :param file_path: Chemin du fichier
        :return: True si le fichier doit être ignoré
        """
        ignore_patterns = [
            'node_modules', '.git', '.venv', 'venv', '__pycache__',
            '.egg-info', 'build', 'dist', '.pytest_cache', '.tox',
            'target', '.gradle', '.m2', '.bundle', 'vendor'
        ]
        
        path_str = str(file_path).lower()
        for pattern in ignore_patterns:
            if f"{os.sep}{pattern}{os.sep}" in path_str or path_str.startswith(pattern):
                return True
        
        return False
    
    def _create_structure_summary(self) -> str:
        """
        Crée un résumé de la structure du projet.
        
        :return: Chaîne de caractères décrivant la structure
        """
        parts = []
        
        if self.detected_languages:
            parts.append(f"Languages: {', '.join(sorted(self.detected_languages))}")
        
        if self.detected_frameworks:
            frameworks_str = '; '.join([
                f"{lang}: {', '.join(frameworks)}"
                for lang, frameworks in self.detected_frameworks.items()
            ])
            parts.append(f"Frameworks: {frameworks_str}")
        
        if self.file_count_by_language:
            file_str = '; '.join([
                f"{lang}: {count} files"
                for lang, count in sorted(self.file_count_by_language.items(), key=lambda x: x[1], reverse=True)
            ])
            parts.append(f"Files: {file_str}")
        
        return ' | '.join(parts) if parts else "No project structure detected"
    
    def get_scan_candidates(self) -> List[str]:
        """
        Retourne les scanners candidats basé sur les langages/frameworks détectés.
        
        :return: Liste des scanners candidats
        """
        candidates = []
        
        language_to_scanner = {
            'python': 'bandit',
            'javascript': 'eslint',
            'typescript': 'eslint',
            'java': 'sonarcloud',
            'kotlin': 'detekt',
            'go': 'gosec',
            'rust': 'clippy',
            'php': 'psalm',
            'ruby': 'brakeman',
            'cpp': 'cppcheck',
            'c': 'cppcheck',
        }
        
        # Ajoute les scanners basé sur les langages détectés
        for language in self.detected_languages:
            if language in language_to_scanner:
                apps.scans = language_to_scanner[language]
                if apps.scans not in candidates:
                    candidates.append(apps.scans)
        
        # SonarCloud peut analyser plusieurs langages
        if len(self.detected_languages) > 1:
            if 'sonarcloud' not in candidates:
                candidates.append('sonarcloud')
        
        # Semgrep peut aussi analyser plusieurs langages
        if 'semgrep' not in candidates:
            candidates.append('semgrep')
        
        return candidates
