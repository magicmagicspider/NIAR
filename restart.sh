#!/bin/bash
# NIAR 开发环境重启脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "  重启 NIAR 开发环境"
echo "=========================================="
echo

# 停止服务
"${SCRIPT_DIR}/stop.sh"

# 等待一下确保完全停止
echo "等待服务完全停止..."
sleep 2

# 启动服务
"${SCRIPT_DIR}/start.sh" "$@"


