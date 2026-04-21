import requests
import json

url = "http://localhost:8000/api/scans/github/"
token = "devsecops-cicd-token-2024"

payload = {
    "repo_full_name": "firas/test-repo",
    "repo_owner": "firas",
    "repo_name": "test-repo",
    "branch": "main",
    "commit_sha": "abc123456789",
    "reports": {
        "sast": {
            "scanner": "semgrep",
            "data": {
                "results": [
                    {
                        "check_id": "rules.python.security.injection.crypto-bad-cipher",
                        "path": "app.py",
                        "start": {"line": 10, "col": 5},
                        "end": {"line": 10, "col": 20},
                        "extra": {
                            "message": "Use of unsafe block cipher detected. AES is recommended.",
                            "severity": "ERROR",
                            "lines": "cipher = DES.new(key)",
                            "metadata": {
                                "cwe": ["CWE-327"],
                                "references": ["https://owasp.org/www-project-top-ten/2017/A6_2017-Security_Misconfiguration"]
                            }
                        }
                    }
                ]
            }
        },
        "sca": {
            "scanner": "npm-audit",
            "data": {
                "auditReportVersion": 2,
                "vulnerabilities": {
                    "express": {
                        "name": "express",
                        "severity": "high",
                        "isDirect": true,
                        "via": [
                            {
                                "source": 109,
                                "name": "express",
                                "dependency": "express",
                                "title": "Denial of Service in Express",
                                "url": "https://npmjs.com/advisories/109",
                                "severity": "high",
                                "cwe": ["CWE-400"],
                                "range": "<4.17.3"
                            }
                        ],
                        "range": "<4.17.3"
                    }
                }
            }
        }
    }
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

print(f"Sending mock CI/CD payload to {url}...")
try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Body: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
