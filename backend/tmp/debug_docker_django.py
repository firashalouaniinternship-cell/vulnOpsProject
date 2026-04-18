import os
import sys
import shutil
import tempfile

# Add backend directory to path
sys.path.append(os.path.abspath('backend'))

from scanners.sast.cppcheck_runner import run_cppcheck

# Replicate the Django environment
base_tmp = os.path.abspath('backend/tmp')
if not os.path.exists(base_tmp):
    os.makedirs(base_tmp)

tmp_dir = tempfile.mkdtemp(prefix='debug_cppcheck_', dir=base_tmp)
print(f"Testing in directory: {tmp_dir}")

# Create a test file
with open(os.path.join(tmp_dir, 'test.c'), 'w') as f:
    f.write('int main() { char a[10]; a[10] = 0; return 0; }')

# Run the apps.scans
result = run_cppcheck(tmp_dir)

print("\n--- Result ---")
if 'errors' in result:
    print(f"Error: {result['errors']}")
elif 'xml' in result:
    print("Success! Received XML.")
else:
    print(f"Unexpected: {result}")

# Clean up
shutil.rmtree(tmp_dir)
