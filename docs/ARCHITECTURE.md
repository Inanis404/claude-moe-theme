# 架构

Windows 快捷方式调用 PowerShell 启动器，经 WSL 普通用户运行独立的 Claude 版本副本。安装器保持官方二进制不变，校验原始 packed 文件，仅替换 package.json 中的本地启动入口并添加定制模块。

`claude-bootstrap.cjs` 接入 Electron 生命周期，继续加载官方入口。`startup-cover.cjs` 使用临时 WebContentsView 播放线稿和视频，素材准备完成后才显示；正常完成、跳过、超时与失败都释放覆盖层。

`chat-background.cjs` 仅在允许的官方聊天界面注入隔离世界脚本。`chat-background.js` 只识别聊天容器，使用绝对定位贴合容器边界，避免 transform/contain 祖先造成重复偏移。它保持一个静音播放器，不处理聊天内容、不代理接口、不读取凭据。

开场使用 1080p60，背景使用 1080p30。原始 4K 文件仅用于素材保留与重新制作。背景在开场、隐藏和最小化时暂停；新增聊天结构触发必要的识别，流式文字不触发全页扫描。

本地诊断仅在显式启用 `CLAUDE_BACKGROUND_DIAGNOSTICS=1` 时记录播放器计数、尺寸、播放状态和元素类型，不记录聊天正文。诊断和机器配置属于运行时数据，不进入源码包。

更换核心版本时需验证入口、沙箱、远端 DOM、登录、Chat/Code/Cowork 和正常退出行为，不能单纯修改兼容版本号。
