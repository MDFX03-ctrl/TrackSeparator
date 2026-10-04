param([string]$InstallDir = 'D:\Tools\TrackSeparator-UninstallTest')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$target = [IO.Path]::GetFullPath($InstallDir).TrimEnd('\')
if ($target -ne 'D:\Tools\TrackSeparator-UninstallTest') {
    throw 'This destructive uninstall test is restricted to D:\Tools\TrackSeparator-UninstallTest.'
}
$key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{6B7A3F72-45EB-4BCD-9E8A-04855EB302A1}_is1'
$registered = Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue
if ($registered -and $registered.InstallLocation.TrimEnd('\') -ne $target) {
    throw 'An existing user installation is registered. Do not run this test on a daily-use installation.'
}
if (Test-Path -LiteralPath $target) { throw 'Remove the previous isolated installation with its own uninstaller first.' }
$setup = Join-Path $projectRoot 'dist\installer\TrackSeparator-Setup.exe'
$data = Join-Path $projectRoot '.build\uninstall-test-data'
New-Item -ItemType Directory -Path $data -Force | Out-Null
$audio = Join-Path $data 'keep-audio.wav'
$stems = Join-Path $data 'keep-stems.wav'
Set-Content -LiteralPath $audio -Value 'uninstall audio preservation sentinel'
Set-Content -LiteralPath $stems -Value 'uninstall stem preservation sentinel'
$audioHash = (Get-FileHash -LiteralPath $audio).Hash
$stemsHash = (Get-FileHash -LiteralPath $stems).Hash
$install = Start-Process -FilePath $setup -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/CURRENTUSER',('/DIR='+$target) -WindowStyle Hidden -Wait -PassThru
if ($install.ExitCode) { throw ('Installation failed: '+$install.ExitCode) }
$cache = Join-Path $target '_internal\uninstall-test\__pycache__'
New-Item -ItemType Directory -Path $cache -Force | Out-Null
Set-Content -LiteralPath (Join-Path $cache 'generated.pyc') -Value 'generated after setup'
$app = Start-Process -FilePath (Join-Path $target 'TrackSeparator.exe') -ArgumentList 'app','--no-browser','--data-home',('"'+$data+'"') -WindowStyle Hidden -PassThru
$ready = $false
for ($attempt = 0; $attempt -lt 100; $attempt++) {
    try {
        $instance = Get-Content -LiteralPath (Join-Path $data 'instance.json') -Raw | ConvertFrom-Json
        $health = Invoke-RestMethod ($instance.url+'api/health')
        if ($health.ready -and $health.instance -eq $instance.instance) { $ready = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 200
}
if (-not $ready) { throw 'Test app did not start.' }
$uninstall = Start-Process -FilePath (Join-Path $target 'unins000.exe') -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="'+(Join-Path $projectRoot '.build\uninstall-test.log')+'"') -WindowStyle Hidden -Wait -PassThru
if ($uninstall.ExitCode) { throw ('Uninstall failed: '+$uninstall.ExitCode) }
for ($attempt = 0; $attempt -lt 50 -and (Test-Path -LiteralPath $target); $attempt++) { Start-Sleep -Milliseconds 200 }
if (Test-Path -LiteralPath $target) { throw 'Installation directory remains.' }
if (Test-Path -LiteralPath $key) { throw 'Uninstall registration remains.' }
if ((Get-FileHash -LiteralPath $audio).Hash -ne $audioHash -or (Get-FileHash -LiteralPath $stems).Hash -ne $stemsHash) {
    throw 'Saved audio or stems changed.'
}
if (Get-CimInstance Win32_Process -Filter "Name = 'TrackSeparator.exe'" | Where-Object { $_.ExecutablePath -eq (Join-Path $target 'TrackSeparator.exe') }) {
    throw 'Installed application process remains.'
}
Write-Output 'PASS: running app stopped; generated caches, installation directory, and uninstall registration removed; audio and stems preserved.'
