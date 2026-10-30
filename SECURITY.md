# Security

本项目不需要 API 密钥，不保存账号密码，不向聊天页面开放 Node API；账号登录和官方通信由 Claude 客户端处理。

请勿把凭据、登录链接、Cookie、真实聊天记录或本机环境文件放入公开 issue。报告问题时使用脱敏描述与合成复现。发现已经泄露的凭据时，请在对应服务撤销并重新生成。

发布前执行 `python3 scripts/privacy_check.py`；源码 ZIP 仅由 `scripts/package.py` 的允许列表生成。
