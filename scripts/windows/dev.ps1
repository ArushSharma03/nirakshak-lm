<#
.SYNOPSIS
    Provision and run the Nirikshak-LM dev environment on Windows.

.DESCRIPTION
    Installs or locates Python 3.13, Node.js 20.9+, Tesseract OCR and the VC++
    runtime (via winget), creates backend\.venv, installs backend, dev and
    Xiaomi OCR dependencies (torch wheels from the PyTorch index), prefetches
    the pinned Xiaomi-OCR-0 checkpoint, installs frontend packages, then runs
    the FastAPI backend and the Next.js dev server together. Ctrl+C stops both.

    Re-runs skip steps whose inputs (requirement files, lockfile, torch flavour)
    have not changed. Environment changes are scoped to this process; no .env
    file is written.

.EXAMPLE
    scripts\windows\dev.cmd
.EXAMPLE
    scripts\windows\dev.cmd -Torch cu126 -Languages eng+hin
.EXAMPLE
    scripts\windows\dev.cmd -SetupOnly -RunTests
#>
[CmdletBinding()]
param(
    # PyTorch wheel index: cpu, or a CUDA build for NVIDIA GPUs.
    [ValidateSet('cpu', 'cu126', 'cu130', 'cu132')]
    [string]$Torch = 'cpu',
    # Tesseract languages, e.g. eng or eng+hin. Missing data is downloaded.
    [ValidatePattern('^[A-Za-z_]+(\+[A-Za-z_]+)*$')]
    [string]$Languages = 'eng',
    [ValidateRange(1, 65535)][int]$BackendPort = 8000,
    [ValidateRange(1, 65535)][int]$FrontendPort = 3000,
    [ValidateRange(1, 32)][int]$CpuThreads = 4,
    # Skip Xiaomi and keep Tesseract geometry and transcript diagnostics.
    [switch]$NoXiaomi,
    # Do not prefetch the Xiaomi checkpoint; the first analysis downloads it.
    [switch]$SkipModelDownload,
    # Do not install missing tools with winget; fail with instructions instead.
    [switch]$NoWinget,
    # Provision and verify only; do not start the servers.
    [switch]$SetupOnly,
    # Skip provisioning; launch with the existing environment.
    [switch]$SkipSetup,
    # Run backend pytest, frontend lint and type-check after provisioning.
    [switch]$RunTests,
    # Start uvicorn with --reload (reloads the OCR model after every edit).
    [switch]$Reload,
    # Do not open the browser once the frontend is ready.
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

if ($PSVersionTable.PSVersion.Major -ge 6 -and -not $IsWindows) {
    throw 'scripts/windows/dev.ps1 targets Windows. On Linux/macOS follow docs/week-8-usage.md.'
}
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$BackendDir = Join-Path $RepoRoot 'backend'
$FrontendDir = Join-Path $RepoRoot 'frontend'
$VenvDir = Join-Path $BackendDir '.venv'
$VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
$VenvStamp = Join-Path $VenvDir '.nirikshak-setup.json'
$NodeStamp = Join-Path $FrontendDir 'node_modules\.nirikshak-setup.json'
$StateDir = Join-Path $env:LOCALAPPDATA 'Nirikshak'
$XiaomiModel = 'xiaomi-research/Xiaomi-OCR-0'
$TorchVersion = '2.14.0'
$TorchVisionVersion = '0.29.0'

# ---------------------------------------------------------------- helpers --

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Note([string]$Message) { Write-Host "    $Message" -ForegroundColor DarkGray }
function Write-Warn([string]$Message) { Write-Host "!!  $Message" -ForegroundColor Yellow }

function Invoke-Checked {
    param([Parameter(Mandatory)][string]$FilePath, [string[]]$ArgumentList = @())
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $FilePath $($ArgumentList -join ' ')"
    }
}

# Run a native command without letting stderr become a terminating error
# (Windows PowerShell 5.1 turns redirected stderr into ErrorRecords).
function Invoke-Quiet([scriptblock]$Block) {
    $ErrorActionPreference = 'Continue'
    try { & $Block 2>$null } catch { }
}

# Python snippets passed with -c must not contain double quotes: Windows
# PowerShell 5.1 does not escape them for native commands.

