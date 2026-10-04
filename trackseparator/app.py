"""Managed library and single-instance browser launcher."""
import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
import urllib.request
import webbrowser
from pathlib import Path
from trackseparator import models
from trackseparator.jobs import Jobs
from trackseparator.separation import STEMS
from trackseparator.runtime import ROOT, data_home, ffmpeg, hidden_process
from trackseparator.storage import LOCK, Conflict, atomic_json, read


class App:
    def __init__(self, home=None):
        self.home = Path(home or data_home()).resolve()
        self.home.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.home / 'settings.json'
        self.settings = read(self.settings_path, {'version': 1, 'library': str(self.home / 'library')})
        self.library = Path(self.settings['library']).resolve(); self.library.mkdir(parents=True, exist_ok=True)
        self.trash = self.home / 'trash'; self.trash.mkdir(exist_ok=True)
        self.jobs = Jobs(self.home)
        self.instance = uuid.uuid4().hex
        self.started = time.time()
        self.server = None

    def find(self, ident):
        if not isinstance(ident, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', ident): raise ValueError('Invalid song ID')
        song = self.library / ident
        if song.is_symlink() or not song.is_dir() or song.resolve().parent != self.library:
            raise FileNotFoundError('Song not found')
        return song

    def songs(self):
        rows = []
        for song in sorted(self.library.iterdir()):
            if song.name.startswith('.') or song.is_symlink() or not song.is_dir(): continue
            if not (song/'source.json').exists() and not (song/'manifest.json').exists(): continue
            try:
                source = read(song/'source.json', {})
                manifest = read(song/'manifest.json', {})
                stems = [name for name in STEMS if (song/'stems'/f'{name}.wav').is_file()]
                rows.append({'id': song.name, 'title': source.get('title') or song.name,
                             'duration': source.get('duration') or next((s.get('duration') for s in manifest.get('stems', [])), None),
                             'folder': str(song/'stems'),
                             'stems': stems, 'ready': len(stems) == len(STEMS) and bool(manifest)})
            except (ValueError, OSError) as exc:
                rows.append({'id': song.name, 'title': song.name, 'error': str(exc), 'ready': False, 'stems': []})
        return rows

    def open_stems_folder(self, ident):
        with LOCK:
            song = self.find(ident)
            folder = song/'stems'
            if folder.is_symlink() or not folder.is_dir() or folder.resolve().parent != song.resolve():
                raise FileNotFoundError('Stems folder not found')
            if self.jobs.active and self.jobs.get(self.jobs.active).get('song') == str(song):
                raise Conflict('Wait for separation to finish before opening the stems folder')
            os.startfile(str(folder))
            return {'folder': str(folder)}

    def separate(self, ident):
        with LOCK:
            song = self.find(ident)
            source = read(song/'source.json', {})
            filename = source.get('file', '')
            if not filename or Path(filename).name != filename or not (song/filename).is_file():
                raise ValueError('Import the original audio before separating this track')
            if not models.status(self.home/'models')['ready']:
                raise ValueError('Download or repair the separation model first')
            return self.jobs.start(song)

    def imported(self, filename, stream, length):
        filename = filename.replace('\\', '/').split('/')[-1]
        suffix = Path(filename).suffix.lower()
        if suffix not in ('.wav', '.mp3', '.m4a', '.aac', '.ogg', '.flac', '.aiff', '.aif', '.wma'):
            raise ValueError('Choose a supported audio file')
        if not 0 < length <= 2 * 1024**3: raise ValueError('Audio file must be between 1 byte and 2 GB')
        if shutil.disk_usage(self.library).free < length * 2 + 1024**3: raise ValueError('Not enough disk space to import this song')
        ident = uuid.uuid4().hex
        staging = self.library / ('.import-' + ident); staging.mkdir()
        source = staging / ('source' + suffix)
        try:
            with source.open('wb') as out:
                remaining = length
                while remaining:
                    chunk = stream.read(min(256 * 1024, remaining))
                    if not chunk: raise ValueError('Upload was interrupted; choose the file again')
                    out.write(chunk); remaining -= len(chunk)
            formats = {'.wav':'wav', '.mp3':'mp3', '.m4a':'mov', '.aac':'aac', '.ogg':'ogg', '.flac':'flac', '.aiff':'aiff', '.aif':'aiff', '.wma':'asf'}
            result = subprocess.run([ffmpeg(), '-hide_banner', '-protocol_whitelist', 'file,pipe', '-f', formats[suffix], '-i', str(source)], capture_output=True, encoding='utf-8', errors='replace', timeout=30, **hidden_process())
            info = result.stderr
            duration = re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)', info)
            if not duration or not re.search(r'Stream .*Audio:', info): raise ValueError('The file could not be decoded as audio')
            seconds = int(duration[1])*3600 + int(duration[2])*60 + float(duration[3])
            if not 0 < seconds <= 900: raise ValueError('Choose audio up to 15 minutes long')
            atomic_json(staging / 'source.json', {'version': 1, 'file': source.name, 'filename': filename, 'title': Path(filename).stem,
                                                'duration': seconds, 'created': time.time()})
            os.replace(staging, self.library / ident)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return {'id': ident, 'title': Path(filename).stem, 'duration': seconds}

    def move_to_trash(self, ident):
        with LOCK:
            song = self.find(ident)
            if self.jobs.active and self.jobs.get(self.jobs.active).get('song') == str(song): raise Conflict('Cancel this songâ€™s job before removing it')
            ticket = uuid.uuid4().hex
            target = self.trash / ticket
            # Persist recovery information before the song leaves the library.
            atomic_json(song / '.trash.json', {'id': ident, 'removed': time.time(), 'title': read(song/'source.json', {}).get('title', ident)})
            # shutil.move supports a library located on another drive.
            shutil.move(str(song), str(target))
            return ticket

    def trash_list(self):
        return [dict(read(p / '.trash.json'), ticket=p.name) for p in self.trash.iterdir() if p.is_dir() and (p/'.trash.json').exists()]

    def restore(self, ticket):
        if not re.fullmatch(r'[a-f0-9]{32}', str(ticket)): raise ValueError('Invalid trash item')
        with LOCK:
            source = self.trash / ticket
            doc = read(source / '.trash.json')
            if not doc: raise FileNotFoundError('Trash item not found')
            ident = doc['id']
            target = self.library / ident
            if target.exists(): ident = uuid.uuid4().hex; target = self.library / ident
            shutil.move(str(source), str(target)); (target / '.trash.json').unlink()
            return {'id': ident}

    def change_library(self, path):
        with LOCK:
            if self.jobs.active: raise Conflict('Wait for processing to finish before changing libraries')
            if not isinstance(path, str) or not path.strip(): raise ValueError('Choose a library folder')
            library = Path(path).expanduser().resolve()
            if library == ROOT or ROOT in library.parents: raise ValueError('Use a data folder outside the installed app')
            library.mkdir(parents=True, exist_ok=True)
            settings = {**self.settings, 'library': str(library)}
            atomic_json(self.settings_path, settings)
            self.settings = settings
            self.library = library
            return self.settings

    def close(self):
        self.jobs.close()


