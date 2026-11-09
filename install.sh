#!/usr/bin/env bash
# netconfig-skill installer (macOS / Linux / WSL / Git Bash)
#
#   curl -fsSL https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.sh | bash
#
# Options (pass after `bash -s --` when piping):
#   --project               install into the current project (./.agents/skills, ./.claude/skills)
#                           instead of your home folder (Hermes has no project folder; skipped)
#   --uninstall             remove the skill from every location this script manages
#   --dry-run               show the exact paths and commands, change nothing
#   --hermes-profile NAME   install into / remove from that Hermes profile instead of the default
#   --no-hermes-cli         for Hermes, copy the folder even if the `hermes` command is available
#   --no-force              run `hermes skills install` without --force; if Hermes' scanner blocks the
#                           skill with a CAUTION verdict, copy it instead
#   --source DIR            use a local checkout (repo root or skills/network-config) instead of downloading
#
# What it does: downloads the latest skills/network-config folder from GitHub and copies it into
#   ~/.agents/skills/            (shared folder read by Codex, Cursor, Copilot, Gemini CLI, OpenCode, Goose,
#                                 Amp, Kilo, Roo, Qwen, Droid, Windsurf/Devin and others)
# plus the private folder of each of these agents that you have installed:
#   Claude Code, Antigravity, Cline, Kiro, Trae, Continue
# Hermes Agent does NOT read ~/.agents/skills by default. If Hermes is installed (its home folder exists
# or `hermes` is on PATH) the skill is installed with `hermes skills install ... --category networking`,
# with --force, so `hermes skills update` works. Hermes' scanner rates this skill CAUTION (it documents
# sudo/system commands); --force accepts that but never a DANGEROUS verdict, which stops the script with
# nothing copied. Other failures (rate limit, offline, older Hermes) fall back to copying the folder to
# <hermes-home>/skills/networking/network-config; re-run later to switch to a hub install.
# Hermes home = $HERMES_HOME, else %LOCALAPPDATA%\hermes on native Windows (Git Bash), else ~/.hermes.
set -euo pipefail

REPO="Lumax-Solutions/netconfig-skill"
BRANCH="main"
NAME="network-config"
HUB_ID="$REPO/skills/$NAME"
CATEGORY="networking"
MODE="global"; ACTION="install"; DRY=0; PROFILE=""; NO_CLI=0; NO_FORCE=0; SOURCE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --project) MODE="project" ;;
    --uninstall) ACTION="uninstall" ;;
    --dry-run) DRY=1 ;;
    --hermes-profile) PROFILE="${2:?--hermes-profile needs a name}"; shift ;;
    --hermes-profile=*) PROFILE="${1#*=}" ;;
    --no-hermes-cli) NO_CLI=1 ;;
    --no-force) NO_FORCE=1 ;;
    --source) SOURCE="${2:?--source needs a folder}"; shift ;;
    --source=*) SOURCE="${1#*=}" ;;
    -h|--help) sed -n '2,31p' "$0" 2>/dev/null || true; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

run() { if [ "$DRY" = 1 ]; then echo "  (dry-run) $*"; else "$@"; fi; }
is_ours() { [ -f "$1/SKILL.md" ] && grep -q "^name: $NAME\$" "$1/SKILL.md"; }

