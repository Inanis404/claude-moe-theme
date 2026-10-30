# 故障排查

- 无法启动：先运行 `scripts/windows/Start.ps1 -CheckOnly`。确认受支持的核心版本、WSLg、systemd 和普通用户配置。
- 老版本没有退出：在旧窗口正常退出，完成可能存在的确认后再启动。启动器不会强行终止活跃任务。
- 登录不能回跳：从 Linux Claude 重新发起登录并使用 Ubuntu Firefox 完成；不要把 OAuth 链接或 Cookie 贴到 issue。
- 无法输入中文：检查 Fcitx5 服务和 `GTK_IM_MODULE`、`QT_IM_MODULE`、`XMODIFIERS`，用 Ctrl + 空格切换。
- 背景错位或远端界面变更：先确认当前工程是最新定位逻辑；背景应贴合聊天容器，不使用重复的窗口偏移。
- 视频卡顿：当前默认播放 1080p30 背景和 1080p60 开场；不要将原始 4K 文件直接覆盖播放副本。
- 工程移位：重新运行安装器刷新快捷方式。本机配置和日志不要提交到仓库。
