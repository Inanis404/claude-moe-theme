#!/usr/bin/env python3
"""Checks prerequisites; never reads Claude profiles or starts Claude."""
import datetime
import fcntl
import grp
import json
import os
import pathlib
import platform
import subprocess
import sys
import argparse
import configparser
import shlex
import shutil

report = {"stage": "claude-atelier", "checks": [],
          "manual_tests": {"login": "not_run", "chat": "not_run", "code": "not_run", "cowork_task": "not_run"}}

def record(name, status, detail):
    report["checks"].append({"name": name, "status": status, "detail": detail})

def run(args, timeout=15):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)

record("non_root_user", "pass" if os.getuid() != 0 else "fail", "regular user required")
record("wslg", "pass" if pathlib.Path('/mnt/wslg').is_dir() and os.environ.get('DISPLAY') else "fail", "WSLg + DISPLAY")
groups = [grp.getgrgid(gid).gr_name for gid in os.getgroups()]
record("kvm_group", "pass" if "kvm" in groups else "fail", "kvm membership")
packages = ["claude-desktop", "qemu-system-x86", "ovmf", "virtiofsd", "gnome-keyring", "dbus-user-session", "desktop-file-utils", "firefox", "xdotool", "fcitx5", "fcitx5-pinyin", "fcitx5-frontend-gtk3"]
for package in packages:
    p = run(["dpkg-query", "-W", "-f=${db:Status-Status} ${Version}", package])
    record(package, "pass" if p.returncode == 0 and p.stdout.startswith("installed ") else "fail", p.stdout.strip() or "not installed")
for device in ["/dev/kvm", "/dev/vhost-vsock"]:
    try:
        with open(device, "r+b", buffering=0) as handle:
            detail = "opened with user permissions"
            if device == "/dev/kvm":
                version = fcntl.ioctl(handle, 0xAE00, 0)
                if version != 12:
                    raise RuntimeError("Unexpected KVM API: " + str(version))
                detail += "; KVM API 12"
        record(device, "pass", detail)
    except (OSError, RuntimeError) as error:
        record(device, "fail", str(error))
try:
    p = run(["busctl", "--user", "--no-pager", "list"])
    record("user_dbus", "pass" if p.returncode == 0 else "fail", "user bus available" if p.returncode == 0 else "user bus unavailable")
except (OSError, subprocess.TimeoutExpired) as error:
    record("user_dbus", "fail", type(error).__name__)
record("linux_url_routing", "pass" if os.environ.get('XDG_CURRENT_DESKTOP') == 'X-Generic' else "fail", "XDG_CURRENT_DESKTOP=" + os.environ.get('XDG_CURRENT_DESKTOP', '(unset)'))
ime_env = {'GTK_IM_MODULE':'fcitx', 'QT_IM_MODULE':'fcitx', 'XMODIFIERS':'@im=fcitx'}
record('chinese_input_environment', 'pass' if all(os.environ.get(k)==v for k,v in ime_env.items()) else 'fail', 'GTK / Qt / XIM input modules')
ime_service = run(['systemctl', '--user', 'is-enabled', 'fcitx5-atelier.service'])
record('chinese_input_autostart', 'pass' if ime_service.returncode==0 else 'warning', ime_service.stdout.strip() or 'not enabled')
def is_linux_firefox(desktop_id):
    # Firefox may register a generated userapp-Firefox-*.desktop after login.
    # Validate its real executable rather than rejecting a working MIME handler.
    if not desktop_id or pathlib.Path(desktop_id).name != desktop_id:
        return False
    roots = [pathlib.Path(os.environ.get('XDG_DATA_HOME', str(pathlib.Path.home()/'.local/share')))]
    roots += [pathlib.Path(p) for p in os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':') if p]
    for root in roots:
        entry = root/'applications'/desktop_id
        if not entry.is_file():
            continue
        try:
            config = configparser.ConfigParser(interpolation=None)
            config.read(entry)
            section = config['Desktop Entry']
            command = shlex.split(section.get('Exec',''))
            executable = shutil.which(command[0]) if command else None
            allowed = {pathlib.Path(p).resolve() for p in ['/usr/bin/firefox','/usr/lib/firefox/firefox','/usr/lib/firefox/firefox-bin'] if pathlib.Path(p).is_file()}
            return section.get('Type') == 'Application' and section.get('Hidden','false').lower() != 'true' and executable is not None and pathlib.Path(executable).resolve() in allowed
        except (OSError, ValueError, configparser.Error):
            return False
    return False

for mime, desktop in [('x-scheme-handler/http','firefox.desktop'), ('x-scheme-handler/https','firefox.desktop'), ('x-scheme-handler/claude','com.anthropic.Claude.desktop')]:
    try:
        # GIO resolves real installed desktop entries; xdg-mime alone can return an unusable fallback.
        p = subprocess.run(['gio','mime',mime],capture_output=True,text=True,timeout=15,env=dict(os.environ,LC_ALL='C'))
        first = p.stdout.splitlines()[0] if p.stdout.splitlines() else ''
        handler = first.rpartition(': ')[2]
        valid_handler = is_linux_firefox(handler) if desktop == 'firefox.desktop' else handler == desktop
        ok = p.returncode == 0 and first.startswith('Default application for ') and valid_handler
        record(mime, 'pass' if ok else 'fail', 'registered handler valid' if ok else 'handler missing or unexpected')
    except (OSError, subprocess.TimeoutExpired) as error:
        record(mime, 'fail', type(error).__name__)
try:
    cid = str(20000 + os.getpid() % 40000)
    cmd = ["qemu-system-x86_64", "-machine", "q35,accel=kvm", "-cpu", "host", "-m", "128", "-nodefaults", "-display", "none", "-S", "-device", "vhost-vsock-pci,guest-cid=" + cid, "-qmp", "stdio"]
    # Paused VM: no guest code runs; no disk, network, GUI, or persistent state.
    commands = "\n".join(json.dumps(c) for c in [
        {"execute": "qmp_capabilities", "id": "hello"},
        {"execute": "query-kvm", "id": "kvm"},
        {"execute": "quit", "id": "quit"}]) + "\n"
    p = subprocess.run(cmd, input=commands, capture_output=True, text=True, timeout=15)
    replies = [json.loads(line) for line in p.stdout.splitlines() if line.strip().startswith("{")]
    kvm = next((r.get("return", {}) for r in replies if r.get("id") == "kvm"), {})
    success = p.returncode == 0 and kvm.get("enabled") is True and kvm.get("present") is True
    record("qemu_kvm_vsock", "pass" if success else "fail", "Paused VM initialized with KVM and vhost-vsock; clean exit" if success else "QMP did not confirm KVM")
except (OSError, subprocess.TimeoutExpired, ValueError) as error:
    record("qemu_kvm_vsock", "fail", type(error).__name__)
report["prerequisites_pass"] = all(c["status"] != "fail" for c in report["checks"])
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(0 if report["prerequisites_pass"] else 2)
