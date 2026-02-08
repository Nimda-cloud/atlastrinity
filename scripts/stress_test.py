import json
import sys
import time

import requests

URL = "http://127.0.0.1:8000/api/chat"
HEALTH_URL = "http://127.0.0.1:8000/api/health"

TASK = """
RESEARCH COMPLEXITY STRESS TEST:
1. Check the current system CPU usage using a terminal command.
2. Find the top 3 largest files in the current directory recursively.
3. Write these statistics to 'system_report.md'.
4. Verify the file exists and is not empty.
"""

def wait_for_server():
    print("Waiting for server...")
    for _ in range(120):  # 2 minutes wait
        try:
            resp = requests.get(HEALTH_URL)
            if resp.status_code == 200:
                print("\nServer is UP!")
                return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            print(".", end="", flush=True)
    return False

if __name__ == "__main__":
    if not wait_for_server():
        print("\nServer failed to start within timeout.")
        sys.exit(1)

    print(f"\nSending stress test task:\n{TASK}")
    try:
        resp = requests.post(URL, json={"request": TASK}, timeout=600)  # 10 min timeout for task
        if resp.status_code == 200:
            print("\n✅ Task Completed Successfully!")
            print(json.dumps(resp.json(), indent=2))
        else:
            print(f"\n❌ Task Failed: {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"\n❌ Request Exception: {e}")
