"""Loopback-only API and bounded playback of local audio."""
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from trackseparator import models
from trackseparator.runtime import ROOT
from trackseparator.separation import STEMS
from trackseparator.storage import Conflict


def make_server(app, port=0):
    class Handler(BaseHTTPRequestHandler):
        def local(self):
            port = self.server.server_address[1]
            hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
            origin = self.headers.get('Origin')
            site = self.headers.get('Sec-Fetch-Site', '').lower()
            navigation = (self.command == 'GET' and urlparse(self.path).path in ('/', '/index.html')
                          and self.headers.get('Sec-Fetch-Mode') == 'navigate'
                          and self.headers.get('Sec-Fetch-Dest') == 'document')
            if (self.headers.get('Host', '').lower() not in hosts
                or origin is not None and origin.lower() not in {'http://'+h for h in hosts}
                or site not in ('', 'same-origin', 'none') and not navigation):
                self.json({'error': 'Forbidden request'}, 403)
                return False
            self.connection.settimeout(60)
            return True

        def json(self, value, status=200):
            body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers(); self.wfile.write(body)

        def file(self, path, mime):
            size = path.stat().st_size
            start, end, status = 0, size-1, 200
            requested = self.headers.get('Range')
            if requested:
                import re
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
                try:
                    if not match or not any(match.groups()): raise ValueError()
                    a, b = match.groups()
                    if a:
                        start = int(a); end = min(size-1, int(b)) if b else size-1
                    else:
                        if int(b) <= 0: raise ValueError()
                        start = max(0, size-int(b))
                    if start > end or start >= size: raise ValueError()
                    status = 206
                except ValueError:
                    self.send_response(416); self.send_header('Content-Range', f'bytes */{size}')
                    self.send_header('Content-Length', '0'); self.end_headers(); return
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(max(0, end-start+1)))
            self.send_header('Cache-Control', 'no-store')
            if status == 206: self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            with path.open('rb') as handle:
                handle.seek(start); remaining = end-start+1
                while remaining > 0:
                    chunk = handle.read(min(256*1024, remaining))
                    if not chunk: break
                    self.wfile.write(chunk); remaining -= len(chunk)

        def song(self, ident):
            song = app.find(ident)
            if app.jobs.active and app.jobs.get(app.jobs.active).get('song') == str(song):
                raise Conflict('Wait for separation to finish before listening')
            return song

        def do_GET(self): self.dispatch('GET')
        def do_POST(self): self.dispatch('POST')
        def do_DELETE(self): self.dispatch('DELETE')

        def dispatch(self, method):
            if not self.local(): return
            parsed = urlparse(self.path); path = parsed.path
            query = parse_qs(parsed.query)
            get = lambda name, default='': query.get(name, [default])[0]
            try:
                if method == 'GET':
                    if path in ('/', '/index.html', '/app.js', '/app.css'):
                        name = 'index.html' if path == '/' else path[1:]
                        mime = {'index.html': 'text/html; charset=utf-8', 'app.js': 'text/javascript', 'app.css': 'text/css'}[name]
                        self.file(ROOT/'viewer'/name, mime)
                    elif path == '/api/health': self.json({'app': 'Track Separator', 'version': '0.4.0', 'instance': app.instance, 'ready': True})
                    elif path == '/api/library': self.json({'songs': app.songs(), 'settings': app.settings})
                    elif path == '/api/setup': self.json(models.status(app.home/'models'))
                    elif path == '/api/jobs': self.json(app.jobs.get(get('id')) if get('id') else {'jobs': app.jobs.list(), 'active': app.jobs.active})
                    elif path == '/api/trash': self.json({'items': app.trash_list()})
                    elif path == '/api/audio':
                        song = self.song(get('id')); stem = get('stem')
                        if stem not in (*STEMS, 'input'): raise ValueError('Choose an existing stem')
                        target = song/'input.wav' if stem == 'input' else song/'stems'/f'{stem}.wav'
                        if target.is_symlink() or song.resolve() not in target.resolve().parents: raise ValueError('Invalid audio location')
                        self.file(target, 'audio/wav')
                    else: self.json({'error': 'Not found'}, 404)
                elif method == 'POST':
                    kind = self.headers.get('Content-Type', '').split(';')[0].strip().lower()
                    length = int(self.headers.get('Content-Length') or 0)
                    if self.headers.get('Transfer-Encoding'): raise ValueError('Unsupported transfer encoding')
                    if path == '/api/import':
                        if kind != 'application/octet-stream' or self.headers.get('X-Track-Separator-Upload') != '1':
                            raise ValueError('Use the app file importer')
                        self.json(app.imported(get('filename'), self.rfile, length), 201)
                        return
                    if kind != 'application/json' or not 0 < length <= 1000000: raise ValueError('Send a JSON object')
                    payload = json.loads(self.rfile.read(length).decode('utf-8'))
                    if not isinstance(payload, dict): raise ValueError('Send a JSON object')
                    if path == '/api/separate': self.json(app.separate(payload.get('id')), 202)
                    elif path == '/api/open-folder': self.json(app.open_stems_folder(payload.get('id')))
                    elif path == '/api/setup': self.json(app.jobs.start(kind='setup'), 202)
                    elif path == '/api/jobs/cancel': self.json(app.jobs.cancel(payload.get('id')), 202)
                    elif path == '/api/jobs/retry': self.json(app.jobs.retry(payload.get('id')), 202)
                    elif path == '/api/settings': self.json(app.change_library(payload.get('library')))
                    elif path == '/api/trash/restore': self.json(app.restore(payload.get('ticket')))
                    elif path == '/api/shutdown':
                        self.json({'stopping': True})
                        threading.Thread(target=self.server.shutdown, daemon=True).start()
                    else: self.json({'error': 'Not found'}, 404)
                elif method == 'DELETE' and path == '/api/tracks':
                    self.json({'ticket': app.move_to_trash(get('id'))})
                else: self.json({'error': 'Not found'}, 404)
            except Conflict as exc: self.json({'error': str(exc)}, 409)
            except FileNotFoundError as exc: self.json({'error': str(exc)}, 404)
            except (ValueError, KeyError, TypeError, UnicodeError) as exc: self.json({'error': str(exc)}, 400)
            except subprocess.TimeoutExpired: self.json({'error': 'Audio inspection timed out'}, 400)
            except (BrokenPipeError, ConnectionResetError): pass
            except OSError as exc: self.json({'error': str(exc)}, 500)

        def log_message(self, fmt, *args):
            print('%s %s' % (self.address_string(), fmt % args), flush=True)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    return server
