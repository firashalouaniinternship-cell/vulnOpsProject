import logging
import os
from github import Github
from ..state import GraphState

logger = logging.getLogger(__name__)

def auto_pr_node(state: GraphState) -> GraphState:
    """
    Node: Creates a Pull Request with the remediation patches.
    This node should ONLY be called if the user explicitly confirmed it 
    (Human-in-the-loop) because state['auto_pr_enabled'] must be True.
    """
    if not state.get("auto_pr_enabled"):
        logger.info("[Auto-PR Node] Skipped: User confirmation required (auto_pr_enabled=False).")
        return state
        
    patches = state.get("remediation_patches", [])
    repo_url = state.get("repo_url")
    
    if not patches or not repo_url:
        logger.warning("[Auto-PR Node] No patches or repo URL available.")
        return state
        
    logger.info("[Auto-PR Node] Generating Pull Request...")
    
    try:
        # Extraire owner/repo depuis l'URL
        # ex: https://github.com/owner/repo
        parts = repo_url.replace("https://github.com/", "").split("/")
        if len(parts) >= 2:
            owner, repo_name = parts[0], parts[1].replace(".git", "")
            
            token = os.getenv("GITHUB_TOKEN")
            if not token:
                raise ValueError("GITHUB_TOKEN is missing in environment.")
                
            g = Github(token)
            repo = g.get_repo(f"{owner}/{repo_name}")
            
            # Dans une implémentation complète: 
            # 1. Créer une nouvelle branche
            # 2. Appliquer les diffs (patchs)
            # 3. Commit
            # 4. Créer la PR
            # Pour l'instant on simule le retour d'URL:
            
            pr_url = f"https://github.com/{owner}/{repo_name}/pull/new-security-patch"
            state["pr_url"] = pr_url
            logger.info(f"[Auto-PR Node] Pull Request simulated/created: {pr_url}")
            
    except Exception as e:
        logger.error(f"[Auto-PR Node] Error: {str(e)}")
        state["errors"] = state.get("errors", []) + [f"Auto-PR failed: {str(e)}"]

    return state
