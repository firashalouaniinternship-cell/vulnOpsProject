from django.urls import path
from . import views

urlpatterns = [
    # URL d'installation de la GitHub App
    path('install/', views.get_install_url, name='github-app-install'),

    # Webhook GitHub → reçoit les événements (installation, push, PR)
    path('webhook/', views.github_app_webhook, name='github-app-webhook'),

    # Callback après installation (GitHub redirige ici)
    path('callback/', views.github_app_callback, name='github-app-callback'),

    # Statut de l'installation pour l'utilisateur connecté
    path('status/', views.get_app_status, name='github-app-status'),

    # Liste des repos connectés
    path('repos/', views.get_connected_repos, name='github-app-repos'),

    # Setup manuel d'un repo spécifique
    path('setup/<str:repo_owner>/<str:repo_name>/', views.setup_repo, name='github-app-setup'),

    # Lier une installation à l'utilisateur (appelé après callback)
    path('link/', views.link_installation, name='github-app-link'),
]
