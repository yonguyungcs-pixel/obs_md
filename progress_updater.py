import time
import subprocess

print("Starting progress updater loop...")
while True:
    try:
        subprocess.run(["python", "update_md.py"], check=False, capture_output=True)
        subprocess.run(["python", "update_sfs_md.py"], check=False, capture_output=True)
    except Exception as e:
        print(f"Error updating md: {e}")
    time.sleep(15)
