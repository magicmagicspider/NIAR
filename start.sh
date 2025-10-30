#!/bin/bash
# NIAR 开发环境启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "=========================================="
echo "  启动 NIAR 开发环境"
echo "=========================================="
echo

# 参数解析
WITH_BETTERCAP=true
if [ "$1" = "--no-bettercap" ]; then
    WITH_BETTERCAP=false
fi

# ==========================================
# 1. 启动后端
# ==========================================
echo "【1/3】启动后端..."

cd backend

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "  ⚠️  虚拟环境不存在，正在创建..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# 启动后端
nohup python3 -m uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --reload \
    --log-level info \
    > ../logs/backend.log 2>&1 &

BACKEND_PID=$!
deactivate

echo "  ✓ 后端已启动 (PID: ${BACKEND_PID})"
echo "  📝 日志: ${SCRIPT_DIR}/logs/backend.log"

cd ..

# ==========================================
# 2. 启动前端
# ==========================================
echo
echo "【2/3】启动前端..."

cd frontend

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "  ⚠️  依赖未安装，正在安装..."
    npm install
fi

# 启动前端开发服务器
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!

echo "  ✓ 前端已启动 (PID: ${FRONTEND_PID})"
echo "  📝 日志: ${SCRIPT_DIR}/logs/frontend.log"

cd ..

# ==========================================
# 3. 启动 Bettercap (可选)
# ==========================================
if [ "$WITH_BETTERCAP" = true ]; then
    echo
    echo "【3/3】启动 Bettercap (双实例)..."
    
    if command -v bettercap &> /dev/null; then
        # 启动实例1：扫描专用（端口8081）
        if pgrep -f "bettercap.*8081" > /dev/null; then
            echo "  ⚠️  Bettercap扫描实例已在运行 (端口8081)"
        else
            nohup sudo bettercap \
                -eval "set api.rest.address 127.0.0.1; set api.rest.port 8081; set api.rest.username user; set api.rest.password pass; api.rest on" \
                > logs/bettercap_scan.log 2>&1 &
            
            SCAN_PID=$!
            echo "  ✓ Bettercap扫描实例已启动 (PID: ${SCAN_PID})"
            echo "    🔗 REST API: http://127.0.0.1:8081"
            echo "    📝 日志: ${SCRIPT_DIR}/logs/bettercap_scan.log"
        fi
        
        # 启动实例2：Ban专用（端口8082）
        if pgrep -f "bettercap.*8082" > /dev/null; then
            echo "  ⚠️  Bettercap Ban实例已在运行 (端口8082)"
        else
            nohup sudo bettercap \
                -eval "set api.rest.address 127.0.0.1; set api.rest.port 8082; set api.rest.username user; set api.rest.password pass; api.rest on" \
                > logs/bettercap_ban.log 2>&1 &
            
            BAN_PID=$!
            echo "  ✓ Bettercap Ban实例已启动 (PID: ${BAN_PID})"
            echo "    🔗 REST API: http://127.0.0.1:8082"
            echo "    📝 日志: ${SCRIPT_DIR}/logs/bettercap_ban.log"
        fi
        
        echo "  👤 认证: user / pass (两个实例通用)"
    else
        echo "  ⚠️  Bettercap 未安装，跳过"
        echo "     参考: https://www.bettercap.org/installation/"
    fi
else
    echo
    echo "【3/3】跳过 Bettercap (使用 --no-bettercap)"
fi

echo
echo "=========================================="
echo "  ✅ 启动完成！"
echo "=========================================="
echo
echo "访问地址:"
echo "  前端开发服务器: http://localhost:5173"
echo "  后端 API: http://127.0.0.1:8000"
echo "  API 文档: http://127.0.0.1:8000/docs"
if [ "$WITH_BETTERCAP" = true ]; then
echo "  Bettercap扫描实例: http://127.0.0.1:8081"
echo "  Bettercap Ban实例: http://127.0.0.1:8082"
fi
echo
echo "日志文件:"
echo "  后端: ${SCRIPT_DIR}/logs/backend.log"
echo "  前端: ${SCRIPT_DIR}/logs/frontend.log"
if [ "$WITH_BETTERCAP" = true ]; then
echo "  Bettercap扫描: ${SCRIPT_DIR}/logs/bettercap_scan.log"
echo "  Bettercap Ban: ${SCRIPT_DIR}/logs/bettercap_ban.log"
fi
echo
echo "停止服务: ./stop.sh"
echo "重启服务: ./restart.sh"
echo