def _claim_instance(lockfile):
    lockfile.seek(0)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lockfile.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _instance_request(url, route, payload=None):
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(url + 'api/' + route, data=body,
                                     headers={'Content-Type': 'application/json'} if body is not None else {})
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.load(response)


def launch(home=None, browser=True):
    home = Path(home or data_home()).resolve(); home.mkdir(parents=True, exist_ok=True)
    # OS-owned lock is released automatically after crashes.
    lockfile = (home / 'instance.lock').open('a+b')
    lockfile.seek(0); lockfile.write(b'0'); lockfile.flush(); lockfile.seek(0)
    owner = False
    try:
        owner = _claim_instance(lockfile)
        if not owner:
            handing_over = False
            for _ in range(100):
                if _claim_instance(lockfile):
                    owner = True
                    break
                record = read(home / 'instance.json', {})
                url = record.get('url', '')
                if not handing_over and re.fullmatch(r'http://127\.0\.0\.1:\d+/', url):
                    try:
                        health = _instance_request(url, 'health')
                        if health.get('instance') == record.get('instance'):
                            if health.get('app') == 'Track Separator':
                                if browser: webbrowser.open(url)
                                return 0
                            if health.get('app') == 'MusicDigestChords':
                                if _instance_request(url, 'jobs').get('active'):
                                    raise RuntimeError('The previous app is processing a track. Let it finish or cancel its job, then open Track Separator again.')
                                _instance_request(url, 'shutdown', {})
                                handing_over = True
                    except (OSError, ValueError): pass
                time.sleep(.1)
            if not owner:
                raise RuntimeError('The app is still starting or stopping. Try launching it again.')
        app = App(home)
        from trackseparator.http import make_server
        server = make_server(app, 0)
        app.server = server
        url = f'http://127.0.0.1:{server.server_address[1]}/'
        atomic_json(home / 'instance.json', {'url': url, 'instance': app.instance})
        if browser: webbrowser.open(url)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
        finally: app.close(); server.server_close(); (home/'instance.json').unlink(missing_ok=True)
    finally:
        lockfile.close()
    return 0
