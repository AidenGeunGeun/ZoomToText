[CmdletBinding()]
param(
  [string]$Venv = ".venv",
  [ValidateSet("cpu", "cu121", "cu122", "skip")]
  [string]$Torch = "cpu",
  [switch]$Editable,
  [switch]$InstallFFmpeg
)

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Info($msg) { Write-Host "$msg" -ForegroundColor Gray }
function Write-Warn($msg) { Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "[error] $msg" -ForegroundColor Red }

# Detect Python launcher or python.exe
$pythonExe = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $pythonExe = "python" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $pythonExe = "py" }
else { Write-Err "Python 3.10+ not found on PATH."; exit 1 }

function Py {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
  if ($pythonExe -eq "py") { & py -3 @Args } else { & python @Args }
  if ($LASTEXITCODE -ne 0) { throw "Python command failed: $Args" }
}

Write-Step "Python info"
Py -c "import sys,platform;print('Python',sys.version.split()[0],'arch',platform.architecture()[0])"

if (-not (Test-Path $Venv)) {
  Write-Step "Create venv at $Venv"
  Py -m venv $Venv
} else {
  Write-Info "Venv already exists: $Venv"
}

Write-Step "Activate venv"
$activate = Join-Path $Venv "Scripts/Activate.ps1"
if (-not (Test-Path $activate)) { Write-Err "Could not find $activate"; exit 1 }
. $activate

Write-Step "Upgrade pip tooling"
Py -m pip install --upgrade pip setuptools wheel

Write-Step "Install loopback dependency (soundcard)"
Py -m pip install --upgrade soundcard

if ($Torch -ne "skip") {
  Write-Step "Install PyTorch ($Torch)"
  $indexUrl = switch ($Torch) {
    "cpu" { "https://download.pytorch.org/whl/cpu" }
    "cu121" { "https://download.pytorch.org/whl/cu121" }
    "cu122" { "https://download.pytorch.org/whl/cu122" }
  }
  Py -m pip install --upgrade torch torchvision torchaudio --index-url $indexUrl
} else {
  Write-Warn "Skipping PyTorch install (Whisper will not work without it)."
}

Write-Step "Install project + Whisper"
if ($Editable) { Py -m pip install -e .[whisper] }
else { Py -m pip install .[whisper] }

Write-Step "Verify soundcard"
Py -c "import soundcard as sc;print([s.name for s in sc.all_speakers()])"

if ($InstallFFmpeg) {
  Write-Step "Check/install FFmpeg"
  if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
      Write-Info "Installing FFmpeg via winget (you may be prompted to accept)."
      winget install -e --id Gyan.FFmpeg
    }
    elseif (Get-Command choco -ErrorAction SilentlyContinue) {
      Write-Info "Installing FFmpeg via chocolatey (admin may be required)."
      choco install -y ffmpeg
    } else {
      Write-Warn "winget/choco not found. Please install FFmpeg manually from https://www.gyan.dev/ffmpeg/builds/ and add it to PATH."
    }
  } else { Write-Info "FFmpeg already available." }
}

# sounddevice no longer required; loopback uses `soundcard`.

Write-Step "Done"
Write-Host "Usage examples:" -ForegroundColor Green
Write-Host "  python -m zoom_to_text.cli --list-devices" -ForegroundColor Green
Write-Host "  python -m zoom_to_text.cli --live --device <index> --output-dir outdir" -ForegroundColor Green
Write-Host "  python -m zoom_to_text.cli transcribe --input input.wav --output-dir outdir" -ForegroundColor Green
