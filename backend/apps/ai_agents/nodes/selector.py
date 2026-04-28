import logging
import json
import shutil
import subprocess
from langchain_core.prompts import PromptTemplate
from ..state import GraphState
from ..llm_factory import get_best_model
from rag.llm_selector import LLMSelector

logger = logging.getLogger(__name__)

def is_tool_installed(tool_name: str) -> bool:
    """Vérifie si l'outil de scan est installé et fonctionnel."""
    # Some tools might be run via python -m
    python_tools = {"bandit"}
    if tool_name in python_tools:
        try:
            subprocess.run(["python", "-m", tool_name, "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
            
    # For others like semgrep, eslint, etc.
    if shutil.which(tool_name):
        return True
    return False

def selector_node(state: GraphState) -> GraphState:
    """
    Node 2: Selects the appropriate security scanners based on project context
    and verifies if they are actually installed/functional.
    """
    context = state.get("project_context", {})
    if not context.get("languages"):
        logger.warning("[Selector Node] No languages to analyze.")
        state["selected_scanners"] = []
        return state
        
    logger.info("[Selector Node] Asking LLM for scanner suggestions...")
    
    # We can reuse the prompt from LLMSelector but run it through our LangChain factory
    llm = get_best_model(temperature=0.1)
    
    available_scanners = LLMSelector.AVAILABLE_SCANNERS
    scanner_info = "\\n".join([
        f"- {name}: {info['language']} | {info['description']}"
        for name, info in available_scanners.items()
    ])
    
    prompt = PromptTemplate.from_template(
        """You are a code security scanner selection expert. Based on the project analysis below, 
select the BEST suited security scanners from the available options.

PROJECT ANALYSIS:
- Languages: {languages}
- Frameworks: {frameworks}
- File Counts: {file_counts}
- Summary: {structure_summary}

AVAILABLE SCANNERS:
{scanner_info}

SELECTION CRITERIA:
1. Match scanner language support with detected languages
2. Prioritize dedicated scanners for specific languages
3. Multi-language scanners (sonarcloud, semgrep) for diverse projects
4. Include at least 1 scanner for security analysis
5. Maximum 3 scanners for efficiency (avoid scanner overkill)

Return ONLY valid JSON with this exact structure:
{{
    "selected_scanners": ["scanner1", "scanner2"]
}}
"""
    )
    
    try:
        formatted_prompt = prompt.format(
            languages=", ".join(context.get("languages", [])),
            frameworks=json.dumps(context.get("frameworks", {})),
            file_counts=json.dumps(context.get("file_counts", {})),
            structure_summary=context.get("structure_summary", ""),
            scanner_info=scanner_info
        )
        
        response = llm.invoke(formatted_prompt)
        
        # Clean potential markdown from response
        content = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        suggested_scanners = data.get("selected_scanners", [])
        
        # --- VERIFICATION STEP (as requested by user) ---
        verified_scanners = []
        for scanner in suggested_scanners:
            if scanner in available_scanners:
                if is_tool_installed(scanner):
                    verified_scanners.append(scanner)
                    logger.info(f"[Selector Node] Scanner '{scanner}' is installed and functional.")
                else:
                    logger.warning(f"[Selector Node] Scanner '{scanner}' suggested but NOT installed/functional. Skipping.")
                    
        # Fallback if none verified
        if not verified_scanners and "semgrep" in suggested_scanners:
            # Let's just assume we can run semgrep if it's suggested, but mark as unverified
            # In a real environment we'd install it dynamically or fail
            pass
            
        state["selected_scanners"] = verified_scanners
        logger.info(f"[Selector Node] Final verified scanners: {verified_scanners}")
        
    except Exception as e:
        logger.error(f"[Selector Node] Failed to select scanners via LLM: {str(e)}")
        # Fallback logic
        state["selected_scanners"] = ["semgrep"] if is_tool_installed("semgrep") else []
        state["errors"] = state.get("errors", []) + [f"Selector failed: {str(e)}"]

    return state
