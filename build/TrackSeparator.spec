from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent
datas = [(str(root/'viewer'), 'viewer'), (str(root/'LICENSE'), '.'),
         (str(root/'THIRD-PARTY.md'), '.'), (str(root/'build/vendor'), 'bin'),
         (str(root/'build/notices'), 'notices')]
binaries, hidden = [], []
for package in ('demucs', 'soundfile', 'julius', 'openunmix'):
    d, b, h = collect_all(package)
    datas += d; binaries += b; hidden += h
a = Analysis([str(root/'build/entry.py')], pathex=[str(root)], binaries=binaries,
             datas=datas, hiddenimports=hidden,
             excludes=['mdchord', 'librosa', 'pedalboard', 'mido', 'scipy', 'sklearn',
                       'matplotlib', 'IPython', 'pytest', 'tensorboard'])
a.datas = [row for row in a.datas if '__pycache__' not in Path(row[1]).parts
           and Path(row[1]).suffix not in ('.nbc', '.nbi', '.pyc')]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='TrackSeparator', console=False)
coll = COLLECT(exe, a.binaries, a.datas, name='TrackSeparator')
