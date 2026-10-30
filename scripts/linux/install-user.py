#!/usr/bin/env python3
"""Register the local skin, Linux browser routing, and Chinese input for the current user."""
import json, os, pathlib, shutil, subprocess, sys

scripts = pathlib.Path(__file__).resolve().parent
home = pathlib.Path.home()
if os.getuid() == 0:
    raise SystemExit('Run user setup as your regular Linux account, not root.')
if not pathlib.Path('/mnt/wslg').is_dir():
    raise SystemExit('This installer expects a WSLg session.')
subprocess.run([sys.executable, str(scripts/'setup-ime.py')], check=True)
subprocess.run([sys.executable, str(scripts/'install-runtime.py')], check=True)
# Preserve MIME associations before the explicit Linux browser routing changes.
mime = home/'.config/mimeapps.list'
backup = mime.with_name('mimeapps.list.before-atelier-browser')
if mime.exists() and not backup.exists():
    shutil.copy2(mime, backup)
for kind in ['x-scheme-handler/http', 'x-scheme-handler/https', 'text/html']:
    subprocess.run(['gio', 'mime', kind, 'firefox.desktop'], check=True, stdout=subprocess.DEVNULL)
print(json.dumps({'ok': True, 'next': 'Run the environment check, then launch Claude.'}))
