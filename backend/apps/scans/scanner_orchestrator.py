"""
Module d'orchestration pour l'auto-détection et sélection des scanners.
Combine le ProjectAnalyzer et OpenRouterSelector pour une solution complète.
"""
import os
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import tempfile
import shutil
from git import Repo
from git.exc import GitCommandError
import stat


from core.utils.project_analyzer import ProjectAnalyzer
from rag.llm_selector import LLMSelector

logger = logging.getLogger(__name__)


class AutoScannerOrchestrator:
    """Orchestre l'auto-détection et la sélection des scanners."""
    
    def __init__(self):
        """Initialise l'orchestrateur."""
        self.analyzer = None
        self.selector = LLMSelector()
        self.project_path = None
    
    def auto_select_scanners(
        self,
        clone_url: str,
        github_token: str,
        repo_owner: str,
        repo_name: str,
        branch: str = None,
        cleanup: bool = True
    ) -> Dict:
        """
        Clone un dépôt et sélectionne automatiquement les scanners.
        
        :param clone_url: URL du dépôt à clôner
        :param github_token: Token GitHub pour l'accès
        :param repo_owner: Propriétaire du dépôt
        :param repo_name: Nom du dépôt
        :return: Dictionnaire avec scanners sélectionnés et analyse
        """
        temp_dir = None
        try:
            # Clone le dépôt dans un répertoire temporaire
            temp_dir = tempfile.mkdtemp(prefix="vulnops_analysis_")
            logger.info(f"Cloning repository to {temp_dir} (branch: {branch or 'default'})")
            
            self.project_path = self._clone_repository(clone_url, github_token, temp_dir, branch=branch)
            
            # Analyse le projet
            logger.info(f"Analyzing project structure at {self.project_path}")
            self.analyzer = ProjectAnalyzer(self.project_path)
            analysis = self.analyzer.analyze()
            
            # Vérifie si on a pu détecter quelque chose
            if not analysis.get('languages'):
                logger.warning("No languages detected in project")
                return {
                    'success': False,
                    'error': 'Could not detect any languages in the project',
                    'analysis': analysis,
                    'suggested_scanners': ['sonarcloud', 'semgrep'],  # Fallback defaults
                    'confidence': 0.3
                }
            
            # Utilise LLMSelector pour sélectionner les scanners
            logger.info("Using LLMSelector to select scanners")
            selection = self.selector.suggest_scanners(
                languages=analysis['languages'],
                frameworks=analysis['frameworks'],
                file_counts=analysis['file_counts'],
                structure_summary=analysis['structure_summary']
            )
            
            # Combine l'analyse et la sélection
            result = {
                'success': True,
                'repo_owner': repo_owner,
                'repo_name': repo_name,
                'analysis': analysis,
                'selection': selection,
                'suggested_scanners': selection['selected_scanners'],
                'reasoning': selection['reasoning'],
                'confidence': selection['confidence'],
                'source': selection['source'],
                'temp_dir': temp_dir
            }
            
            logger.info(f"Auto-selection complete: {result['suggested_scanners']}")
            return result
            
        except Exception as e:
            logger.error(f"Auto-selection failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'suggested_scanners': ['sonarcloud', 'semgrep'],  # Fallback defaults
                'confidence': 0.0
            }
        
        finally:
            # Nettoie le répertoire temporaire uniquement si demandé
            if cleanup and temp_dir and os.path.exists(temp_dir):
                try:
                    logger.info(f"Cleaning up temporary directory: {temp_dir}")
                    # Sur Windows, .git/objects/pack/ sont souvent en lecture seule
                    def on_rm_error(func, path, exc_info):
                        # Modifie les permissions et réessaie
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                        
                    shutil.rmtree(temp_dir, onerror=on_rm_error)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory: {e}")
    
    def _clone_repository(self, clone_url: str, github_token: str, dest_dir: str, branch: str = None) -> Path:
        """
        Clone un dépôt GitHub.
        
        :param clone_url: URL du dépôt
        :param github_token: Token GitHub
        :param dest_dir: Répertoire de destination
        :return: Chemin du dépôt cloné
        :raises: Exception si le clonage échoue
        """
        # Modifie l'URL pour inclure le token (nécessaire pour accéder aux repos privés)
        if github_token and 'https://github.com/' in clone_url:
            clone_url = clone_url.replace(
                'https://github.com/',
                f'https://{github_token}@github.com/'
            )
        
            # Clone le dépôt (shallow clone pour performance)
            logger.info(f"Cloning from {clone_url} (shallow clone, branch={branch or 'main'})")
            
            clone_kwargs = {
                'depth': 1,
                'single_branch': True,
            }
            if branch:
                clone_kwargs['branch'] = branch
            else:
                clone_kwargs['branch'] = 'main'

            try:
                repo = Repo.clone_from(clone_url, dest_dir, **clone_kwargs)
            except GitCommandError as e:
                if not branch and 'main' in str(e).lower():
                    logger.info("'main' branch not found, trying 'master'")
                    clone_kwargs['branch'] = 'master'
                    repo = Repo.clone_from(clone_url, dest_dir, **clone_kwargs)
                else:
                    raise

            logger.info(f"Repository cloned successfully to {dest_dir}")
            return Path(dest_dir)
    
    def analyze_existing_project(self, project_path: str) -> Dict:
        """
        Analyse un projet existant sur le disque.
        
        :param project_path: Chemin du projet
        :return: Dictionnaire avec analyse et sélection
        """
        try:
            self.project_path = project_path
            self.analyzer = ProjectAnalyzer(project_path)
            
            logger.info(f"Analyzing existing project at {project_path}")
            analysis = self.analyzer.analyze()
            
            if not analysis.get('languages'):
                logger.warning("No languages detected in project")
                return {
                    'success': False,
                    'error': 'Could not detect any languages in the project',
                    'analysis': analysis,
                    'suggested_scanners': ['sonarcloud', 'semgrep'],
                    'confidence': 0.3
                }
            
            # Utilise LLMSelector pour sélectionner les scanners
            selection = self.selector.suggest_scanners(
                languages=analysis['languages'],
                frameworks=analysis['frameworks'],
                file_counts=analysis['file_counts'],
                structure_summary=analysis['structure_summary']
            )
            
            result = {
                'success': True,
                'analysis': analysis,
                'selection': selection,
                'suggested_scanners': selection['selected_scanners'],
                'reasoning': selection['reasoning'],
                'confidence': selection['confidence'],
                'source': selection['source']
            }
            
            logger.info(f"Auto-analysis complete: {result['suggested_scanners']}")
            return result
        
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'suggested_scanners': ['sonarcloud', 'semgrep'],
                'confidence': 0.0
            }
    
    def batch_analyze_projects(self, projects: List[Dict]) -> List[Dict]:
        """
        Analyse plusieurs projets en batch.
        Chaque projet doit contenir: 'path', 'name' (optionnel)
        
        :param projects: Liste des projets à analyser
        :return: Liste des résultats d'analyse
        """
        results = []
        
        for project in projects:
            path = project.get('path')
            name = project.get('name', path)
            
            if not path:
                logger.warning("Skipping project without path")
                continue
            
            logger.info(f"Analyzing project: {name}")
            result = self.analyze_existing_project(path)
            result['project_name'] = name
            result['project_path'] = path
            results.append(result)
        
        return results
