# cursor-provider-switch

**Cursor 第三方模型接入** —— 在 macOS 的 Cursor 里一键切换 DeepSeek / MiniMax 直连（OpenAI API Key + Override Base URL）。

> 关键词：cursor 第三方模型接入

## 它解决什么问题

Cursor 支持自定义 OpenAI 兼容端点（Settings → Models → Override OpenAI Base URL + API Key），但这个配置只能手动点，而且：

- 每次切换都要退出、改设置、重启窗口，来回点好几次；
- 想用便宜的中转模型（DeepSeek、MiniMax）跑日常任务，切回官方时又要重复一遍；
- 多台机器同步密钥很麻烦。

这个工具把整套流程压成一条命令：

```bash
curswitch minimax     # 或 mm / m
curswitch deepseek    # 或 ds / d
curswitch status      # 看当前生效的 provider
```

Cursor 开着也没关系：检测到运行中就拉起后台 worker，自动退出 → 写配置 → 重开窗口 → 二次 patch 开关，全程约 5 秒闪屏。

配套一个 Cursor Agent Skill：在聊天里说「切 minimax」「切换 DeepSeek」也能触发同一套逻辑。

## 支持的提供商

| 提供商 | Base URL | 密钥变量 |
| --- | --- | --- |
| DeepSeek | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` |
| MiniMax | `https://api.minimaxi.com/v1` | `MINIMAX_CN_API_KEY` / `MINIMAX_API_KEY` |

要加第三个 provider，改两处即可：`scripts/switch-cursor-provider.py` 里的 `PROVIDERS` 字典，和 `config/cursor-providers.env`。

## 快速开始

```bash
git clone https://github.com/PMtfo/cursor-provider-switch.git
cd cursor-provider-switch

# 1. 填密钥
cp config/secrets.env.example config/secrets.env
#   编辑 config/secrets.env，填入你自己的 DeepSeek / MiniMax Key

# 2. 加密后入库（密钥明文不进 git）
bash scripts/env-lock.sh

# 3. 安装（生成 curswitch 命令 + 装 Cursor Skill）
bash scripts/install.sh

# 4. 用
curswitch status
curswitch deepseek
```

可选：`CURSOR_DEFAULT_WORKSPACE=~/Projects/foo bash scripts/install.sh` 指定切换后 Cursor 打开的默认工作区。

### 多机同步密钥

密钥用 OpenSSL AES-256 加密后**放在你自己本地**（`config/secrets.env.enc`，已 gitignore）。要跨机同步就把它放到自己的私有位置，在另一台机器上解密：

```bash
bash scripts/env-unlock.sh    # 提示输入密码 → 解密到 ~/.cursor-provider-switch/secrets.env
```

加密密码只在你脑子里，文件里只有密文。**忘记密码无法恢复**，只能重新 `env-lock.sh` 覆盖。

如果你的 Key 已经存在别处（例如某个已有的 `.env`），可以用 `scripts/import-legacy-env.sh` 把需要的字段提取出来：

```bash
bash scripts/import-legacy-env.sh ~/somewhere/.env   # 不传参默认 ~/.cursor-provider-switch/.env
bash scripts/env-lock.sh
```

## 工作原理

1. 检测 Cursor 是否在运行 → 在运行则 `nohup` 启动后台 worker
2. 强制结束 Cursor 主进程（避开 Agent 的「Quit Anyway」弹窗）
3. 写 Cursor 的 `state.vscdb`：`openAIBaseUrl`、`useOpenAIKey`、`cursorAuth/openAIKey`
4. `open -a Cursor` 打开默认工作区
5. 启动后二次 patch —— Cursor 可能把 `useOpenAIKey` 改回 `False`

数据库路径：`~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`

## 安装位置

| 项 | 路径 |
| --- | --- |
| 命令 | `~/local/bin/curswitch` |
| 解密后的密钥 | `~/.cursor-provider-switch/secrets.env` |
| Skill | `~/.cursor/skills/cursor-provider-switch/SKILL.md` |
| 切换日志 | `~/.cursor-switch.log` |
| Cursor 配置库 | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` |

## 目录结构

```
cursor-provider-switch/
├── README.md
├── skill/SKILL.md                    Cursor Agent Skill
├── config/
│   ├── cursor-providers.env          provider 名称与 Base URL（无密钥）
│   ├── secrets.env.example           字段模板（无真值）
│   └── secrets.env.enc               加密密文，本地生成、已 gitignore
└── scripts/
    ├── switch-cursor-provider.py     核心切换逻辑
    ├── install.sh                    安装 curswitch + Skill
    ├── env-lock.sh                   明文 → 密文
    ├── env-unlock.sh                 密文 → ~/.cursor-provider-switch/secrets.env
    └── import-legacy-env.sh          从已有的 .env 提取字段
```

## 故障排查

```bash
tail -10 ~/.cursor-switch.log
curswitch status
```

| 现象 | 处理 |
| --- | --- |
| 提示缺少密钥 | 运行 `bash scripts/env-unlock.sh` |
| Base URL 对了但开关是 OFF | 再执行一次同方向的 `curswitch` |
| 5 秒内没重开 | 看日志；手动 `open -a Cursor` |
| 命令找不到 | 确认 `~/local/bin` 在 `PATH` 里 |

## 安全提示

- 本仓库**不含任何密钥**（明文或密文）。`config/secrets.env` 和 `config/secrets.env.enc` 都在 `.gitignore` 中，由你在本地生成。
- 日志与 `status` 输出里 API Key 只显示前 8 位和后 4 位。
- `env-lock.sh` 用 OpenSSL AES-256-CBC + PBKDF2（10 万次迭代），依赖系统自带 `openssl`。

## 平台要求

- **仅 macOS**（依赖 AppleScript、`state.vscdb` 路径）
- Cursor 已安装且至少启动过一次

## License

MIT
