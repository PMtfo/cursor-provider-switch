#!/usr/bin/env bash
# 安装 curswitch 命令、解锁密钥、安装 Cursor Skill
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="${INSTALL_BIN_DIR:-$HOME/local/bin}"
SKILL_DIR="${INSTALL_SKILL_DIR:-$HOME/.cursor/skills/cursor-provider-switch}"
WORKSPACE="${CURSOR_DEFAULT_WORKSPACE:-$HOME/Projects}"

mkdir -p "$BIN_DIR" "$HOME/.cursor-provider-switch" "$SKILL_DIR"

# 记录安装路径与默认工作区
cat > "$HOME/.cursor-provider-switch/config" <<EOF
REPO_ROOT=$ROOT
CURSOR_DEFAULT_WORKSPACE=$WORKSPACE
EOF

# curswitch 命令
cat > "$BIN_DIR/curswitch" <<EOF
#!/bin/bash
export CURSOR_DEFAULT_WORKSPACE="$WORKSPACE"
exec /usr/bin/python3 "$ROOT/scripts/switch-cursor-provider.py" "\$@"
EOF
chmod +x "$BIN_DIR/curswitch"

# Skill
cp "$ROOT/skill/SKILL.md" "$SKILL_DIR/SKILL.md"

# 密钥：优先解密仓库内 enc
if [[ -f "$ROOT/config/secrets.env.enc" ]]; then
  echo "检测到加密密钥，运行解锁..."
  bash "$ROOT/scripts/env-unlock.sh" "$ROOT/config/secrets.env.enc"
elif [[ ! -f "$HOME/.cursor-provider-switch/secrets.env" ]]; then
  echo "提示: 尚无密钥。可复制 config/secrets.env.example → config/secrets.env 填写后执行 env-lock.sh"
fi

echo ""
echo "✓ 安装完成"
echo "  命令: curswitch status | minimax | deepseek"
echo "  Skill: $SKILL_DIR/SKILL.md"
echo "  确保 PATH 含: $BIN_DIR"
