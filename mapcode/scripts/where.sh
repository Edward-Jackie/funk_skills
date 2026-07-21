#!/usr/bin/env bash
# 按需定位文件内符号的当前行号，导航图只保存路径和符号名。

set -uo pipefail

FILE="${1:?用法：where.sh <文件> <符号>}"
SYM="${2:?用法：where.sh <文件> <符号>}"
[ -f "$FILE" ] || { echo "文件不存在：$FILE" >&2; exit 1; }

B='[^A-Za-z0-9_]'
defs="$(grep -nE \
  "(func|function|def|class|type|interface)[[:space:]]+(\([^)]*\)[[:space:]]*)?${SYM}(${B}|$)|(const|let|var)[[:space:]]+${SYM}[[:space:]]*=|(^|${B})${SYM}[[:space:]]*\([^)]*\)[[:space:]]*\\{" \
  "$FILE" 2>/dev/null || true)"

if [ -n "$defs" ]; then
  echo "$defs"
else
  echo "（未找到 '${SYM}' 的定义，列出所有出现位置：）"
  grep -nE "(^|${B})${SYM}(${B}|$)" "$FILE" 2>/dev/null || echo "  文件中不存在该符号。"
fi
