# Run as Administrator.
param()

$ErrorActionPreference = "Stop"

function Assert-Admin {
  $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script as Administrator."
  }
}

function Copy-VoiceKeys {
  param(
    [string]$Source,
    [string]$Destination
  )
  if (-not (Test-Path $Source)) {
    Write-Warning "Source not found: $Source"
    return
  }
  if (-not (Test-Path $Destination)) {
    New-Item -Path $Destination -Force | Out-Null
  }
  Get-ChildItem -Path $Source | ForEach-Object {
    $destPath = Join-Path $Destination $_.PSChildName
    Copy-Item -Path $_.PSPath -Destination $destPath -Recurse -Force
  }
  Write-Host "Copied voices from $Source to $Destination"
}

try {
  Assert-Admin
  Copy-VoiceKeys -Source "HKLM:\SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens" `
                 -Destination "HKLM:\SOFTWARE\Microsoft\Speech\Voices\Tokens"
  Copy-VoiceKeys -Source "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Speech_OneCore\Voices\Tokens" `
                 -Destination "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Speech\Voices\Tokens"

  Write-Host "`nDone. Restart the app to reload voices."
} catch {
  Write-Error $_
  exit 1
}
