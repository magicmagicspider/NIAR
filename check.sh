#!/bin/bash
# NIAR 开发环境状态检查脚本

echo "=========================================="
echo "  NIAR 开发环境状态检查"
echo "=========================================="
echo

# ==========================================
# 1. 后端状态
# ==========================================
echo "【1/3】后端服务状态"

BACKEND_PIDS=$(pgrep -f "uvicorn app.main:app" || true)
if [ -n "$BACKEND_PIDS" ]; then
    echo "  ✓ 后端正在运行"
    echo "$BACKEND_PIDS" | while read -r pid; do
        echo "    PID: $pid"
        ps -p "$pid" -o etime,cmd | tail -1 | awk '{print "    运行时间: " $1}'
    done
    
    # 检查端口
    if netstat -tuln 2>/dev/null | grep -q ":8000 "; then
        echo "    ✓ 端口 8000 正在监听"
    else
        echo "    ⚠️  端口 8000 未监听"
    fi
    
    # 测试 API
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "    ✓ API 健康检查通过"
    else
        echo "    ⚠️  API 健康检查失败"
    fi
else
    echo "  ✗ 后端未运行"
fi

# ==========================================
# 2. 前端状态
# ==========================================
echo
echo "【2/3】前端服务状态"

FRONTEND_PIDS=$(pgrep -f "vite" || true)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "  ✓ 前端正在运行"
    echo "$FRONTEND_PIDS" | while read -r pid; do
        echo "    PID: $pid"
        ps -p "$pid" -o etime,cmd | tail -1 | awk '{print "    运行时间: " $1}'
    done
    
    # 检查端口
    if netstat -tuln 2>/dev/null | grep -q ":5173 "; then
        echo "    ✓ 端口 5173 正在监听"
    else
        echo "    ⚠️  端口 5173 未监听"
    fi
else
    echo "  ✗ 前端未运行"
fi

# ==========================================
# 3. Bettercap 状态
# ==========================================
echo
echo "【3/3】Bettercap 服务状态"

BETTERCAP_PIDS=$(pgrep -f "bettercap.*api.rest" || true)
if [ -n "$BETTERCAP_PIDS" ]; then
    echo "  ✓ Bettercap 正在运行"
    echo "$BETTERCAP_PIDS" | while read -r pid; do
        echo "    PID: $pid"
        ps -p "$pid" -o etime,cmd | tail -1 | awk '{print "    运行时间: " $1}'
    done
    
    # 检查端口
    if netstat -tuln 2>/dev/null | grep -q ":8081 "; then
        echo "    ✓ 端口 8081 正在监听"
    else
        echo "    ⚠️  端口 8081 未监听"
    fi
    
    # 测试 API
    if curl -s -u user:pass http://127.0.0.1:8081/api/session > /dev/null 2>&1; then
        echo "    ✓ REST API 连接正常"
        
        # 获取运行模式
        SESSION=$(curl -s -u user:pass http://127.0.0.1:8081/api/session)
        PROBE_RUNNING=$(echo "$SESSION" | grep -o '"net.probe"[^}]*"running":true' || true)
        RECON_RUNNING=$(echo "$SESSION" | grep -o '"net.recon"[^}]*"running":true' || true)
        
        if [ -n "$PROBE_RUNNING" ] && [ -n "$RECON_RUNNING" ]; then
            echo "    📡 工作模式: 主动探测 (net.probe + net.recon)"
        elif [ -n "$RECON_RUNNING" ]; then
            echo "    📡 工作模式: 被动侦察 (net.recon only)"
        elif [ -n "$PROBE_RUNNING" ]; then
            echo "    📡 工作模式: 仅主动探测 (net.probe only)"
        else
            echo "    ⏸️  工作模式: 空闲 (无模块运行)"
        fi
    else
        echo "    ⚠️  REST API 连接失败"
    fi
else
    echo "  ✗ Bettercap 未运行"
fi

# ==========================================
# 总结
# ==========================================
echo
echo "=========================================="

BACKEND_COUNT=$(pgrep -f "uvicorn app.main:app" | wc -l)
FRONTEND_COUNT=$(pgrep -f "vite" | wc -l)
BETTERCAP_COUNT=$(pgrep -f "bettercap.*api.rest" | wc -l)

ALL_RUNNING=true
if [ "$BACKEND_COUNT" -eq 0 ]; then
    ALL_RUNNING=false
fi
if [ "$FRONTEND_COUNT" -eq 0 ]; then
    ALL_RUNNING=false
fi

if [ "$ALL_RUNNING" = true ]; then
    echo "  ✅ 所有核心服务正常运行"
else
    echo "  ⚠️  部分服务未运行"
fi

echo "=========================================="
echo


