from django.urls import path
from . import views

urlpatterns = [
    path('repos/', views.list_repos, name='list-repos'),
    path('<str:owner>/<str:repo>/tree/', views.get_file_tree, name='file-tree'),
    path('<str:owner>/<str:repo>/branches/', views.get_branches, name='get-branches'),
    path('<str:owner>/<str:repo>/file/', views.get_file_content, name='file-content'),
]
