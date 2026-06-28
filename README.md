# cursor-provider-switch

在 macOS 的 **Cursor** 里一键切换 **DeepSeek** / **MiniMax** 直连（OpenAI API Key + Override Base URL），并自动退出、写入配置、重开窗口。

配套 **Cursor Agent Skill**：在聊天里说「切 minimax」「切换 DeepSeek」即可触发。

## 功能

- `curswitch minimax` / `curswitch deepseek` / `curswitch status`
- Cursor 运行时后台 worker 自动处理（约 5 秒闪屏重开）
- 密钥用 **OpenSSL 密码加密** 存仓库，换电脑 clone 后输入密码解锁
- 安装脚本 + Cursor Skill 一并部署

## 提供商配置

| 提供商 | Base URL |
|--------|----------|
| DeepSeek | `https://api.deepseek.com` |
| MiniMax | `https://api.minimaxi.com/v1` |

## 快速开始（新电脑）

### 1. Clone 私密仓库

```bash
git clone git@github.com:PMtfo/cursor-provider-switch.git
cd cursor-provider-switch
```

### 2. 解锁密钥（密码加密）

仓库内是 **`config/secrets.env.enc`**（密文），不含明文 Key。

```bash
bash scripts/env-unlock.sh
# 提示输入你当初设置的密码 → 解密到 ~/.cursor-provider-switch/secrets.env
```

### 3. 安装

```bash
bash scripts/install.sh
# 可选：安装前指定默认工作区
# CURSOR_DEFAULT_WORKSPACE=~/Projects/foo bash scripts/install.sh
```

### 4. 使用

```bash
curswitch status
curswitch minimax    # 或 mm / m
curswitch deepseek   # 或 ds / d
```

在 Cursor 聊天中说「切 minimax」也会走同一套逻辑（需已安装 Skill）。

---

## 首次上传密钥（本机）

**Git 不支持带密码的 .env 原生加密**；本仓库用 **OpenSSL AES-256** 实现「设密码 → 上传密文 → 他机输入密码解密」。

### 方式 A：从 `~/.hermes/.env` 导入

```bash
bash scripts/import-from-hermes.sh
bash scripts/env-lock.sh          # 输入并确认你的加密密码
rm -f config/secrets.env          # 删除明文
git add config/secrets.env.enc
git commit -m "add encrypted secrets"
git push
```

### 方式 B：从模板填写

```bash
cp config/secrets.env.example config/secrets.env
# 编辑 config/secrets.env 填入真实 Key
bash scripts/env-lock.sh
rm -f config/secrets.env
git add config/secrets.env.enc && git commit && git push
```

### 密码说明

- 加密密码**只在你脑子里**，仓库里只有 `secrets.env.enc` 密文
- **忘记密码无法恢复**，只能重新 `env-lock` 再 push
- 换密码：重新 `env-lock` 覆盖 `secrets.env.enc` 后提交
- 依赖系统自带 `openssl`，无需额外安装

---

## 目录结构

```
cursor-provider-switch/
├── README.md
├── skill/SKILL.md                 # Cursor Agent Skill
├── config/
│   ├── cursor-providers.env       # URL 模板（无密钥）
│   ├── secrets.env.example        # 密钥模板
│   └── secrets.env.enc            # 加密密钥（提交到私密仓库）
└── scripts/
    ├── switch-cursor-provider.py  # 核心切换逻辑
    ├── install.sh                 # 安装 curswitch + Skill
    ├── env-lock.sh                # 明文 → 密文
    ├── env-unlock.sh              # 密文 → ~/.cursor-provider-switch/secrets.env
    └── import-from-hermes.sh      # 从 ~/.hermes/.env 提取字段
```

## 安装位置

| 项 | 路径 |
|----|------|
| 命令 | `~/local/bin/curswitch` |
| 解密密钥 | `~/.cursor-provider-switch/secrets.env` |
| Skill | `~/.cursor/skills/cursor-provider-switch/SKILL.md` |
| 切换日志 | `~/.cursor-switch.log` |
| Cursor 配置库 | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` |

## 工作原理

1. 检测 Cursor 是否打开 → 是则 `nohup` 后台 worker
2. 强制结束 Cursor 主进程（避免 Agent「Quit Anyway」弹窗）
3. 写入 `state.vscdb`：`openAIBaseUrl`、`useOpenAIKey`、`cursorAuth/openAIKey`
4. `open -a Cursor` 打开默认工作区
5. 启动后二次 patch（Cursor 可能把 `useOpenAIKey` 改回 `False`）

## 故障排查

```bash
tail -10 ~/.cursor-switch.log
curswitch status
```

| 现象 | 处理 |
|------|------|
| 缺少密钥 | 运行 `bash scripts/env-unlock.sh` |
| Base URL 对但开关 OFF | 再执行一次同方向 `curswitch` |
| 5 秒未重开 | 看日志；手动 `open -a Cursor` |

## 安全提示

- 仓库请保持 **Private**
- 切勿提交 `config/secrets.env` 明文
- 回复/日志中不要打印完整 API Key

## 平台

- **macOS only**（依赖 AppleScript、`state.vscdb` 路径）
- Cursor 已安装且至少打开过一次

## License

Private / personal use.