function Update-SessionPath {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = (@($machine, $user) | Where-Object { $_ }) -join ';'
}

function Install-WithWinget([string]$Id, [string]$Name) {
    if ($NoWinget) { throw "$Name is missing. Install it, or re-run without -NoWinget." }
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "$Name is missing and winget is unavailable. Install 'App Installer' from the Microsoft Store or install $Name manually."
    }
    Write-Step "Installing $Name with winget ($Id); accept the UAC prompt if shown"
    Invoke-Checked winget.exe @('install', '--id', $Id, '--exact', '--silent',
        '--accept-package-agreements', '--accept-source-agreements')
    Update-SessionPath
}

function Get-InputHash([string[]]$Paths, [string]$Extra = '') {
    $parts = foreach ($p in $Paths) { (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash }
    $text = (@($parts) + $Extra) -join '|'
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($text))
        return ([BitConverter]::ToString($bytes) -replace '-', '')
    } finally { $sha.Dispose() }
}

function Test-Stamp([string]$Path, [string]$Hash) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    try { return ((Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json).hash -eq $Hash) } catch { return $false }
}

function Set-Stamp([string]$Path, [string]$Hash) {
    @{ hash = $Hash; updated = (Get-Date).ToString('o') } | ConvertTo-Json | Set-Content -Encoding ASCII -LiteralPath $Path
}

function Test-PortFree([int]$Port) {
    $listener = $null
    try {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    } catch { return $false } finally { if ($listener) { $listener.Stop() } }
}

# ------------------------------------------------------------- toolchain --

function Get-Python313 {
    $candidates = New-Object System.Collections.Generic.List[string]
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $exe = Invoke-Quiet { & py.exe -3.13 -c 'import sys; print(sys.executable)' }
        if ($LASTEXITCODE -eq 0 -and $exe) { $candidates.Add($exe.Trim()) }
    }
    $candidates.Add((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'))
    $candidates.Add((Join-Path $env:ProgramFiles 'Python313\python.exe'))
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike '*\WindowsApps\*') { $candidates.Add($cmd.Source) }
    foreach ($c in $candidates) {
        if (-not (Test-Path -LiteralPath $c)) { continue }
        $v = Invoke-Quiet { & $c -c "import sys; print('%d.%d' % sys.version_info[:2])" }
        if ($LASTEXITCODE -eq 0 -and "$v".Trim() -eq '3.13') { return $c }
    }
    return $null
}

function Initialize-Python {
    $py = Get-Python313
    if (-not $py) {
        Install-WithWinget 'Python.Python.3.13' 'Python 3.13'
        $py = Get-Python313
        if (-not $py) { throw 'Python 3.13 was installed but not found. Open a new terminal and re-run.' }
    }
    Write-Note "Python 3.13: $py"
    return $py
}

function Initialize-Node {
    $node = Get-Command node.exe -ErrorAction SilentlyContinue
    if (-not $node) {
        Install-WithWinget 'OpenJS.NodeJS.LTS' 'Node.js LTS'
        $node = Get-Command node.exe -ErrorAction SilentlyContinue
        if (-not $node) { throw 'Node.js was installed but not found. Open a new terminal and re-run.' }
    }
    $version = [version]((& $node.Source --version).Trim().TrimStart('v'))
    if ($version -lt [version]'20.9.0') {
        throw "Node.js $version is too old; Next.js 16 needs 20.9+. Run: winget upgrade OpenJS.NodeJS.LTS"
    }
    Write-Note "Node.js $version`: $($node.Source)"
    return $node.Source
}

function Find-Tesseract {
    $cmd = Get-Command tesseract.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $roots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, (Join-Path $env:LOCALAPPDATA 'Programs')) | Where-Object { $_ }
    foreach ($r in $roots) {
        $p = Join-Path $r 'Tesseract-OCR\tesseract.exe'
        if (Test-Path -LiteralPath $p) { return $p }
    }
    return $null
}

