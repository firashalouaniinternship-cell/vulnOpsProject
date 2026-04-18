import os
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)

def get_docker_path_mapping(repo_path: str) -> str:
    """
    Convertit un chemin local en chemin compatible avec les volumes Docker.
    Gère particulièrement les spécificités de Windows.
    """
    abs_path = os.path.abspath(repo_path)
    if os.name == 'nt':
        # Sur Windows, Docker Desktop accepte C:/path/to/repo
        # On remplace les backslashes par des forward slashes
        return abs_path.replace('\\', '/')
    return abs_path

def ensure_docker_image(image_name: str, timeout: int = 1800) -> tuple[bool, str]:
    """
    Vérifie si une image Docker est présente, sinon tente de la puller.
    Retourne (success, error_message).
    """
    if not shutil.which('docker'):
        return False, "Docker n'est pas installé ou n'est pas dans le PATH."

    print(f"Vérification/Pull de l'image Docker : {image_name}")
    try:
        # On tente de pull l'image séparément pour éviter les timeouts lors du run
        # et pour avoir de meilleurs messages d'erreur.
        pull_cmd = ['docker', 'pull', image_name]
        result = subprocess.run(
            pull_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8'
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Erreur inconnue lors du pull"
            if "npipe" in error_msg:
                return False, f"Impossible de se connecter au démon Docker. Vérifiez que Docker Desktop est lancé. (Erreur: {error_msg[:100]})"
            return False, f"Échec du pull de l'image {image_name} : {error_msg[:200]}"
            
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"Timeout lors du pull de l'image {image_name} (dépassé {timeout/60} minutes)."
    except Exception as e:
        return False, f"Erreur lors de la vérification de Docker : {str(e)}"

def run_docker_container(image_name: str, volume_mapping: str, working_dir: str, command: list, timeout: int = 1200) -> subprocess.CompletedProcess:
    """
    Exécute un conteneur Docker avec les paramètres spécifiés.
    """
    docker_cmd = [
        'docker', 'run', '--rm',
        '-v', f"{volume_mapping}:{working_dir}",
        '-w', working_dir,
        image_name
    ] + command
    
    print(f"Running Docker command: {' '.join(docker_cmd)}")
    
    # On sature les arguments pour éviter les problèmes de parsing avec les espaces sur Windows
    return subprocess.run(
        docker_cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding='utf-8'
    )
