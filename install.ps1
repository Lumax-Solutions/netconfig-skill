# netconfig-skill installer for Windows (PowerShell 5.1+ / PowerShell 7)
#
#   irm https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.ps1 | iex
#
# With options, download first:
#   irm https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.ps1 -OutFile install.ps1
#   .\install.ps1 -Project               # install into the current project (.agents\skills, .claude\skills)
#   .\install.ps1 -Uninstall             # remove from every location this script manages
#   .\install.ps1 -DryRun                # show the exact paths and commands, change nothing
#   .\install.ps1 -HermesProfile work    # install into / remove from that Hermes profile
#   .\install.ps1 -NoHermesCli           # for Hermes, copy the folder even if `hermes` is available
#   .\install.ps1 -NoForce               # run `hermes skills install` without --force; a CAUTION block copies instead
#   .\install.ps1 -Source C:\path\repo   # use a local checkout instead of downloading
#
# Installs skills\network-config into %USERPROFILE%\.agents\skills (shared folder read by Codex, Cursor,
# Copilot, Gemini CLI, OpenCode, Goose, Amp, Kilo, Roo, Qwen, Droid, Windsurf/Devin and others), plus the
# private folder of each of these agents you have installed: Claude Code, Antigravity, Cline, Kiro, Trae,
# Continue.
# Hermes Agent does NOT read ~\.agents\skills by default. If Hermes is installed (its home folder exists or
# `hermes` is on PATH) the skill is installed with `hermes skills install ... --category networking`, so
# `hermes skills update` works. It passes --force: Hermes' scanner rates this skill CAUTION (it documents
# sudo/system commands), and --force never overrides a DANGEROUS verdict, which stops the script with
# nothing copied. Other failures (rate limit, offline, older Hermes) fall back to copying the folder to
# <hermes-home>\skills\networking\network-config; re-run later to switch to a hub install.
# Hermes home = $env:HERMES_HOME, else %LOCALAPPDATA%\hermes on Windows (a legacy %USERPROFILE%\.hermes is
# used only if it has a config.yaml and %LOCALAPPDATA%\hermes doesn't exist), else ~/.hermes elsewhere.
param([switch]$Project, [switch]$Uninstall, [switch]$DryRun, [string]$HermesProfile = '',
      [switch]$NoHermesCli, [switch]$NoForce, [string]$Source = '')
$ErrorActionPreference = 'Stop'
$script:HermesAbort = $false
$Repo = 'Lumax-Solutions/netconfig-skill'; $Branch = 'main'; $Name = 'network-config'
$HubId = "$Repo/skills/$Name"; $Category = 'networking'

function J { $p = $args[0]; foreach ($x in $args[1..($args.Count)]) { if ($x) { $p = [IO.Path]::Combine($p, $x) } }; $p }
function Test-Ours($d) {
    $f = J $d 'SKILL.md'
    (Test-Path $f) -and ((Get-Content -Raw $f) -match "(?m)^name: $Name\s*$")
}

$OnWindows = ($PSVersionTable.PSEdition -eq 'Desktop') -or $IsWindows -or ($env:NETCONFIG_TEST_WINDOWS -eq '1')
$H = $env:USERPROFILE; if (-not $H) { $H = $HOME }