function Get-TesseractLanguages([string]$Exe, [string]$TessData) {
    $old = $env:TESSDATA_PREFIX
    try {
        if ($TessData) { $env:TESSDATA_PREFIX = $TessData } else { Remove-Item Env:TESSDATA_PREFIX -ErrorAction SilentlyContinue }
        $out = Invoke-Quiet { & $Exe --list-langs 2>&1 } | ForEach-Object { "$_".Trim() }
    } finally {
        if ($null -ne $old) { $env:TESSDATA_PREFIX = $old } else { Remove-Item Env:TESSDATA_PREFIX -ErrorAction SilentlyContinue }
    }
    return @($out | Where-Object { $_ -and $_ -notmatch '^List of available languages' })
}

# Returns @{ Exe; Dir; TessData } where TessData is $null when the install's own data suffices.
function Initialize-Tesseract([string[]]$Wanted) {
    $exe = Find-Tesseract
    if (-not $exe) {
        Install-WithWinget 'UB-Mannheim.TesseractOCR' 'Tesseract OCR'
        $exe = Find-Tesseract
        if (-not $exe) { throw 'Tesseract was installed but tesseract.exe was not found.' }
    }
    $dir = Split-Path -Parent $exe
    Write-Note "Tesseract: $exe"

    $installed = Get-TesseractLanguages $exe $null
    $missing = @($Wanted | Where-Object { $installed -notcontains $_ })
    if ($missing.Count -eq 0) { return @{ Exe = $exe; Dir = $dir; TessData = $null } }

    # Program Files is read-only for normal users, so keep a per-user copy of
    # tessdata (including configs\tsv) and add the missing language files there.
    $sourceData = Join-Path $dir 'tessdata'
    $userData = Join-Path $StateDir 'tessdata'
    if (-not (Test-Path -LiteralPath (Join-Path $userData 'configs\tsv'))) {
        if (-not (Test-Path -LiteralPath $sourceData)) { throw "Tesseract data directory not found: $sourceData" }
        Write-Step "Copying Tesseract data to $userData"
        New-Item -ItemType Directory -Force -Path $userData | Out-Null
        Copy-Item -Recurse -Force -Path (Join-Path $sourceData '*') -Destination $userData
    }
    foreach ($lang in $missing) {
        $target = Join-Path $userData "$lang.traineddata"
        if (Test-Path -LiteralPath $target) { continue }
        $url = "https://github.com/tesseract-ocr/tessdata/raw/main/$lang.traineddata"
        Write-Step "Downloading Tesseract language data: $lang"
        $tmp = "$target.download"
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $tmp
            Move-Item -Force -LiteralPath $tmp -Destination $target
        } catch {
            Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $tmp
            throw "Could not download $url. Check the language code and network access."
        }
    }
    $now = Get-TesseractLanguages $exe $userData
    $still = @($Wanted | Where-Object { $now -notcontains $_ })
    if ($still.Count -gt 0) { throw "Tesseract still lacks: $($still -join ', ')" }
    return @{ Exe = $exe; Dir = $dir; TessData = $userData }
}

function Initialize-VCRuntime {
    $key = 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64'
    $ok = $false
    try { $ok = ((Get-ItemProperty -Path $key -ErrorAction Stop).Installed -eq 1) } catch { $ok = $false }
    if (-not $ok) {
        Write-Note 'PyTorch needs the Microsoft Visual C++ 2015-2022 runtime.'
        Install-WithWinget 'Microsoft.VCRedist.2015+.x64' 'Visual C++ runtime'
    }
}

function Test-LongPaths {
    try {
        $v = (Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -ErrorAction Stop).LongPathsEnabled
        if ($v -ne 1 -and $RepoRoot.Length -gt 60) {
            Write-Warn "Long paths are disabled and the repo path is long ($($RepoRoot.Length) chars). If pip fails with path errors, enable LongPathsEnabled or move the repo closer to the drive root."
        }
    } catch { }
}

# --------------------------------------------------------------- backend --

