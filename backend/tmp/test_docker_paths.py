import os
import subprocess

abs_repo_path = os.path.abspath('tmp')
drive = abs_repo_path[0].lower()
unix_path = '/' + drive + abs_repo_path[2:].replace('\\', '/')

# Test various path formats
paths_to_test = [
    f"{abs_repo_path}:/src",          # C:\Users\...
    f"{unix_path}:/src",             # /c/Users/...
    f"//{drive}/{abs_repo_path[3:].replace('\\', '/')}:/src" # //c/Users/...
]

for p in paths_to_test:
    print(f"\nTesting path format: {p}")
    docker_cmd = [
        'docker', 'run', '--rm', 
        '-v', p, 
        'alpine', 'ls', '/src'
    ]
    print(f"Command: {' '.join(docker_cmd)}")
    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        print(f"Return code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
    except Exception as e:
        print(f"Error: {e}")
