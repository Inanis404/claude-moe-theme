# 安装说明

## 环境

需要 Windows WSL2 / WSLg、Ubuntu 24.04+ amd64、systemd 和普通 Linux 用户。当前实际验证环境为 Ubuntu 24.04，支持的 Claude Desktop 版本固定为 `config/compatibility.json` 中的 4.29.0。其他核心版本和 ARM64 未适配。

先运行 `wsl -l -v` 查看发行版。在 Ubuntu 中运行 `cat /proc/1/comm` 确认 systemd。首次使用 WSL 时需自行完成系统初始化；安装脚本不会关闭其他 WSL 会话或自动重启系统。

## Windows 入口

```powershell
.\scripts\windows\Install.ps1 -Plan
.\scripts\windows\Install.ps1 -Distro Ubuntu
.\scripts\windows\Start.ps1 -CheckOnly
```

需要指定普通 Linux 用户时增加 `-LinuxUser your_linux_user`。参数仅保存在被忽略的 `.local/windows.json`，代码不硬编码用户名或工程路径。

安装程序从已核对签名指纹的官方软件源获取支持版本及依赖。若核心较新、版本已不可获取或现有软件源配置不同，程序会停止，不擅自降级或换用其他来源。

`-SkipSystemPackages` 跳过系统依赖安装；`-Startup` 创建 Windows 登录启动项。默认不创建启动项。PowerShell 遵循现有执行策略。安装后请保留工程目录，移动目录后重新运行安装器。

## Ubuntu 手动入口

```bash
sudo bash scripts/linux/install-system.sh "$USER"
python3 scripts/linux/install-user.py
bash scripts/linux/check.sh
bash "$HOME/.local/share/claude-atelier/bin/run.sh"
```

以上第一条命令应从普通用户终端运行。Cowork 需要有效的 KVM、QEMU 和相应组权限，安装依赖本身不能保证所有宿主机都支持嵌套虚拟化。加入 kvm 组后需要新的登录会话。

外部登录通过 Ubuntu 中的 Firefox 回跳 Linux 客户端。请自行完成官方登录和密钥环解锁。本工程不提供也不接收密码、验证码或 API 密钥。

## 版本副本和卸载

官方 `/usr/lib/claude-desktop` 保持不变，定制副本保存在当前用户的 `~/.local/share/claude-atelier/releases/`。内部目录名用于兼容旧安装，不是账号标识。

运行 `scripts/windows/Uninstall.ps1` 可移除本工程对应的桌面/启动入口，保留账号数据、官方软件和输入法。卸载前正常退出定制客户端。
