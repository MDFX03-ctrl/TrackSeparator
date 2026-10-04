"""Atomic documents, revisions and process-local serialization."""
import json
import os
import tempfile
import threading
import time
from pathlib import Path

LOCK = threading.RLock()


class Conflict(ValueError):
    pass


def read(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with path.open(encoding='utf-8-sig') as handle:
        return json.load(handle)


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        # Windows readers and antivirus scanners may briefly hold the destination.
        # Keep the old complete document visible until replacement succeeds.
        for attempt in range(9):
            try:
                os.replace(name, path)
                break
            except PermissionError:
                if attempt == 8: raise
                time.sleep(min(.01 * 2**attempt, .2))
    finally:
        if os.path.exists(name):
            os.unlink(name)
