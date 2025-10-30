#!/bin/bash
# NIAR 停止脚本

set -e

echo "=========================================="
echo "  停止 NIAR 服务"
echo "=========================================="
echo

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# ==========================================
# 1. 停止 Nginx
# ==========================================
echo "【1/3】停止 Nginx..."

if systemctl is-active --quiet nginx; then
    systemctl stop nginx
    echo "  ✓ Nginx 已停止"
else
    echo "  ⚠️  Nginx 未运行"
fi

echo

# ==========================================
# 2. 停止后端
# ==========================================
echo "【2/3】停止后端服务..."

if pkill -f "uvicorn app.main:app" 2>/dev/null; then
    echo "  ✓ 后端已停止"
    sleep 2
else
    echo "  ⚠️  后端未运行"
fi

echo

# ==========================================
# 3. 停止 Bettercap（双实例）
# ==========================================
echo "【3/3】停止 Bettercap（双实例）..."

SCAN_PIDS=$(pgrep -f "bettercap.*8081" 2>/dev/null || true)
BAN_PIDS=$(pgrep -f "bettercap.*8082" 2>/dev/null || true)

if [ -n "$SCAN_PIDS" ]; then
    kill $SCAN_PIDS 2>/dev/null || true
    echo "  ✓ Bettercap扫描实例已停止（端口8081）"
fi

if [ -n "$BAN_PIDS" ]; then
    kill $BAN_PIDS 2>/dev/null || true
    echo "  ✓ Bettercap Ban实例已停止（端口8082）"
fi

if [ -z "$SCAN_PIDS" ] && [ -z "$BAN_PIDS" ]; then
    echo "  ⚠️  Bettercap 未运行"
fi

sleep 1

# 强制停止任何残留的bettercap进程
if pkill -9 -f "bettercap.*api.rest" 2>/dev/null; then
    echo "  ⚠️  强制停止残留进程"
fi

echo

# ==========================================
# 验证停止
# ==========================================
echo "验证服务状态..."

BACKEND_RUNNING=$(pgrep -f "uvicorn app.main:app" | wc -l)
BETTERCAP_RUNNING=$(pgrep -f "bettercap.*api.rest" | wc -l)
if systemctl is-active --quiet nginx 2>/dev/null; then
    NGINX_RUNNING=1
else
    NGINX_RUNNING=0
fi

if [ "$BACKEND_RUNNING" -eq 0 ]; then
    echo "  ✓ 后端已完全停止"
else
    echo "  ⚠️  后端仍有 ${BACKEND_RUNNING} 个进程"
fi

if [ "$BETTERCAP_RUNNING" -eq 0 ]; then
    echo "  ✓ Bettercap 已完全停止"
else
    echo "  ⚠️  Bettercap 仍有 ${BETTERCAP_RUNNING} 个进程"
fi

if [ "$NGINX_RUNNING" -eq 0 ]; then
    echo "  ✓ Nginx 已完全停止"
else
    echo "  ⚠️  Nginx 仍在运行"
fi

echo
echo "=========================================="
echo "  ✅ NIAR 服务已停止"
echo "=========================================="
echo

