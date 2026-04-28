"""
Downloads OWASP/CWE security documentation into backend/data/source_docs/.
Run once before ingest_docs.py.

Usage (from backend/ directory, venv activated):
    python scripts/download_security_docs.py
"""

import os
import logging
import requests
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SOURCE_DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "source_docs"

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
    "CS_File_Upload.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/File_Upload_Cheat_Sheet.md",
    "CS_Secrets_Management.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Secrets_Management_Cheat_Sheet.md",
    "CS_TLS.txt":
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
    "CS_Logging.txt":
        "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Logging_Cheat_Sheet.md",
}

OWASP_API_SECURITY_2023 = {
    "OWASP_API01_Broken_Object_Auth.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xa1-broken-object-level-authorization.md",
    "OWASP_API02_Broken_Auth.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xa2-broken-authentication.md",
    "OWASP_API03_Broken_Object_Property_Auth.txt":
        "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0xa3-broken-object-property-level-authorization.md",
    "OWASP_API04_Unrestricted_Resource.txt":
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

ALL_SOURCES = {**OWASP_TOP10_2021, **OWASP_CHEATSHEETS, **OWASP_API_SECURITY_2023}

CATEGORIES = {
    "OWASP Top 10 2021 (10 files)":       list(OWASP_TOP10_2021.keys()),
    "OWASP Cheat Sheets (18 files)":      list(OWASP_CHEATSHEETS.keys()),
    "OWASP API Security 2023 (8 files)":  list(OWASP_API_SECURITY_2023.keys()),
}


def download_file(filename: str, url: str) -> bool:
    try:
        resp = requests.get(url, headers={"User-Agent": "VulnOps-RAG/2.0"}, timeout=30)
        resp.raise_for_status()
        filepath = SOURCE_DOCS_DIR / filename
        filepath.write_text(resp.text, encoding="utf-8")
        logger.info(f"  ✓ {filename} ({len(resp.text) // 1024} KB)")
        return True
    except requests.HTTPError as e:
        logger.warning(f"  ✗ {filename} — HTTP {e.response.status_code}")
        return False
    except Exception as e:
        logger.error(f"  ✗ {filename} — {e}")
        return False


def main():
    SOURCE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Destination: {SOURCE_DOCS_DIR}\n")

    ok = 0
    for category, filenames in CATEGORIES.items():
        logger.info(f"── {category}")
        for name in filenames:
            if download_file(name, ALL_SOURCES[name]):
                ok += 1

    logger.info(f"\n{'='*55}")
    logger.info(f"Done: {ok}/{len(ALL_SOURCES)} files saved.")
    logger.info(f"{'='*55}")
    logger.info("Next: run  python scripts/ingest_docs.py  to build ChromaDB.")


if __name__ == "__main__":
    main()
