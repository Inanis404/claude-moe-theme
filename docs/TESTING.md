# 测试

## 多会话背景回归

使用独立 Chromium 进程和合成页面，无需 Claude、账号或运行中的桌面窗口：

```bash
python -m pip install playwright
python -m playwright install chromium
python tests/multi_panel.py
```

覆盖单会话、双/三/四分屏、增减面板、尺寸变化、隐藏恢复、明暗遮罩、暂停恢复、流式文本稳定性、输入命中和视频解码帧推进。脱敏截图及结果生成在 `.local/multi-panel/`。各面板共享一个 Blob URL；每个可见面板保留自己的播放器，隐藏时暂停，移除时释放。此测试不证明具体 Claude 版本或 Linux 原生 Electron 的 GUI 兼容性。

## 源码与隐私

Linux / WSL 下需要 Python 3、Node.js、FFmpeg：

```bash
python3 scripts/privacy_check.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
for file in scripts/linux/*.sh scripts/prepare-media.sh; do bash -n "$file"; done
node --check runtime/chat-background.js
```

Windows 下运行 `./tests/windows.ps1` 检查 PowerShell 语法、参数引用及目标识别；该测试不会安装软件或读取真实用户配置。

隐私检查覆盖允许列表内的文本、嵌入的图片/音频、图片元数据、MP4 容器和流标签，以及未批准的文件类型。额外姓名或标识可用 `--deny-term` 参数在本机传入，检查结果只显示文件和原因，不打印命中内容。

## 隔离的原生 Electron 测试

需要本机已安装适配的官方核心，以及 xvfb / xauth：

```bash
python3 scripts/linux/install-runtime.py --base "$HOME/.cache/claude-source-test" --no-desktop
xvfb-run -a python3 tests/native.py --base "$HOME/.cache/claude-source-test"
```

测试使用独立显示和临时用户目录，验证线稿到视频、完整播放、循环、暂停、标题栏排除、输入不被遮挡、transform/contain 容器对齐、侧栏收起、窗口缩放、跳过及超时。不使用真实账号或向真实会话发送消息。结果位于 `.local/test-results/`，不会打包。

CI 运行源码、隐私、退出交接和脚本检查，不下载专有 Claude 核心、不登录、不发布源码。新机器安装、账号登录、音效听感和不同显卡/缩放环境仍需单独验证。
