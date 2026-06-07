param(
    [ValidateSet("start", "stop", "restart", "status", "logs")]
    [string] $Action = "start",
    [switch] $WithPostgres,
    [int] $BackendPort = 8000,
    [int] $FrontendPort = 5173,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $RemainingArgs
)

$ErrorActionPreference = "Stop"

for ($Index = 0; $Index -lt $RemainingArgs.Count; $Index++) {
    switch ($RemainingArgs[$Index]) {
        "--with-postgres" {
            $WithPostgres = $true
        }
        "--backend-port" {
            $Index += 1
            if ($Index -ge $RemainingArgs.Count) {
                throw "Missing value for --backend-port"
            }
            $BackendPort = [int] $RemainingArgs[$Index]
        }
        "--frontend-port" {
            $Index += 1
            if ($Index -ge $RemainingArgs.Count) {
                throw "Missing value for --frontend-port"
            }
            $FrontendPort = [int] $RemainingArgs[$Index]
        }
        default {
            throw "Unknown option: $($RemainingArgs[$Index])"
        }
    }
}

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$StateDir = Join-Path $ProjectRoot ".dev"
$PidDir = Join-Path $StateDir "pids"
$LogDir = Join-Path $StateDir "logs"
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"

function Ensure-StateDirs {
    New-Item -ItemType Directory -Force -Path $PidDir | Out-Null
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

function Get-PidFile {
    param([string] $Name)
    Join-Path $PidDir "$Name.pid"
}

function Get-ManagedPid {
    param([string] $Name)
    $PidFile = Get-PidFile $Name
    if (-not (Test-Path $PidFile)) {
        return $null
    }

    $RawPid = (Get-Content -Path $PidFile -Raw).Trim()
    if (-not $RawPid) {
        return $null
    }

    [int] $ProcessId = $RawPid
    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($null -eq $Process) {
        Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
        return $null
    }

    return $ProcessId
}

function Stop-ProcessTree {
    param([int] $ProcessId)

    $Children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue
    foreach ($Child in $Children) {
        Stop-ProcessTree -ProcessId ([int] $Child.ProcessId)
    }

    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Start-ManagedProcess {
    param(
        [string] $Name,
        [string] $FilePath,
        [string[]] $ArgumentList,
        [string] $WorkingDirectory
    )

    $ExistingPid = Get-ManagedPid $Name
    if ($null -ne $ExistingPid) {
        Write-Host "$Name already running (pid $ExistingPid)."
        return
    }

    if (-not (Test-Path $FilePath) -and -not (Get-Command $FilePath -ErrorAction SilentlyContinue)) {
        throw "$Name executable not found: $FilePath"
    }

    $StdOut = Join-Path $LogDir "$Name.out.log"
    $StdErr = Join-Path $LogDir "$Name.err.log"
    $Process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $StdOut `
        -RedirectStandardError $StdErr `
        -WindowStyle Hidden `
        -PassThru

    Set-Content -Path (Get-PidFile $Name) -Value $Process.Id
    Write-Host "Started $Name (pid $($Process.Id))."
}

function Stop-ManagedProcess {
    param([string] $Name)

    $ProcessId = Get-ManagedPid $Name
    if ($null -eq $ProcessId) {
        Write-Host "$Name is not running."
        return
    }

    Stop-ProcessTree -ProcessId $ProcessId
    Remove-Item -Path (Get-PidFile $Name) -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped $Name."
}

function Show-ManagedStatus {
    param([string] $Name)

    $ProcessId = Get-ManagedPid $Name
    if ($null -eq $ProcessId) {
        Write-Host "${Name}: stopped"
        return
    }

    Write-Host "${Name}: running (pid $ProcessId)"
}

function Show-Logs {
    Write-Host "Logs directory: $LogDir"
    Get-ChildItem -Path $LogDir -Filter "*.log" -ErrorAction SilentlyContinue |
        Sort-Object Name |
        ForEach-Object {
            Write-Host ""
            Write-Host "== $($_.Name) =="
            Get-Content -Path $_.FullName -Tail 20 -ErrorAction SilentlyContinue
        }
}

function Start-DevServices {
    Ensure-StateDirs

    if (-not (Test-Path $PythonExe)) {
        throw "Backend virtualenv not found. Expected: $PythonExe"
    }

    if ($WithPostgres) {
        Push-Location $ProjectRoot
        try {
            docker compose up -d postgres
        }
        finally {
            Pop-Location
        }
    }

    Start-ManagedProcess `
        -Name "backend" `
        -FilePath $PythonExe `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "$BackendPort") `
        -WorkingDirectory $BackendDir

    Start-ManagedProcess `
        -Name "worker" `
        -FilePath $PythonExe `
        -ArgumentList @("-m", "app.workers.worker_main") `
        -WorkingDirectory $BackendDir

    $FrontendServer = Join-Path $FrontendDir "server.js"
    Start-ManagedProcess `
        -Name "frontend" `
        -FilePath "powershell" `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "`$env:PORT='$FrontendPort'; node '$FrontendServer'"
        ) `
        -WorkingDirectory $ProjectRoot

    Write-Host ""
    Write-Host "Backend:  http://127.0.0.1:$BackendPort"
    Write-Host "Docs:     http://127.0.0.1:$BackendPort/docs"
    Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
}

function Stop-DevServices {
    Stop-ManagedProcess "frontend"
    Stop-ManagedProcess "worker"
    Stop-ManagedProcess "backend"
}

switch ($Action) {
    "start" {
        Start-DevServices
    }
    "stop" {
        Stop-DevServices
    }
    "restart" {
        Stop-DevServices
        Start-DevServices
    }
    "status" {
        Ensure-StateDirs
        Show-ManagedStatus "backend"
        Show-ManagedStatus "worker"
        Show-ManagedStatus "frontend"
    }
    "logs" {
        Ensure-StateDirs
        Show-Logs
    }
}
