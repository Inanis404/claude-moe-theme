# Contributing

使用普通用户环境开发，在独立分支中修改代码。请先运行 `python3 scripts/privacy_check.py` 和 Python 单元测试，再按 `docs/TESTING.md` 运行与变更对应的检查。

不要提交账号配置、环境文件、Cookie、API 密钥、日志、真实聊天内容、个人路径或带账号信息的截图。问题复现请使用合成文本。媒体变更请保留来源和许可信息。

核心版本更新需重新确认 Electron 入口、沙箱、聊天界面、登录和退出行为，不能只修改版本字符串以绕过适配检查。
