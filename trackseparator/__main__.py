"""Launch Track Separator or check its local runtime."""
import argparse
import sys
from trackseparator.runtime import data_home, ffmpeg, redirect_output


def main(argv=None):
    redirect_output(argv)
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv: argv = ['app']
    if argv[0] == 'worker':
        from trackseparator.jobs import run_job
        if len(argv) != 4 or argv[1] != 'job': raise ValueError('Invalid worker command')
        return run_job(argv[2], argv[3])
    parser = argparse.ArgumentParser(prog='trackseparator')
    sub = parser.add_subparsers(dest='command', required=True)
    app = sub.add_parser('app', help='Open Track Separator')
    app.add_argument('--data-home')
    app.add_argument('--no-browser', action='store_true')
    sub.add_parser('setup', help='Download and verify the separation model')
    sub.add_parser('doctor', help='Check the local runtime')
    args = parser.parse_args(argv)
    if args.command == 'app':
        from trackseparator.app import launch
        return launch(args.data_home, browser=not args.no_browser)
    if args.command == 'setup':
        from trackseparator.models import install
        install(data_home()/'models')
        return 0
    import subprocess
    from trackseparator.runtime import hidden_process
    subprocess.run([ffmpeg(), '-version'], check=True, stdout=subprocess.DEVNULL, **hidden_process())
    for name in ('numpy', 'soundfile', 'torch', 'demucs'):
        __import__(name)
        print(f'{name}: import ok')
    print('Track Separator: local runtime ready')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
