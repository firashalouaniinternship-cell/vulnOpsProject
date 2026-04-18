import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from ..models import Vulnerability, ApiUsage
from rag.rag_utils import get_vulnerability_recommendation as fetch_rag_recommendation

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def get_vulnerability_recommendation(request, pk):
    """
    Retourne une recommandation RAG pour une vulnérabilité spécifique.
    - Si une recommandation a déjà été générée, elle est retournée depuis le cache (DB).
    - Sinon, elle est générée via RAG et sauvegardée pour les prochains appels.
    """
    user_filter = request.user if request.user.is_authenticated else None
    try:
        vuln = Vulnerability.objects.get(pk=pk, scan__user=user_filter)
    except Vulnerability.DoesNotExist:
        return Response({'error': 'Vulnérabilité non trouvée'}, status=status.HTTP_404_NOT_FOUND)

    # 🔄 FORCE REGENERATE : Si l'utilisateur demande explicitement une nouvelle génération
    force_regenerate = request.GET.get('force', 'false').lower() == 'true'

    # ✅ CACHE : Si une recommandation existe déjà (et pas de force), la retourner directement
    if vuln.rag_recommendation and not force_regenerate:
        logger.info(f"Returning cached RAG recommendation for vulnerability {pk}")
        return Response({
            'result': vuln.rag_recommendation,
            'sources': vuln.rag_sources or [],
            'cached': True
        }, status=status.HTTP_200_OK)

    # Si force, on efface l'ancien cache
    if force_regenerate and vuln.rag_recommendation:
        logger.info(f"Force regenerating RAG recommendation for vulnerability {pk}")
        vuln.rag_recommendation = ''
        vuln.rag_sources = []
    # 🔄 GÉNÉRATION : Appel au système RAG
    logger.info(f"Generating new RAG recommendation for vulnerability {pk} ({vuln.test_name})")
    result = fetch_rag_recommendation(
        test_name=vuln.test_name,
        issue_text=vuln.issue_text,
        cwe=vuln.cwe,
        code_snippet=vuln.code_snippet
    )

    if "error" in result:
        return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 💾 SAUVEGARDE : Stocker dans la base de données pour les prochains appels
    vuln.rag_recommendation = result.get('result', '')
    vuln.rag_sources = result.get('sources', [])
    vuln.save(update_fields=['rag_recommendation', 'rag_sources'])
    logger.info(f"RAG recommendation saved to DB for vulnerability {pk}")

    # Incrémente l'utilisation de l'API RAG si connecté
    if request.user.is_authenticated:
        api_usage, created = ApiUsage.objects.get_or_create(user=request.user)
        api_usage.rag_calls_count += 1
        api_usage.save()

    return Response({
        **result,
        'cached': False
    }, status=status.HTTP_200_OK)