function Initialize-Backend([string]$Python) {
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Write-Step 'Creating backend\.venv'
        Invoke-Checked $Python @('-m', 'venv', $VenvDir)
    }
    $v = (& $VenvPython -c "import sys; print('%d.%d' % sys.version_info[:2])").Trim()
    if ($v -ne '3.13') { throw "backend\.venv uses Python $v; delete backend\.venv and re-run to recreate it with 3.13." }

    $reqs = @('requirements.txt', 'requirements-dev.txt') | ForEach-Object { Join-Path $BackendDir $_ }
    $flavour = 'none'
    if (-not $NoXiaomi) {
        $reqs += (Join-Path $BackendDir 'requirements-ocr.txt')
        $flavour = $Torch
    }
    $hash = Get-InputHash $reqs "torch=$flavour|$TorchVersion|$TorchVisionVersion"
    if (Test-Stamp $VenvStamp $hash) {
        Write-Note 'Backend dependencies are up to date.'
        return
    }

    Write-Step 'Installing backend dependencies'
    Invoke-Checked $VenvPython @('-m', 'pip', 'install', '--upgrade', 'pip')
    Invoke-Checked $VenvPython @('-m', 'pip', 'install', '-r', (Join-Path $BackendDir 'requirements-dev.txt'))
    if (-not $NoXiaomi) {
        Write-Step "Installing torch $TorchVersion ($Torch) for Xiaomi OCR"
        Invoke-Checked $VenvPython @('-m', 'pip', 'install', '--force-reinstall', "torch==$TorchVersion", "torchvision==$TorchVisionVersion",
            '--index-url', "https://download.pytorch.org/whl/$Torch")
        Invoke-Checked $VenvPython @('-m', 'pip', 'install', '-r', (Join-Path $BackendDir 'requirements-ocr.txt'))
    }
    Set-Stamp $VenvStamp $hash
}

function Test-BackendRuntime {
    Write-Step 'Verifying backend imports'
    Push-Location $BackendDir
    try {
        Invoke-Checked $VenvPython @('-c', "import cv2, fastapi, app.main; print('backend import ok, opencv', cv2.__version__)")
        if (-not $NoXiaomi) {
            $code = @'
import torch, transformers
print('torch', torch.__version__, '| transformers', transformers.__version__, '| cuda available:', torch.cuda.is_available())
'@
            Invoke-Checked $VenvPython @('-c', $code)
            if ($Torch -ne 'cpu') {
                $cuda = (& $VenvPython -c 'import torch; print(torch.cuda.is_available())').Trim()
                if ($cuda -ne 'True') { throw "Torch $Torch cannot see a CUDA device. Update the NVIDIA driver or use -Torch cpu." }
            }
        }
    } finally { Pop-Location }
}

function Get-XiaomiRevision {
    $src = Get-Content -Raw -LiteralPath (Join-Path $BackendDir 'app\services\ocr.py')
    $m = [regex]::Match($src, 'XIAOMI_REVISION\s*=\s*"([0-9a-f]{40})"')
    if (-not $m.Success) { throw 'Could not read XIAOMI_REVISION from backend\app\services\ocr.py' }
    return $m.Groups[1].Value
}

function Save-XiaomiModel {
    $rev = Get-XiaomiRevision
    Write-Step "Prefetching $XiaomiModel@$($rev.Substring(0, 12)) (large; resumes if interrupted)"
    $code = @"
from huggingface_hub import snapshot_download
print(snapshot_download('$XiaomiModel', revision='$rev'))
"@
    Invoke-Checked $VenvPython @('-c', $code)
}

