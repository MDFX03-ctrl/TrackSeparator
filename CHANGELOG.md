# Changelog

## 0.4.1 - 2026-10-04

- Local Windows track separation into vocals, drums, bass, guitar, piano, and other.
- Explicit model setup, CPU processing, cancellation, and retry.
- Stem playback and opening existing WAV folders without downloading copies.
- Library selection, recoverable trash, and restoration.
- Installer uninstallation closes the installed app and removes generated
  private runtime files and the empty program folder.
- Models, settings, audio, and stems outside the program folder are preserved.
- Source repository excludes generated bundles, models, and personal audio.

Validation: the packaged app was previously checked for import, six-stem
separation, audio streaming, and playback. The 0.4.1 installer was checked on
Windows with a running app and generated runtime-cache files: the program
folder and uninstall registration were removed, and audio/stem sentinels
remained unchanged. Separation quality depends on the source recording.
