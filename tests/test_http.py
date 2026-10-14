"""HTTP end-to-end checks on two real loopback web servers, not cloud networking."""
import importlib.util
import json
import threading
import unittest
from contextlib import ExitStack
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener
from wsgiref.simple_server import WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


class HTTPTests(unittest.TestCase):
    def test_two_real_servers_login_idor_and_answer_identity(self):
        path = ROOT / 'provisioning/roles/server/files/idor_app.py'
        self.assertTrue(path.exists())
        spec = importlib.util.spec_from_file_location('http_app', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with ExitStack() as stack:
            urls = []
            for label in ['A', 'B']:
                server = stack.enter_context(make_server(
                    '127.0.0.1', 0, module.create_app('answer-' + label, 'test-password', sandbox_id=label),
                    handler_class=QuietHandler))
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                stack.callback(worker.join, 2)
                stack.callback(server.shutdown)
                urls.append(f'http://127.0.0.1:{server.server_port}')
            clients = [build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar())) for _ in urls]
            for url, client, label in zip(urls, clients, ['A', 'B']):
                with client.open(url + '/health', timeout=5) as response:
                    self.assertEqual(json.load(response)['sandbox'], label)
                with self.assertRaises(HTTPError) as error:
                    client.open(url + '/api/documents/1002', timeout=5)
                self.assertEqual(error.exception.code, 401)
                login = Request(url + '/login', data=urlencode({'username': 'alice', 'password': 'test-password'}).encode())
                with client.open(login, timeout=5) as response:
                    self.assertEqual(json.load(response)[0]['id'], 1001)
                with client.open(url + '/api/documents/1002', timeout=5) as response:
                    result = json.load(response)
                    self.assertEqual(result['owner'], 'bob')
                    self.assertEqual(result['flag'], 'answer-' + label)


if __name__ == '__main__':
    unittest.main()