function Test-TesseractTsv {
    Write-Step 'Verifying Tesseract TSV output'
    $code = @"
import os, subprocess, cv2, numpy as np
img = np.full((80, 360), 255, np.uint8)
cv2.putText(img, 'NET WT 500 g', (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, 0, 3)
ok, png = cv2.imencode('.png', img)
out = subprocess.run(['tesseract', 'stdin', 'stdout', '-l', os.environ['TESSERACT_LANGUAGES'], '--psm', '11', 'tsv'],
                     input=png.tobytes(), capture_output=True, check=True, timeout=40).stdout.decode('utf-8', 'replace')
words = [r.split('\t')[-1] for r in out.splitlines()[1:] if r.count('\t') >= 11 and r.split('\t')[-1].strip()]
print('tesseract words:', words)
assert out.startswith('level\t'), 'no TSV header'
assert '500' in words, 'expected test quantity missing from TSV'
"@
    Push-Location $BackendDir
    try { Invoke-Checked $VenvPython @('-c', $code) } finally { Pop-Location }
}

# -------------------------------------------------------------- frontend --

function Initialize-Frontend([string]$Node) {
    $lock = Join-Path $FrontendDir 'package-lock.json'
    $hash = Get-InputHash @($lock, (Join-Path $FrontendDir 'package.json')) ((& $Node --version).Trim())
    if ((Test-Path -LiteralPath (Join-Path $FrontendDir 'node_modules\next')) -and (Test-Stamp $NodeStamp $hash)) {
        Write-Note 'Frontend packages are up to date.'
        return
    }
    $npm = Join-Path (Split-Path -Parent $Node) 'npm.cmd'
    if (-not (Test-Path -LiteralPath $npm)) { $npm = 'npm.cmd' }
    Write-Step 'Installing frontend packages (npm ci)'
    Push-Location $FrontendDir
    try { Invoke-Checked $npm @('ci', '--no-audit', '--no-fund') } finally { Pop-Location }
    Set-Stamp $NodeStamp $hash
}

function Invoke-Tests([string]$Node) {
    Write-Step 'Running backend tests'
    Push-Location $BackendDir
    try { Invoke-Checked $VenvPython @('-m', 'pytest', 'tests', '-q') } finally { Pop-Location }
    Write-Step 'Running frontend lint and type-check'
    Push-Location $FrontendDir
    try {
        Invoke-Checked $Node @('node_modules\eslint\bin\eslint.js')
        Invoke-Checked $Node @('node_modules\typescript\bin\tsc', '--noEmit')
    } finally { Pop-Location }
}

# ---------------------------------------------------------------- launch --

function Wait-Http([string]$Url, [Diagnostics.Process]$Process, [int]$TimeoutSec) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) { return $false }
        try {
            $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri $Url
            if ($r.StatusCode -lt 500) { return $true }
        } catch { }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

function Stop-Tree([Diagnostics.Process]$Process) {
    if ($Process -and -not $Process.HasExited) {
        Invoke-Quiet { & taskkill.exe /PID $Process.Id /T /F 2>&1 } | Out-Null
    }
}

function Start-Servers([string]$Node) {
    foreach ($p in @($BackendPort, $FrontendPort)) {
        if (-not (Test-PortFree $p)) { throw "Port $p is in use. Stop that process or pass -BackendPort/-FrontendPort." }
    }
    $apiUrl = "http://localhost:$BackendPort"
    $webUrl = "http://localhost:$FrontendPort"
    $env:NEXT_PUBLIC_API_URL = $apiUrl
    $env:CORS_ORIGINS = "[`"$webUrl`",`"http://127.0.0.1:$FrontendPort`"]"
    $env:NEXT_TELEMETRY_DISABLED = '1'

    $uvicorn = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', "$BackendPort")
    if ($Reload) { $uvicorn += '--reload' }

    $backend = $null; $frontend = $null
    try {
        Write-Step "Starting backend on $apiUrl"
        $backend = Start-Process -FilePath $VenvPython -ArgumentList $uvicorn -WorkingDirectory $BackendDir -NoNewWindow -PassThru
        if (-not (Wait-Http "http://127.0.0.1:$BackendPort/health" $backend 120)) {
            throw 'Backend did not become healthy; see the output above.'
        }
        Write-Step "Starting frontend on $webUrl"
        $nextBin = Join-Path $FrontendDir 'node_modules\next\dist\bin\next'
        $frontend = Start-Process -FilePath $Node -ArgumentList @("`"$nextBin`"", 'dev', '--port', "$FrontendPort") `
            -WorkingDirectory $FrontendDir -NoNewWindow -PassThru
        if (-not (Wait-Http $webUrl $frontend 180)) { throw 'Frontend did not start; see the output above.' }

        Write-Host ''
        Write-Host "Nirikshak-LM is running." -ForegroundColor Green
        Write-Host "  Frontend : $webUrl"
        Write-Host "  API docs : $apiUrl/docs"
        $ocrMode = 'Tesseract diagnostics only'
        if (-not $NoXiaomi) { $ocrMode = "Xiaomi-OCR-0 ($env:OCR_DEVICE) + Tesseract" }
        Write-Host "  OCR      : $ocrMode, languages $Languages"
        Write-Host "Press Ctrl+C to stop both servers."
        if (-not $NoBrowser) { Start-Process $webUrl | Out-Null }

        while (-not $backend.HasExited -and -not $frontend.HasExited) { Start-Sleep -Milliseconds 500 }
        if ($backend.HasExited) { Write-Warn "Backend exited (code $($backend.ExitCode))." }
        if ($frontend.HasExited) { Write-Warn "Frontend exited (code $($frontend.ExitCode))." }
    } finally {
        Write-Step 'Stopping servers'
        Stop-Tree $frontend
        Stop-Tree $backend
    }
}

