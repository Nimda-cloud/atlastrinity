import http.server
import socketserver
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Setup logging
def log(msg):
    print(f"[CopilotProxy] {msg}", file=sys.stderr)

class CopilotProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        log(f"Handling POST to {self.path}")
        
        # 1. Read input
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            # 2. Add required headers
            # Authenticate with session token from environment or header
            auth_header = self.headers.get('Authorization')
            
            # Copilot required headers
            headers = {
                "Content-Type": "application/json",
                "Editor-Version": "vscode/1.85.0",
                "Editor-Plugin-Version": "copilot/1.144.0",
                "User-Agent": "GithubCopilot/1.144.0"
            }
            if auth_header:
                headers["Authorization"] = auth_header
            
            # 3. Forward to GitHub Copilot
            # Vibe sends to /chat/completions (usually)
            # We map local /chat/completions -> https://api.githubcopilot.com/chat/completions
            target_url = "https://api.githubcopilot.com" + self.path
            
            req = urllib.request.Request(target_url, data=post_data, headers=headers, method="POST")
            
            with urllib.request.urlopen(req) as response:
                self.send_response(response.status)
                for k, v in response.headers.items():
                    # Forward relevant headers
                    if k.lower() in ("content-type", "date"):
                        self.send_header(k, v)
                self.end_headers()
                
                # Stream content back
                self.wfile.write(response.read())
                
        except urllib.error.HTTPError as e:
            log(f"Upstream error: {e.code} {e.reason}")
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            log(f"Proxy error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

def run(port=8085):
    server_address = ('127.0.0.1', port)
    httpd = socketserver.TCPServer(server_address, CopilotProxyHandler)
    log(f"Serving at http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down")
        httpd.server_close()

if __name__ == "__main__":
    run()
