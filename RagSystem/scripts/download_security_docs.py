"""
Downloads authoritative security documentation for the VulnOps RAG knowledge base.

Sources chosen to match what the SAST/SCA/DAST scanners actually report:
  - OWASP Top 10 2021 (A01-A10)  → maps to Bandit, Semgrep, ESLint, GoSec, etc. findings
  - OWASP Cheat Sheet Series      → practical remediation guides per vulnerability type
  - OWASP API Security Top 10 2023 → API-level vulnerabilities
  - CWE Top 25 2024               → the weakness IDs embedded in scanner outputs

All files are fetched as raw Markdown/text from official OWASP GitHub repos
(no HTML scraping — clean content, higher embedding quality).
"""

import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DOCS_DIR = os.path.join(BASE_DIR, "data", "source_docs")

# ---------------------------------------------------------------------------
# Source catalogue
# Raw GitHub URLs → no HTML parsing needed, clean Markdown text
# ---------------------------------------------------------------------------

OWASP_TOP10_2021 = {
    "OWASP_A01_Broken_Access_Control.txt":
        "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/A01_2021-Broken_Access_Control.md",
    "OWASP_A02_Cryptographic_Failures.txt":
        "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/A02_2021-Cryptographic_Failures.md",
    "OWASP_A03_Injection.txt":
        "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/A03_2021-Injection.md",
    "OWASP_A04_Insecure_Design.txt":
        "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/A04_2021-Insecure_Design.md",
    "OWASP_A05_Security_Misconfiguration.txt":
        "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/A05_2021-Security_Misconfiguration.md",
    "OWASP_A06_Vulnerable_Components.txt":
        "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/A06_2021-Vulnerable_and_Outdated_Components.md",
    "OWASP_A07_Auth_Failures.txt":
        "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/A07_2021-Identification_and_Authentication_Failures.md",
    "OWASP_A08_Integrity_Failures.txt":
        "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/A08_2021-Software_and_Data_Integrity_Failures.md",
    "OWASP_A09_Logging_Failures.txt":
        "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/A09_2021-Security_Logging_and_Monitoring_Failures.md",
    "OWASP_A10_SSRF.txt":
        "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/A10_2021-Server-Side_Request_Forgery_(SSRF).md",
}

# Cheat sheets chosen to match the most common findings from Bandit, Semgrep,
# ESLint security plugins, GoSec, Brakeman, Psalm, etc.
OWASP_CHEATSHEETS = {
    "CS_SQL_Injection_Prevention.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.md",
    "CS_XSS_Prevention.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.md",
    "CS_Authentication.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Authentication_Cheat_Sheet.md",
    "CS_Cryptographic_Storage.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Cryptographic_Storage_Cheat_Sheet.md",
    "CS_Injection_Prevention.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Injection_Prevention_Cheat_Sheet.md",
    "CS_OS_Command_Injection.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.md",
    "CS_Path_Traversal.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/File_Upload_Cheat_Sheet.md",
    "CS_Secrets_Management.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Secrets_Management_Cheat_Sheet.md",
    "CS_TLS_Transport_Layer.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Transport_Layer_Security_Cheat_Sheet.md",
    "CS_Deserialization.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Deserialization_Cheat_Sheet.md",
    "CS_Input_Validation.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Input_Validation_Cheat_Sheet.md",
    "CS_Password_Storage.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Password_Storage_Cheat_Sheet.md",
    "CS_Session_Management.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Session_Management_Cheat_Sheet.md",
    "CS_Access_Control.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Access_Control_Cheat_Sheet.md",
    "CS_CSRF_Prevention.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.md",
    "CS_XXE_Prevention.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.md",
    "CS_SSRF_Prevention.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md",
    "CS_Logging_Monitoring.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Logging_Cheat_Sheet.md",
}

OWASP_API_SECURITY_2023 = {
    "OWASP_API01_Broken_Object_Auth.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xa1-broken-object-level-authorization.md",
    "OWASP_API02_Broken_Auth.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xa2-broken-authentication.md",
    "OWASP_API03_Broken_Object_Property_Auth.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xa3-broken-object-property-level-authorization.md",
    "OWASP_API04_Unrestricted_Resource_Consumption.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xa4-unrestricted-resource-consumption.md",
    "OWASP_API05_Broken_Function_Auth.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xa5-broken-function-level-authorization.md",
    "OWASP_API08_Security_Misconfiguration.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xa8-security-misconfiguration.md",
    "OWASP_API09_Improper_Inventory.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xa9-improper-inventory-management.md",
    "OWASP_API10_Unsafe_API_Consumption.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xaa-unsafe-consumption-of-apis.md",
}

CWE_TOP25_2024 = {
    "CWE_Top25_2024.txt":
        "https://cwe.mitre.org/top25/archive/2024/2024_top25_list.html",
}


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

ALL_SOURCES = {
    **OWASP_TOP10_2021,
    **OWASP_CHEATSHEETS,
    **OWASP_API_SECURITY_2023,
    **CWE_TOP25_2024,
}

CATEGORIES = {
    "OWASP Top 10 2021": list(OWASP_TOP10_2021.keys()),
    "OWASP Cheat Sheets": list(OWASP_CHEATSHEETS.keys()),
    "OWASP API Security 2023": list(OWASP_API_SECURITY_2023.keys()),
    "CWE Top 25 2024": list(CWE_TOP25_2024.keys()),
}


def download_raw(url: str, filename: str) -> bool:
    filepath = os.path.join(SOURCE_DOCS_DIR, filename)
    try:
        response = requests.get(url, headers={"User-Agent": "VulnOps-RAG/1.0"}, timeout=30)
        response.raise_for_status()
        
        # If it's an HTML page (like CWE), parse it to get clean text
        if "text/html" in response.headers.get("Content-Type", "") or url.endswith(".html"):
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            # Remove script and style elements
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            content = soup.get_text(separator="\n")
            # Clean up whitespace
            lines = (line.strip() for line in content.splitlines())
            content = "\n".join(line for line in lines if line)
        else:
            # Assume it's Markdown or plain text
            content = response.text

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        size_kb = len(content) // 1024
        logger.info(f"  ✓ {filename} ({size_kb} KB)")
        return True
    except requests.exceptions.HTTPError as e:
        logger.warning(f"  ✗ {filename} — HTTP {e.response.status_code}: {url}")
        return False
    except Exception as e:
        logger.error(f"  ✗ {filename} — {e}")
        return False



def main():
    os.makedirs(SOURCE_DOCS_DIR, exist_ok=True)
    logger.info(f"Target directory: {SOURCE_DOCS_DIR}\n")

    total_ok = 0
    total = len(ALL_SOURCES)

    for category, filenames in CATEGORIES.items():
        logger.info(f"── {category} ({len(filenames)} files)")
        for filename in filenames:
            url = ALL_SOURCES[filename]
            if download_raw(url, filename):
                total_ok += 1

    logger.info(f"\n{'='*50}")
    logger.info(f"Download complete: {total_ok}/{total} files saved to source_docs/")
    logger.info(f"{'='*50}")
    logger.info("\nNext step: run  python scripts/ingest_docs.py  to rebuild the ChromaDB index.")


if __name__ == "__main__":
    main()
