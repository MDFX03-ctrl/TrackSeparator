"""Read-only bundled assets and writable per-user state are separate."""
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))


def data_home():
    override = os.environ.get('TRACK_SEPARATOR_DATA_HOME') or os.environ.get('MDCHORD_DATA_HOME')
    base = Path(override) if override else Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.local' / 'share') / 'TrackSeparator'
    if not override and not base.exists():
        legacy = base.parent / 'MusicDigestChords'
        if legacy.exists(): base = legacy
    return base.resolve()


def ffmpeg():
    bundled = ROOT / 'bin' / 'ffmpeg.exe'
    return str(bundled) if bundled.is_file() else shutil.which('ffmpeg') or 'ffmpeg'


def worker_command(*args):
    if getattr(sys, 'frozen', False):
        return [sys.executable, 'worker', *map(str, args)]
    return [sys.executable, '-m', 'trackseparator', 'worker', *map(str, args)]


def hidden_process():
    import subprocess
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}


def redirect_output(argv=None):
    """Honor the chosen data folder before windowless startup writes any logs."""
    args = list(sys.argv[1:] if argv is None else argv)
    if '--data-home' in args:
        index = args.index('--data-home')
        if index + 1 < len(args): os.environ['TRACK_SEPARATOR_DATA_HOME'] = str(Path(args[index+1]).resolve())
    elif len(args) == 4 and args[:2] == ['worker', 'job']:
        os.environ['TRACK_SEPARATOR_DATA_HOME'] = str(Path(args[3]).resolve())
    os.environ['TORCH_HOME'] = str(data_home() / 'cache' / 'torch')
    if sys.stdout is None or sys.stderr is None:
        logs = data_home() / 'logs'; logs.mkdir(parents=True, exist_ok=True)
        stream = Path(os.environ.get('TRACK_SEPARATOR_WORKER_LOG', logs/'application.log')).open('a', encoding='utf-8', buffering=1)
        if sys.stdout is None: sys.stdout = stream
        if sys.stderr is None: sys.stderr = stream
