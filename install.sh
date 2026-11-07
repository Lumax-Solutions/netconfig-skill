#!/usr/bin/env bash
# netconfig-skill installer (macOS / Linux / WSL / Git Bash)
#
#   curl -fsSL https://raw.githubusercontent.com/Lumax-Solutions/netconfig-skill/main/install.sh | bash
#
# Options (pass after `bash -s --` when piping):
#   --project      install into the current project (./.agents/skills, ./.claude/skills) instead of your home folder
#   --uninstall    remove the skill from every location this script manages
#   --dry-run      show what would happen, change nothing
#
# What it does: downloads the latest skills/network-config folder from GitHub and copies it into
#   ~/.agents/skills/            (shared folder read by Codex, Cursor, Copilot, Gemini CLI, OpenCode, Goose,
#                                 Amp, Kilo, Roo, Qwen, Droid, Windsurf/Devin and others)
# plus the private folder of each of these agents that you have installed:
#   Claude Code, Antigravity, Cline, Kiro, Trae, Hermes, Continue
set -euo pipefail

REPO="Lumax-Solutions/netconfig-skill"
BRANCH="main"
NAME="network-config"
MODE="global"; ACTION="install"; DRY=0
for a in "$@"; do
  case "$a" in
    --project) MODE="project" ;;
    --uninstall) ACTION="uninstall" ;;
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '2,17p' "$0" 2>/dev/null || true; exit 0 ;;
    *) echo "Unknown option: $a" >&2; exit 2 ;;
  esac
done

run() { if [ "$DRY" = 1 ]; then echo "  (dry-run) $*"; else "$@"; fi; }

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
  [ -d "$H/.hermes" ]          && targets+=("$H/.hermes/skills")
  [ -d "$H/.continue" ]        && targets+=("$H/.continue/skills")
fi

if [ "$ACTION" = "uninstall" ]; then
  for t in "${targets[@]}"; do
    if [ -f "$t/$NAME/SKILL.md" ]; then echo "Removing $t/$NAME"; run rm -rf -- "$t/$NAME"; fi
  done
  echo "Done."; exit 0
fi

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
echo "Downloading $REPO ($BRANCH)..."
curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" | tar -xz -C "$tmp"
src="$(find "$tmp" -maxdepth 3 -type d -path "*/skills/$NAME" | head -n1)"
if [ -z "$src" ] || [ ! -f "$src/SKILL.md" ]; then echo "Could not find skills/$NAME/SKILL.md in the download." >&2; exit 1; fi

for t in "${targets[@]}"; do
  echo "Installing into $t/$NAME"
  run mkdir -p "$t"
  [ -e "$t/$NAME" ] && run rm -rf -- "$t/$NAME"
  run cp -R "$src" "$t/$NAME"
  run rm -rf -- "$t/$NAME/evals"   # test cases are for development, not needed at runtime
done

echo
echo "Installed netconfig-skill into ${#targets[@]} location(s). Restart your agent, then ask:"
echo '  "Which skills do you have? Use network-config to audit this Cisco config: ..."'
[ -d "$HOME/.hermes" ] && [ "$MODE" = "global" ] && echo "Hermes: if it doesn't show up, run: hermes skills list"
exit 0
