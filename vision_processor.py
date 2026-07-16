import threading
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List

class VisionProcessor:
    """Acts as a local HTTP server to receive the exact board matrix from the stealth DOM reader."""
    
    def __init__(self, license_manager=None):
        self.license_manager = license_manager
        self.latest_matrix = [['' for _ in range(8)] for _ in range(8)]
        self.is_white_bottom = True
        self.latest_time_left = 300.0
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

    def _run_server(self):
        parent = self
        
        class RequestHandler(BaseHTTPRequestHandler):
            def do_OPTIONS(self):
                self.send_response(204) # 204 No Content for OPTIONS
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.send_header('Access-Control-Allow-Private-Network', 'true')
                self.end_headers()

            def do_GET(self):
                if self.path == '/auth':
                    is_authed = parent.license_manager and parent.license_manager.is_valid
                    self.send_response(200)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Private-Network', 'true')
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    if is_authed:
                        self.wfile.write(b'{"status":"authenticated"}')
                    else:
                        self.wfile.write(b'{"status":"unauthorized"}')
                    return
                
                self.send_response(404)
                self.end_headers()
                
            def do_POST(self):
                # Verify license is active before processing data
                is_authed = parent.license_manager and parent.license_manager.is_valid
                if not is_authed:
                    self.send_response(401)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Private-Network', 'true')
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"status":"unauthorized"}')
                    return

                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    if 'matrix' in data:
                        parent.latest_matrix = data['matrix']
                    if 'is_white_bottom' in data:
                        parent.is_white_bottom = data['is_white_bottom']
                    if 'time_left' in data:
                        parent.latest_time_left = float(data['time_left'])
                except Exception as e:
                    print(f"Error parsing DOM data: {e}")
                
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Private-Network', 'true')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
                
            def log_message(self, format, *args):
                pass # Suppress HTTP logs to keep terminal clean

        print("Started Stealth DOM Server on http://127.0.0.1:5005")
        server = HTTPServer(('127.0.0.1', 5005), RequestHandler)
        server.serve_forever()

    def get_board_data(self) -> dict:
        return {
            "matrix": self.latest_matrix, 
            "is_white_bottom": self.is_white_bottom,
            "time_left": self.latest_time_left
        }

