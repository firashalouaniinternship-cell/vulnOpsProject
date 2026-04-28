import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .standalone.chatbot_agent import chatbot_agent
from apps.scans.models import ScanResult

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def chat(request):
    """
    VulnOps security chatbot endpoint.

    Body (JSON):
        message        — required, the user's question
        repo_owner     — optional, used to fetch the latest scan report as context
        repo_name      — optional
        project_context — optional dict { languages, frameworks, structure_summary }
    """
    user_message = request.data.get('message', '').strip()
    if not user_message:
        return Response({'error': 'Le champ "message" est requis'}, status=status.HTTP_400_BAD_REQUEST)

    repo_owner      = request.data.get('repo_owner', '')
    repo_name       = request.data.get('repo_name', '')
    project_context = request.data.get('project_context') or {}

    # Build report context from the latest completed scan of the repo
    report_context = ''
    if repo_owner and repo_name:
        try:
            user_filter = request.user if request.user.is_authenticated else None
            latest = ScanResult.objects.filter(
                user=user_filter,
                repo_owner=repo_owner,
                repo_name=repo_name,
                status='COMPLETED',
            ).order_by('-started_at').first()

            if latest:
                top_vulns = latest.vulnerabilities.order_by('-llm_score')[:5].values(
                    'test_name', 'severity', 'filename', 'line_number', 'cwe', 'llm_score'
                )
                lines = [
                    f"Dernier scan ({latest.scanner_type.upper()}): "
                    f"{latest.total_issues} vulnérabilité(s) — "
                    f"Critique: {latest.critical_count}, Haute: {latest.high_count}"
                ]
                for v in top_vulns:
                    lines.append(
                        f"  [{v['severity']}] {v['test_name']} "
                        f"in {v['filename']}:{v['line_number']} "
                        f"(CWE: {v['cwe'] or 'N/A'}, Score AI: {v['llm_score']:.2f})"
                    )
                report_context = '\n'.join(lines)
        except Exception as e:
            logger.warning(f"Could not build report context for chat: {e}")

    try:
        answer = chatbot_agent.chat(
            user_input=user_message,
            project_context=project_context,
            report_context=report_context,
        )
        return Response({'response': answer}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Chatbot error: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
