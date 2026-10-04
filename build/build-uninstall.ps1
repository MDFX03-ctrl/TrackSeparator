$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compiler)) { throw 'The Windows .NET Framework C# compiler is required.' }
& $compiler /nologo /target:winexe /platform:anycpu /reference:System.Windows.Forms.dll "/out:$projectRoot\uninstall.exe" "$PSScriptRoot\uninstall.cs"
if ($LASTEXITCODE) { throw 'Uninstaller launcher build failed' }
