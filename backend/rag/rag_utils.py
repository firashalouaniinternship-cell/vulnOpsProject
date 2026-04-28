"""
RAG utilities — thin wrapper around the integrated RAGService.
Replaces the old subprocess-based implementation.
"""

import logging
from rag.rag_service import rag_service

logger = logging.getLogger(__name__)


def get_vulnerability_recommendation(test_name, issue_text, cwe=None, code_snippet=None):
    """
    Returns a security recommendation for a vulnerability.
    Result: { result: str, sources: list[int] }
    """
    query = f"Vulnerability: {test_name}. Description: {issue_text}."
    if cwe:
        query += f" CWE: {cwe}."
    if code_snippet:
        query += f"\nCode Context:\n```\n{code_snippet}\n```"
    query += (
        "\n\nProvide a concise mitigation recommendation "
        "and mention the relevant OWASP Top 10 2021 category."
    )

    logger.info(f"RAG recommendation for: {test_name}")
    return rag_service.invoke({"query": query})


def get_vulnerability_score(test_name, issue_text, severity, context_summary, code_snippet=None):
    """
    Returns a priority score for a vulnerability.
    Result: { score: float, reasoning: str }
    """
    query = f"Vulnerability: {test_name}. Description: {issue_text}. Scanner Severity: {severity}."
    if code_snippet:
        query += f"\nCode Context:\n```\n{code_snippet}\n```"

    logger.info(f"RAG scoring for: {test_name}")
    return rag_service.score_vulnerability({"query": query, "context": context_summary})
