param(
  [string]$TargetDir = ""
)

$port = 20128
$tcp = New-Object System.Net.Sockets.TcpClient
$running = $false
try {
  $tcp.Connect('127.0.0.1', $port)
  $running = $true
  $tcp.Close()
} catch {
  $running = $false
}

if (-not $running) {
  Write-Host "OmniRoute server is not running. Starting it in background..." -ForegroundColor Yellow
  Start-Process cmd.exe -ArgumentList '/c', 'start', '/min', 'powershell', '-NoExit', '-Command', 'omniroute'
  Write-Host "Waiting for OmniRoute to initialize on port 20128..." -ForegroundColor Cyan
  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
      $tcp = New-Object System.Net.Sockets.TcpClient
      $tcp.Connect('127.0.0.1', $port)
      $tcp.Close()
      $running = $true
      break
    } catch {}
  }
}

if ($running) {
  Write-Host " OmniRoute is Online on port 20128!" -ForegroundColor Green
} else {
  Write-Host " Warning: OmniRoute could not be reached" -ForegroundColor Red
}

$profileDir = "$env:USERPROFILE\.claude\profiles\meta-combo-ai"
$env:CLAUDE_CONFIG_DIR = $profileDir
$env:ANTHROPIC_AUTH_TOKEN = "dummy"
Remove-Item env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue

$projectDir = if ($TargetDir -and (Test-Path $TargetDir)) { $TargetDir } else { (Resolve-Path "$PSScriptRoot\..").Path }
Set-Location $projectDir

$claudeExe = "$env:USERPROFILE\AppData\Local\Microsoft\WinGet\Packages\Anthropic.ClaudeCode_Microsoft.Winget.Source_8wekyb3d8bbwe\claude.exe"
if (-not (Test-Path $claudeExe)) {
  $cmdPath = (Get-Command claude -ErrorAction SilentlyContinue).Source
  if ($cmdPath) { $claudeExe = $cmdPath }
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  JARVIS Coding Agent Launcher" -ForegroundColor Green
Write-Host "  Profile:   META-COMBO-AI (Kiro GLM-5)" -ForegroundColor Yellow
Write-Host "  Directory: $PWD" -ForegroundColor Yellow
Write-Host "  Gateway:   http://localhost:20128" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

& "$claudeExe"