# ---------------------------------------------------------------- Hermes location
if ($env:HERMES_HOME) { $HH = $env:HERMES_HOME }
elseif ($OnWindows) {
    $la = $env:LOCALAPPDATA; if (-not $la) { $la = J $H 'AppData' 'Local' }
    $HH = J $la 'hermes'
    $legacy = J $H '.hermes'
    if (-not (Test-Path $HH) -and (Test-Path (J $legacy 'config.yaml'))) { $HH = $legacy }
} else { $HH = J $H '.hermes' }
if ($HermesProfile) { $HSK = J $HH 'profiles' $HermesProfile 'skills' } else { $HSK = J $HH 'skills' }
$HDest = J $HSK $Category $Name
$HCli = (-not $NoHermesCli) -and [bool](Get-Command hermes -ErrorAction SilentlyContinue)
$Hermes = (-not $Project) -and ((Test-Path $HH) -or $HCli)
$HPrefix = @(); if ($HermesProfile) { $HPrefix = @('-p', $HermesProfile) }
function Show-Hermes { 'hermes ' + (($HPrefix + $args) -join ' ') }
function Test-HubInstalled {
    $lock = J $HSK '.hub' 'lock.json'
    (Test-Path $lock) -and ((Get-Content -Raw $lock) -match "`"$Name`"")
}
# Run `hermes skills install`, show its output, return ok | caution | dangerous | failed.
# Hermes can exit 0 when it didn't install, so read the result instead of the exit code.
function Invoke-HermesInstall($hargs) {
    $old = $env:COLUMNS; $env:COLUMNS = '400'
    try { $out = (& hermes @HPrefix @hargs 2>&1 | Out-String) } catch { $out = "$_" } finally { $env:COLUMNS = $old }
    Write-Host $out
    $flat = ($out -replace '\s+', ' ')
    $script:HVerdict = ''
    if ($flat -match 'Verdict: (SAFE|CAUTION|DANGEROUS)') { $script:HVerdict = $Matches[1].ToLower() }
    $script:HRate = $flat -match 'rate limit'
    $blocked = $flat -match 'Installation blocked'
    if ($blocked -and ($flat -match 'dangerous verdict|Verdict: DANGEROUS')) { return 'dangerous' }
    if ($blocked -and ($flat -match 'caution verdict|Verdict: CAUTION')) { return 'caution' }
    $found = Get-ChildItem -Path $HSK -Filter 'SKILL.md' -Recurse -Depth 3 -ErrorAction SilentlyContinue |
        Where-Object { $_.Directory.Name -eq $Name }
    if (-not ($flat -match 'Installation blocked|rate limit|(^|\s)Error:?\s') -and (Test-HubInstalled) -and $found) { return 'ok' }
    return 'failed'
}
function Get-HermesCopies {
    $c = @((J $HSK $Category $Name), (J $HSK $Name))
    $old = J $H '.hermes'
    if ($OnWindows -and ($HH -ne $old)) { $c += (J $old 'skills' $Name) }   # old wrong path
    $c
}

# ---------------------------------------------------------------- other agents
$targets = @()
if ($Project) {
    $targets += (J $PWD.Path '.agents' 'skills'), (J $PWD.Path '.claude' 'skills')
} else {
    $targets += (J $H '.agents' 'skills')
    $map = [ordered]@{
        '.claude'   = @('.claude', 'skills')
        '.gemini'   = @('.gemini', 'config', 'skills')   # Google Antigravity
        '.cline'    = @('.cline', 'skills')
        '.kiro'     = @('.kiro', 'skills')
        '.trae'     = @('.trae', 'skills')
        '.trae-cn'  = @('.trae-cn', 'skills')
        '.continue' = @('.continue', 'skills')
    }
    foreach ($k in $map.Keys) { if (Test-Path (J $H $k)) { $targets += (J $H @($map[$k])[0] @($map[$k])[1] @($map[$k])[2]) } }
}

if ($Uninstall) {
    foreach ($t in $targets) {
        $d = J $t $Name
        if (Test-Path (J $d 'SKILL.md')) {
            Write-Host "Removing $d"
            if (-not $DryRun) { Remove-Item -Recurse -Force $d }
        }
    }
    if ($Hermes) {
        if ($HCli -and (Test-HubInstalled)) {
            $cmd = Show-Hermes 'skills' 'uninstall' $Name
            Write-Host "Hermes: $cmd"
            if ($DryRun) { Write-Host "  (dry-run) 'y' | $cmd" }
            else { try { 'y' | & hermes @HPrefix skills uninstall $Name } catch { Write-Host $_ } }
        }
        foreach ($d in Get-HermesCopies) {
            if (Test-Ours $d) { Write-Host "Removing $d"; if (-not $DryRun) { Remove-Item -Recurse -Force $d } }
        }
        if (-not $DryRun -and (Test-HubInstalled)) {
            Write-Host "Hermes still lists $Name as hub-installed; run: $(Show-Hermes 'skills' 'uninstall' $Name)"
        }
        Write-Host 'Hermes: start a new session (or /reset) for the change to take effect.'
    }
    Write-Host 'Done.'; return
}

# ---------------------------------------------------------------- get the skill
$tmp = J ([IO.Path]::GetTempPath()) ("netconfig-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    if ($Source) {
        if (Test-Path (J $Source 'SKILL.md')) { $srcPath = (Resolve-Path $Source).Path }
        else { $srcPath = J (Resolve-Path $Source).Path 'skills' $Name }
    } else {
        Write-Host "Downloading $Repo ($Branch)..."
        $zip = J $tmp 'repo.zip'
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/$Repo/archive/refs/heads/$Branch.zip" -OutFile $zip
        Expand-Archive -Path $zip -DestinationPath $tmp -Force
        $src = Get-ChildItem -Path $tmp -Directory -Recurse -Depth 3 |
            Where-Object { $_.Name -eq $Name -and $_.Parent.Name -eq 'skills' } | Select-Object -First 1
        $srcPath = if ($src) { $src.FullName } else { '' }
    }
    if (-not $srcPath -or -not (Test-Path (J $srcPath 'SKILL.md'))) { throw "Could not find skills\$Name\SKILL.md." }

    function Copy-Skill($dest) {
        if ($DryRun) { Write-Host "  (dry-run) copy $srcPath -> $dest (without evals)"; return }
        New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
        if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
        Copy-Item -Recurse -Path $srcPath -Destination $dest
        $ev = J $dest 'evals'
        if (Test-Path $ev) { Remove-Item -Recurse -Force $ev }   # test cases are not needed at runtime
    }

    foreach ($t in $targets) {
        $dest = J $t $Name
        Write-Host "Installing into $dest"
        Copy-Skill $dest
    }

    # ------------------------------------------------------------ Hermes
    $HMsg = ''
    if ($Hermes) {
        if ($HermesProfile -and -not (Test-Path (J $HH 'profiles' $HermesProfile)) -and -not $DryRun -and -not $HCli) {
            Write-Warning "Hermes profile '$HermesProfile' not found at $(J $HH 'profiles' $HermesProfile); skipping Hermes."
        } else {
            $method = ''
            if ($HCli) {
                $hargs = @('skills', 'install', $HubId, '--category', $Category, '--yes')
                # One attempt with --force: Hermes' scanner rates this skill CAUTION (it documents sudo/system
                # commands), and --force never overrides a DANGEROUS verdict, so a first try without it adds no
                # safety and doubles the GitHub API calls (60/hour without a token).
                if ((-not $NoForce) -or (Test-HubInstalled)) { $hargs += '--force' }
                $cmd = Show-Hermes @hargs
                Write-Host "Hermes: $cmd"
                if ($DryRun) {
                    Write-Host "  (dry-run) $cmd"
                    Write-Host "  (dry-run) if Hermes' scanner says DANGEROUS: stop, nothing is copied"
                    if ($NoForce) { Write-Host "  (dry-run) if it blocks a CAUTION verdict (no --force): copy to $HDest" }
                    Write-Host "  (dry-run) if it fails for another reason (rate limit, offline, older Hermes): copy to $HDest"
                    $method = 'dry-run'
                } else {
                    # remove an older local copy so the hub install doesn't collide with it
                    if (-not (Test-HubInstalled)) { foreach ($d in Get-HermesCopies) { if (Test-Ours $d) { Remove-Item -Recurse -Force $d } } }
                    $r = Invoke-HermesInstall $hargs
                    switch ($r) {
                        'ok' {
                            $method = 'hub'
                            if ($script:HVerdict -eq 'caution') {
                                Write-Host "Hermes: the scanner rated it CAUTION because this network-admin skill documents sudo and other"
                                Write-Host "        system commands (it never runs them); installed with --force. Review it any time with:"
                                Write-Host "        hermes skills inspect $HubId"
                            }
                        }
                        'dangerous' {
                            Write-Host "Hermes: the scanner rated it DANGEROUS, so it was NOT installed for Hermes (nothing was copied)." -ForegroundColor Red
                            Write-Host "        Please open an issue with the output above: https://github.com/$Repo/issues" -ForegroundColor Red
                            $script:HermesAbort = $true
                        }
                        'caution'   { Write-Host "Hermes: blocked by the scanner (CAUTION) and -NoForce was given; copying instead." }
                        default {
                            if ($script:HRate) {
                                Write-Host "Hermes: GitHub's API rate limit was hit (60 requests/hour without a token); it resets within an hour."
                            } else {
                                Write-Host "Hermes: 'hermes skills install' did not complete (offline, or an older Hermes?)."
                            }
                            Write-Host "        Copying instead. To switch the copy to an updatable hub install later, re-run this"
                            Write-Host "        installer (after the limit resets, or after adding GITHUB_TOKEN=<token> to $(J $HH '.env'))."
                        }
                    }
                }
            }
            if ($script:HermesAbort) { $method = 'abort' }
            if (-not $method) {
                Write-Host "Installing into $HDest"
                foreach ($d in Get-HermesCopies) {
                    if (($d -ne $HDest) -and (Test-Ours $d)) {
                        if ($DryRun) { Write-Host "  (dry-run) remove $d" } else { Remove-Item -Recurse -Force $d }
                    }
                }
                Copy-Skill $HDest
                $method = 'copy'
            }
            switch ($method) {
                'hub'     { $HMsg = "Hermes: installed with 'hermes skills install' (update later with: $(Show-Hermes 'skills' 'update' $Name))." }
                'copy'    { if ($DryRun) { $HMsg = "Hermes: would copy to $HDest." }
                            else { $HMsg = "Hermes: copied to $HDest. A copied skill is 'local': 'hermes skills update' won't update it; re-run this installer instead." } }
                'dry-run' { $HMsg = 'Hermes: would install as shown above.' }
                'abort'   { $HMsg = '' }
            }
        }
    }

    $n = $targets.Count; if ($HMsg) { $n++ }
    Write-Host ''
    Write-Host "Installed netconfig-skill into $n location(s). Restart your agent, then ask:"
    Write-Host '  "Which skills do you have? Use network-config to audit this Cisco config: ..."'
    if ($HMsg) {
        Write-Host $HMsg
        Write-Host "Hermes: start a new session (or /reset) to load it; check with: $(Show-Hermes 'skills' 'list')"
    }
} finally {
    Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
if ($script:HermesAbort) {
    # exit code 3 when run as a file; with `irm | iex` an exit would close the window, so throw instead
    if ($PSCommandPath) { exit 3 } else { throw 'Hermes scanner verdict DANGEROUS: network-config was not installed for Hermes.' }
}
