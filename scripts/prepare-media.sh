#!/usr/bin/env bash
set -Eeuo pipefail
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_root"
command -v ffmpeg >/dev/null || { echo 'FFmpeg is required.' >&2; exit 1; }
ffmpeg -hide_banner -y -i assets/original-videos/live2d_4k60_loop.mp4 \
  -vf scale=1920:1080:flags=lanczos,fps=30 -an -c:v libx264 -preset fast -crf 22 \
  -pix_fmt yuv420p -movflags +faststart -threads 4 runtime/chat-background.mp4
ffmpeg -hide_banner -y -i assets/original-videos/live2d_awake_4k60.mp4 \
  -vf scale=1920:1080:flags=lanczos -c:v libx264 -preset fast -crf 21 -pix_fmt yuv420p \
  -c:a copy -movflags +faststart -threads 4 runtime/splash/assets/video/awake-playback.mp4
ffmpeg -hide_banner -y -i runtime/chat-background.mp4 -frames:v 1 -q:v 3 runtime/chat-background.jpg
