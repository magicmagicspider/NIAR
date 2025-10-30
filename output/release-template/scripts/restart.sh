#!/bin/bash
# NIAR 重启脚本

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "=========================================="
echo "  重启 NIAR 服务"
echo "=========================================="
echo

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# 停止服务
echo "停止服务..."
"${SCRIPT_DIR}/stop.sh"

echo
echo "等待 3 秒..."
sleep 3
echo

# 启动服务
echo "启动服务..."
"${SCRIPT_DIR}/start.sh"

echo
echo "=========================================="
echo "  ✅ NIAR 服务已重启"
echo "=========================================="
echo

