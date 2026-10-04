param(
    [string]$Exe = 'dist/TrackSeparator/TrackSeparator.exe',
    [string]$DataHome = '.app-data/windows-smoke',
    [switch]$Setup
)
# Runs on Windows without Python, Node, or system FFmpeg. Use disposable test data.
$ErrorActionPreference = 'Stop'
$executable = (Resolve-Path -LiteralPath $Exe).Path
$testHome = [IO.Path]::GetFullPath($DataHome)
New-Item -ItemType Directory -Force $testHome | Out-Null
$previousPath = $env:PATH
$previousData = $env:TRACK_SEPARATOR_DATA_HOME
$base = $null
function Api([string]$Route, $Body = $null) {
    if ($null -eq $Body) { return Invoke-RestMethod ($base + 'api/' + $Route) }
    Invoke-RestMethod ($base + 'api/' + $Route) -Method Post -ContentType 'application/json' -Body ($Body | ConvertTo-Json -Depth 30 -Compress)
}
function WaitJob([string]$Id) {
    $deadline = (Get-Date).AddMinutes(20)
    do {
        $job = Api ('jobs?id=' + $Id)
        if ($job.status -eq 'completed') { return $job }
        if ($job.status -in @('failed','cancelled','interrupted')) { throw $job.error }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)
    throw 'Analysis timed out'
}
try {
    $env:PATH = $env:SystemRoot + ';' + $env:SystemRoot + '\System32'
    $env:TRACK_SEPARATOR_DATA_HOME = $testHome
    Start-Process -FilePath $executable -ArgumentList @('app','--data-home',('"'+$testHome+'"'),'--no-browser') -WindowStyle Hidden | Out-Null
    $env:PATH = $previousPath
    $env:TRACK_SEPARATOR_DATA_HOME = $previousData
    $deadline = (Get-Date).AddSeconds(60)
    do {
        try {
            $instance = Get-Content -LiteralPath (Join-Path $testHome 'instance.json') -Raw | ConvertFrom-Json
            $base = $instance.url
            $health = Api 'health'
            if ($health.ready -and $health.instance -eq $instance.instance) { break }
        } catch { $base = $null }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $deadline)
    if (-not $base) { throw 'The app did not become ready' }
    if (-not (Api 'setup').ready) {
        if (-not $Setup) { throw 'Complete model setup first, or run this script with -Setup while online' }
        $modelJob = Api 'setup' @{}
        WaitJob $modelJob.id | Out-Null
    }
    $audio = Join-Path $testHome 'smoke.wav'
    $rate = 22050; $samples = $rate * 8; $bytes = $samples * 4
    $writer = New-Object IO.BinaryWriter([IO.File]::Create($audio))
    try {
        $writer.Write([Text.Encoding]::ASCII.GetBytes('RIFF')); $writer.Write([int](36+$bytes))
        $writer.Write([Text.Encoding]::ASCII.GetBytes('WAVEfmt ')); $writer.Write([int]16)
        $writer.Write([int16]1); $writer.Write([int16]2); $writer.Write([int]$rate)
        $writer.Write([int]($rate*4)); $writer.Write([int16]4); $writer.Write([int16]16)
        $writer.Write([Text.Encoding]::ASCII.GetBytes('data')); $writer.Write([int]$bytes)
        for ($i=0; $i -lt $samples; $i++) {
            $time=$i/$rate
            $frequencies=if ($time -lt 4) { @(65.406,261.626,329.628,391.995) } else { @(97.999,246.942,293.665,391.995) }
            $value=0.0
            foreach ($frequency in $frequencies) { $value += .07*[Math]::Sin(2*[Math]::PI*$frequency*$time) }
            $sample=[int16]($value*32767); $writer.Write($sample); $writer.Write($sample)
        }
    } finally { $writer.Dispose() }
    $imported = Invoke-RestMethod ($base+'api/import?filename=smoke.wav') -Method Post -ContentType 'application/octet-stream' -Headers @{'X-Track-Separator-Upload'='1'} -InFile $audio
    if ((Api 'health').app -ne 'Track Separator') { throw 'Wrong application name' }
    $job = Api 'separate' @{id=$imported.id}
    WaitJob $job.id | Out-Null
    $song = (Api 'library').songs | Where-Object { $_.id -eq $imported.id }
    if (-not $song.ready -or $song.stems.Count -ne 6) { throw 'Six stems were not produced' }
    $songFolder = Join-Path (Join-Path $testHome 'library') $imported.id
    foreach ($name in @('track.json','review.json','measurement.json','grid.json','bars.json','voicings.json','previews.json')) {
        if (Test-Path -LiteralPath (Join-Path $songFolder $name)) { throw ('Unexpected analysis file: '+$name) }
    }
    $stemsFolder=Join-Path $songFolder 'stems'
    if ($song.folder -ne $stemsFolder) { throw 'The app reported a different stems folder' }
    foreach ($stem in @('vocals','drums','bass','guitar','piano','other')) {
        $wav=Join-Path $stemsFolder ($stem+'.wav')
        $stream=[IO.File]::OpenRead($wav)
        try {
            $header=New-Object byte[] 4
            $stream.Read($header,0,4) | Out-Null
            if ($stream.Length -le 44 -or [Text.Encoding]::ASCII.GetString($header) -ne 'RIFF') { throw ('Invalid local WAV: '+$stem) }
        } finally { $stream.Dispose() }
    }
    $range = Invoke-WebRequest ($base+'api/audio?id='+$imported.id+'&stem=bass') -Headers @{Range='bytes=0-43'} -UseBasicParsing
    if ($range.StatusCode -ne 206 -or $range.RawContentLength -ne 44) { throw 'Audio seeking is broken' }
    $removed = Invoke-RestMethod ($base+'api/tracks?id='+$imported.id) -Method Delete
    Api 'trash/restore' @{ticket=$removed.ticket} | Out-Null
    if (-not (Test-Path -LiteralPath (Join-Path $songFolder 'stems/bass.wav'))) { throw 'Trash restore lost audio' }
    Write-Output 'Track Separator packaged import, six-stem separation, local stem files, audio ranges, trash restore: passed'

} finally {
    $env:PATH = $previousPath; $env:TRACK_SEPARATOR_DATA_HOME = $previousData
    if ($base) { try { Api 'shutdown' @{} | Out-Null } catch {} }
}
