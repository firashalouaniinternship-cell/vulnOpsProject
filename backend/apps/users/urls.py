from django.urls import path
from . import views

urlpatterns = [
    path('github/login/', views.github_login, name='github-login'),
    path('github/callback/', views.github_callback, name='github-callback'),
    path('register/', views.register_manual, name='register-manual'),
    path('login/', views.login_manual, name='login-manual'),
    path('debug-login/', views.debug_login, name='debug-login'),
    path('me/', views.me, name='me'),
    path('logout/', views.logout_view, name='logout'),
]
