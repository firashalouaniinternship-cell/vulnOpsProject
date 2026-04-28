import requests
import json
import time

def trigger_test_scan():
    url = "http://localhost:8000/api/apps.scans/scan/"
    payload = {
        "repo_full_name": "firasHalouani/vulnerable",
        "clone_url": "https://github.com/firasHalouani/vulnerable.git",
        "repo_name": "vulnerable",
        "repo_owner": "firasHalouani",
        "scanner_type": "bandit",
        "run_sca": True
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Triggering scan for {payload['repo_full_name']}...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
        print(f"Response Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Scan triggered successfully!")
            print(f"Scan ID: {data.get('scan_id')}")
            print(f"Issues Found: {data.get('metrics', {}).get('total_issues', 0)}")
            print("Check results on dashboard.")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    trigger_test_scan()
