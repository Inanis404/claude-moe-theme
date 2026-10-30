#!/usr/bin/env python3
"""Exercise the real Electron splash under an isolated X server and user profile."""
import argparse, json, os, pathlib, shutil, signal, subprocess, sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base', type=pathlib.Path, required=True)
args = parser.parse_args()
if not os.environ.get('DISPLAY') or os.environ['DISPLAY'] == ':0':
    raise SystemExit('Run under xvfb-run, never the real WSLg display.')
target = pathlib.Path(json.loads((args.base/'current.json').read_text())['release'])/'claude-desktop'
env = dict(os.environ, XDG_CURRENT_DESKTOP='X-Generic')
env.pop('WAYLAND_DISPLAY', None)
process = subprocess.Popen([str(target), '--claude-splash-self-test', '--ozone-platform=x11'],
    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
try:
    stdout, stderr = process.communicate(timeout=90)
except subprocess.TimeoutExpired:
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
    raise SystemExit('Only the isolated test process was stopped after a timeout.')
rows = [line.partition('CLAUDE_SPLASH_TEST ')[2] for line in (stdout+'\n'+stderr).splitlines() if 'CLAUDE_SPLASH_TEST ' in line]
if not rows:
    raise SystemExit('No test report returned: '+stderr[-3000:])
report = json.loads(rows[-1])
output = pathlib.Path(__file__).resolve().parents[1]/'.local/test-results'
output.mkdir(parents=True, exist_ok=True)
(output/'splash-native.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
for name in ['splash', 'first-frame', 'chat-background']:
    preview = pathlib.Path(report['testRoot'])/(name+'.png')
    if preview.is_file():
        shutil.copy2(preview, output/(name+'-preview.png'))
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(0 if report.get('passed') and process.returncode == 0 else 1)
