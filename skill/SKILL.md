---
name: cursor-provider-switch
description: >-
  在 Cursor 中切换 DeepSeek / MiniMax 直连（OpenAI API Key + Base URL），自动退出并重开。
  触发：切换 DeepSeek、切换 Minimax/MiniMax、切 deepseek、切 minimax、切 ds/mm、
  curswitch、Cursor 换模型、当前用的什么模型、DeepSeek MiniMax 互换。
---

# Cursor 模型切换（DeepSeek ↔ MiniMax）

## 触发即执行

识别到切换意图后**立即执行**，不要追问确认、不要手改 Settings。

| 用户说法 | 命令 |
|---------|------|
| 切 minimax / 切换 minimax / mm | `curswitch minimax` |
| 切 deepseek / 切换 deepseek / ds | `curswitch deepseek` |
| 当前配置 / status | `curswitch status` |

## 提供商口径

| 提供商 | Base URL | 密钥变量 |
|--------|----------|----------|
| DeepSeek | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` |
| MiniMax | `https://api.minimaxi.com/v1` | `MINIMAX_CN_API_KEY` |

密钥：`~/.cursor-provider-switch/secrets.env`（由 `env-unlock.sh` 解密）

## 流程

Cursor 开着 → 后台 worker → 强制退出 → 写 state.vscdb → 重开 → 二次 patch `useOpenAIKey`

日志：`~/.cursor-switch.log`

## 明确非目标

不走 new-api / 隧道；不同步飞书；不回显完整 API Key。
