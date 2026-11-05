<#
.SYNOPSIS
    Entrypoint for LLM Benchmark (Windows PowerShell).
.DESCRIPTION
    Run:  .\run.ps1
    Or:   .\run.ps1 baseline --url http://localhost:4000/v1/chat/completions --model qwen-30b
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$PSScriptRootLocation = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($PSScriptRootLocation) {
    Set-Location -LiteralPath $PSScriptRootLocation
}

# Ensure console output supports UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$host.UI.RawUI.WindowTitle = "LLM Benchmark"

$pyCandidates = @(
    @{ Cmd = "py"; Args = @("-3") },
    @{ Cmd = "python"; Args = @() },
    @{ Cmd = "python3"; Args = @() }
)

$chosenCmd = $null
$chosenArgs = @()

foreach ($candidate in $pyCandidates) {
    $cmd = $candidate.Cmd
    $cmdArgs = $candidate.Args
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $testArgs = $cmdArgs + @("-c", "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)")
        & $cmd $testArgs 2>$null
        if ($LASTEXITCODE -eq 0) {
            $chosenCmd = $cmd
            $chosenArgs = $cmdArgs
            break
        }
    }
}

if (-not $chosenCmd) {
    # Check if python is installed but older than 3.9
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        Write-Host "Python was detected but version is older than 3.9:" -ForegroundColor Red
        & python -V
    } else {
        Write-Host "Python 3.9 or newer was not found on this system." -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Installation Guide:" -ForegroundColor Yellow
    Write-Host "  1. Download Python from https://www.python.org/downloads/"
    Write-Host "  2. During installation, CHECK `"Add python.exe to PATH`""
    Write-Host "  3. Reopen PowerShell once installation completes."
    exit 1
}

if (-not (Test-Path "llmload.py")) {
    Write-Host "File llmload.py was not found in: $(Get-Location)" -ForegroundColor Red
    exit 1
}

$firstArg = if ($ArgsList -and $ArgsList.Count -gt 0) { $ArgsList[0].ToLower() } else { "" }
$subcommands = @("menu", "baseline", "ramp", "rate", "soak", "compare", "report")

if ($subcommands -contains $firstArg) {
    $execArgs = $chosenArgs + @("llmload.py") + $ArgsList
} else {
    $execArgs = $chosenArgs + @("llmload.py", "menu") + $ArgsList
}

& $chosenCmd $execArgs
exit $LASTEXITCODE