# ---------------------------------------------------------------- Hermes location
native_windows() {
  [ "${NETCONFIG_TEST_WINDOWS:-}" = 1 ] && return 0          # test hook used by CI
  case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) return 0 ;; esac
  return 1                                                     # WSL counts as Linux
}
to_posix() { if command -v cygpath >/dev/null 2>&1; then cygpath -u "$1"; else printf '%s' "$1"; fi; }
hermes_home() {
  if [ -n "${HERMES_HOME:-}" ]; then printf '%s' "$HERMES_HOME"; return; fi
  if native_windows; then
    local la="${LOCALAPPDATA:-$HOME/AppData/Local}"; la="$(to_posix "$la")"
    # legacy: an old Hermes home in %USERPROFILE%\.hermes, only if it is a real one
    if [ ! -d "$la/hermes" ] && [ -f "$HOME/.hermes/config.yaml" ]; then printf '%s' "$HOME/.hermes"; return; fi
    printf '%s' "$la/hermes"; return
  fi
  printf '%s' "$HOME/.hermes"
}
HH="$(hermes_home)"
if [ -n "$PROFILE" ]; then HSK="$HH/profiles/$PROFILE/skills"; else HSK="$HH/skills"; fi
HDEST="$HSK/$CATEGORY/$NAME"
HCLI=0; [ "$NO_CLI" = 0 ] && command -v hermes >/dev/null 2>&1 && HCLI=1
HERMES=0; { [ -d "$HH" ] || [ "$HCLI" = 1 ]; } && HERMES=1
[ "$MODE" = "project" ] && HERMES=0
hermes_cmd() { if [ -n "$PROFILE" ]; then echo hermes -p "$PROFILE" "$@"; else echo hermes "$@"; fi; }
hermes_run() { if [ -n "$PROFILE" ]; then hermes -p "$PROFILE" "$@"; else hermes "$@"; fi; }
# hermes_install <args...>: run `hermes skills install`, show its output, set HRESULT to
# ok | caution (blocked) | dangerous (blocked) | failed, HVERDICT to the scan verdict it printed
# (safe/caution/dangerous or empty) and HRATE=1 on a GitHub rate limit. Hermes can exit 0 when it
# didn't install, so read the result instead of the exit code.
hermes_install() {
  local out
  out="$(COLUMNS=400 hermes_run "$@" </dev/null 2>&1)"; printf '%s\n' "$out"
  out="$(printf '%s' "$out" | tr '\n' ' ' | tr -s ' ')"
  HVERDICT="$(grep -oiE 'Verdict: (SAFE|CAUTION|DANGEROUS)' <<<"$out" | head -n1 | awk '{print tolower($2)}' || true)"
  HRATE=0; grep -qiE 'rate limit' <<<"$out" && HRATE=1
  if grep -qi 'Installation blocked' <<<"$out" && grep -qiE 'dangerous verdict|Verdict: DANGEROUS' <<<"$out"; then
    HRESULT=dangerous
  elif grep -qi 'Installation blocked' <<<"$out" && grep -qiE 'caution verdict|Verdict: CAUTION' <<<"$out"; then
    HRESULT=caution
  elif ! grep -qiE 'Installation blocked|rate limit|^Error|[[:space:]]Error:' <<<"$out" && hub_installed \
       && find "$HSK" -maxdepth 3 -path "*/$NAME/SKILL.md" | grep -q .; then
    HRESULT=ok
  else HRESULT=failed; fi
}
hub_installed() { [ -f "$HSK/.hub/lock.json" ] && grep -q "\"$NAME\"" "$HSK/.hub/lock.json"; }
hermes_copies() {   # copies made by this script (current and older layouts, plus the old wrong Windows path)
  printf '%s\n' "$HSK/$CATEGORY/$NAME" "$HSK/$NAME"
  if native_windows && [ "$HH" != "$HOME/.hermes" ]; then printf '%s\n' "$HOME/.hermes/skills/$NAME"; fi
}

# ---------------------------------------------------------------- other agents
targets=()
if [ "$MODE" = "project" ]; then
  targets+=("$PWD/.agents/skills" "$PWD/.claude/skills")
else
  H="$HOME"
  targets+=("$H/.agents/skills")
  [ -d "$H/.claude" ]          && targets+=("$H/.claude/skills")
  [ -d "$H/.gemini" ]          && targets+=("$H/.gemini/config/skills")      # Google Antigravity
  [ -d "$H/.cline" ]           && targets+=("$H/.cline/skills")
  [ -d "$H/.kiro" ]            && targets+=("$H/.kiro/skills")
  [ -d "$H/.trae" ]            && targets+=("$H/.trae/skills")
  [ -d "$H/.trae-cn" ]         && targets+=("$H/.trae-cn/skills")
  [ -d "$H/.continue" ]        && targets+=("$H/.continue/skills")
fi

if [ "$ACTION" = "uninstall" ]; then
  for t in "${targets[@]}"; do
    if [ -f "$t/$NAME/SKILL.md" ]; then echo "Removing $t/$NAME"; run rm -rf -- "$t/$NAME"; fi
  done
  if [ "$HERMES" = 1 ]; then
    if [ "$HCLI" = 1 ] && hub_installed; then
      echo "Hermes: $(hermes_cmd skills uninstall "$NAME")"
      if [ "$DRY" = 1 ]; then echo "  (dry-run) printf 'y\\n' | $(hermes_cmd skills uninstall "$NAME")"
      else printf 'y\n' | hermes_run skills uninstall "$NAME" || true; fi
    fi
    while IFS= read -r d; do
      if is_ours "$d"; then echo "Removing $d"; run rm -rf -- "$d"; fi
    done < <(hermes_copies)
    [ "$DRY" = 1 ] || ! hub_installed || echo "Hermes still lists $NAME as hub-installed; run: $(hermes_cmd skills uninstall "$NAME")"
    echo "Hermes: start a new session (or /reset) for the change to take effect."
  fi
  echo "Done."; exit 0
fi

# ---------------------------------------------------------------- get the skill
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
if [ -n "$SOURCE" ]; then
  if [ -f "$SOURCE/SKILL.md" ]; then src="$SOURCE"; else src="$SOURCE/skills/$NAME"; fi
else
  echo "Downloading $REPO ($BRANCH)..."
  curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" | tar -xz -C "$tmp"
  src="$(find "$tmp" -maxdepth 3 -type d -path "*/skills/$NAME" | head -n1)"
