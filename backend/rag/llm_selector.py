"""
Module pour intégrer Ollama (en priorité) ou OpenRouter pour faire des appels
à un modèle LLM afin de choisir automatiquement les scanners appropriés.
"""
import os
import json
import logging
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMSelector:
    """Utilise Ollama (ou OpenRouter en secours) pour choisir les scanners appropriés."""
    
    AVAILABLE_SCANNERS = {
        'bandit': {
            'name': 'Bandit',
            'language': 'Python',
            'description': 'Security linter for Python code. Finds common security issues.',
            'frameworks': ['Django', 'Flask', 'FastAPI']
        },
        'eslint': {
            'name': 'ESLint',
            'language': 'JavaScript/TypeScript',
            'description': 'Linter for JavaScript and TypeScript. Finds code quality and potential bugs.',
            'frameworks': ['React', 'Vue', 'Angular', 'Node.js']
        },
        'sonarcloud': {
            'name': 'SonarCloud',
            'language': 'Multi-language',
            'description': 'Cloud-based code quality and security platform. Supports 30+ languages.',
            'frameworks': ['Multi-language support']
        },
        'semgrep': {
            'name': 'Semgrep',
            'language': 'Multi-language',
            'description': 'Pattern-based static analysis tool. Supports 17+ languages.',
            'frameworks': ['Multi-language support']
        },
        'cppcheck': {
            'name': 'Cppcheck',
            'language': 'C/C++',
            'description': 'Static analysis tool for C/C++ code.',
            'frameworks': []
        },
        'gosec': {
            'name': 'Gosec',
            'language': 'Go',
            'description': 'Security scanner for Go code.',
            'frameworks': []
        },
        'psalm': {
            'name': 'Psalm',
            'language': 'PHP',
            'description': 'Static analysis tool for PHP code.',
            'frameworks': ['Laravel', 'Symfony']
        },
        'brakeman': {
            'name': 'Brakeman',
            'language': 'Ruby',
            'description': 'Security scanner for Ruby on Rails applications.',
            'frameworks': ['Rails']
        },
        'clippy': {
            'name': 'Clippy',
            'language': 'Rust',
            'description': 'Linter for Rust code.',
            'frameworks': []
        },
        'detekt': {
            'name': 'Detekt',
            'language': 'Kotlin',
            'description': 'Static analysis tool for Kotlin code.',
            'frameworks': ['Android']
        },
    }
    
    def __init__(self):
        """Initialise le sélecteur Ollama/OpenRouter."""
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        self.api_base = "https://openrouter.ai/api/v1"
        self.model = os.getenv('OPENROUTER_MODEL', 'mistral/mistral-7b-instruct')
        
        if not self.api_key and not os.getenv("OLLAMA_API_URL"):
            logger.warning("Neither OPENROUTER_API_KEY nor OLLAMA_API_URL set in environment variables")
    
    def suggest_scanners(
        self,
        languages: List[str],
        frameworks: Dict[str, List[str]],
        file_counts: Dict[str, int],
        structure_summary: str
    ) -> Dict:
        """
        Utilise Ollama/OpenRouter pour suggérer les scanners appropriés.
        
        :param languages: Liste des langages détectés
        :param frameworks: Dictionnaire des frameworks par langage
        :param file_counts: Nombre de fichiers par langage
        :param structure_summary: Résumé de la structure
        :return: Dictionnaire contenant les scanners suggérés et le raisonnement
        """
        # Construit le prompt
        prompt = self._build_prompt(languages, frameworks, file_counts, structure_summary)
        
        try:
            response = self._call_llm(prompt)
            return self._parse_response(response, languages, frameworks)
        except Exception as e:
            logger.error(f"Error calling LLM selector: {e}")
            logger.info("Falling back to default scanner selection")
            return self._fallback_selection(languages, frameworks)
    
    def _build_prompt(
        self,
        languages: List[str],
        frameworks: Dict[str, List[str]],
        file_counts: Dict[str, int],
        structure_summary: str
    ) -> str:
        """
        Construit le prompt pour le modèle.
        
        :return: Prompt pour l'IA
        """
        scanner_info = "\n".join([
            f"- {name}: {info['language']} | {info['description']}"
            for name, info in self.AVAILABLE_SCANNERS.items()
        ])
        
        prompt = f"""You are a code security scanner selection expert. Based on the project analysis below, 
select the BEST suited security scanners from the available options.

PROJECT ANALYSIS:
- Languages: {', '.join(languages) if languages else 'None detected'}
- Frameworks: {json.dumps(frameworks) if frameworks else 'None detected'}
- File Counts: {json.dumps(file_counts) if file_counts else 'None'}
- Summary: {structure_summary}

AVAILABLE SCANNERS:
{scanner_info}

SELECTION CRITERIA:
1. Match scanner language support with detected languages
2. Prioritize dedicated scanners for specific languages
3. Multi-language scanners (sonarcloud, semgrep) for diverse projects
4. Include at least 1 scanner for security analysis
5. Maximum 3 scanners for efficiency (avoid scanner overkill)

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{{
    "selected_scanners": ["scanner1", "scanner2", ...],
    "reasoning": "Brief explanation of why these scanners were selected",
    "confidence": 0.95
}}

Think step-by-step:
1. Identify primary language(s)
2. Find scanners that support these languages
3. Check for framework-specific scanners
4. Select best combination for comprehensive coverage

Return ONLY valid JSON, no markdown formatting."""
        
        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """
        Fait un appel à l'API (Ollama ou OpenRouter) selon la variable LLM_PROVIDER.
        
        :param prompt: Prompt à envoyer
        :return: Réponse du modèle
        """
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        ollama_url = os.getenv("OLLAMA_API_URL")
        ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")
        
        if provider == "ollama":
            if not ollama_url:
                logger.error("Configuration OLLAMA_API_URL manquante pour le fournisseur: ollama")
                raise Exception("Missing OLLAMA configuration")
                
            logger.info(f"Calling Ollama at {ollama_url} with model: {ollama_model}")
            data = {
                "model": ollama_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.3
                }
            }
            try:
                response = requests.post(ollama_url, json=data, timeout=45)
                if response.status_code == 200:
                    content = response.json()["message"]["content"].strip()
                    logger.info("Ollama response received")
                    print(f"\n✅ Connecté avec succès au LLM (Local/Ollama - {ollama_model}) !\n")
                    return content
                else:
                    logger.error(f"Ollama failed with status: {response.status_code}")
                    raise Exception(f"Ollama failed with status: {response.status_code}")
            except Exception as e:
                logger.error(f"Ollama error: {e}")
                raise

        elif provider == "openrouter":
            if not self.api_key:
                logger.error("Configuration OPENROUTER_API_KEY manquante pour le fournisseur: openrouter")
                raise Exception("Missing OpenRouter configuration")

            logger.info(f"Calling OpenRouter with model: {self.model}")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/vulnops",
                "X-Title": "VulnOps Scanner Selection"
            }
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500,
            }
            
            try:
                response = requests.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                response.raise_for_status()
                
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                
                logger.info(f"OpenRouter response received: {content[:100]}...")
                print(f"\n✅ Connecté avec succès au LLM (OpenRouter - {self.model}) !\n")
                return content
                
            except requests.exceptions.Timeout:
                logger.error("OpenRouter API timeout")
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"OpenRouter API error: {e}")
                raise
                
        else:
            logger.error(f"LLM_PROVIDER inconnu: {provider}")
            raise Exception(f"Unknown LLM_PROVIDER: {provider}")
    
    def _parse_response(
        self,
        response: str,
        languages: List[str],
        frameworks: Dict[str, List[str]]
    ) -> Dict:
        """
        Parse la réponse du modèle.
        
        :param response: Réponse du modèle
        :param languages: Langages détectés
        :param frameworks: Frameworks détectés
        :return: Dictionnaire avec scanners sélectionnés
        """
        try:
            # Essaie de parser JSON
            data = json.loads(response)
            
            selected = data.get('selected_scanners', [])
            reasoning = data.get('reasoning', 'No explanation provided')
            confidence = data.get('confidence', 0.5)
            
            # Valide que les scanners sélectionnés existent
            valid_scanners = [s for s in selected if s in self.AVAILABLE_SCANNERS]
            
            if not valid_scanners:
                logger.warning(f"No valid scanners in response: {selected}")
                return self._fallback_selection(languages, frameworks)
            
            logger.info(f"Selected scanners: {valid_scanners} (confidence: {confidence})")
            
            return {
                'selected_scanners': valid_scanners,
                'reasoning': reasoning,
                'confidence': confidence,
                'source': 'ai'
            }
            
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI response as JSON: {response}")
            return self._fallback_selection(languages, frameworks)
    
    def _fallback_selection(
        self,
        languages: List[str],
        frameworks: Dict[str, List[str]]
    ) -> Dict:
        """
        Sélection par défaut si l'IA n'est pas disponible.
        
        :param languages: Langages détectés
        :param frameworks: Frameworks détectés
        :return: Dictionnaire avec scanners por défaut
        """
        logger.info("Using fallback scanner selection")
        
        language_to_scanner = {
            'python': 'bandit',
            'javascript': 'eslint',
            'typescript': 'eslint',
            'java': 'sonarcloud',
            'kotlin': 'detekt',
            'go': 'gosec',
            'rust': 'clippy',
            'php': 'psalm',
            'ruby': 'brakeman',
            'cpp': 'cppcheck',
            'c': 'cppcheck',
        }
        
        selected = []
        
        # Ajoute les scanners spécifiques au langage
        for lang in languages:
            if lang in language_to_scanner:
                scanner = language_to_scanner[lang]
                if scanner not in selected:
                    selected.append(scanner)
        
        # Ajoute SonarCloud si multi-langage
        if len(languages) > 1 and 'sonarcloud' not in selected:
            selected.append('sonarcloud')
        
        # Ajoute Semgrep pour analyse supplémentaire
        if len(selected) == 0:
            selected = ['semgrep']
        elif 'semgrep' not in selected and len(selected) < 3:
            selected.append('semgrep')
        
        return {
            'selected_scanners': selected[:3],  # Max 3 scanners
            'reasoning': f"Auto-selected scanners for {', '.join(languages)}",
            'confidence': 0.7,
            'source': 'fallback'
        }
