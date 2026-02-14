import time

import requests


def test_models():
    print("Testing models via Windsurf Proxy (Port 8085)...")
    url = "http://127.0.0.1:8085/v1/chat/completions"
    headers = {"Content-Type": "application/json"}

    models = ["deepseek-v3", "swe-1.5"]

    for model in models:
        print(f"\n- Testing {model}...")
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello! Reply only with 'OK'."}],
            "temperature": 0.1,
        }
        try:
            start = time.time()
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            elapsed = time.time() - start
            print(f"  Status: {response.status_code} ({elapsed:.2f}s)")
            if response.status_code == 200:
                print(f"  AI: {response.json()['choices'][0]['message']['content']}")
            else:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"  Request failed: {e}")


if __name__ == "__main__":
    test_models()
