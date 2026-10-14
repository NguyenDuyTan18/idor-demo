"""Purpose-built IDOR lab. Standard library only; not a production web server."""
import argparse
import hmac
import json
import secrets
import time
from http import HTTPStatus
from http.cookies import CookieError, SimpleCookie
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server


def create_app(flag, password, enforce_owner=False, sandbox_id='local'):
    if not flag or not password:
        raise ValueError('An APG answer and a lab password are required')
    sessions = {}
    documents = {
        1001: {'id': 1001, 'owner': 'alice', 'title': 'My research notes'},
        1002: {'id': 1002, 'owner': 'bob', 'title': 'Restricted research document', 'flag': flag},
    }

    def app(env, start_response):
        path, method = env.get('PATH_INFO', '/'), env.get('REQUEST_METHOD', 'GET')

        def response(status, body, headers=None, html=False):
            content = body.encode('utf-8') if html else json.dumps(body).encode('utf-8')
            common = [('Content-Type', 'text/html; charset=utf-8' if html else 'application/json'),
                      ('Content-Length', str(len(content))), ('Cache-Control', 'no-store'),
                      ('X-Content-Type-Options', 'nosniff')]
            start_response(f'{status} {HTTPStatus(status).phrase}', common + (headers or []))
            return [content]

        if method not in ('GET', 'POST'):
            return response(405, {'error': 'Method not allowed'})
        if path == '/health' and method == 'GET':
            return response(200, {'status': 'ok', 'sandbox': sandbox_id})
        if path == '/' and method == 'GET':
            return response(200, '''<!doctype html><html lang="vi"><meta charset="utf-8">
<title>IDOR APG Lab</title><h1>Cổng tài liệu nghiên cứu</h1>
<form method="post" action="/login"><label>Tài khoản <input name="username" required></label>
<label>Mật khẩu <input type="password" name="password" required></label><button>Đăng nhập</button></form>
<p><a href="/api/documents">Tài liệu của tôi</a></p></html>''', html=True)
        if path == '/login':
            if method != 'POST':
                return response(405, {'error': 'Use POST'})
            try:
                size = int(env.get('CONTENT_LENGTH') or 0)
                if not 0 <= size <= 4096:
                    return response(413, {'error': 'Request too large'})
                form = parse_qs(env['wsgi.input'].read(size).decode('utf-8'), max_num_fields=8)
            except (ValueError, UnicodeDecodeError):
                return response(400, {'error': 'Invalid form'})
            if form.get('username') != ['alice'] or not hmac.compare_digest(
                    form.get('password', [''])[0].encode('utf-8'), password.encode('utf-8')):
                return response(401, {'error': 'Invalid credentials'})
            # Expire old sessions before inserting another one.
            now = time.time()
            for token in list(sessions):
                if now - sessions[token] >= 1800:
                    del sessions[token]
            token = secrets.token_urlsafe(32)
            sessions[token] = now
            return response(303, {'status': 'logged in'}, [
                ('Location', '/api/documents'),
                ('Set-Cookie', f'session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=1800')])
        try:
            cookie = SimpleCookie(env.get('HTTP_COOKIE', ''))
            token = cookie['session'].value if 'session' in cookie else ''
        except CookieError:
            token = ''
        if token not in sessions or time.time() - sessions[token] >= 1800:
            return response(401, {'error': 'Login required'})
        if path == '/logout' and method == 'POST':
            del sessions[token]
            return response(303, {'status': 'logged out'}, [
                ('Location', '/'), ('Set-Cookie', 'session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0')])
        if method != 'GET':
            return response(405, {'error': 'Use GET'})
        if path == '/api/documents':
            return response(200, [d for d in documents.values() if d['owner'] == 'alice'])
        if path.startswith('/api/documents/'):
            try:
                document = documents[int(path.rsplit('/', 1)[-1])]
            except (KeyError, ValueError):
                return response(404, {'error': 'Document not found'})
            # The exercise intentionally omits this object-owner check by default.
            if enforce_owner and document['owner'] != 'alice':
                return response(403, {'error': 'Forbidden'})
            return response(200, document)
        return response(404, {'error': 'Not found'})

    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    with open(args.config, encoding='utf-8') as file:
        settings = json.load(file)
    app = create_app(**settings)
    with make_server(args.host, args.port, app) as server:
        server.serve_forever()


if __name__ == '__main__':
    main()
