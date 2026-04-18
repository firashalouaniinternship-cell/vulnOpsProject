# Quick Command Reference - Auto-Scanner Selection

## 🚀 Getting Started (5 minutes)

### 1. Get OpenRouter API Key (2 min)
```bash
# Go to https://openrouter.io/
# Sign up → Get API Key → Copy Key
# Result: sk-or-v1-xxxxx...
```

### 2. Configure Environment (1 min)
```bash
# Copy example config
cp .env.example .env

# Edit .env and add your OpenRouter API key
# OPENROUTER_API_KEY=sk-or-v1-xxxxx...
```

### 3. Validate Setup (1 min)
```bash
cd backend
python validate_auto_scanner_setup.py
```

Expected output:
```
  RÉSUMÉ
  ============================================================
  ✅ Vérifications réussies: 7
   • OpenRouter API Key
   • OpenRouter Model
   • Python Dependencies
   • Project Structure
   • Module Imports
   • API Endpoints
   • URL Configuration

  Configuration COMPLÈTE ✅
```

### 4. Start Server (1 min)
```bash
cd backend
python manage.py runserver
```

## 📝 Testing

### Create Test User with Token
```bash
cd backend
python manage.py shell
```

```python
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

user = User.objects.create_user('testuser', 'test@example.com', 'testpass')
token, created = Token.objects.get_or_create(user=user)
print(f"Token: {token.key}")
# Copy this token for testing
```

### Test Auto-Select via cURL
```bash
export TOKEN="your_token_here"

curl -X POST http://localhost:8000/api/scanner/auto-select/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_full_name": "django/django",
    "clone_url": "https://github.com/django/django.git",
    "repo_name": "django",
    "repo_owner": "django"
  }' | python -m json.tool
```

### Test Auto-Scan (launches scans)
```bash
curl -X POST http://localhost:8000/api/scanner/auto-scan/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_full_name": "facebook/react",
    "clone_url": "https://github.com/facebook/react.git",
    "repo_name": "react",
    "repo_owner": "facebook"
  }' | python -m json.tool
```

### Run Python Test Suite
```bash
python test_auto_scanner_selection.py
```

## 📚 Documentation

**Main Docs:**
- `AUTO_SCANNER_SELECTION.md` - Full architecture
- `QUICK_SETUP_AUTO_SCANNER.md` - Setup guide
- `AUTO_SCANNER_IMPLEMENTATION_SUMMARY.md` - What was built
- `INTEGRATION_EXAMPLE.tsx` - React integration example

## 🔧 Useful Django Commands

### Create Superuser
```bash
python manage.py createsuperuser
```

### Access Django Shell
```bash
python manage.py shell
```

### Make Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Clear Database
```bash
rm db.sqlite3
python manage.py migrate
```

## 🐛 Debugging

### Enable Verbose Logging
```bash
cd backend
DJANGO_LOG_LEVEL=DEBUG python manage.py runserver
```

### Test OpenRouter Connection
```python
# In Django shell
from scanner.openrouter_selector import OpenRouterSelector
import os

selector = OpenRouterSelector()
result = selector.suggest_scanners(
    languages=['python'],
    frameworks={'python': ['django']},
    file_counts={'python': 100},
    structure_summary="Django project"
)
print(result)
```

### Test Project Analysis
```python
# In Django shell
from scanner.project_analyzer import ProjectAnalyzer

analyzer = ProjectAnalyzer('/path/to/project')
result = analyzer.analyze()
print(result)
```

## 🌍 Environment Variables

### Required
```env
OPENROUTER_API_KEY=sk-or-v1-xxxxx...
```

### Optional
```env
# Choose different model (default: mistral/mistral-7b-instruct)
OPENROUTER_MODEL=mistral/mistral-medium

# Or use OpenAI models (paid)
OPENROUTER_MODEL=openai/gpt-4
```

## 📊 Supported Scanners

| Language | Scanner | Command |
|----------|---------|---------|
| Python | Bandit | `bandit` |
| JS/TS | ESLint | `eslint` |
| Multi | SonarCloud | `sonarcloud` |
| Multi | Semgrep | `semgrep` |
| Go | Gosec | `gosec` |
| Rust | Clippy | `clippy` |
| PHP | Psalm | `psalm` |
| Ruby | Brakeman | `brakeman` |
| C/C++ | Cppcheck | `cppcheck` |
| Kotlin | Detekt | `detekt` |

## 🔄 API Endpoints

### 1. Auto-Select (Recommend)
```
POST /api/scanner/auto-select/
```
Analyzes project and recommends scanners (doesn't run them)

### 2. Auto-Scan (Recommend + Run)
```
POST /api/scanner/auto-scan/
```
Analyzes project, selects scanners, and launches them

### 3. Analyze Existing
```
POST /api/scanner/analyze/
```
Analyzes existing project on disk

## 🚨 Common Issues

### OPENROUTER_API_KEY not set
- Make sure `.env` file exists
- Restart Django after editing `.env`
- Check that the key is correct

### No languages detected
- Project might be empty
- Source files might be in subdirectories
- Common folders are ignored (node_modules, .git)

### Connection timeout
- Check internet connection
- Verify API key is valid
- Check OpenRouter status: https://status.openrouter.io/

### Import errors
- Make sure `requirements.txt` is installed: `pip install -r backend/requirements.txt`
- Check that Python path is correct

## 💡 Tips & Tricks

### Test with Different Repos
```bash
# Python project
curl -X POST http://localhost:8000/api/scanner/auto-select/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_full_name": "django/django",
    "clone_url": "https://github.com/django/django.git",
    "repo_name": "django",
    "repo_owner": "django"
  }'

# JavaScript project
curl -X POST http://localhost:8000/api/scanner/auto-select/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_full_name": "facebook/react",
    "clone_url": "https://github.com/facebook/react.git",
    "repo_name": "react",
    "repo_owner": "facebook"
  }'

# Go project
curl -X POST http://localhost:8000/api/scanner/auto-select/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_full_name": "kubernetes/kubernetes",
    "clone_url": "https://github.com/kubernetes/kubernetes.git",
    "repo_name": "kubernetes",
    "repo_owner": "kubernetes"
  }'
```

### Use Fallback Model
```env
# If OpenRouter is slow, use this default (no API key needed)
# Just comment out OPENROUTER_API_KEY in .env
```

### Test Locally without Cloning
```bash
# Analyze an existing local project
curl -X POST http://localhost:8000/api/scanner/analyze/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "/home/user/my-project"
  }'
```

## 🎓 Learning Resources

- OpenRouter Documentation: https://openrouter.io/docs
- Django REST Framework: https://www.django-rest-framework.org/
- React Hooks: https://react.dev/reference/react/hooks
- GitPython: https://gitpython.readthedocs.io/

## ✅ Checklist

Before deploying:
- [ ] OpenRouter API key obtained
- [ ] `.env` configured with API key
- [ ] `python validate_auto_scanner_setup.py` passes
- [ ] Test user created with token
- [ ] cURL tests pass locally
- [ ] React components integrated into frontend
- [ ] Database migrations applied
- [ ] Logs look clean

## 🎯 Next Steps

1. **Integrate in Frontend** - Use `INTEGRATION_EXAMPLE.tsx`
2. **Test in Production** - Deploy and monitor
3. **Optimize** - Tune confidence thresholds
4. **Extend** - Add more languages/frameworks
5. **Monitor** - Track which scanners are selected

---

**Need Help?** Check the documentation files or review the source code comments.

**Last Updated:** 2024
