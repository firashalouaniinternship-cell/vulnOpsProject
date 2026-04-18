from django.urls import path
from . import views

urlpatterns = [
    path('scan/', views.trigger_scan, name='trigger-scan'),
    path('history/<str:owner>/<str:repo>/', views.get_scan_history, name='scan-history'),
    path('detail/<int:scan_id>/', views.get_scan_detail, name='scan-detail'),
    # Auto-detection and auto-selection endpoints
    path('auto-select/', views.auto_select_scanners, name='auto-select-scanners'),
    path('auto-scan/', views.auto_trigger_scan, name='auto-trigger-scan'),
    path('analyze/', views.analyze_project, name='analyze-project'),
    path('vulnerability/<int:pk>/recommendation/', views.get_vulnerability_recommendation, name='vulnerability-recommendation'),
    path('dashboard-stats/', views.get_dashboard_stats, name='dashboard-stats'),
    # DAST endpoints (OWASP ZAP)
    path('dast/check-prerequisites/', views.check_dast_prerequisites_view, name='dast_check'),
    path('dast/scan/', views.trigger_dast_scan, name='dast_scan'),
    path('dast/auto-scan/', views.trigger_auto_build_dast_scan, name='dast_auto_scan'),
]
