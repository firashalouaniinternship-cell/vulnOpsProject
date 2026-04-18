from django.db import models
from django.contrib.auth.models import User


class ScanResult(models.Model):
    """Résultat d'une analyse SAST"""
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critique'),
        ('HIGH', 'Haute'),
        ('MEDIUM', 'Moyenne'),
        ('LOW', 'Faible'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('RUNNING', 'En cours'),
        ('COMPLETED', 'Terminée'),
        ('FAILED', 'Échouée'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scans', null=True, blank=True)
    repo_owner = models.CharField(max_length=255)
    repo_name = models.CharField(max_length=255)
    repo_full_name = models.CharField(max_length=512)
    scanner_type = models.CharField(max_length=50, default='bandit')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    raw_output = models.TextField(blank=True)
    total_issues = models.IntegerField(default=0)
    critical_count = models.IntegerField(default=0)
    high_count = models.IntegerField(default=0)
    medium_count = models.IntegerField(default=0)
    low_count = models.IntegerField(default=0)

    run_sast = models.BooleanField(default=True)
    run_sca = models.BooleanField(default=False)
    sca_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    sca_critical_count = models.IntegerField(default=0)
    sca_high_count = models.IntegerField(default=0)
    sca_medium_count = models.IntegerField(default=0)
    sca_low_count = models.IntegerField(default=0)

    # DAST fields (OWASP ZAP)
    run_dast = models.BooleanField(default=False)
    dast_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    dast_target_url = models.URLField(max_length=2048, blank=True)
    dast_critical_count = models.IntegerField(default=0)
    dast_high_count = models.IntegerField(default=0)
    dast_medium_count = models.IntegerField(default=0)
    dast_low_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Scan {self.repo_full_name} - {self.status}"

    class Meta:
        ordering = ['-started_at']
        verbose_name = "Résultat de scan"
        verbose_name_plural = "Résultats de scan"


class Vulnerability(models.Model):
    """Vulnérabilité individuelle trouvée lors d'un scan"""
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critique'),
        ('HIGH', 'Haute'),
        ('MEDIUM', 'Moyenne'),
        ('LOW', 'Faible'),
    ]
    CONFIDENCE_CHOICES = [
        ('HIGH', 'Haute'),
        ('MEDIUM', 'Moyenne'),
        ('LOW', 'Basse'),
    ]

    scan = models.ForeignKey(ScanResult, on_delete=models.CASCADE, related_name='vulnerabilities')
    test_id = models.CharField(max_length=50)       # ex: B101
    test_name = models.CharField(max_length=255)     # ex: assert_used
    issue_text = models.TextField()                  # Description du problème
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    confidence = models.CharField(max_length=10, choices=CONFIDENCE_CHOICES)
    filename = models.CharField(max_length=500)      # Fichier concerné
    line_number = models.IntegerField()              # Ligne concernée
    line_range = models.JSONField(default=list)      # Plage de lignes
    code_snippet = models.TextField(blank=True)      # Code source concerné
    cwe = models.CharField(max_length=50, blank=True)  # CWE-ID
    llm_score = models.FloatField(default=0.0)       # Score AI [0-1]
    llm_explanation = models.TextField(blank=True)   # Justification du score
    is_sca = models.BooleanField(default=False)
    is_dast = models.BooleanField(default=False)
    solution = models.TextField(blank=True)
    more_info = models.URLField(max_length=1000, blank=True)          # Lien vers plus d'info
    rag_recommendation = models.TextField(blank=True)                  # Conseil AI (RAG) mis en cache
    rag_sources = models.JSONField(default=list, blank=True)           # Pages sources OWASP

    def __str__(self):
        return f"{self.test_id} - {self.severity} - {self.filename}:{self.line_number}"

    class Meta:
        ordering = ['-llm_score', '-severity', 'filename', 'line_number']
        verbose_name = "Vulnérabilité"
        verbose_name_plural = "Vulnérabilités"

class ApiUsage(models.Model):
    """Suivi de l'utilisation de l'API (ex: appels RAG) par utilisateur"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='api_usage')
    rag_calls_count = models.IntegerField(default=0)
    rag_calls_limit = models.IntegerField(default=100)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Usage API pour {self.user.username}: {self.rag_calls_count}/{self.rag_calls_limit}"
