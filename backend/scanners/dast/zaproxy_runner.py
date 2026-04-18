import asyncio
import os
import json
import logging
import aiohttp
from django.conf import settings
from ..base import BaseScanner

logger = logging.getLogger(__name__)

class ZapRunner(BaseScanner):
    def __init__(self):
        super().__init__("OWASP ZAP")
    
    def run(self, target_url, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        result = loop.run_until_complete(run_zap_scan_async(target_url))
        if result['success']:
            return result['vulnerabilities']
        return []

def run_zap_baseline_scan(target_url: str) -> dict:
    """Version synchrone pour la compatibilit avec les views existantes."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(run_zap_scan_async(target_url))

async def run_zap_scan_async(target_url: str) -> dict:
    """
    Runs an OWASP ZAP baseline scan using Docker.
    """
    import subprocess
    import tempfile
    import os
    import json
    import uuid

    logger.info(f"Starting async ZAP scan for {target_url}")
    
    # Use a temporary directory to store the ZAP report
    temp_dir = tempfile.mkdtemp(prefix='vulnops_zap_')
    report_filename = f"zap_report_{uuid.uuid4().hex[:8]}.json"
    report_path = os.path.join(temp_dir, report_filename)
    
    # Handle localhost issue: if ZAP is in a container, it can't reach 'localhost' of the host.
    # We replace localhost with host.docker.internal which works on Windows/Mac.
    zap_target_url = target_url
    if 'localhost' in zap_target_url:
        zap_target_url = zap_target_url.replace('localhost', 'host.docker.internal')
    elif '127.0.0.1' in zap_target_url:
        zap_target_url = zap_target_url.replace('127.0.0.1', 'host.docker.internal')

    try:
        # ZAP command: -t target -J output.json
        # We mount the temp_dir to /zap/wrk/ in the container
        zap_cmd = [
            'docker', 'run', '--rm',
            '--add-host=host.docker.internal:host-gateway', # Ensure host.docker.internal is available
            '-v', f"{temp_dir}:/zap/wrk/:rw",
            'ghcr.io/zaproxy/zaproxy:stable',
            'zap-baseline.py',
            '-t', zap_target_url,
            '-J', report_filename
        ]
        
        logger.info(f"Running ZAP command: {' '.join(zap_cmd)}")
        
        # Note: zap-baseline.py returns:
        # 0: Success
        # 1: At least one error / warning
        # 2: At least one failure
        # 3: At least one error and one failure
        res = subprocess.run(zap_cmd, capture_output=True, text=True)
        
        if not os.path.exists(report_path):
            logger.error(f"ZAP report not found at {report_path}. Stderr: {res.stderr}")
            return {
                'success': False, 
                'error': f"ZAP failed to generate report. {res.stderr or res.stdout}"
            }
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
            
        alerts = []
        site_info = report_data.get('site', [])
        if site_info:
            # ZAP JSON structure is nested: site -> alerts
            site_alerts = site_info[0].get('alerts', [])
            for alert in site_alerts:
                # Map ZAP risk levels to our severity
                risk = alert.get('riskdesc', 'Low').upper()
                severity = 'INFO'
                if 'HIGH' in risk: severity = 'HIGH'
                elif 'MEDIUM' in risk: severity = 'MEDIUM'
                elif 'LOW' in risk: severity = 'LOW'
                
                alerts.append({
                    'test_id': alert.get('pluginid', 'ZAP'),
                    'test_name': alert.get('alert', 'Vulnerability'),
                    'issue_text': alert.get('description', ''),
                    'severity': severity,
                    'confidence': alert.get('confidence', 'Medium'),
                    'filename': alert.get('url', ''),
                    'line_number': 0,
                    'code_snippet': alert.get('evidence', ''),
                    'cwe': alert.get('cweid', ''),
                    'more_info': alert.get('other', ''),
                    'solution': alert.get('solution', '')
                })
        
        return {
            'success': True,
            'data': alerts,
            'vulnerabilities': alerts,
            'raw': report_data
        }

    except Exception as e:
        logger.exception("Error during ZAP scan")
        return {'success': False, 'error': str(e)}
    finally:
        # Cleanup temp report
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

def check_dast_prerequisites(repo_path: str) -> dict:
    """
    Checks for Docker and OpenAPI files in the project.
    Expected structure by frontend:
    {
        "ready": bool,
        "found": { "dockerfile": bool, "compose": bool, ... },
        "missing": [str],
        "dockerfile_content": str (optional)
    }
    """
    found = {
        'dockerfile': False,
        'compose': False,
        'openapi': False
    }
    missing = []
    dockerfile_content = ""

    # Check for Dockerfile
    dockerfile_path = os.path.join(repo_path, 'Dockerfile')
    if os.path.exists(dockerfile_path):
        found['dockerfile'] = True
        try:
            with open(dockerfile_path, 'r', encoding='utf-8') as f:
                dockerfile_content = f.read()
        except Exception:
            pass
    else:
        missing.append('Dockerfile')

    # Check for docker-compose
    compose_files = ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml', 'compose.yaml']
    for cf in compose_files:
        if os.path.exists(os.path.join(repo_path, cf)):
            found['compose'] = True
            break
    
    if not found['compose']:
        missing.append('docker-compose.yml')

    # Check for OpenAPI / Swagger
    openapi_patterns = ['openapi.json', 'openapi.yaml', 'openapi.yml', 'swagger.json', 'swagger.yaml', 'swagger.yml']
    for root, dirs, files in os.walk(repo_path):
        for f in files:
            if f.lower() in openapi_patterns:
                found['openapi'] = True
                break
        if found['openapi']:
            break
    
    if not found['openapi']:
        missing.append('Spécification OpenAPI (ex: openapi.yaml)')

    # A project is "ready" if it has at least a Dockerfile or Compose file
    ready = found['dockerfile'] or found['compose']

    return {
        'success': True,
        'ready': ready,
        'found': found,
        'missing': missing,
        'dockerfile_content': dockerfile_content
    }

def build_and_run_container(repo_path, repo_name, **kwargs):
    """
    Builds a docker image from the repo_path and runs it.
    Returns: { 'success': bool, 'url': str, 'container_name': str, 'error': str }
    """
    import subprocess
    import time
    import uuid
    import socket

    container_name = f"vulnops_app_{repo_name.lower()}_{uuid.uuid4().hex[:8]}"
    image_name = f"vulnops_img_{repo_name.lower()}"
    manual_port = kwargs.get('manual_port')
    start_command = kwargs.get('start_command')

    try:
        # 1. Build Image
        logger.info(f"Building Docker image {image_name} from {repo_path}")
        build_res = subprocess.run(
            ['docker', 'build', '-t', image_name, '.'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=600
        )
        if build_res.returncode != 0:
            return {'success': False, 'error': f"Docker build failed: {build_res.stderr}"}

        # 2. Find a free port on host to map to
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            host_port = s.getsockname()[1]

        # 3. Determine internal port (default to 8000 or 80 or 5000 or 3000 if not provided)
        # In a real scenario, we might want to inspect the Dockerfile or use a smart default
        internal_port = manual_port or 8000 

        # 4. Run Container
        run_cmd = ['docker', 'run', '-d', '--name', container_name, '-p', f"{host_port}:{internal_port}"]
        if start_command:
            # Note: This might be tricky depending on how the image was built
            # For simplicity, we just append it
            run_cmd.extend([image_name, 'sh', '-c', start_command])
        else:
            run_cmd.append(image_name)

        logger.info(f"Running Docker container: {' '.join(run_cmd)}")
        run_res = subprocess.run(run_cmd, capture_output=True, text=True)
        if run_res.returncode != 0:
            return {'success': False, 'error': f"Docker run failed: {run_res.stderr}"}

        # 5. Wait for app to be ready
        # Simple health check: try to connect to host_port
        max_retries = 30
        url = f"http://localhost:{host_port}"
        logger.info(f"Waiting for app to be ready at {url}...")
        
        for i in range(max_retries):
            try:
                with socket.create_connection(('localhost', host_port), timeout=1):
                    logger.info("App is reachable!")
                    time.sleep(2) # Give it a bit more time to fully initialize
                    return {'success': True, 'url': url, 'container_name': container_name}
            except (ConnectionRefusedError, socket.timeout, OSError):
                time.sleep(1)
        
        # If we reach here, it might still be running but not answering on that port
        # We return success anyway, the ZAP scan will fail if nothing is there
        return {'success': True, 'url': url, 'container_name': container_name, 'warning': 'App might not be ready yet'}

    except Exception as e:
        logger.exception("Error in build_and_run_container")
        return {'success': False, 'error': str(e)}

def stop_and_cleanup_container(container_name):
    import subprocess
    try:
        logger.info(f"Stopping container {container_name}")
        subprocess.run(['docker', 'stop', container_name], capture_output=True)
        logger.info(f"Removing container {container_name}")
        subprocess.run(['docker', 'rm', container_name], capture_output=True)
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