fi
if [ -z "$src" ] || [ ! -f "$src/SKILL.md" ]; then echo "Could not find skills/$NAME/SKILL.md." >&2; exit 1; fi

copy_skill() {   # copy_skill <dest-folder>
  run mkdir -p "$(dirname "$1")"
  [ -e "$1" ] && run rm -rf -- "$1"
  run cp -R "$src" "$1"
  run rm -rf -- "$1/evals"   # test cases are for development, not needed at runtime
}

for t in "${targets[@]}"; do
  echo "Installing into $t/$NAME"
  copy_skill "$t/$NAME"
done

# ---------------------------------------------------------------- Hermes
HMSG=""
if [ "$HERMES" = 1 ]; then
  if [ -n "$PROFILE" ] && [ ! -d "$HH/profiles/$PROFILE" ] && [ "$DRY" = 0 ] && [ "$HCLI" = 0 ]; then
    echo "Hermes profile '$PROFILE' not found at $HH/profiles/$PROFILE; skipping Hermes." >&2
  else
    method=""
    if [ "$HCLI" = 1 ]; then
      args=(skills install "$HUB_ID" --category "$CATEGORY" --yes)
      # One attempt with --force: Hermes' scanner rates this skill CAUTION (it documents sudo/system
      # commands), and --force never overrides a DANGEROUS verdict, so a first try without it adds no
      # safety and doubles the GitHub API calls (60/hour without a token).
      { [ "$NO_FORCE" = 0 ] || hub_installed; } && args+=(--force)
      echo "Hermes: $(hermes_cmd "${args[@]}")"
      if [ "$DRY" = 1 ]; then
        echo "  (dry-run) $(hermes_cmd "${args[@]}")"
        echo "  (dry-run) if Hermes' scanner says DANGEROUS: stop, nothing is copied"
        [ "$NO_FORCE" = 1 ] && echo "  (dry-run) if it blocks a CAUTION verdict (no --force): copy to $HDEST"
        echo "  (dry-run) if it fails for another reason (rate limit, offline, older Hermes): copy to $HDEST"
        method="dry-run"
      else
        # remove an older local copy so the hub install doesn't collide with it
        while IFS= read -r d; do if is_ours "$d" && ! hub_installed; then rm -rf -- "$d"; fi; done < <(hermes_copies)
        hermes_install "${args[@]}"
        case "$HRESULT" in
          ok) method="hub"
            if [ "$HVERDICT" = caution ]; then
              echo "Hermes: the scanner rated it CAUTION because this network-admin skill documents sudo and other"
              echo "        system commands (it never runs them); installed with --force. Review it any time with:"
              echo "        hermes skills inspect $HUB_ID"
            fi ;;
          dangerous)
            echo "Hermes: the scanner rated it DANGEROUS, so it was NOT installed for Hermes (nothing was copied)." >&2
            echo "        Please open an issue with the output above: https://github.com/$REPO/issues" >&2
            exit 3 ;;
          caution)
            echo "Hermes: blocked by the scanner (CAUTION) and --no-force was given; copying instead." ;;
          *)
            if [ "$HRATE" = 1 ]; then
              echo "Hermes: GitHub's API rate limit was hit (60 requests/hour without a token); it resets within an hour."
            else
              echo "Hermes: 'hermes skills install' did not complete (offline, or an older Hermes?)."
            fi
            echo "        Copying instead. To switch the copy to an updatable hub install later, re-run this"
            echo "        installer (after the limit resets, or after adding GITHUB_TOKEN=<token> to $HH/.env)." ;;
        esac
      fi
    fi
    if [ -z "$method" ]; then
      echo "Installing into $HDEST"
      # don't leave an old uncategorised copy next to the new one
      while IFS= read -r d; do if [ "$d" != "$HDEST" ] && is_ours "$d"; then run rm -rf -- "$d"; fi; done < <(hermes_copies)
      copy_skill "$HDEST"
      method="copy"
    fi
    case "$method" in
      hub) HMSG="Hermes: installed with 'hermes skills install' (update later with: $(hermes_cmd skills update $NAME))." ;;
      copy) if [ "$DRY" = 1 ]; then HMSG="Hermes: would copy to $HDEST."
            else HMSG="Hermes: copied to $HDEST. A copied skill is 'local': 'hermes skills update' won't update it; re-run this installer instead."; fi ;;
      dry-run) HMSG="Hermes: would install as shown above." ;;
    esac
  fi
fi

n=${#targets[@]}; [ -n "$HMSG" ] && n=$((n + 1))
echo
echo "Installed netconfig-skill into $n location(s). Restart your agent, then ask:"
echo '  "Which skills do you have? Use network-config to audit this Cisco config: ..."'
if [ -n "$HMSG" ]; then
  echo "$HMSG"
  echo "Hermes: start a new session (or /reset) to load it; check with: $(hermes_cmd skills list)"
fi
exit 0