# ------------------------------------------------------------------ main --

$savedEnv = @{}
$envNames = @('Path', 'XIAOMI_OCR_ENABLED', 'OCR_DEVICE', 'OCR_CPU_THREADS', 'TESSERACT_LANGUAGES', 'TESSDATA_PREFIX',
    'NEXT_PUBLIC_API_URL', 'CORS_ORIGINS', 'NEXT_TELEMETRY_DISABLED', 'HF_HUB_DISABLE_SYMLINKS_WARNING',
    'PYTHONUTF8', 'OMP_NUM_THREADS')
foreach ($n in $envNames) { $savedEnv[$n] = [Environment]::GetEnvironmentVariable($n, 'Process') }

try {
    if ($SkipSetup -and $SetupOnly) { throw '-SkipSetup and -SetupOnly cannot be combined.' }
    $wantedLangs = @($Languages -split '\+')

    if ($SkipSetup) {
        if (-not (Test-Path -LiteralPath $VenvPython)) { throw 'backend\.venv is missing; run once without -SkipSetup.' }
        $nodeCmd = Get-Command node.exe -ErrorAction SilentlyContinue
        if (-not $nodeCmd) { throw 'node.exe not found on PATH.' }
        $node = $nodeCmd.Source
        $tessExe = Find-Tesseract
        if (-not $tessExe) { throw 'tesseract.exe not found; run once without -SkipSetup.' }
        $userData = Join-Path $StateDir 'tessdata'
        $tessData = $null
        $installedLangs = Get-TesseractLanguages $tessExe $null
        if (@($wantedLangs | Where-Object { $installedLangs -notcontains $_ }).Count -gt 0 -and (Test-Path -LiteralPath $userData)) {
            $tessData = $userData
        }
        $tess = @{ Exe = $tessExe; Dir = (Split-Path -Parent $tessExe); TessData = $tessData }
    } else {
        Write-Step "Provisioning Nirikshak-LM in $RepoRoot"
        Test-LongPaths
        $python = Initialize-Python
        $node = Initialize-Node
        $tess = Initialize-Tesseract $wantedLangs
        if (-not $NoXiaomi) { Initialize-VCRuntime }
        Initialize-Backend $python
        Initialize-Frontend $node
    }

    # Process-scoped configuration consumed by app.core.config.Settings.
    $env:Path = "$($tess.Dir);$env:Path"
    if ($tess.TessData) { $env:TESSDATA_PREFIX = $tess.TessData }
    $env:TESSERACT_LANGUAGES = $Languages
    $env:XIAOMI_OCR_ENABLED = if ($NoXiaomi) { 'false' } else { 'true' }
    $env:OCR_DEVICE = if ($Torch -eq 'cpu') { 'cpu' } else { 'cuda' }
    $env:OCR_CPU_THREADS = "$CpuThreads"
    $env:OMP_NUM_THREADS = "$CpuThreads"
    $env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'
    $env:PYTHONUTF8 = '1'

    if (-not $SkipSetup) {
        Test-BackendRuntime
        Test-TesseractTsv
        if (-not $NoXiaomi -and -not $SkipModelDownload) { Save-XiaomiModel }
        if ($RunTests) { Invoke-Tests $node }
        Write-Step 'Environment ready.'
    }

    if (-not $SetupOnly) { Start-Servers $node }
} finally {
    foreach ($n in $envNames) { [Environment]::SetEnvironmentVariable($n, $savedEnv[$n], 'Process') }
}
