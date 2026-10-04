# Track Separator

A local Windows app that separates a track into **vocals, drums, bass, guitar,
piano, and other**. Import one file, separate it, listen to individual stems,
and open the folder containing the full-quality WAV stems. No account, API key, cloud inference,
chord analysis, or MIDI export.

## Open the app

Download `TrackSeparator-Setup.exe` from [Releases](https://github.com/MDFX03-ctrl/TrackSeparator/releases),
install it, then open **Track Separator**
from the Start menu. Or keep the entire `dist/TrackSeparator` folder together
and double-click `TrackSeparator.exe`. `start-app.bat` opens the new bundle.
The runtime and FFmpeg are bundled; no Python, Node, or FFmpeg installation is
required. Windows 11 x64 is the initial target.

## Use it

1. Expand **Model setup** and choose **Download model** once. The explicit
   download is about 52 MB and verifies a pinned full SHA-256 checksum.
2. Choose or drop one audio file up to 15 minutes long. Supported formats:
   WAV, MP3, M4A, AAC, OGG, FLAC, AIFF, and WMA. Separation starts automatically
   when the model is ready and no other job is running; otherwise choose
   **Separate** in the track list.
3. Wait for the six stems. CPU processing can take longer than the audio.
   **Cancel** stops the worker; **Retry** resumes matching completed output
   or starts separation again. Closing the browser leaves processing running.
4. Choose **Open stems**, select a stem in **Listen to**, and use the audio
   player. The six WAVs are already saved locally. **Open stems folder** opens
   their existing folder in File Explorer; no download or extra copy is needed.

**Library and settings** chooses another library folder without moving the old
one. **Remove** moves a track to recoverable trash; **Show trash** and **Restore**
bring it back. **Quit app** stops the server and processing.

New installations use `%LOCALAPPDATA%/TrackSeparator`. When an earlier Music
Digest Chords data directory exists and no new data directory exists, the app
reuses it to preserve the library, settings, and local model. Existing separated
stems remain available. Upgrades and uninstall preserve audio libraries.
Opening Track Separator automatically closes an idle earlier app that holds
the shared library lock. An active earlier job must finish or be cancelled first.

## Source development

The app is `trackseparator/`; the interface is `viewer/`. The repository contains
source and build scripts. Installers, runtime bundles, model weights, and personal
audio are excluded. [Build instructions](build/README.md) describe release builds.

Use Python 3.11 x64 and provide FFmpeg on PATH. Create a virtual environment and
install the pinned CPU dependencies:

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install torch==2.5.1+cpu torchaudio==2.5.1+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r build/requirements-lock.txt
python -m trackseparator doctor
python -m trackseparator app
```

`TRACK_SEPARATOR_DATA_HOME` or `app --data-home FOLDER` selects isolated data.
The previous `MDCHORD_DATA_HOME` override is accepted for compatibility.

## Uninstall

Use Windows Installed apps or run `unins000.exe` in the installation folder.
The uninstaller closes the installed app, removes program files and generated
runtime caches, and removes the empty installation folder. Models, settings,
audio, and stems outside that folder are preserved. Generated uninstallers
belong to their installation and are not distributed as standalone files.

## Credits and license

This project packages a local Windows interface, library management, separation
jobs, stem playback, and installer workflow. The separation engine and
`htdemucs_6s` model are from [Demucs](https://github.com/facebookresearch/demucs).
Demucs runs locally on the CPU; the model is downloaded during explicit setup.

Track Separator evolved from Music Digest Chords. Application source is
MIT licensed; existing contributor attribution is retained in [LICENSE](LICENSE).
Bundled dependencies have their own licenses; see [THIRD-PARTY.md](THIRD-PARTY.md).
