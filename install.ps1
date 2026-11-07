# netconfig-skill installer for Windows (PowerShell 5.1+ / PowerShell 7)
#
#   irm https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.ps1 | iex
#
# With options, download first:
#   irm https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.ps1 -OutFile install.ps1
#   .\install.ps1 -Project      # install into the current project (.agents\skills, .claude\skills)
#   .\install.ps1 -Uninstall    # remove from every location this script manages
#   .\install.ps1 -DryRun       # show what would happen
#
# Installs skills\network-config into %USERPROFILE%\.agents\skills (shared folder read by Codex, Cursor,
# Copilot, Gemini CLI, OpenCode, Goose, Amp, Kilo, Roo, Qwen, Droid, Windsurf/Devin and others), plus the
# private folder of each of these agents you have installed: Claude Code, Antigravity, Cline, Kiro, Trae,
# Hermes, Continue.
param([switch]$Project, [switch]$Uninstall, [switch]$DryRun)
$ErrorActionPreference = 'Stop'
$Repo = 'Lumax-Solutions/netconfig-skill'; $Branch = 'main'; $Name = 'network-config'

$targets = @()
if ($Project) {
    $targets += (Join-Path $PWD '.agents\skills'), (Join-Path $PWD '.claude\skills')
} else {
    $H = $env:USERPROFILE
    $targets += (Join-Path $H '.agents\skills')
    $map = [ordered]@{
        '.claude'   = '.claude\skills'
        '.gemini'   = '.gemini\config\skills'   # Google Antigravity
        '.cline'    = '.cline\skills'
        '.kiro'     = '.kiro\skills'
        '.trae'     = '.trae\skills'
        '.trae-cn'  = '.trae-cn\skills'
        '.hermes'   = '.hermes\skills'
        '.continue' = '.continue\skills'
    }
    foreach ($k in $map.Keys) { if (Test-Path (Join-Path $H $k)) { $targets += (Join-Path $H $map[$k]) } }
}

if ($Uninstall) {
    foreach ($t in $targets) {
        $d = Join-Path $t $Name
        if (Test-Path (Join-Path $d 'SKILL.md')) {
            Write-Host "Removing $d"
            if (-not $DryRun) { Remove-Item -Recurse -Force $d }
        }
    }
    Write-Host 'Done.'; return
}

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("netconfig-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    Write-Host "Downloading $Repo ($Branch)..."
    $zip = Join-Path $tmp 'repo.zip'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/$Repo/archive/refs/heads/$Branch.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $src = Get-ChildItem -Path $tmp -Directory -Recurse -Depth 3 |
        Where-Object { $_.Name -eq $Name -and $_.Parent.Name -eq 'skills' } | Select-Object -First 1
    if (-not $src -or -not (Test-Path (Join-Path $src.FullName 'SKILL.md'))) { throw "Could not find skills\$Name\SKILL.md in the download." }

    foreach ($t in $targets) {
        $dest = Join-Path $t $Name
        Write-Host "Installing into $dest"
        if ($DryRun) { continue }
        New-Item -ItemType Directory -Force -Path $t | Out-Null
        if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
        Copy-Item -Recurse -Path $src.FullName -Destination $dest
        $ev = Join-Path $dest 'evals'
        if (Test-Path $ev) { Remove-Item -Recurse -Force $ev }
    }
    Write-Host ''
    Write-Host "Installed netconfig-skill into $($targets.Count) location(s). Restart your agent, then ask:"
    Write-Host '  "Which skills do you have? Use network-config to audit this Cisco config: ..."'
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
