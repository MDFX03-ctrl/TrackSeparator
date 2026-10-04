"""One isolated worker, persisted jobs, cancellation and explicit retry."""
import os
import subprocess
import threading
import time
import traceback
import uuid
from pathlib import Path
from trackseparator.runtime import ROOT, worker_command, hidden_process
from trackseparator.storage import LOCK, Conflict, atomic_json, read
from trackseparator.separation import STEMS

TERMINAL = ('completed', 'failed', 'cancelled', 'interrupted')


def stop_process(process):
    if process.poll() is not None: return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **hidden_process())
    else:
        process.terminate()
    try: process.wait(timeout=10)
    except subprocess.TimeoutExpired: process.kill(); process.wait()


class Jobs:
    def __init__(self, home):
        self.home = Path(home)
        self.directory = self.home/'jobs'; self.directory.mkdir(parents=True, exist_ok=True)
        self.process = self.active = self.thread = None
        self.closed = False
        for path in self.directory.glob('*.json'):
            doc = read(path)
            if doc.get('kind') in ('separation', 'setup') and doc['status'] not in TERMINAL:
                doc.update(status='interrupted', error='Processing stopped. Choose Retry to continue.', finished=time.time())
                atomic_json(path, doc)

    def list(self):
        rows = (self.get(p.stem) for p in self.directory.glob('*.json'))
        return sorted((r for r in rows if r.get('kind') in ('separation', 'setup')), key=lambda r: r['created'], reverse=True)

    def get(self, ident):
        if not isinstance(ident, str) or not ident.isalnum(): raise ValueError('Invalid job ID')
        doc = read(self.directory/(ident+'.json'))
        if not doc: raise FileNotFoundError('Job not found')
        if self.active == ident and doc['status'] == 'completed' and self.process and self.process.poll() is None:
            doc = {**doc, 'status': 'running', 'stage': 'finishing'}
        return doc

    def start(self, song=None, kind='separation'):
        with LOCK:
            if self.active or self.closed: raise Conflict('Another job is running')
            if kind not in ('separation', 'setup'): raise ValueError('Unknown job type')
            ident = uuid.uuid4().hex
            doc = {'id': ident, 'kind': kind, 'song': str(song) if song else None, 'status': 'queued',
                   'stage': 'waiting', 'created': time.time(), 'started': None, 'finished': None,
                   'progress': {}, 'error': None, 'attempt': 1, 'receipt': None}
            atomic_json(self.directory/(ident+'.json'), doc)
            self._launch(ident)
            return doc

    def retry(self, ident):
        with LOCK:
            if self.active or self.closed: raise Conflict('Another job is running')
            doc = self.get(ident)
            if doc.get('kind') not in ('separation', 'setup'): raise ValueError('Select this track and start separation again')
            if doc['status'] not in ('failed', 'cancelled', 'interrupted'): raise ValueError('Only stopped jobs can be retried')
            if doc['kind'] == 'separation' and not Path(doc['song']).is_dir():
                raise ValueError('Restore the removed track before retrying')
            doc.update(status='queued', error=None, finished=None, started=None, attempt=doc.get('attempt', 1)+1)
            atomic_json(self.directory/(ident+'.json'), doc)
            (self.directory/(ident+'.cancel')).unlink(missing_ok=True)
            self._launch(ident)
            return doc

    def _launch(self, ident):
        self.active = ident
        self.thread = threading.Thread(target=self._run, args=(ident,), daemon=True)
        self.thread.start()

    def _run(self, ident):
        path = self.directory/(ident+'.json')
        logs = self.home/'logs'; logs.mkdir(exist_ok=True)
        try:
            with (logs/(ident+'.log')).open('ab') as log:
                with LOCK:
                    if path.with_suffix('.cancel').exists(): raise InterruptedError('Cancelled')
                    self.process = subprocess.Popen(worker_command('job', path, self.home), cwd=ROOT,
                        stdout=log, stderr=log,
                        env=dict(os.environ, TRACK_SEPARATOR_DATA_HOME=str(self.home),
                                 TRACK_SEPARATOR_WORKER_LOG=str(logs/(ident+'.log'))), **hidden_process())
                code = self.process.wait()
            with LOCK:
                doc = read(path)
                if path.with_suffix('.cancel').exists():
                    doc.update(status='cancelled', error='Cancelled. Choose Retry to continue.', finished=time.time())
                elif doc['status'] not in TERMINAL:
                    doc.update(status='failed', error=f'Worker exited with code {code}. See job log.', finished=time.time())
                atomic_json(path, doc)
        except Exception as exc:
            with LOCK:
                doc = read(path)
                doc.update(status='cancelled' if isinstance(exc, InterruptedError) else 'failed', error=str(exc), finished=time.time())
                atomic_json(path, doc)
        finally:
            with LOCK: self.process = self.active = None

    def cancel(self, ident):
        with LOCK:
            if self.active != ident: raise ValueError('This job is not running')
            if read(self.directory/(ident+'.json'))['status'] == 'completed': raise ValueError('This job has already finished')
            (self.directory/(ident+'.cancel')).touch()
            process = self.process
        if process: stop_process(process)
        return self.get(ident)

    def close(self):
        self.closed = True
        if self.active:
            try: self.cancel(self.active)
            except ValueError: pass
        if self.thread: self.thread.join(timeout=15)


def receipt(song):
    names = ['manifest.json', 'input.wav'] + [f'stems/{name}.wav' for name in STEMS]
    if not all((song/name).is_file() for name in names): return None
    return {name: [(song/name).stat().st_size, (song/name).stat().st_mtime_ns] for name in names}


def run_job(path, home):
    from trackseparator import models
    from trackseparator.separation import separate
    path, home = Path(path), Path(home)
    job = read(path)
    def update(stage, progress=None):
        if path.with_suffix('.cancel').exists(): raise InterruptedError('Cancelled')
        job.update(stage=stage, progress=progress or {})
        atomic_json(path, job)
    try:
        job.update(status='running', started=time.time(), error=None)
        update('starting')
        if job['kind'] == 'setup':
            models.install(home/'models', lambda p: update('download model', p))
        elif job['kind'] == 'separation':
            song = Path(job['song'])
            if not song.is_dir(): raise ValueError('Restore the removed track before retrying')
            update('separating')
            saved = job.get('receipt')
            if not saved or saved != receipt(song):
                job['receipt'] = None; atomic_json(path, job)
                source = read(song/'source.json', {})
                filename = source.get('file', '')
                if not filename or Path(filename).name != filename: raise ValueError('Original audio is missing')
                separate(song/filename, song, home/'models')
                job['receipt'] = receipt(song)
                atomic_json(path, job)
        else: raise ValueError('Unknown job type')
        update('finishing')
        job.update(status='completed', stage='done', finished=time.time(), progress={})
        atomic_json(path, job)
        return 0
    except BaseException as exc:
        job.update(status='cancelled' if isinstance(exc, InterruptedError) else 'failed', error=str(exc) or exc.__class__.__name__, finished=time.time())
        atomic_json(path, job)
        traceback.print_exc()
        return 1
