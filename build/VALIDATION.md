# Track Separator validation

Date: 2026-10-04. Track Separator 0.4.0 replaces the former chord application.
The active package contains only library management, local model setup,
separation jobs, audio streaming, and local stem-folder access. Existing user
audio and libraries are preserved. Earlier unit and browser tests were run in
the development workspace; those test suites are not included in this minimal
source repository.

- All 30 separation-focused unit/integration tests pass. Coverage includes
  Unicode imports, library persistence, recoverable trash, failed writes,
  cancellation, explicit crash retry, complete-output receipts, silence,
  local stem paths, folder actions without file copies, audio ranges, and
  loopback request guards.
- Startup tests cover automatic handover from an idle legacy app, protection
  of its active jobs, and reuse of an already-running Track Separator instance.
- The rebuilt executable passes a real two-process legacy handover test,
  retaining the library and original audio. Its second launch reuses the
  running instance. Launch with the existing default data directory succeeds,
  retaining the existing track library and ready local model.
- `python -m trackseparator doctor` and JavaScript syntax checks pass.
- The packaged smoke test passes with Python, Node, and system FFmpeg absent
  from the app and worker PATH. A synthetic clip produces six aligned stems;
  no chord, timing, review, MIDI, or preview analysis files are generated.
- Installed Edge tests pass against the new packaged executable: native audio
  playback and seeking, all six stem controls, local folder controls, responsive
  layout, reload, and trash restoration. No page errors or external requests.
- Inspection of the executable's module archive confirms that the old chord
  package, Librosa, Pedalboard, Mido, SciPy, and scikit-learn are absent. Sampled
  instruments are absent from the application folder.

Clean Windows VM installation and upgrade have not been repeated for this
release. Synthetic checks do not establish separation quality.

The local-folder revision removes download/ZIP controls and their API route.
The app reports the existing stems directory and uses Windows folder opening
only when the user clicks Open stems folder. Tests mock the OS opening action
and verify the target directory and unchanged stem files.

Installer 0.4.1 was installed in an isolated Windows test directory. With the
app running and an untracked generated Python cache in its private runtime,
the generated uninstaller stopped the installed processes and removed the
entire installation directory and uninstall registration. Audio and stem
sentinels outside the installation directory retained their original hashes.
The reproducible check is `build/uninstall-smoke.ps1`.
