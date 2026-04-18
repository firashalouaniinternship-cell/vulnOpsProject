import os
import git
import logging

logger = logging.getLogger(__name__)

def clone_repo(clone_url: str, access_token: str, dest_dir: str) -> str:
    """Clone un dépôt GitHub avec authentification si le token est valide"""
    # Nettoyage du token
    if access_token in ["null", "undefined", "", "mock_access_token"]:
        access_token = None

    try:
        if access_token:
            # Injecte le token dans l'URL pour l'auth
            auth_url = clone_url.replace(
                'https://', f'https://oauth2:{access_token}@'
            )
        else:
            auth_url = clone_url
            
        logger.info(f"Cloning {clone_url} to {dest_dir}...")
        git.Repo.clone_from(auth_url, dest_dir)
        return dest_dir
    except Exception as e:
        logger.error(f"Clone error: {e}")
        raise Exception(f"Failed to clone repository: {str(e)}")
