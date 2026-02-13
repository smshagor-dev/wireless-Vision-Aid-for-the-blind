param(
  [Parameter(Mandatory = $false)]
  [string[]]$Languages = @("en-US", "ru-RU"),
  [switch]$CopyToSettings
)

function Assert-Admin {
  $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script as Administrator."
  }
}

function Install-LanguageWithSpeech {
  param([string]$LangCode, [bool]$CopySettings)

  Write-Host "=== Installing language: $LangCode ==="

  if ($CopySettings) {
    Install-Language -Language $LangCode -CopyToSettings -ErrorAction Stop | Out-Null
  } else {
    Install-Language -Language $LangCode -ErrorAction Stop | Out-Null
  }

  $caps = @(
    "Language.Speech~~~$LangCode~0.0.1.0",
    "Language.TextToSpeech~~~$LangCode~0.0.1.0"
  )

  foreach ($cap in $caps) {
    try {
      Add-WindowsCapability -Online -Name $cap -ErrorAction Stop | Out-Null
      Write-Host "Installed capability: $cap"
    } catch {
      Write-Warning "Capability not installed (may be unavailable on this edition): $cap"
    }
  }
}

function Show-InstalledVoices {
  Add-Type -AssemblyName System.Speech
  $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
  Write-Host "`nInstalled voices:"
  $s.GetInstalledVoices() | ForEach-Object {
    $v = $_.VoiceInfo
    Write-Host (" - " + $v.Name + " | " + $v.Culture.Name)
  }
}

try {
  Assert-Admin
  foreach ($lang in $Languages) {
    Install-LanguageWithSpeech -LangCode $lang -CopySettings:$CopyToSettings.IsPresent
  }

  Write-Host "`nLanguage install complete."
  Show-InstalledVoices
  Write-Host "`nRecommended: Restart the device for all voices to become available."
} catch {
  Write-Error $_
  exit 1
}
