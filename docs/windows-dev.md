# Windows development setup

`scripts\windows\dev.cmd` provisions a Windows 10/11 (x64) machine and runs the
backend and frontend together. It wraps `scripts\windows\dev.ps1` with
`-ExecutionPolicy Bypass` for that process only. The machine execution policy
is unchanged. It targets Command Prompt, PowerShell 5.1 and PowerShell 7.

```bat
cd path\to\nirakshak
scripts\windows\dev.cmd
```

The first run takes a while. The torch wheel and the Xiaomi-OCR-0 checkpoint
together are several GB. Later runs skip anything already up to date and start
in seconds. Press Ctrl+C to stop both servers.

With an NVIDIA GPU the script picks a CUDA build of PyTorch by itself, from the
driver's CUDA version (13.0+ → `cu130`, 12.6+ → `cu126`, otherwise `cpu`).
The OCR device is then set from what the installed torch can actually use.

On first start, an empty store is filled with the sample inspections in
`backend\seed` (seven real packages with their photos and analyses). A store
that already holds records is never changed. To replace the samples with your
current inspections, run `python -m app.services.seed export` in `backend`.

## What it does

1. Looks for Python 3.13, Node.js 20.9+, Tesseract OCR and, for Xiaomi OCR,
   the Visual C++ 2015–2022 x64 runtime. Missing tools are installed with
   `winget`: `Python.Python.3.13`, `OpenJS.NodeJS.LTS`,
   `UB-Mannheim.TesseractOCR` and `Microsoft.VCRedist.2015+.x64`. Installers
   may show a UAC prompt. The Microsoft Store `python.exe` alias is ignored.
2. Checks Tesseract's language data for `-Languages` (default `eng`). If any
   are missing, it copies the install's `tessdata` to
   `%LOCALAPPDATA%\Nirikshak\tessdata`. It then downloads the missing
   `*.traineddata` files from `github.com/tesseract-ocr/tessdata` into that
   copy. Program Files is not modified.
3. Creates `backend\.venv` with Python 3.13. It installs
   `requirements-dev.txt`, then `torch==2.14.0` and `torchvision==0.29.0` from
   the PyTorch index for `-Torch`, then `requirements-ocr.txt`. A hash of the
   requirement files and the torch flavour is kept in
   `backend\.venv\.nirikshak-setup.json`. Pip runs again only when that hash
   changes.
4. Runs `npm ci` in `frontend` when `package-lock.json`, `package.json` or the
   Node version changes. The stamp is
   `frontend\node_modules\.nirikshak-setup.json`.
5. Verifies the runtime. It imports `app.main`, OpenCV, torch and transformers.
   With a CUDA flavour, it requires `torch.cuda.is_available()`. It also renders
   a test label and checks that `tesseract … tsv` reads it. The backend uses
   that same invocation.
6. Prefetches the pinned Xiaomi-OCR-0 revision into the Hugging Face cache
   (`%USERPROFILE%\.cache\huggingface`). The revision is read from
   `backend\app\services\ocr.py`, and interrupted downloads resume.
7. Starts uvicorn on `127.0.0.1:<BackendPort>` and waits for `/health`. It
   then starts `next dev` on `<FrontendPort>` and opens the browser.

Configuration is set as environment variables on the script's own process,
which the servers inherit. No `.env` file is written. The variables are
`TESSERACT_LANGUAGES`, `TESSDATA_PREFIX` (only when the per-user copy is used),
`XIAOMI_OCR_ENABLED`, `OCR_DEVICE` (`cpu` or `cuda`), `OCR_CPU_THREADS`,
`OMP_NUM_THREADS`, `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS`. Ports are
therefore consistent on both sides. Values in a repo `.env` are overridden by
these. A `TYPESAFE_API_KEY` in your environment or `.env` is left as is. Jev
still needs explicit per-request opt-in.

## Options

