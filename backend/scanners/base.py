import abc
import logging

logger = logging.getLogger(__name__)

class BaseScanner(abc.ABC):
    """
    Classe de base pour tous les scanners (SAST, SCA, DAST).
    """
    
    def __init__(self, name):
        self.name = name

    @abc.abstractmethod
    def run(self, target_path_or_url, **kwargs):
        """
        Excute le scan sur la cible fournie.
        
        :param target_path_or_url: Chemin local ou URL  scanner
        :return: Liste de dictionnaires de vulnrabilits (format normalis)
        """
        pass

    def cleanup(self):
        """Action optionnelle de nettoyage aprs le scan."""
        pass
