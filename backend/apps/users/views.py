import requests
from django.http import HttpResponseRedirect
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import GitHubProfile


@api_view(['POST'])
@permission_classes([AllowAny])
def register_manual(request):
    """Inscription manuelle d'un utilisateur"""
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.create_user(username=username, email=email, password=password)
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return Response({'message': 'User created successfully', 'username': username})


@api_view(['POST'])
@permission_classes([AllowAny])
def login_manual(request):
    """Connexion manuelle d'un utilisateur"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    from django.contrib.auth import authenticate
    user = authenticate(request, username=username, password=password)
    
    if user is not None:
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return Response({'message': 'Login successful', 'username': username})
    else:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([AllowAny])
def github_login(request):
    """Redirige l'utilisateur vers GitHub pour l'autorisation OAuth"""
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        return Response(
            {'error': 'GitHub OAuth credentials not configured'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=repo,user:email"
    )
    return Response({'auth_url': github_auth_url})


@api_view(['GET'])
@permission_classes([AllowAny])
def github_callback(request):
    """Reçoit le code de GitHub et l'échange contre un token d'accès"""
    code = request.GET.get('code')
    if not code:
        return Response({'error': 'Code manquant'}, status=status.HTTP_400_BAD_REQUEST)

    # Nettoyage des credentials au cas où il y aurait des espaces invisibles
    client_id = settings.GITHUB_CLIENT_ID.strip()
    client_secret = settings.GITHUB_CLIENT_SECRET.strip()

    # Échange le code contre un token d'accès
    token_response = requests.post(
        'https://github.com/login/oauth/access_token',
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code.strip(),
        },
        headers={
            'Accept': 'application/json',
            'User-Agent': 'VulnOps-App-v2'
        },
        timeout=20
    )

    print(f"DEBUG: Status Code: {token_response.status_code}")
    print(f"DEBUG: Response Headers: {token_response.headers}")
    print(f"DEBUG: Response Body: '{token_response.text}'")

    try:
        token_data = token_response.json()
    except Exception as e:
        print(f"DEBUG: JSONDecodeError details: {e}")
        # Fallback if GitHub returns query parameters instead of JSON
        import urllib.parse
        token_data = dict(urllib.parse.parse_qsl(token_response.text))
        print(f"DEBUG: Parsed as query string: {token_data}")

    access_token = token_data.get('access_token')

    if not access_token:
        error_desc = token_data.get('error_description')
        error_code = token_data.get('error')
        full_error = f"{error_code}: {error_desc}" if error_code and error_desc else (error_desc or error_code or "Impossible d'obtenir le token")
        
        return Response({
            'error': full_error,
            'debug_info': {
                'status_code': token_response.status_code,
                'raw_response': token_response.text[:200] # Limiter la taille
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    # Récupère le profil GitHub de l'utilisateur
    user_response = requests.get(
        'https://api.github.com/user',
        headers={
            'Authorization': f'token {access_token}',
            'Accept': 'application/json',
        },
        timeout=10
    )

    if user_response.status_code != 200:
        return Response({'error': 'Impossible de récupérer le profil GitHub'}, status=status.HTTP_400_BAD_REQUEST)

    github_user = user_response.json()
    github_id = github_user.get('id')
    github_login_name = github_user.get('login', '')
    github_name = github_user.get('name', '') or ''
    github_email = github_user.get('email', '') or ''
    github_avatar = github_user.get('avatar_url', '')

    # Crée ou met à jour l'utilisateur Django
    try:
        github_profile = GitHubProfile.objects.get(github_id=github_id)
        django_user = github_profile.user
        # Met à jour le token
        github_profile.github_access_token = access_token
        github_profile.github_name = github_name
        github_profile.github_email = github_email
        github_profile.github_avatar_url = github_avatar
        github_profile.save()
    except GitHubProfile.DoesNotExist:
        # Crée un nouveau utilisateur
        username = github_login_name
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{github_login_name}_{counter}"
            counter += 1

        django_user = User.objects.create_user(
            username=username,
            email=github_email,
            first_name=github_name.split(' ')[0] if github_name else '',
            last_name=' '.join(github_name.split(' ')[1:]) if github_name and ' ' in github_name else '',
        )

        GitHubProfile.objects.create(
            user=django_user,
            github_id=github_id,
            github_login=github_login_name,
            github_name=github_name,
            github_email=github_email,
            github_avatar_url=github_avatar,
            github_access_token=access_token,
        )

    # Connecte l'utilisateur
    login(request, django_user, backend='django.contrib.auth.backends.ModelBackend')

    # Redirige vers le frontend
    return HttpResponseRedirect(f"{settings.FRONTEND_URL}/MesProjects")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Retourne les informations de l'utilisateur connecté"""
    data = {
        'id': request.user.id,
        'username': request.user.username,
        'email': request.user.email,
        'is_github_user': False
    }
    try:
        profile = request.user.github_profile
        data.update({
            'github_login': profile.github_login,
            'github_name': profile.github_name,
            'github_email': profile.github_email,
            'github_avatar_url': profile.github_avatar_url,
            'is_github_user': True
        })
    except Exception:
        pass
    
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Déconnecte l'utilisateur"""
    logout(request)
    return Response({'message': 'Déconnecté avec succès'})


@api_view(['GET'])
@permission_classes([AllowAny])
def debug_login(request):
    """Bypass pour le développement : connecte automatiquement un utilisateur de test"""
    if not settings.DEBUG:
        return Response({'error': 'Debug login is only available in DEBUG mode'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user = User.objects.get(username='testuser')
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return HttpResponseRedirect(f"{settings.FRONTEND_URL}/MesProjects")
    except User.DoesNotExist:
        return Response({'error': 'Test user not found. Please run create_test_user.py script.'}, status=status.HTTP_404_NOT_FOUND)
