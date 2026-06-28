#!/usr/bin/env bash
# 用密码解密 secrets.env.enc → ~/.cursor-provider-switch/secrets.env
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENC="${1:-$ROOT/config/secrets.env.enc}"
DEST="${CURSOR_SWITCH_SECRETS:-$HOME/.cursor-provider-switch/secrets.env}"

if [[ ! -f "$ENC" ]]; then
  echo "未找到加密文件: $ENC" >&2
  echo "若仓库尚无 secrets.env.enc，请先在本机运行 env-lock.sh 生成并 push" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
echo "解密到: $DEST"
echo "请输入解密密码:"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
  -in "$ENC" -out "$DEST"

chmod 600 "$DEST"
echo "✓ 密钥已解锁到 $DEST"
echo "  测试: curswitch status"
