#!/usr/bin/env bash
# Checks the Hermes support in install.sh and install.ps1 without touching your real folders:
# every case runs with a temporary HOME / HERMES_HOME / LOCALAPPDATA and the local checkout as source.
#
#   bash tests/install/hermes_install_test.sh            # install.sh (+ install.ps1 if pwsh is installed)
#   HERMES_REAL=1 bash tests/install/hermes_install_test.sh   # also check the copy with the real `hermes` CLI
#
# Cases: copy fallback (no hermes on PATH), dry-run paths (HERMES_HOME set / unset / Windows default /
# legacy Windows home / profile), the `hermes skills install` path with a stub hermes (one call with
# --force; CAUTION -> hub install + note, DANGEROUS -> abort without copying, rate limit -> copy and a
# later re-run switches to hub, --no-force -> no --force and a CAUTION block copies), uninstall (copy,
# hub, old wrong Windows path).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PASS=0; FAIL=0
ok()   { echo "PASS $*"; PASS=$((PASS + 1)); }
bad()  { echo "FAIL $*"; FAIL=$((FAIL + 1)); }
check() { local name="$1"; shift; if "$@"; then ok "$name"; else bad "$name"; fi; }
has()  { grep -qF -- "$2" <<<"$1"; }
hasnt() { ! grep -qF -- "$2" <<<"$1"; }

# PATH for the installers: basic tools plus pwsh, but no `hermes` unless a case adds the stub
TOOLS="$(mktemp -d)"
command -v pwsh >/dev/null 2>&1 && ln -s "$(command -v pwsh)" "$TOOLS/pwsh"
BASEPATH="$TOOLS:/usr/bin:/bin"

fresh() { T="$(mktemp -d)"; mkdir -p "$T/home" "$T/hh" "$T/la"; }
sh_run() {  # sh_run <extra env...> -- <installer args...>
  local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  env -i PATH="$PATH_OVERRIDE" HOME="$T/home" "${envs[@]}" bash "$ROOT/install.sh" --source "$ROOT" "$@" 2>&1
}
ps_run() {
  local envs=(); while [ "$1" != "--" ]; do envs+=("$1"); shift; done; shift
  env -i PATH="$PATH_OVERRIDE" HOME="$T/home" "${envs[@]}" pwsh -NoProfile -NonInteractive -File "$ROOT/install.ps1" -Source "$ROOT" "$@" 2>&1
}

# A stub `hermes` that prints what Hermes 0.19 prints. STUB_MODE:
#   ok (default) installs; caution = blocked unless --force (what Hermes does with this skill);
#   dangerous = always blocked; ratelimit = GitHub rate limit, nothing installed. All exit 0, like Hermes.
STUB="$(mktemp -d)"
cat > "$STUB/hermes" <<'STUBEOF'
#!/usr/bin/env bash
echo "stub hermes $*" >> "$STUB_LOG"
home="${HERMES_HOME:-$HOME/.hermes}"
if [ "$1" = "-p" ]; then home="$home/profiles/$2"; shift 2; fi
sk="$home/skills"
case "$1 $2" in
  "skills install")
    cat=""; force=0; prev=""
    for a in "$@"; do [ "$prev" = --category ] && cat="$a"; [ "$a" = --force ] && force=1; prev="$a"; done
    case "${STUB_MODE:-ok}" in
      ratelimit) echo "GitHub API rate limit exhausted (unauthenticated: 60 req/hr)."
                 echo "Error: Could not fetch '$3' from any source."; exit 0 ;;
      dangerous) echo "Scan: network-config (x/community)  Verdict: DANGEROUS"
                 echo "Installation blocked: Blocked (community source + dangerous verdict, 3 findings). --force does"
                 echo "not override a dangerous verdict."; exit 0 ;;
      caution)   echo "Scan: network-config (x/community)  Verdict: CAUTION"
                 # Hermes prints the policy decision even when --force then installs it
                 echo "Decision: BLOCKED — Blocked (community source + caution verdict, 16 findings). Use --force to override."
                 if [ "$force" = 0 ]; then
                   echo "Installation blocked: Blocked (community source + caution verdict, 16 findings). Use --force to"
                   echo "override."; exit 0
                 fi
                 echo "Installed: $cat/network-config" ;;
    esac
    mkdir -p "$sk/$cat/network-config" "$sk/.hub"
    printf -- '---\nname: network-config\n---\n' > "$sk/$cat/network-config/SKILL.md"
    echo '{"version": 1, "installed": {"network-config": {"install_path": "x"}}}' > "$sk/.hub/lock.json" ;;
  "skills uninstall")
    read -r answer; [ "$answer" = y ] || exit 0
    rm -rf "$sk/networking/network-config"; echo '{"version": 1, "installed": {}}' > "$sk/.hub/lock.json" ;;
