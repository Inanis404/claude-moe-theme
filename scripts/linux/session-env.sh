#!/usr/bin/env bash
# xdg-utils otherwise detects WSL and forwards URLs to Windows rundll32.exe.
# Use its supported generic Linux desktop route for this app and its children.
export XDG_CURRENT_DESKTOP=X-Generic
export BROWSER=/usr/bin/firefox
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}
if [[ -z ${DBUS_SESSION_BUS_ADDRESS:-} && -S "$XDG_RUNTIME_DIR/bus" ]]; then
  export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
fi
# WSLg does not automatically inherit the Windows IME. Use its Linux input modules.
if command -v fcitx5 >/dev/null 2>&1; then
  export GTK_IM_MODULE=fcitx
  export QT_IM_MODULE=fcitx
  export XMODIFIERS=@im=fcitx
fi
