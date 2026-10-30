#!/usr/bin/env bash
set -Eeuo pipefail
atelier_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
if [[ ${1:-} == --plan ]]; then
  printf '%s\n' 'Install verified Anthropic and Mozilla APT sources; install the supported Claude version, Cowork dependencies, Firefox, CJK fonts and Fcitx 5; add the chosen regular user to kvm. No full system upgrade or reboot.'
  exit 0
fi
target_user=${1:?Usage: install-system.sh REGULAR_LINUX_USER}
[[ $(id -u) == 0 ]] || { echo 'Run system setup as root or with sudo.' >&2; exit 1; }
[[ "$target_user" =~ ^[a-z_][a-z0-9_-]*\$?$ ]] && [[ $(id -u "$target_user") -ge 1000 ]] || { echo 'A regular Linux user is required.' >&2; exit 2; }
[[ $(dpkg --print-architecture) == amd64 ]] || { echo 'This release supports amd64 only.' >&2; exit 2; }
source /etc/os-release
[[ "$ID" == ubuntu ]] && dpkg --compare-versions "$VERSION_ID" ge 24.04 || { echo 'This installer targets Ubuntu 24.04+ on WSL2.' >&2; exit 2; }
[[ -d /mnt/wslg ]] && [[ $(cat /proc/1/comm) == systemd ]] || { echo 'WSLg and systemd must be enabled first. See the installation guide.' >&2; exit 2; }
export DEBIAN_FRONTEND=noninteractive
apt-get -o DPkg::Lock::Timeout=60 update
apt-get -o DPkg::Lock::Timeout=60 --no-remove -y install ca-certificates curl gnupg python3
expected=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["coreVersion"])' "$atelier_root/config/compatibility.json")
installed=$(dpkg-query -W -f='${Version}' claude-desktop 2>/dev/null || true)
if [[ -n "$installed" ]] && dpkg --compare-versions "$installed" gt "$expected"; then
  echo "Installed Claude is newer than supported $expected. No downgrade performed; see compatibility.json and the update guide." >&2; exit 3
fi
key_temp=$(mktemp)
trap 'rm -f -- "$key_temp"' EXIT
fetch_key() {
  curl --fail --silent --show-error --location --retry 2 --connect-timeout 20 --max-time 120 "$1" -o "$key_temp"
  local fingerprint
  fingerprint=$(gpg --batch --show-keys --with-colons "$key_temp" | awk -F: '$1=="fpr" {print $10; exit}')
  [[ "$fingerprint" == "$2" ]] || { echo 'Repository signing-key fingerprint mismatch; stopped.' >&2; exit 4; }
  install -D -m 0644 "$key_temp" "$3"
}
write_config() {
  local filename=$1 content=$2
  if [[ -e "$filename" ]] && [[ $(cat "$filename") != "$content" ]]; then echo "Existing repository configuration differs: $filename. Review it before retrying." >&2; exit 4; fi
  printf '%s\n' "$content" > "$filename"
}
fetch_key https://downloads.claude.ai/claude-desktop/key.asc 31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE /usr/share/keyrings/claude-desktop-archive-keyring.asc
write_config /etc/apt/sources.list.d/claude-desktop.list 'deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/claude-desktop-archive-keyring.asc] https://downloads.claude.ai/claude-desktop/apt/stable stable main'
fetch_key https://packages.mozilla.org/apt/repo-signing-key.gpg 35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3 /etc/apt/keyrings/packages.mozilla.org.asc
write_config /etc/apt/sources.list.d/mozilla.sources 'Types: deb
URIs: https://packages.mozilla.org/apt
Suites: mozilla
Components: main
Signed-By: /etc/apt/keyrings/packages.mozilla.org.asc'
write_config /etc/apt/preferences.d/claude-atelier-firefox 'Package: firefox firefox-l10n-*
Pin: origin packages.mozilla.org
Pin-Priority: 1000

Package: firefox
Pin: release o=Ubuntu
Pin-Priority: -1'
apt-get -o DPkg::Lock::Timeout=60 update
if ! apt-cache madison claude-desktop | awk '{print $3}' | grep -Fxq "$expected"; then
  echo "The official repository no longer offers supported version $expected. Nothing unverified will be substituted. See docs/INSTALL.zh-CN.md." >&2; exit 5
fi
apt-get -o DPkg::Lock::Timeout=60 --no-remove -y --no-install-recommends install \
  "claude-desktop=$expected" qemu-system-x86 ovmf virtiofsd gnome-keyring dbus-user-session desktop-file-utils firefox xdotool \
  fonts-noto-cjk fonts-noto-color-emoji locales fcitx5 fcitx5-pinyin fcitx5-frontend-gtk3 fcitx5-frontend-gtk4 \
  fcitx5-frontend-qt5 fcitx5-frontend-qt6 fcitx5-config-qt im-config
usermod -aG kvm "$target_user"
fc-cache -f
echo 'System setup complete. Start a new WSL session to pick up kvm membership; no reboot or application termination was performed.'
