#!/usr/bin/env bash
set -Eeuo pipefail
atelier_bin=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$atelier_bin/session-env.sh"
dbus-update-activation-environment --systemd DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR XDG_CURRENT_DESKTOP BROWSER GTK_IM_MODULE QT_IM_MODULE XMODIFIERS >/dev/null 2>&1 || true
if command -v fcitx5 >/dev/null 2>&1 && ! fcitx5-remote --check >/dev/null 2>&1; then
  systemctl --user start fcitx5-atelier.service >/dev/null 2>&1 || true
fi
gnome-keyring-daemon --start --components=secrets >/dev/null 2>&1 || true
exec python3 "$atelier_bin/launch-skin.py" "$@"
