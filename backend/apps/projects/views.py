import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status


def get_github_token(request):
    """Récupère le token GitHub de la requête ou de l'utilisateur connecté"""
    custom_token = request.GET.get('custom_token') or request.data.get('custom_token')
    if custom_token:
        return custom_token
    
    if request.user and request.user.is_authenticated:
        try:
            return request.user.github_profile.github_access_token
        except Exception:
            pass
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_repos(request):
    """Liste tous les dépôts GitHub de l'utilisateur"""
    token = get_github_token(request)
    if not token:
        return Response({'error': 'Token GitHub non trouvé'}, status=status.HTTP_401_UNAUTHORIZED)

    # Mock mode for Demo
    if token == 'mock_access_token':
        return Response([{
            'id': 1,
            'name': 'bandit',
            'full_name': 'PyCQA/bandit',
            'description': 'Security oriented static analyser for python code.',
            'language': 'Python',
            'stars': 5000,
            'forks': 400,
            'private': False,
            'html_url': 'https://github.com/PyCQA/bandit',
            'clone_url': 'https://github.com/PyCQA/bandit.git',
            'updated_at': '2026-04-01T00:00:00Z',
            'created_at': '2015-01-01T00:00:00Z',
            'size': 1200,
            'default_branch': 'main'
        }, {
            'id': 2,
            'name': 'spring-petclinic',
            'full_name': 'spring-projects/spring-petclinic',
            'description': 'A sample Spring-based application',
            'language': 'Java',
            'stars': 15000,
            'forks': 12000,
            'private': False,
            'html_url': 'https://github.com/spring-projects/spring-petclinic',
            'clone_url': 'https://github.com/spring-projects/spring-petclinic.git',
            'updated_at': '2026-04-05T00:00:00Z',
            'created_at': '2012-01-01T00:00:00Z',
            'size': 5000,
            'default_branch': 'main'
        }])

    repos = []
    page = 1
    while True:
        response = requests.get(
            'https://api.github.com/user/repos',
            headers={
                'Authorization': f'token {token}',
                'Accept': 'application/json',
            },
            params={
                'per_page': 100,
                'page': page,
                'sort': 'updated',
                'affiliation': 'owner,collaborator',
            },
            timeout=15
        )

        if response.status_code != 200:
            return Response({'error': 'Impossible de récupérer les dépôts'}, status=status.HTTP_400_BAD_REQUEST)

        data = response.json()
        if not data:
            break

        repos.extend(data)
        if len(data) < 100:
            break
        page += 1

    # Formate les données et vérifie les scans en base
    from apps.scans.models import ScanResult
    
    # Récupère tous les dépôts déjà scannés par cet utilisateur pour optimiser
    scanned_repos = set(ScanResult.objects.filter(
        user=request.user, 
        status='COMPLETED'
    ).values_list('repo_full_name', flat=True).distinct())

    formatted_repos = []
    for repo in repos:
        full_name = repo['full_name']
        formatted_repos.append({
            'id': repo['id'],
            'name': repo['name'],
            'full_name': full_name,
            'description': repo.get('description', ''),
            'language': repo.get('language', ''),
            'stars': repo.get('stargazers_count', 0),
            'forks': repo.get('forks_count', 0),
            'private': repo.get('private', False),
            'html_url': repo.get('html_url', ''),
            'clone_url': repo.get('clone_url', ''),
            'updated_at': repo.get('updated_at', ''),
            'created_at': repo.get('created_at', ''),
            'size': repo.get('size', 0),
            'default_branch': repo.get('default_branch', 'main'),
            'has_scans': full_name in scanned_repos
        })

    return Response(formatted_repos)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_file_tree(request, owner, repo):
    """Retourne l'arborescence complète d'un dépôt GitHub"""
    token = get_github_token(request)
    
    # We do not fail purely on empty token if it is a public repo, wait and see if github request fails.
    # But if doing so, the API request without auth header is restricted to 60 calls/hour.
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'token {token}'

    if token == 'mock_access_token':
        # Mock tree for Demo
        return Response({
            'tree': [{'name': 'src', 'path': 'src', 'type': 'tree', 'size': 0, 'children': []}],
            'repo': repo,
            'owner': owner
        })

    branch = request.GET.get('branch', 'main')

    # Essaie d'abord 'main', puis 'master'
    for branch_try in [branch, 'main', 'master']:
        response = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch_try}',
            headers=headers,
            params={'recursive': '1'},
            timeout=15
        )
        if response.status_code == 200:
            break

    if response.status_code != 200:
        return Response({'error': 'Impossible de récupérer l\'arborescence'}, status=status.HTTP_400_BAD_REQUEST)

    data = response.json()
    tree_items = data.get('tree', [])

    # Construit un arbre hiérarchique
    def build_tree(items):
        root = []
        node_map = {}

        for item in items:
            path = item['path']
            parts = path.split('/')
            name = parts[-1]

            node = {
                'name': name,
                'path': path,
                'type': item['type'],  # 'blob' = fichier, 'tree' = dossier
                'size': item.get('size', 0),
                'children': [] if item['type'] == 'tree' else None,
            }
            node_map[path] = node

            if len(parts) == 1:
                root.append(node)
            else:
                parent_path = '/'.join(parts[:-1])
                if parent_path in node_map:
                    node_map[parent_path]['children'].append(node)

        return root

    tree = build_tree(tree_items)
    return Response({'tree': tree, 'repo': repo, 'owner': owner})


@api_view(['GET'])
@permission_classes([AllowAny])
def get_file_content(request, owner, repo):
    """Retourne le contenu d'un fichier dans un dépôt GitHub"""
    token = get_github_token(request)
    
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = f'token {token}'

    file_path = request.GET.get('path', '')
    if not file_path:
        return Response({'error': 'Chemin du fichier manquant'}, status=status.HTTP_400_BAD_REQUEST)

    response = requests.get(
        f'https://api.github.com/repos/{owner}/{repo}/contents/{file_path}',
        headers=headers,
        timeout=10
    )

    if response.status_code != 200:
        return Response({'error': 'Fichier non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    data = response.json()
    import base64
    try:
        content = base64.b64decode(data.get('content', '')).decode('utf-8')
    except Exception:
        content = '[Contenu binaire non affichable]'

    return Response({
        'path': file_path,
        'name': data.get('name', ''),
        'content': content,
        'size': data.get('size', 0),
        'encoding': 'utf-8',
    })