esac
STUBEOF
chmod +x "$STUB/hermes"

run_suite() {   # run_suite sh|ps
  local kind="$1" R rc; local I="${kind}_run"
  local DRY="--dry-run" UN="--uninstall" PROF="--hermes-profile" NOCLI="--no-hermes-cli" NOFORCE="--no-force"
  if [ "$kind" = ps ]; then DRY="-DryRun"; UN="-Uninstall"; PROF="-HermesProfile"; NOCLI="-NoHermesCli"; NOFORCE="-NoForce"; fi
  local HUBDIR; local CMD="hermes skills install Lumax-Solutions/netconfig-skill/skills/network-config --category networking --yes"
  echo "== $kind =="
  PATH_OVERRIDE="$BASEPATH"

  # 1. copy fallback: no hermes on PATH, HERMES_HOME set
  fresh; R="$($I HERMES_HOME="$T/hh" --)"
  D="$T/hh/skills/networking/network-config"
  check "$kind copy: SKILL.md in \$HERMES_HOME/skills/networking/network-config" test -f "$D/SKILL.md"
  check "$kind copy: references copied" test -f "$D/references/fortigate.md"
  check "$kind copy: evals/ left out" test ! -e "$D/evals"
  check "$kind copy: message names the method" has "$R" "Hermes: copied to"
  check "$kind copy: says copies don't get 'hermes skills update'" has "$R" "won't update it"
  check "$kind copy: message says start a new session" has "$R" "start a new session"
  check "$kind copy: Hermes not installed into ~/.hermes" test ! -e "$T/home/.hermes"
  R="$($I HERMES_HOME="$T/hh" -- $UN)"
  check "$kind uninstall: copy removed" test ! -e "$D"

  # 2. dry-run paths
  fresh; R="$($I HERMES_HOME="$T/hh" -- $DRY)"
  check "$kind dry-run (HERMES_HOME set): shows \$HERMES_HOME path" has "$R" "$T/hh/skills/networking/network-config"
  check "$kind dry-run: changes nothing" test -z "$(ls -A "$T/hh")"
  check "$kind dry-run: says 'would copy'" has "$R" "Hermes: would copy to"
  fresh; mkdir -p "$T/home/.hermes"; R="$($I -- $DRY)"
  check "$kind dry-run (unset, Linux/macOS): ~/.hermes/skills/networking/network-config" has "$R" "$T/home/.hermes/skills/networking/network-config"
  fresh; mkdir -p "$T/la/hermes"; R="$($I NETCONFIG_TEST_WINDOWS=1 LOCALAPPDATA="$T/la" USERPROFILE="$T/home" -- $DRY)"
  check "$kind dry-run (unset, Windows): %LOCALAPPDATA%\\hermes" has "$R" "$T/la/hermes/skills/networking/network-config"
  fresh; mkdir -p "$T/home/.hermes"; touch "$T/home/.hermes/config.yaml"
  R="$($I NETCONFIG_TEST_WINDOWS=1 LOCALAPPDATA="$T/la" USERPROFILE="$T/home" -- $DRY)"
  check "$kind dry-run (Windows, legacy ~/.hermes with config.yaml)" has "$R" "$T/home/.hermes/skills/networking/network-config"
  fresh; mkdir -p "$T/home/.hermes"   # legacy folder without config.yaml is ignored on Windows
  R="$($I NETCONFIG_TEST_WINDOWS=1 LOCALAPPDATA="$T/la" USERPROFILE="$T/home" -- $DRY)"
  check "$kind dry-run (Windows, ~/.hermes without config.yaml ignored)" hasnt "$R" "$T/home/.hermes/skills/networking"
  fresh; mkdir -p "$T/hh/profiles/work"; R="$($I HERMES_HOME="$T/hh" -- $DRY $PROF work)"
  check "$kind dry-run (profile): profiles/work/skills path" has "$R" "$T/hh/profiles/work/skills/networking/network-config"
  fresh; R="$($I HERMES_HOME="$T/nonexistent" -- $DRY)"
  check "$kind no Hermes home and no hermes on PATH: Hermes skipped" hasnt "$R" "Hermes:"

  # 3. hermes on PATH (stub). One call, with --force (unless --no-force).
  PATH_OVERRIDE="$STUB:$BASEPATH"
  calls() { grep -c "skills install" "$STUB_LOG" 2>/dev/null || echo 0; }
  fresh; export STUB_LOG="$T/stub.log"; HUBDIR="$T/hh/skills/networking/network-config"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" -- $DRY)"
  check "$kind dry-run with hermes: shows the exact command (with --force)" has "$R" "$CMD --force"
  check "$kind dry-run with hermes: explains dangerous / copy" bash -c "grep -q 'DANGEROUS' <<<\"\$0\" && grep -qF '$HUBDIR' <<<\"\$0\"" "$R"
  check "$kind dry-run with hermes: hermes not called" test ! -e "$STUB_LOG"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" -- $DRY $NOFORCE)"
  check "$kind dry-run --no-force: command without --force" bash -c "grep -qF -- '$CMD' <<<\"\$0\" && ! grep -qF -- '$CMD --force' <<<\"\$0\"" "$R"
  # plain hub install (scanner safe), re-install, uninstall
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" --)"
  check "$kind hub: installed into the networking category" test -f "$HUBDIR/SKILL.md"
  check "$kind hub: a single call, with --force" bash -c "[ \$(grep -c 'skills install' '$STUB_LOG') = 1 ] && grep -q -- '--category networking --yes --force$' '$STUB_LOG'"
  check "$kind hub: message names the method" has "$R" "installed with 'hermes skills install'"
  check "$kind hub (safe verdict): no CAUTION note" hasnt "$R" "rated it CAUTION"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" --)"
  check "$kind hub: re-install is again one call with --force" bash -c "[ \$(grep -c 'skills install' '$STUB_LOG') = 2 ] && [ \$(grep -c -- '--yes --force$' '$STUB_LOG') = 2 ]"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" -- $UN)"
  check "$kind hub uninstall: hermes skills uninstall called" grep -q "skills uninstall network-config" "$STUB_LOG"
  check "$kind hub uninstall: folder gone" test ! -e "$HUBDIR"
  # profile
  fresh; export STUB_LOG="$T/stub.log"; mkdir -p "$T/hh/profiles/work"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" -- $PROF work)"
  check "$kind hub (profile): hermes -p work skills install" grep -q "^stub hermes -p work skills install" "$STUB_LOG"
  check "$kind hub (profile): installed in the profile" test -f "$T/hh/profiles/work/skills/networking/network-config/SKILL.md"
  # scanner CAUTION -> one call with --force, hub install, explanation afterwards
  fresh; export STUB_LOG="$T/stub.log"; HUBDIR="$T/hh/skills/networking/network-config"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" STUB_MODE=caution --)"
  check "$kind caution: a single call, with --force" bash -c "[ \$(grep -c 'skills install' '$STUB_LOG') = 1 ] && grep -q -- '--yes --force$' '$STUB_LOG'"
  check "$kind caution: installed (hub)" bash -c "test -f '$HUBDIR/SKILL.md' && grep -q network-config '$T/hh/skills/.hub/lock.json'"
  check "$kind caution: ends as a hub install" has "$R" "installed with 'hermes skills install'"
  check "$kind caution: explains the verdict" has "$R" "rated it CAUTION"
  check "$kind caution: points to hermes skills inspect" has "$R" "hermes skills inspect Lumax-Solutions/netconfig-skill/skills/network-config"
  check "$kind caution: explanation comes after the install" bash -c "awk '/Installed: networking/{i=NR} /rated it CAUTION/{c=NR} END{exit !(i && c > i)}' <<<\"\$0\"" "$R"
  # CAUTION + --no-force -> one call without --force, copy
  fresh; export STUB_LOG="$T/stub.log"; HUBDIR="$T/hh/skills/networking/network-config"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" STUB_MODE=caution -- $NOFORCE)"
  check "$kind caution + no-force: one call, without --force" bash -c "[ \$(grep -c 'skills install' '$STUB_LOG') = 1 ] && ! grep -q -- '--force' '$STUB_LOG'"
  check "$kind caution + no-force: copied instead" test -f "$HUBDIR/references/cisco-ios.md"
  check "$kind caution + no-force: says so" has "$R" "blocked by the scanner (CAUTION)"
  check "$kind caution + no-force: says copies don't get 'hermes skills update'" has "$R" "won't update it"
  # scanner DANGEROUS (even with --force) -> non-zero exit, nothing copied for Hermes, issue link
  fresh; export STUB_LOG="$T/stub.log"; HUBDIR="$T/hh/skills/networking/network-config"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" STUB_MODE=dangerous --)"; rc=$?
  check "$kind dangerous: non-zero exit (got $rc)" test "$rc" != 0
  check "$kind dangerous: nothing copied for Hermes" test ! -e "$HUBDIR"
  check "$kind dangerous: a single call" bash -c "[ \$(grep -c 'skills install' '$STUB_LOG') = 1 ]"
  check "$kind dangerous: tells the user to open an issue" has "$R" "open an issue"
  # rate limit -> one call, copy fallback, reset + re-run + GITHUB_TOKEN hints; a later re-run switches to hub
  fresh; export STUB_LOG="$T/stub.log"; HUBDIR="$T/hh/skills/networking/network-config"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" STUB_MODE=ratelimit --)"
  check "$kind rate limit: a single call" bash -c "[ \$(grep -c 'skills install' '$STUB_LOG') = 1 ]"
  check "$kind rate limit: falls back to copy" test -f "$HUBDIR/references/cisco-ios.md"
  check "$kind rate limit: says it resets within an hour" has "$R" "resets within an hour"
  check "$kind rate limit: says re-running switches to a hub install" has "$R" "re-run this"
  check "$kind rate limit: GITHUB_TOKEN hint" has "$R" "GITHUB_TOKEN"
  check "$kind rate limit: says copies don't get 'hermes skills update'" has "$R" "won't update it"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" STUB_MODE=caution --)"
  check "$kind re-run after rate limit: now a hub install" bash -c "grep -q network-config '$T/hh/skills/.hub/lock.json' && grep -q \"installed with 'hermes skills install'\" <<<\"\$0\"" "$R"
  check "$kind re-run after rate limit: the copy was replaced (no references/ left from it)" test ! -e "$HUBDIR/references"
  # --no-hermes-cli
  fresh; export STUB_LOG="$T/stub.log"
  R="$($I HERMES_HOME="$T/hh" STUB_LOG="$STUB_LOG" -- $NOCLI)"
  check "$kind no-hermes-cli: copies, never calls hermes" bash -c "test -f '$T/hh/skills/networking/network-config/SKILL.md' && test ! -e '$STUB_LOG'"

  # 4. old wrong Windows path is cleaned up
  PATH_OVERRIDE="$BASEPATH"
  fresh; mkdir -p "$T/la/hermes" "$T/home/.hermes/skills"; cp -R "$ROOT/skills/network-config" "$T/home/.hermes/skills/"
  R="$($I NETCONFIG_TEST_WINDOWS=1 LOCALAPPDATA="$T/la" USERPROFILE="$T/home" -- $UN)"
  check "$kind uninstall (Windows): old %USERPROFILE%\\.hermes\\skills\\network-config removed" test ! -e "$T/home/.hermes/skills/network-config"
}

run_suite sh
if command -v pwsh >/dev/null 2>&1; then run_suite ps; else echo "pwsh not found: install.ps1 cases skipped"; fi

# 5. the real Hermes CLI sees the copied skill (offline: no GitHub needed)
if [ "${HERMES_REAL:-0}" = 1 ]; then
  echo "== real hermes =="
  fresh; PATH_OVERRIDE="$BASEPATH"
  sh_run HERMES_HOME="$T/hh" -- --no-hermes-cli >/dev/null
  L="$(HERMES_HOME="$T/hh" COLUMNS=200 hermes skills list --source local 2>&1)"; echo "$L" | tail -5
  check "real hermes: 'hermes skills list' shows network-config in category networking" \
    bash -c "grep -E 'network-config +│ +networking +│ +local' <<<\"\$0\"" "$L"
fi

echo; echo "$PASS passed, $FAIL failed"
[ "$FAIL" = 0 ]
