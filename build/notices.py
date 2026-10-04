"""Collect installed dependency metadata and license texts into the distribution."""
import importlib.metadata
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
out = root / 'notices'; out.mkdir(exist_ok=True)
rows = []
python_license = Path(sys.base_prefix) / 'LICENSE.txt'
if not python_license.is_file(): raise FileNotFoundError('Build environment must include the Python distribution license')
(out/'Python').mkdir(exist_ok=True)
shutil.copyfile(python_license, out/'Python'/'LICENSE.txt')
rows.append(f'Python {sys.version.split()[0]}\nLicense: Python Software Foundation\nSource: https://www.python.org/downloads/source/\n')
for distribution in sorted(importlib.metadata.distributions(), key=lambda d: d.metadata['Name'].lower()):
    name = distribution.metadata['Name']
    rows.append(f'{name}=={distribution.version}\nLicense: {distribution.metadata.get("License", distribution.metadata.get("License-Expression", "See package license"))}\nSource: {distribution.metadata.get("Home-page", "") }\n')
    for file in distribution.files or []:
        if any(token in file.name.lower() for token in ('license', 'copying', 'notice')):
            source = Path(distribution.locate_file(file))
            if source.is_file():
                dest = out / name / str(file).replace('..', '_')
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
(out / 'DEPENDENCIES.txt').write_text('\n'.join(rows), encoding='utf-8')
