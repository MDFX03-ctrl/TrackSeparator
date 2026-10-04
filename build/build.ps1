param([string]$Python = 'python', [string]$FFmpeg = '', [switch]$Installer)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
& $Python -c "import torch,struct; assert struct.calcsize('P') == 8; assert torch.__version__ == '2.5.1+cpu', 'Install the pinned CPU PyTorch build'"
if ($LASTEXITCODE) { throw 'Use the pinned Windows x64 CPU build environment' }
if (-not $FFmpeg) { $FFmpeg = (Get-Command ffmpeg -ErrorAction Stop).Source }
New-Item -ItemType Directory -Force 'build/vendor','build/notices' | Out-Null
Copy-Item -LiteralPath $FFmpeg -Destination 'build/vendor/ffmpeg.exe'
$ffmpegRoot = Split-Path -Parent (Split-Path -Parent $FFmpeg)
$ffmpegNotices = Join-Path $projectRoot 'build/notices/FFmpeg'
New-Item -ItemType Directory -Force $ffmpegNotices | Out-Null
foreach ($name in @('LICENSE','README.txt')) {
    $notice = Join-Path $ffmpegRoot $name
    if (-not (Test-Path -LiteralPath $notice)) { throw ('Missing FFmpeg distribution notice: '+$name) }
    Copy-Item -LiteralPath $notice -Destination (Join-Path $ffmpegNotices $name)
}
# ffprobe is useful for diagnostics, but the app does not require it.
$probe = Join-Path (Split-Path -Parent $FFmpeg) 'ffprobe.exe'
if (Test-Path -LiteralPath $probe) { Copy-Item -LiteralPath $probe -Destination 'build/vendor/ffprobe.exe' }
& $Python 'build/notices.py'
if ($LASTEXITCODE) { throw 'Dependency notice generation failed' }
& $FFmpeg -version | Set-Content 'build/notices/FFmpeg/BUILD.txt' -Encoding utf8
& $Python -m PyInstaller --noconfirm --workpath '.build' --distpath 'dist' 'build/TrackSeparator.spec'
if ($LASTEXITCODE) { throw 'App bundle build failed' }
& "$PSScriptRoot\build-uninstall.ps1"
Copy-Item -LiteralPath "$projectRoot\uninstall.exe" -Destination "$projectRoot\dist\TrackSeparator\uninstall.exe"
if ($Installer) {
    & ISCC 'build/installer.iss'
    if ($LASTEXITCODE) { throw 'Installer build failed' }
}
