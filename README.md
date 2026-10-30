# Claude

一个通过 Windows WSL2 / WSLg 运行的 Claude Desktop 外观定制工程。

保留官方聊天功能，增加线稿开场、人物动画、循环背景及自定义图标。当前适配官方 Linux 客户端 **4.29.0 / amd64**，测试环境为 Ubuntu 24.04。不是 Anthropic 官方项目。

## 功能

- 原始线稿开场渐变上色，再完整播放人物睁眼视频；可点击或按 Esc 跳过。
- 开场播放副本为 1080p60，聊天循环背景为 1080p30，背景静音。
- 背景贴合聊天内容区，不覆盖标题栏、侧栏或输入操作；窗口缩放和侧栏收起时保持对齐。
- 仅保留一个背景播放器；开场、隐藏和最小化期间暂停背景播放，流式回复不触发整页扫描。
- 不添加对话头像、气泡调整或皮肤设置面板。
- 保留 Fcitx5 中文输入支持，默认 Ctrl + 空格切换。
- 图标、播放素材和原始 4K60 视频随工程保存。

## 安装

先准备 Windows WSL2、WSLg、Ubuntu 24.04+ amd64 和 systemd，并在 Ubuntu 中创建普通用户。工程不包含 Claude 官方二进制、账号或登录状态。

从工程根目录在 PowerShell 中运行：

```powershell
.\scripts\windows\Install.ps1 -Plan
.\scripts\windows\Install.ps1 -Distro Ubuntu
.\scripts\windows\Start.ps1 -CheckOnly
```

安装后双击桌面 **Claude**。安装器自动识别当前用户与路径，不需要填写 API 密钥。请自行在官方界面登录。

若系统依赖已安装，可使用 `-SkipSystemPackages`。只有显式指定 `-Startup` 才会创建 Windows 登录启动项。安装器遵循系统现有 PowerShell 执行策略。工程目录移动后需重新运行安装器刷新快捷方式。

详见 [安装说明](docs/INSTALL.zh-CN.md)、[故障排查](docs/TROUBLESHOOTING.md)。

## 工程目录

```text
assets/                 图标、原始 4K 视频和保留的旧素材
config/                 核心版本适配记录
runtime/                动画、聊天背景及 Electron 接入代码
scripts/windows/        Windows 安装、启动与卸载入口
scripts/linux/          WSL 安装、版本副本、输入法和环境检查
scripts/privacy_check.py  发布前隐私检查
scripts/package.py        通过检查后生成源码 ZIP
scripts/prepare-media.sh  从原始视频重新制作播放副本
tests/                  合成界面、退出交接和隐私检查测试
docs/                   安装、架构、隐私与测试说明
.github/workflows/      源码、隐私及脚本检查
```

## 检查与打包

在 Ubuntu / WSL 工程根目录运行（需要 Python 3、Node.js、FFmpeg）：

```bash
python3 scripts/privacy_check.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/package.py --output dist/claude-source.zip
```

源码包只包含允许发布的工程文件和媒体；`.git`、`.local`、环境文件、密钥、日志、缓存和测试截图不进入 ZIP。另有 [隔离原生测试](docs/TESTING.md)，不会使用真实聊天账号。

发布目录不携带旧 Git 历史。创建自己的仓库后上传这些文件即可；后续提交的作者信息由自己的 Git 配置和 GitHub 账号决定。

## 许可

代码遵循 [MIT License](LICENSE)，第三方声明见 [NOTICE.md](NOTICE.md)。图片、视频、角色和商标不自动适用代码的 MIT 许可，保留原有权利与来源标记；媒体清单见 [素材说明](assets/README.md)。
