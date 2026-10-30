#!/usr/bin/env python3
"""Remove Atelier launch registration; preserve accounts, themes, input dictionaries and packages."""
import os, pathlib, shutil, subprocess
from native_quit import main_instances

home = pathlib.Path.home()
base = home/'.local/share/claude-atelier'
if os.getuid() == 0:
    raise SystemExit('Run as your regular user.')
if any(i.executable.parent.parent == base/'releases' for i in main_instances(base)):
    raise SystemExit('Quit Claude normally before removing its registration.')
desktop = home/'.local/share/applications/com.anthropic.Claude.desktop'
backup = desktop.with_name(desktop.name+'.before-atelier')
if desktop.exists() and 'X-Claude-Atelier=true' in desktop.read_text():
    if backup.exists():
        shutil.copy2(backup, desktop)
    else:
        desktop.unlink()
    subprocess.run(['update-desktop-database', str(desktop.parent)], check=True)
print('Atelier desktop registration removed. The official client, account, saved themes, browser and Chinese input remain available.')
print('Start the official program with /usr/bin/claude-desktop. See the README for optional cleanup.')
