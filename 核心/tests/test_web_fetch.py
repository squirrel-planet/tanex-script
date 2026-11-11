import json
import threading
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer

import pytest

class _handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/text':
            self._send(200, 'text/plain; charset=utf-8', 'hello 世界'.encode('utf-8'))
        elif self.path == '/json':
            body = json.dumps({'name': 'tanex', 'value': 7}, ensure_ascii = False)
            self._send(200, 'application/json; charset=utf-8', body.encode('utf-8'))
        else:
            self._send(404, 'text/plain; charset=utf-8', b'not found')

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode('utf-8'))
        body = json.dumps({'echo': payload}, ensure_ascii = False)
        self._send(200, 'application/json; charset=utf-8', body.encode('utf-8'))

    def _send(self, status, content_type, body):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return

@pytest.fixture
def server_url():
    server = ThreadingHTTPServer(('127.0.0.1', 0), _handler)
    thread = threading.Thread(target = server.serve_forever, daemon = True)
    thread.start()
    url = 'http://127.0.0.1:' + str(server.server_address[1])
    try:
        yield url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout = 5)

def test_fetch_text(run_tsuc, server_url):
    source = 'standard_output << python_api.web_fetch.fetch("' + server_url + '/text");'
    assert run_tsuc(source) == 'hello 世界'

def test_fetch_json(run_tsuc, server_url):
    source = '* data = python_api.web_fetch.fetch_json("' + server_url + '/json");\ndata.index("name") == "tanex" ? { standard_output << "OK"; } : { standard_output << "FAIL"; };'
    assert run_tsuc(source) == 'OK'

def test_post_json(run_tsuc, server_url):
    source = '* payload = dictionary{[["x", 5]]};\n* data = python_api.web_fetch.post_json("' + server_url + '/post", payload);\ndata.index("echo").index("x") == 5 ? { standard_output << "OK"; } : { standard_output << "FAIL"; };'
    assert run_tsuc(source) == 'OK'

def test_http_error_is_catchable(run_tsuc, server_url):
    source = 'python_api.web_fetch.fetch("' + server_url + '/missing") | err : { standard_output << "ERR"; } : { standard_output << "OK"; };'
    assert run_tsuc(source) == 'ERR'

def test_non_http_scheme_rejected(run_tsuc):
    source = 'python_api.web_fetch.fetch("file:///etc/passwd") | err : { standard_output << "ERR"; } : { standard_output << "OK"; };'
    assert run_tsuc(source) == 'ERR'
