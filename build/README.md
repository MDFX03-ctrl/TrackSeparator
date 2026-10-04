# Build Track Separator

Build on Windows x64 with Python 3.11 and the pinned CPU-only environment.

```
python -m pip install torch==2.5.1+cpu torchaudio==2.5.1+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r build/requirements-lock.txt
powershell -NoProfile -File build/build.ps1 -Python python -Installer
```

Provide FFmpeg on PATH or pass `-FFmpeg PATH`. Its distribution must include
`LICENSE` and `README.txt` beside `bin/`. The build copies notices and runtime
files, packages `trackseparator` and `viewer`, then creates the installer using
Inno Setup's `ISCC`. Neither the local legacy source archive nor user data ships.

Outputs: `dist/TrackSeparator/TrackSeparator.exe` and
`dist/installer/TrackSeparator-Setup.exe`. Keep the entire application folder
together. The installer is per-user, uses the existing application upgrade ID,
and preserves libraries on upgrade and uninstall.

Installer 0.4.1 closes processes launched from its exact installed executable
before removing files. Its generated `unins000.exe` also removes the private
`_internal` runtime and Python caches created after installation, then removes
the empty installation directory. Audio, stems, models, and settings outside
the installation directory are preserved. Unrelated user files placed in the
installation directory are preserved too. Install the updated setup over an
older copy to update its uninstaller; do not copy a generated `unins000.exe`
between installations, since it belongs with that installation's uninstall log.

Run `python -m trackseparator doctor` to check the local runtime.
`build/smoke.ps1` tests packaged import, separation, local stem files and folder paths, HTTP
seeking, and trash restoration using isolated data and no developer tools on
PATH. Copy an existing verified model into its data folder, or explicitly pass
`-Setup` for the online download.

`build/uninstall-smoke.ps1` verifies complete program removal with the app running,
generated cache cleanup, and preservation of audio and stems. It is restricted
to a disposable installation at `D:\Tools\TrackSeparator-UninstallTest` and
refuses to run if a different user installation is registered. Do not run it
against a daily-use installation. Historical validation is recorded in
`build/VALIDATION.md`; clean Windows VM checks remain separate.
