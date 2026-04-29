from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import json
import sys

if len(sys.argv) < 2:
    print("Usage: python bridge.py <printer_ip>")
    sys.exit(1)
PRINTER_IP  = sys.argv[1]
ENGINE_BASE = f"http://{PRINTER_IP}:9966"  # /engine/*
DATA_BASE   = f"http://{PRINTER_IP}:9911"  # /data/*
PORT = 8765

def resolve_target(path):
    if path.startswith('/data/'):
        return DATA_BASE
    return ENGINE_BASE

class ProxyHandler(BaseHTTPRequestHandler):

    def add_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.add_cors()
        self.end_headers()

    def proxy(self, method):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else None
        target = resolve_target(self.path)

        try:
            resp = requests.request(
                method,
                f"{target}{self.path}",
                data=body,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            self.send_response(resp.status_code)
            self.send_header('Content-Type', 'application/json')
            self.add_cors()
            self.end_headers()
            self.wfile.write(resp.content)
        except Exception as e:
            self.send_response(502)
            self.add_cors()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())

    def do_GET(self):    self.proxy('GET')
    def do_POST(self):   self.proxy('POST')
    def do_DELETE(self): self.proxy('DELETE')

    def log_message(self, fmt, *args):
        target = resolve_target(self.path)
        port = "9911" if "9911" in target else "9966"
        print(f"{self.command} {self.path} → :{port} {args[1]}")

print(f"Proxy running: http://localhost:{PORT}")
print(f"  /engine/* → {ENGINE_BASE}")
print(f"  /data/*   → {DATA_BASE}")
HTTPServer(('localhost', PORT), ProxyHandler).serve_forever()
