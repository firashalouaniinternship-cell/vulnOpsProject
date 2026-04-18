from django.contrib import admin
from .models import ScanResult, Vulnerability


@admin.register(ScanResult)
class ScanResultAdmin(admin.ModelAdmin):
    list_display = ['repo_full_name', 'status', 'total_issues', 'high_count', 'medium_count', 'started_at']
    list_filter = ['status', 'scanner_type']
    search_fields = ['repo_full_name']


@admin.register(Vulnerability)
class VulnerabilityAdmin(admin.ModelAdmin):
    list_display = ['test_id', 'severity', 'confidence', 'filename', 'line_number']
    list_filter = ['severity', 'confidence']
    search_fields = ['test_name', 'filename', 'cwe']
