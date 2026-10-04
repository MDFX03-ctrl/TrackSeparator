"""Separate audio into six aligned WAV stems using a verified local model."""
import shutil
import subprocess
from pathlib import Path
from trackseparator.runtime import ffmpeg, hidden_process
from trackseparator.storage import atomic_json

STEMS = ('vocals', 'drums', 'bass', 'guitar', 'piano', 'other')


def separate(source, song, repository):
    import numpy as np
    import soundfile as sf
    from trackseparator import models

    song = Path(song)
    if not models.status(repository, verify=True)['ready']:
        raise ValueError('Separation model is missing or corrupt. Download or repair it, then retry.')
    if shutil.disk_usage(song).free < 1024**3 + 900 * 44100 * 4 * 7:
        raise ValueError('Not enough disk space for separated audio')
    wav = song/'input.wav'
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-protocol_whitelist', 'file,pipe',
                    '-i', str(source), '-vn', '-t', '901', '-ac', '2', '-ar', '44100', str(wav)],
                   check=True, **hidden_process())
    if not 0 < sf.info(wav).duration <= 900:
        raise ValueError('Audio must be at most 15 minutes long')
    with sf.SoundFile(wav) as handle:
        silent = all(not np.any(block) for block in handle.blocks(blocksize=44100*30, dtype='float32'))
    temporary = song/'separated'/models.MODEL/'input'
    if silent:
        temporary.mkdir(parents=True, exist_ok=True)
        for name in STEMS: shutil.copyfile(wav, temporary/f'{name}.wav')
    else:
        import torch
        from demucs.separate import main
        torch.set_num_threads(min(8, max(1, (torch.get_num_threads() - 2))))
        main(['-n', models.MODEL, '--repo', str(repository), '-d', 'cpu', '--shifts', '0', '-j', '1',
              '-o', str(song/'separated'), str(wav)])
    (song/'stems').mkdir(exist_ok=True)
    rows = []
    for name in STEMS:
        path = temporary/f'{name}.wav'
        # Stream level measurements instead of loading a full stem into memory.
        total, samples = 0.0, 0
        with sf.SoundFile(path) as handle:
            duration = len(handle)/handle.samplerate
            for block in handle.blocks(blocksize=44100*30, dtype='float32', always_2d=True):
                total += float(np.sum(np.square(block), dtype=np.float64))
                samples += block.size
        rows.append({'kind': name, 'file': f'stems/{name}.wav', 'duration': duration,
                     'rms_db': round(10 * np.log10(total/max(1, samples) + 1e-12), 1)})
        path.replace(song/'stems'/f'{name}.wav')
    atomic_json(song/'manifest.json', {'version': 1, 'model': models.MODEL, 'stems': rows})
    # This is a fixed temporary output folder within the managed song directory.
    shutil.rmtree(song/'separated', ignore_errors=True)
