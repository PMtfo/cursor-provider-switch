#!/usr/bin/env bash
# 从 ~/.hermes/.env 提取 Cursor 切换所需字段到 config/secrets.env
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-$HOME/.hermes/.env}"
DEST="$ROOT/config/secrets.env"

if [[ ! -f "$SRC" ]]; then
  echo "未找到: $SRC" >&2
  exit 1
fi

KEYS=(DEEPSEEK_BASE_URL DEEPSEEK_API_KEY MINIMAX_BASE_URL MINIMAX_CN_API_KEY MINIMAX_API_KEY)
{
  echo "# 从 $SRC 提取，仅供 cursor-provider-switch"
  for k in "${KEYS[@]}"; do
    v=$(grep -E "^${k}=" "$SRC" | head -1 | cut -d= -f2- || true)
    if [[ -n "$v" ]]; then
      echo "${k}=${v}"
    fi
  done
} > "$DEST"

chmod 600 "$DEST"
echo "✓ 已写入 $DEST"
echo "  下一步: bash scripts/env-lock.sh"
