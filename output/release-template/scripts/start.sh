#!/bin/bash
# NIAR 启动脚本
# 使用 Nginx 部署方式

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  启动 NIAR 服务"
echo "=========================================="
echo

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# 函数：获取默认网络接口
get_default_interface() {
    local interface=$(ip route | grep default | awk '{print $5}' | head -n 1)
    if [ -z "$interface" ]; then
        interface=$(route -n | grep '^0.0.0.0' | awk '{print $8}' | head -n 1)
    fi
    echo "$interface"
}

# ==========================================
# 1. 检查安装
# ==========================================
echo "【1/4】检查安装..."

if [ ! -d "${PROJECT_DIR}/backend/.venv" ]; then
    echo "  ❌ 未安装，请先运行: sudo ./install.sh"
    exit 1
fi

if [ ! -f "/etc/nginx/sites-enabled/niar" ]; then
    echo "  ❌ Nginx 未配置，请先运行: sudo ./install.sh"
    exit 1
fi

echo "  ✓ 已安装"
echo

# ==========================================
# 2. 启动后端
# ==========================================
echo "【2/4】启动后端服务..."

cd "${PROJECT_DIR}/backend"

# 停止旧进程
pkill -f "uvicorn app.main:app" 2>/dev/null || true
sleep 1

# 启动后端（激活虚拟环境后使用 python3 -m uvicorn）
source .venv/bin/activate
nohup python3 -m uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 1 \
    --log-level info \
    > ../logs/backend.log 2>&1 &

BACKEND_PID=$!
deactivate
echo "  ✓ 后端已启动 (PID: ${BACKEND_PID})"
sleep 2

# 检查后端是否运行
if ! ps -p ${BACKEND_PID} > /dev/null 2>&1; then
    echo "  ❌ 后端启动失败，查看日志: tail -f ${PROJECT_DIR}/logs/backend.log"
    exit 1
fi

echo

# ==========================================
# 3. 启动 Bettercap（双实例架构）
# ==========================================
echo "【3/4】启动 Bettercap（双实例）..."

if command -v bettercap &> /dev/null; then
    # 停止旧进程
    pkill -f "bettercap.*api.rest" 2>/dev/null || true
    sleep 1
    
    # 获取网络接口
    INTERFACE=$(get_default_interface)
    
    if [ -n "${INTERFACE}" ]; then
        # 启动扫描实例（端口8081）
        nohup bettercap -iface ${INTERFACE} -eval "
            set api.rest.username user;
            set api.rest.password pass;
            set api.rest.address 0.0.0.0;
            set api.rest.port 8081;
            api.rest on;
            events.stream off;
        " > ../logs/bettercap_scan.log 2>&1 &
        
        SCAN_PID=$!
        echo "  ✓ Bettercap扫描实例已启动 (PID: ${SCAN_PID}, 端口: 8081, 接口: ${INTERFACE})"
        
        sleep 1
        
        # 启动Ban实例（端口8082）
        nohup bettercap -iface ${INTERFACE} -eval "
            set api.rest.username user;
            set api.rest.password pass;
            set api.rest.address 0.0.0.0;
            set api.rest.port 8082;
            api.rest on;
            events.stream off;
        " > ../logs/bettercap_ban.log 2>&1 &
        
        BAN_PID=$!
        echo "  ✓ Bettercap Ban实例已启动 (PID: ${BAN_PID}, 端口: 8082, 接口: ${INTERFACE})"
        echo "  ℹ️  双实例架构：扫描和Ban可同时运行，互不干扰"
    else
        echo "  ⚠️  无法检测网络接口，跳过 Bettercap"
    fi
else
    echo "  ⚠️  Bettercap 未安装，跳过"
    echo "  安装方法: https://www.bettercap.org/installation/"
fi

echo

# ==========================================
# 4. 启动 Nginx
# ==========================================
echo "【4/4】启动 Nginx..."

systemctl start nginx

if systemctl is-active --quiet nginx; then
    echo "  ✓ Nginx 已启动"
else
    echo "  ❌ Nginx 启动失败"
    echo "  查看日志: sudo journalctl -u nginx -n 50"
    exit 1
fi

echo

# ==========================================
# 启动完成
# ==========================================
echo "=========================================="
echo "  ✅ NIAR 启动完成！"
echo "=========================================="
echo
echo "访问地址:"
echo "  前端: http://localhost"
echo "  前端: http://$(hostname -I | awk '{print $1}')"
echo "  API: http://localhost/api"
echo "  API文档: http://localhost/docs"
echo
echo "服务状态:"
if ps -p ${BACKEND_PID} > /dev/null 2>&1; then
    echo "  ✓ 后端运行中 (PID: ${BACKEND_PID})"
else
    echo "  ✗ 后端未运行"
fi

if systemctl is-active --quiet nginx; then
    echo "  ✓ Nginx 运行中"
else
    echo "  ✗ Nginx 未运行"
fi

if command -v bettercap &> /dev/null; then
    SCAN_RUNNING=false
    BAN_RUNNING=false
    
    if [ -n "${SCAN_PID}" ] && ps -p ${SCAN_PID} > /dev/null 2>&1; then
        echo "  ✓ Bettercap扫描实例运行中 (PID: ${SCAN_PID}, 端口: 8081)"
        SCAN_RUNNING=true
    fi
    
    if [ -n "${BAN_PID}" ] && ps -p ${BAN_PID} > /dev/null 2>&1; then
        echo "  ✓ Bettercap Ban实例运行中 (PID: ${BAN_PID}, 端口: 8082)"
        BAN_RUNNING=true
    fi
    
    if ! $SCAN_RUNNING && ! $BAN_RUNNING; then
        echo "  ⚠️  Bettercap 未运行"
    fi
fi

echo
echo "管理命令:"
echo "  查看日志: tail -f ${PROJECT_DIR}/logs/backend.log"
echo "  停止服务: sudo ./stop.sh"
echo "  重启服务: sudo ./restart.sh"
echo "  Bettercap 状态: ./check_mode.sh"
echo

