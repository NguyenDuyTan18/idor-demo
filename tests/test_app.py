import importlib.util
import io
import json
import unittest
from unittest.mock import patch, MagicMock
import tempfile
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'provisioning/roles/server/files/idor_app.py'
        self.assertTrue(path.is_file(), 'IDOR web implementation must exist')
        spec = importlib.util.spec_from_file_location('idor_app', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.app = self.module.create_app('flag-A', 'test-password', sandbox_id='sandbox-A')

    def request(self, path, method='GET', data=None, cookie='', app=None):
        body = urlencode(data or {}).encode()
        env = {'REQUEST_METHOD': method, 'PATH_INFO': path,
               'CONTENT_LENGTH': str(len(body)), 'wsgi.input': io.BytesIO(body),
               'HTTP_COOKIE': cookie, 'CONTENT_TYPE': 'application/x-www-form-urlencoded'}
        response = {}
        def start(status, headers):
            response.update(status=int(status.split()[0]), headers=dict(headers))
        response['body'] = b''.join((app or self.app)(env, start))
        return response

    def login(self, app=None):
        response = self.request('/login', 'POST', {'username': 'alice', 'password': 'test-password'}, app=app)
        self.assertEqual(response['status'], 303)
        cookie = SimpleCookie(response['headers']['Set-Cookie'])
        self.assertTrue(cookie['session']['httponly'])
        self.assertEqual(cookie['session']['samesite'], 'Lax')
        return 'session=' + cookie['session'].value

    def test_health_has_identity_without_answer(self):
        response = self.request('/health')
        self.assertEqual(response['status'], 200)
        self.assertEqual(json.loads(response['body'])['sandbox'], 'sandbox-A')
        self.assertNotIn(b'flag-A', response['body'])

    def test_login_page_and_own_list_do_not_leak_bob(self):
        self.assertIn(b'<form', self.request('/')['body'])
        response = self.request('/api/documents', cookie=self.login())
        docs = json.loads(response['body'])
        self.assertEqual([doc['id'] for doc in docs], [1001])
        self.assertNotIn(b'flag-A', response['body'])

    def test_unauthenticated_and_tampered_cookie_are_rejected(self):
        for cookie in ['', 'session=forged', 'session="unterminated']:
            self.assertEqual(self.request('/api/documents/1002', cookie=cookie)['status'], 401)

    def test_wrong_credentials_do_not_create_session(self):
        for name, password in [('alice', 'wrong'), ('bob', 'test-password'), ('alice', 'mật-khẩu')]:
            response = self.request('/login', 'POST', {'username': name, 'password': password})
            self.assertEqual(response['status'], 401)
            self.assertNotIn('Set-Cookie', response['headers'])

    def test_idor_requires_auth_but_allows_other_owner(self):
        cookie = self.login()
        own = self.request('/api/documents/1001', cookie=cookie)
        other = self.request('/api/documents/1002', cookie=cookie)
        self.assertEqual(own['status'], 200)
        self.assertEqual(json.loads(own['body'])['owner'], 'alice')
        self.assertEqual(other['status'], 200)
        self.assertEqual(json.loads(other['body']), {'id': 1002, 'owner': 'bob', 'title': 'Restricted research document', 'flag': 'flag-A'})

    def test_patched_mode_blocks_other_owner(self):
        app = self.module.create_app('flag-A', 'test-password', enforce_owner=True)
        cookie = self.login(app)
        self.assertEqual(self.request('/api/documents/1001', cookie=cookie, app=app)['status'], 200)
        self.assertEqual(self.request('/api/documents/1002', cookie=cookie, app=app)['status'], 403)

    def test_two_sandbox_answers_and_sessions_are_separate(self):
        other = self.module.create_app('flag-B', 'test-password', sandbox_id='sandbox-B')
        cookie_a = self.login()
        self.assertEqual(self.request('/api/documents/1002', cookie=cookie_a, app=other)['status'], 401)
        cookie_b = self.login(other)
        result = self.request('/api/documents/1002', cookie=cookie_b, app=other)
        self.assertEqual(json.loads(result['body'])['flag'], 'flag-B')

    def test_unknown_document_and_invalid_methods(self):
        cookie = self.login()
        for path in ['/missing', '/api/documents/bad', '/api/documents/9999']:
            self.assertEqual(self.request(path, cookie=cookie)['status'], 404)
        self.assertEqual(self.request('/api/documents/1002', 'POST', cookie=cookie)['status'], 405)
        self.assertEqual(self.request('/login')['status'], 405)

    def test_logout_revokes_session(self):
        cookie = self.login()
        self.assertEqual(self.request('/logout', 'POST', cookie=cookie)['status'], 303)
        self.assertEqual(self.request('/api/documents/1002', cookie=cookie)['status'], 401)

    def test_missing_apg_answer_or_password_fails_closed(self):
        for flag, password in [('', 'password'), ('flag', '')]:
            with self.assertRaises(ValueError):
                self.module.create_app(flag, password)

    def test_request_boundaries_and_expired_session(self):
        self.assertEqual(self.request('/', 'DELETE')['status'], 405)
        with patch.object(self.module.time, 'time', return_value=1000):
            cookie = self.login()
        with patch.object(self.module.time, 'time', return_value=3000):
            self.assertEqual(self.request('/api/documents/1002', cookie=cookie)['status'], 401)
            self.login()  # The old session is removed when a new one is inserted.
        for length, body, expected in [('bad', b'', 400), ('5000', b'', 413), ('1', b'\xff', 400)]:
            env = {'REQUEST_METHOD': 'POST', 'PATH_INFO': '/login', 'CONTENT_LENGTH': length, 'wsgi.input': io.BytesIO(body)}
            result = {}
            self.app(env, lambda status, headers: result.update(status=int(status.split()[0])))
            self.assertEqual(result['status'], expected)

    def test_service_entrypoint_uses_config_and_requested_listener(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.json'
            config.write_text(json.dumps({'flag': 'cli-answer', 'password': 'test-password', 'sandbox_id': 'cli'}), encoding='utf-8')
            listener = MagicMock()
            with patch('sys.argv', ['idor_app.py', '--config', str(config), '--host', '0.0.0.0', '--port', '8080']), patch.object(self.module, 'make_server', return_value=listener) as make:
                self.module.main()
            self.assertEqual(make.call_args.args[:2], ('0.0.0.0', 8080))
            listener.__enter__.return_value.serve_forever.assert_called_once()


if __name__ == '__main__':
    unittest.main()