| Option | Effect |
|---|---|
| `-Torch auto\|cpu\|cu126\|cu130\|cu132` | PyTorch wheel index. Default `auto`: a CUDA build the NVIDIA driver supports, else `cpu`. `OCR_DEVICE` follows what the installed torch can use (`cuda` uses float16). Switching flavour reinstalls torch. |
| `-Languages eng+hin` | Tesseract languages; any `tessdata` codes joined by `+`. |
| `-NoXiaomi` | Skips torch/transformers and the model; runs with `XIAOMI_OCR_ENABLED=false` (Tesseract geometry only). |
| `-SkipModelDownload` | Do not prefetch the checkpoint; the first analysis downloads it. |
| `-CpuThreads N` | CPU threads for Xiaomi inference (default 4). |
| `-BackendPort N` / `-FrontendPort N` | Defaults 8000 / 3000. The script refuses to start if a port is taken. |
| `-SetupOnly` | Provision and verify, then exit. |
| `-SkipSetup` | Launch only; uses the existing venv, `node_modules` and Tesseract. |
| `-RunTests` | After setup, runs `pytest tests -q`, `eslint` and `tsc --noEmit`. |
| `-Reload` | uvicorn `--reload`. Each backend edit reloads the OCR model. |
| `-NoWinget` | Never install tools; fail with the missing tool's name. |
| `-NoBrowser` | Do not open the browser. |

Examples:

```bat
scripts\windows\dev.cmd -SetupOnly -RunTests
scripts\windows\dev.cmd -Torch cu126 -Languages eng+hin
scripts\windows\dev.cmd -SkipSetup -NoBrowser
```

## Troubleshooting

- **"installed but not found"**: the script reloads PATH from the registry
  before each step, so a tool installed by an earlier run in the same terminal
  is found. If one still is not, open a new terminal and run again.
- **"Port 8000 is in use by …"**: the message names the process and PID. It is
  usually an earlier run of this script; stop it with `Stop-Process -Id <PID>`.
- **pip path-length errors**: enable `LongPathsEnabled`, or clone the repo
  closer to the drive root. The script warns when long paths are off and the
  path is long.
- **`backend\.venv uses Python 3.x`**: an older venv exists. Delete
  `backend\.venv` and run again.
- **CUDA flavour check fails**: update the NVIDIA driver, or use `-Torch cpu`.
- **Force a reinstall**: delete the matching `.nirikshak-setup.json` stamp.
- **PostgreSQL**: optional. Without it, inspections are saved to the local JSON
  store (`Demo / Offline Fallback`). To use it, set `DATABASE_URL` in `.env`.
- CPU Xiaomi reads can take minutes per view. Behaviour and limits are covered
  in [Run the evidence pipeline](week-8-usage.md).

## Validation status

Run end to end on Windows 11 with PowerShell 7 and an RTX 3050 laptop GPU
(driver CUDA 13.4), on 2026-11-18/19, starting with only Python 3.14 present.
The script installed Python 3.13, Node.js and Tesseract with winget, created the
venv, installed the `cu130` torch wheels, ran `npm ci`, downloaded the
Xiaomi-OCR-0 checkpoint, passed `-RunTests`, and launched both servers with OCR on
`cuda`. Three bugs found there are fixed: winget output leaked into the
returned tool path, winget's "already installed" exit code (`0x8A15002B`) was
treated as a failure, and the Tesseract self-test rejected `500g` read without a
space. A rerun from a terminal whose PATH predated the installs found every tool,
detected the GPU without `-Torch`, and installed the sample inspections into an
empty store.

Earlier checks, from the original Linux authoring:

- PowerShell 7.7 parses the script with zero errors. PSScriptAnalyzer 1.25
  reports only style warnings.
- The embedded Python checks pass against this backend. These are the import
  check, the Tesseract TSV probe and the `CORS_ORIGINS` JSON override.
- The launch helpers were run under pwsh. These are the input hashes, stamps,
  the revision parse, the port probe and `-NoWinget`. Starting uvicorn reached
  `/health`, and an exited process was detected. Starting `next dev` returned
  HTTP 200.
- `torch==2.14.0` and `torchvision==0.29.0` publish `cp313 win_amd64` wheels on
  the `cpu`, `cu126`, `cu130` and `cu132` indexes.
