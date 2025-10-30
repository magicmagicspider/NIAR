#!/bin/bash
# NIAR 安装脚本
# 包含依赖安装、Nginx 配置等所有安装步骤

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "=========================================="
echo "  NIAR 安装程序"
echo "  版本: 1.0"
echo "=========================================="
echo

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# ==========================================
# 1. 安装系统依赖
# ==========================================
echo "【1/6】安装系统依赖..."

# 检查包管理器
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt-get"
    echo "  检测到系统: Debian/Ubuntu"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    echo "  检测到系统: CentOS/RHEL"
else
    echo "  ❌ 不支持的操作系统"
    exit 1
fi

# 安装基础依赖
echo "  正在安装基础依赖（Python、Nginx、rsync）..."

# 检查是否有本地系统包（完全离线安装）
if [ -d "${SCRIPT_DIR}/packages/system-debs" ] && [ "$(ls -A ${SCRIPT_DIR}/packages/system-debs/*.deb 2>/dev/null)" ]; then
    echo "  使用本地系统包（完全离线安装）..."
    
    # 安装所有本地deb包
    dpkg -i "${SCRIPT_DIR}"/packages/system-debs/*.deb 2>/dev/null || true
    
    # 修复可能的依赖问题
    if [ "$PKG_MANAGER" = "apt-get" ]; then
        apt-get install -f -y 2>&1 | grep -v "^Reading\|^Building" || true
    fi
    
    echo "  ✓ 系统依赖已从本地包安装"
else
    # 在线安装
    echo "  本地包不存在，使用在线安装..."
    if [ "$PKG_MANAGER" = "apt-get" ]; then
        apt-get update -qq
        apt-get install -y python3 python3-pip python3-venv nginx rsync curl lsof net-tools 2>&1 | grep -v "^Selecting\|^Preparing\|^Unpacking" || true
    elif [ "$PKG_MANAGER" = "yum" ]; then
        yum install -y python3 python3-pip nginx rsync curl lsof net-tools -q
    fi
    echo "  ✓ 系统依赖已从在线源安装"
fi

# 验证安装
if ! command -v python3 &> /dev/null; then
    echo "  ❌ Python3 安装失败"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "  ✓ Python: ${PYTHON_VERSION}"

# 验证 python3-venv
if ! python3 -m venv --help &> /dev/null 2>&1; then
    echo "  ❌ python3-venv 不可用"
    exit 1
fi
echo "  ✓ python3-venv 已安装"

if ! command -v nginx &> /dev/null; then
    echo "  ❌ Nginx 安装失败"
    exit 1
fi
echo "  ✓ Nginx: $(nginx -v 2>&1 | cut -d'/' -f2)"

if ! command -v rsync &> /dev/null; then
    echo "  ❌ rsync 安装失败"
    exit 1
fi
echo "  ✓ rsync 已安装"

if ! command -v netstat &> /dev/null; then
    echo "  ⚠️  netstat 未安装（net-tools），功能可能受限"
else
    echo "  ✓ netstat 已安装"
fi

# 安装 Nmap（从本地或在线）
echo "  正在安装 Nmap..."
if ! command -v nmap &> /dev/null; then
    # 优先使用本地 deb 包
    if [ -f "${SCRIPT_DIR}/packages/binaries/nmap_"*".deb" ]; then
        echo "    使用本地 Nmap 包..."
        dpkg -i "${SCRIPT_DIR}"/packages/binaries/nmap_*.deb 2>/dev/null || apt-get install -f -y 2>&1 | grep -v "^Selecting\|^Preparing" || true
    else
        echo "    使用在线安装..."
        if [ "$PKG_MANAGER" = "apt-get" ]; then
            apt-get install -y nmap 2>&1 | grep -v "^Selecting\|^Preparing" || true
        else
            yum install -y nmap -q
        fi
    fi
fi

if command -v nmap &> /dev/null; then
    echo "  ✓ Nmap: $(nmap --version 2>&1 | head -1 | awk '{print $3}')"
else
    echo "  ⚠️  Nmap 安装失败（非致命错误，可继续）"
fi

# 安装 Bettercap（从本地）
echo "  正在安装 Bettercap..."
if ! command -v bettercap &> /dev/null; then
    # 优先使用本地二进制文件
    if [ -f "${SCRIPT_DIR}/packages/binaries/bettercap" ]; then
        echo "    使用本地 Bettercap 二进制..."
        cp "${SCRIPT_DIR}/packages/binaries/bettercap" /usr/local/bin/
        chmod +x /usr/local/bin/bettercap
    else
        echo "    ⚠️  本地 Bettercap 二进制不存在"
    fi
fi

if command -v bettercap &> /dev/null; then
    BETTERCAP_VERSION=$(bettercap -version 2>&1 | head -1 | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
    echo "  ✓ Bettercap: ${BETTERCAP_VERSION}"
else
    echo "  ⚠️  Bettercap 未安装（可选组件，可稍后手动安装）"
fi

echo

# ==========================================
# 2. 安装 Python 依赖
# ==========================================
echo "【2/6】安装 Python 依赖..."

cd "${SCRIPT_DIR}/backend"

# 创建虚拟环境
if [ ! -d ".venv" ]; then
    echo "  创建虚拟环境..."
    python3 -m venv .venv
    if [ ! -d ".venv" ]; then
        echo "  ❌ 创建虚拟环境失败"
        exit 1
    fi
    echo "  ✓ 虚拟环境创建完成"
else
    echo "  ⚠️  虚拟环境已存在，跳过创建"
fi

# 激活虚拟环境
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "  ❌ 激活虚拟环境失败"
    exit 1
fi

# 检查本地包
if [ -d "${SCRIPT_DIR}/packages/python-site-packages" ]; then
    echo "  使用本地 Python 包（离线安装）..."
    
    VENV_SITE_PACKAGES=".venv/lib/python3.10/site-packages"
    
    echo "  正在复制包到虚拟环境..."
    rsync -a --exclude='__pycache__' \
             --exclude='*.pyc' \
             --exclude='*.pyo' \
             --exclude='_distutils_hack' \
             --exclude='pip*' \
             --exclude='setuptools*' \
             --exclude='pkg_resources' \
             "${SCRIPT_DIR}/packages/python-site-packages/" "${VENV_SITE_PACKAGES}/"
    
    echo "  ✓ Python 依赖安装完成（离线模式）"
else
    echo "  本地包不存在，使用在线安装..."
    if [ -f "requirements.txt" ]; then
        pip install --no-cache-dir -r requirements.txt -q
        echo "  ✓ Python 依赖安装完成（在线模式）"
    else
        echo "  ❌ requirements.txt 不存在"
        deactivate
        exit 1
    fi
fi

# 验证关键依赖
echo "  验证关键依赖..."
REQUIRED_PACKAGES=("fastapi" "uvicorn" "sqlmodel" "httpx" "apscheduler" "jose" "passlib" "multipart")
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python -c "import ${package}" 2>/dev/null; then
        echo "    ✓ ${package}"
    else
        echo "    ❌ ${package} 缺失"
        MISSING_PACKAGES+=("${package}")
    fi
done

deactivate

if [ ${#MISSING_PACKAGES[@]} -ne 0 ]; then
    echo "  ❌ 以下包缺失: ${MISSING_PACKAGES[*]}"
    exit 1
fi

cd "${SCRIPT_DIR}"
echo

# ==========================================
# 3. 检查前端文件
# ==========================================
echo "【3/6】检查前端文件..."

if [ -d "frontend/dist" ]; then
    FILE_COUNT=$(find frontend/dist -type f | wc -l)
    echo "  ✓ 前端已构建（${FILE_COUNT} 个文件）"
else
    echo "  ❌ 前端未构建（frontend/dist 不存在）"
    echo "     如需重新构建："
    echo "     1. 安装 Node.js 18+"
    echo "     2. cd frontend && npm install && npm run build"
    exit 1
fi

echo

# ==========================================
# 4. 配置 Nginx
# ==========================================
echo "【4/6】配置 Nginx..."

NGINX_CONF_SRC="${SCRIPT_DIR}/nginx.conf"
NGINX_CONF_DEST="/etc/nginx/sites-available/niar"
NGINX_CONF_LINK="/etc/nginx/sites-enabled/niar"

if [ ! -f "${NGINX_CONF_SRC}" ]; then
    echo "  ❌ Nginx 配置文件不存在: ${NGINX_CONF_SRC}"
    exit 1
fi

# 复制配置文件
cp "${NGINX_CONF_SRC}" "${NGINX_CONF_DEST}"
echo "  ✓ 已复制配置文件"

# 替换项目路径
sed -i "s|/opt/niar|${SCRIPT_DIR}|g" "${NGINX_CONF_DEST}"
echo "  ✓ 已设置项目路径: ${SCRIPT_DIR}"

# 创建软链接
if [ -L "${NGINX_CONF_LINK}" ]; then
    rm "${NGINX_CONF_LINK}"
fi
ln -s "${NGINX_CONF_DEST}" "${NGINX_CONF_LINK}"
echo "  ✓ 已启用站点配置"

# 禁用默认站点
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    rm /etc/nginx/sites-enabled/default
    echo "  ✓ 已禁用默认站点"
fi

# 测试 Nginx 配置
if nginx -t 2>&1 | grep -q "successful"; then
    echo "  ✓ Nginx 配置测试通过"
else
    echo "  ❌ Nginx 配置测试失败"
    nginx -t
    exit 1
fi

echo

# ==========================================
# 5. 创建日志目录
# ==========================================
echo "【5/6】创建日志目录..."

mkdir -p "${SCRIPT_DIR}/logs"
chmod 755 "${SCRIPT_DIR}/logs"
echo "  ✓ 日志目录: ${SCRIPT_DIR}/logs"

echo

# ==========================================
# 6. 设置脚本权限
# ==========================================
echo "【6/6】设置脚本权限..."

cd "${SCRIPT_DIR}/scripts"
chmod +x *.sh 2>/dev/null || true
echo "  ✓ 已设置 scripts/ 目录脚本权限"

cd "${SCRIPT_DIR}"
chmod +x *.sh 2>/dev/null || true
echo "  ✓ 已设置根目录脚本权限"

echo

# ==========================================
# 安装完成
# ==========================================
echo "=========================================="
echo "  ✅ 安装完成！"
echo "=========================================="
echo
echo "系统信息:"
echo "  项目目录: ${SCRIPT_DIR}"
echo "  Python: ${PYTHON_VERSION}"
echo "  Nginx 配置: ${NGINX_CONF_DEST}"
echo "  日志目录: ${SCRIPT_DIR}/logs"
echo
echo "下一步:"
echo "  1. 启动服务: cd ${SCRIPT_DIR}/scripts && sudo ./start.sh"
echo "  2. 停止服务: cd ${SCRIPT_DIR}/scripts && sudo ./stop.sh"
echo "  3. 查看日志: tail -f ${SCRIPT_DIR}/logs/backend.log"
echo
echo "访问地址:"
echo "  前端: http://localhost"
echo "  前端: http://$(hostname -I | awk '{print $1}')"
echo "  API文档: http://localhost/docs"
echo
echo "配置文件:"
echo "  Nginx: ${NGINX_CONF_DEST}"
echo "  数据库: ${SCRIPT_DIR}/backend/db/niar.db"
echo

