#!/usr/bin/env bash
# 用密码加密 secrets.env → config/secrets.env.enc（可安全提交私密仓库）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLAIN="${1:-$ROOT/config/secrets.env}"
ENC="$ROOT/config/secrets.env.enc"

if [[ ! -f "$PLAIN" ]]; then
  echo "未找到明文文件: $PLAIN" >&2
  echo "可从模板复制: cp config/secrets.env.example config/secrets.env" >&2
  exit 1
fi

echo "将加密: $PLAIN → $ENC"
echo "请输入加密密码（两次确认，忘记则无法恢复密钥）:"
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
  -in "$PLAIN" -out "$ENC"

chmod 600 "$ENC"
echo "✓ 已生成 $ENC"
echo "  可删除本地明文: rm -f $PLAIN"
echo "  提交: git add config/secrets.env.enc && git commit"
