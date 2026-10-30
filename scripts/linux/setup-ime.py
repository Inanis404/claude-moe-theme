#!/usr/bin/env python3
"""Set up this user's WSLg Pinyin session without touching Claude profiles."""
import json, os, pathlib, shutil, subprocess

home = pathlib.Path.home()
assert os.getuid() != 0, 'Run as the regular Linux user.'
written = []

def write(relative, content):
    target = home / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_text() == content:
        return
    if target.exists():
        backup = target.with_name(target.name + '.before-atelier-ime')
        if not backup.exists():
            shutil.copy2(target, backup)
    target.write_text(content)
    written.append(str(target))

ime = home / '.config/fcitx5'
ime.mkdir(parents=True, exist_ok=True)
if not (ime / 'profile').exists():
    write('.config/fcitx5/profile', '''[Groups/0]
Name=Default
Default Layout=us
DefaultIM=pinyin

[Groups/0/Items/0]
Name=keyboard-us
Layout=

[Groups/0/Items/1]
Name=pinyin
Layout=

[GroupOrder]
0=Default
''')
if not (ime / 'config').exists():
    write('.config/fcitx5/config', '''[Hotkey]
EnumerateWithTriggerKeys=True

[Hotkey/TriggerKeys]
0=Control+space
1=Control+Shift+space

[Behavior]
ActiveByDefault=False
''')
env_text = '''# Chinese input for this user's WSLg applications.
if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && command -v fcitx5 >/dev/null 2>&1; then
    export GTK_IM_MODULE=fcitx
    export QT_IM_MODULE=fcitx
    export XMODIFIERS=@im=fcitx
fi
'''
write('.config/claude-atelier/input-env.sh', env_text)
write('.config/environment.d/60-atelier-input.conf', 'GTK_IM_MODULE=fcitx\nQT_IM_MODULE=fcitx\nXMODIFIERS=@im=fcitx\n')
marker = '# Claude Atelier: WSLg Chinese input'
block = '\n' + marker + '\n[ ! -r "$HOME/.config/claude-atelier/input-env.sh" ] || . "$HOME/.config/claude-atelier/input-env.sh"\n'
for name in ['.profile', '.bashrc']:
    target = home / name
    previous = target.read_text() if target.exists() else ''
    if marker not in previous:
        write(name, previous.rstrip('\n') + '\n' + block)

write('.config/systemd/user/fcitx5-atelier.service', '''[Unit]
Description=Chinese Pinyin input for WSLg and Claude Atelier
After=dbus.socket

[Service]
Type=dbus
BusName=org.fcitx.Fcitx5
ExecStart=/usr/bin/fcitx5 -D --disable=wayland
Environment=DISPLAY=:0
Environment=XDG_CURRENT_DESKTOP=X-Generic
Environment=GTK_IM_MODULE=fcitx
Environment=QT_IM_MODULE=fcitx
Environment=XMODIFIERS=@im=fcitx
Restart=on-failure
RestartSec=2
TimeoutStartSec=10

[Install]
WantedBy=default.target
''')
subprocess.run(['im-config', '-n', 'fcitx5'], check=True)
subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
subprocess.run(['systemctl', '--user', 'enable', '--now', 'fcitx5-atelier.service'], check=True)
subprocess.run(['fcitx5-remote', '--check'], check=True)
print(json.dumps({'ok': True, 'written': written, 'inputMethods': ['keyboard-us', 'pinyin'], 'toggle': ['Ctrl+Space', 'Ctrl+Shift+Space']}))
