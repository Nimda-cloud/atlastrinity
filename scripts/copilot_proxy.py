import http.server
import json
import signal
import socketserver
import sys
import time
import urllib.error
import urllib.request
from typing import Optional


# Setup logging
def log(msg):
    print(f"[CopilotProxy] {msg}", file=sys.stderr)


class CopilotProxyHandler(http.server.BaseHTTPRequestHandler):
    # Track processed requests and uptime
    processed_requests: int = 0
    start_time: Optional[float] = None

    def do_GET(self):
        CopilotProxyHandler.processed_requests += 1
        log(f"--- Incoming GET to {self.path} ---")

        if self.path in ["/v1/models", "/models"]:
            # Standard OpenAI-style models list
            models_data = {
                "object": "list",
                "data": [
                    {
                        "id": "gpt-4o",
                        "object": "model",
                        "created": 1715340800,
                        "owned_by": "github-copilot",
                    }
                ],
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(models_data).encode())
        elif self.path == "/v1/status":
            # Return proxy status
            st = CopilotProxyHandler.start_time
            uptime = time.time() - st if st is not None else 0.0
            status_data = {
                "uptime": uptime,
                "processed_requests": CopilotProxyHandler.processed_requests,
                "upstream_model": "gpt-4o",
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(status_data).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        CopilotProxyHandler.processed_requests += 1
        log(f"--- Incoming POST to {self.path} ---")

        # 1. Read input
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data)
            requested_model = payload.get("model", "unknown")
            log(f"Request model: {requested_model}")

            # 2. Add required headers
            # Authenticate with session token from environment or header
            auth_header = self.headers.get("Authorization")

            # Copilot required headers
            headers = {
                "Content-Type": "application/json",
                "Editor-Version": "vscode/1.85.0",
                "Editor-Plugin-Version": "copilot/1.144.0",
                "User-Agent": "GithubCopilot/1.144.0",
                "X-GitHub-Api-Version": "2023-07-07",
            }
            if auth_header:
                headers["Authorization"] = auth_header

            # 3. Forward to GitHub Copilot
            # Vibe/OpenAI style uses /v1/... but GitHub prefers chat/completions directly
            path = self.path
            if path.startswith("/v1/"):
                path = path[3:]
            target_url = "https://api.githubcopilot.com" + path

            req = urllib.request.Request(target_url, data=post_data, headers=headers, method="POST")

            try:
                # Add a reasonable timeout (60s) to prevent hangs
                with urllib.request.urlopen(req, timeout=60) as response:
                    upstream_status = response.status
                    log(f"Upstream response code: {upstream_status}")
                    self.send_response(upstream_status)
                    for k, v in response.headers.items():
                        if k.lower() in (
                            "content-type",
                            "date",
                            "x-request-id",
                            "x-github-request-id",
                        ):
                            self.send_header(k, v)
                    self.end_headers()
                    self.wfile.write(response.read())
            except TimeoutError:
                log("Error: Upstream request timed out (60s)")
                self.send_response(504)
                self.end_headers()
                self.wfile.write(b"Gateway Timeout: GitHub Copilot did not respond")

        except urllib.error.HTTPError as e:
            error_body = e.read().decode(errors="replace")
            log(f"Upstream HTTP error: {e.code} {e.reason} - Body: {error_body[:200]}")
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(error_body.encode())
        except Exception as e:
            log(f"Proxy internal error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())


def run(port=8085):

    CopilotProxyHandler.start_time = time.time()

    server_address = ("127.0.0.1", port)
    # Enable address reuse to avoid "Address already in use" errors
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(server_address, CopilotProxyHandler)
    log(f"Serving at http://127.0.0.1:{port}")

    def handle_signal(sig, frame):
        log(f"Received signal {sig}, shutting down...")
        httpd.server_close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        httpd.serve_forever()
    except Exception as e:
        log(f"Server error: {e}")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()
