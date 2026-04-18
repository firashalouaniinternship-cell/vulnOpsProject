from rest_framework.authentication import SessionAuthentication

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication personnalisée qui désactive la vérification CSRF.
    À utiliser uniquement en développement pour faciliter les tests cross-origin.
    """
    def enforce_csrf(self, request):
        return  # Ne fait rien, désactivant ainsi la vérification CSRF
