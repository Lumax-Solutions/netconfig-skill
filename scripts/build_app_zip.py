#!/usr/bin/env python3
"""Build dist/NetConfig-Assistant.zip: the desktop app plus the skill files it reads, with start
files at the top level for non-technical users. Run from the repository root."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "NetConfig-Assistant.zip"
PREFIX = "NetConfig-Assistant/"

WIN = r'''@echo off
rem Double-click to start NetConfig Assistant. Keep this window open while you use the app.
cd /d "%~dp0app"
call start-windows.bat %*
'''.replace("\n", "\r\n")
MAC = '''#!/usr/bin/env bash
cd "$(dirname "$0")/app" || exit 1
exec ./start-mac-linux.sh "$@"
'''


def add_tree(z, src, dest):
    for f in sorted(src.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
            info = zipfile.ZipInfo(PREFIX + dest + "/" + f.relative_to(src).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 if f.suffix in (".sh", ".command", ".py") else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_bytes())


def add_text(z, name, text, mode=0o644):
    info = zipfile.ZipInfo(PREFIX + name, (2026, 1, 1, 0, 0, 0))
    info.external_attr = mode << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, text)


def main():
    OUT.parent.mkdir(exist_ok=True)
    skill = ROOT / "skills" / "network-config"
    readme = (ROOT / "app" / "README.md").read_text(encoding="utf-8")
    readme = readme.replace("](../skills/", "](skills/").replace("](docs/", "](app/docs/")
    with zipfile.ZipFile(OUT, "w") as z:
        add_text(z, "Start NetConfig Assistant (Windows).bat", WIN)
        add_text(z, "Start NetConfig Assistant (Mac).command", MAC, 0o755)
        add_text(z, "README.md", readme)
        add_text(z, "LICENSE", (ROOT / "LICENSE").read_text(encoding="utf-8"))
        add_tree(z, ROOT / "app", "app")
        add_text(z, "skills/network-config/SKILL.md", (skill / "SKILL.md").read_text(encoding="utf-8"))
        add_tree(z, skill / "references", "skills/network-config/references")
        n = len(z.namelist())
    print(f"Wrote {OUT.relative_to(ROOT)} ({n} files, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
