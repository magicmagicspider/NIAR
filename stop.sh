#!/bin/bash
# NIAR 开发环境停止脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "  停止 NIAR 开发环境"
echo "=========================================="
echo

# ==========================================
# 1. 停止后端
# ==========================================
echo "【1/3】停止后端..."

BACKEND_PIDS=$(pgrep -f "uvicorn app.main:app" || true)
if [ -n "$BACKEND_PIDS" ]; then
    echo "$BACKEND_PIDS" | while read -r pid; do
        kill "$pid" 2>/dev/null || true
        echo "  ✓ 已停止后端进程 (PID: $pid)"
    done
    sleep 1
    
    # 强制杀死未响应的进程
    BACKEND_PIDS=$(pgrep -f "uvicorn app.main:app" || true)
    if [ -n "$BACKEND_PIDS" ]; then
        echo "$BACKEND_PIDS" | while read -r pid; do
            kill -9 "$pid" 2>/dev/null || true
            echo "  ⚠️  强制停止后端进程 (PID: $pid)"
        done
    fi
else
    echo "  ℹ️  后端未运行"
fi

# ==========================================
# 2. 停止前端
# ==========================================
echo
echo "【2/3】停止前端..."

# Vite 开发服务器
FRONTEND_PIDS=$(pgrep -f "vite.*--port 5173" || pgrep -f "npm run dev" || true)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "$FRONTEND_PIDS" | while read -r pid; do
        kill "$pid" 2>/dev/null || true
        echo "  ✓ 已停止前端进程 (PID: $pid)"
    done
    sleep 1
    
    # 强制杀死未响应的进程
    FRONTEND_PIDS=$(pgrep -f "vite" || true)
    if [ -n "$FRONTEND_PIDS" ]; then
        echo "$FRONTEND_PIDS" | while read -r pid; do
            kill -9 "$pid" 2>/dev/null || true
            echo "  ⚠️  强制停止前端进程 (PID: $pid)"
        done
    fi
else
    echo "  ℹ️  前端未运行"
fi

# ==========================================
# 3. 停止 Bettercap (双实例)
# ==========================================
echo
echo "【3/3】停止 Bettercap..."

# 停止扫描实例（8081）
SCAN_PIDS=$(pgrep -f "bettercap.*8081" || true)
if [ -n "$SCAN_PIDS" ]; then
    echo "$SCAN_PIDS" | while read -r pid; do
        sudo kill "$pid" 2>/dev/null || true
        echo "  ✓ 已停止 Bettercap扫描实例 (PID: $pid)"
    done
else
    echo "  ℹ️  Bettercap扫描实例未运行"
fi

# 停止Ban实例（8082）
BAN_PIDS=$(pgrep -f "bettercap.*8082" || true)
if [ -n "$BAN_PIDS" ]; then
    echo "$BAN_PIDS" | while read -r pid; do
        sudo kill "$pid" 2>/dev/null || true
        echo "  ✓ 已停止 Bettercap Ban实例 (PID: $pid)"
    done
else
    echo "  ℹ️  Bettercap Ban实例未运行"
fi

sleep 1

# 强制杀死所有未响应的Bettercap进程
ALL_BETTERCAP_PIDS=$(pgrep -f "bettercap.*api.rest" || true)
if [ -n "$ALL_BETTERCAP_PIDS" ]; then
    echo "$ALL_BETTERCAP_PIDS" | while read -r pid; do
        sudo kill -9 "$pid" 2>/dev/null || true
        echo "  ⚠️  强制停止 Bettercap 进程 (PID: $pid)"
    done
fi

echo
echo "=========================================="
echo "  ✅ 停止完成！"
echo "=========================================="
echo

# 验证停止
echo "验证服务状态..."

BACKEND_RUNNING=$(pgrep -f "uvicorn app.main:app" | wc -l)
FRONTEND_RUNNING=$(pgrep -f "vite" | wc -l)
BETTERCAP_RUNNING=$(pgrep -f "bettercap.*api.rest" | wc -l)

if [ "$BACKEND_RUNNING" -eq 0 ]; then
    echo "  ✓ 后端已完全停止"
else
    echo "  ⚠️  后端仍有 ${BACKEND_RUNNING} 个进程"
fi

if [ "$FRONTEND_RUNNING" -eq 0 ]; then
    echo "  ✓ 前端已完全停止"
else
    echo "  ⚠️  前端仍有 ${FRONTEND_RUNNING} 个进程"
fi

if [ "$BETTERCAP_RUNNING" -eq 0 ]; then
    echo "  ✓ Bettercap 已完全停止"
else
    echo "  ⚠️  Bettercap 仍有 ${BETTERCAP_RUNNING} 个进程"
fi

echo


