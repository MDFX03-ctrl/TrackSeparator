"""Explicit one-time download; analysis uses a verified local repository."""
import hashlib
import os
import urllib.request
from pathlib import Path
from trackseparator.storage import atomic_json, read

MODEL = 'htdemucs_6s'
FILENAME = '5c90dfd2-34c22ccb.th'
URL = 'https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/' + FILENAME
# Full SHA-256 pinned from the verified upstream htdemucs_6s checkpoint.
CHECKSUM = '34c22ccb381c6f9fdbf324f04e1e2fe21aaaf293f5ded163a162697ff9a02ddd'


def digest_file(path):
    sha = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def status(folder, verify=False):
    folder = Path(folder)
    receipt = read(folder / 'receipt.json', {})
    path = folder / FILENAME
    ready = path.is_file() and (folder / (MODEL + '.yaml')).is_file() and receipt.get('model') == MODEL
    if ready:
        ready = path.stat().st_size == receipt.get('bytes') and str(receipt.get('sha256', '')).startswith(CHECKSUM)
    if ready and verify:
        ready = digest_file(path) == receipt['sha256']
    return {'ready': bool(ready), 'model': MODEL, 'message': 'Ready for offline analysis' if ready else 'Download or repair the separation model before analysis'}


def install(folder, progress=lambda value: None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / FILENAME
    partial = folder / (FILENAME + '.partial')
    try:
        with urllib.request.urlopen(URL, timeout=60) as response, partial.open('wb') as out:
            total = int(response.headers.get('Content-Length') or 0)
            received = 0
            for chunk in iter(lambda: response.read(1024 * 1024), b''):
                out.write(chunk); received += len(chunk)
                progress({'downloaded': received, 'total': total})
            out.flush(); os.fsync(out.fileno())
        sha = digest_file(partial)
        if sha != CHECKSUM:
            raise ValueError('Model checksum failed; the downloaded file was not installed')
        os.replace(partial, target)
        config = folder / (MODEL + '.yaml')
        temporary = config.with_suffix('.yaml.tmp')
        temporary.write_text("models: ['5c90dfd2']\n", encoding='utf-8')
        os.replace(temporary, config)
        atomic_json(folder / 'receipt.json', {'model': MODEL, 'sha256': sha, 'bytes': target.stat().st_size, 'url': URL})
    finally:
        partial.unlink(missing_ok=True)
    return status(folder, verify=True)
