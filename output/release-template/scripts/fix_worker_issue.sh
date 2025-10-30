#!/bin/bash
# NIAR 多Worker状态不一致问题修复补丁
# 版本: 1.0.7
# 日期: 2025-10-26
# 
# 问题描述:
#   生产环境使用 --workers 4 导致多个worker进程，每个进程有独立内存空间
#   导致ARP Ban和Bettercap任务状态在不同worker间不同步，刷新页面状态随机变化
#
# 解决方案:
#   1. 将worker数量改为1（核心修复）
#   2. 在nginx配置中添加ip_hash（防御性措施）

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  NIAR 多Worker状态不一致问题修复补丁"
echo "=========================================="
echo
echo "问题: 生产环境状态显示不一致（ARP Ban、Bettercap任务状态随机切换）"
echo "原因: --workers 4 导致多进程内存不共享"
echo "方案: 单worker + nginx ip_hash"
echo

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# ==========================================
# 1. 备份文件
# ==========================================
echo "【1/3】备份原始文件..."

BACKUP_DIR="${PROJECT_DIR}/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${BACKUP_DIR}"

if [ -f "${SCRIPT_DIR}/start.sh" ]; then
    cp "${SCRIPT_DIR}/start.sh" "${BACKUP_DIR}/start.sh.bak"
    echo "  ✓ 已备份: start.sh"
fi

if [ -f "${PROJECT_DIR}/nginx.conf" ]; then
    cp "${PROJECT_DIR}/nginx.conf" "${BACKUP_DIR}/nginx.conf.bak"
    echo "  ✓ 已备份: nginx.conf"
elif [ -f "/etc/nginx/sites-available/niar" ]; then
    cp "/etc/nginx/sites-available/niar" "${BACKUP_DIR}/nginx.conf.bak"
    echo "  ✓ 已备份: /etc/nginx/sites-available/niar"
fi

echo "  备份目录: ${BACKUP_DIR}"
echo

# ==========================================
# 2. 修复 start.sh
# ==========================================
echo "【2/3】修复 start.sh (--workers 4 -> 1)..."

START_SH="${SCRIPT_DIR}/start.sh"

if [ -f "${START_SH}" ]; then
    # 检查是否已经是 workers 1
    if grep -q "\-\-workers 1" "${START_SH}"; then
        echo "  ℹ️  start.sh 已经是 workers 1，跳过修改"
    else
        # 替换 --workers 4 为 --workers 1
        sed -i 's/--workers 4/--workers 1/g' "${START_SH}"
        
        # 验证修改
        if grep -q "\-\-workers 1" "${START_SH}"; then
            echo "  ✓ start.sh 已修复 (workers: 4 -> 1)"
        else
            echo "  ❌ start.sh 修改失败，请手动修改"
            exit 1
        fi
    fi
else
    echo "  ⚠️  start.sh 不存在，跳过"
fi

echo

# ==========================================
# 3. 修复 nginx.conf
# ==========================================
echo "【3/3】修复 nginx.conf (添加 ip_hash)..."

# 查找 nginx 配置文件
NGINX_CONF=""
if [ -f "${PROJECT_DIR}/nginx.conf" ]; then
    NGINX_CONF="${PROJECT_DIR}/nginx.conf"
elif [ -f "/etc/nginx/sites-available/niar" ]; then
    NGINX_CONF="/etc/nginx/sites-available/niar"
fi

if [ -n "${NGINX_CONF}" ]; then
    # 检查是否已经有 ip_hash
    if grep -q "ip_hash" "${NGINX_CONF}"; then
        echo "  ℹ️  nginx.conf 已包含 ip_hash，跳过修改"
    else
        # 在 upstream backend { 后添加 ip_hash;
        sed -i '/upstream backend {/a\    ip_hash;' "${NGINX_CONF}"
        
        # 验证修改
        if grep -q "ip_hash" "${NGINX_CONF}"; then
            echo "  ✓ nginx.conf 已修复 (添加 ip_hash)"
            
            # 测试 nginx 配置
            if nginx -t 2>&1 | grep -q "successful"; then
                echo "  ✓ Nginx 配置测试通过"
            else
                echo "  ⚠️  Nginx 配置测试失败，但补丁已应用"
                echo "     请手动检查: nginx -t"
            fi
        else
            echo "  ❌ nginx.conf 修改失败，请手动修改"
            exit 1
        fi
    fi
else
    echo "  ⚠️  未找到 nginx 配置文件"
    echo "     请手动在 upstream backend { 块中添加: ip_hash;"
fi

echo

# ==========================================
# 完成
# ==========================================
echo "=========================================="
echo "  ✅ 补丁安装完成！"
echo "=========================================="
echo
echo "修改内容:"
echo "  1. start.sh: --workers 4 -> 1"
echo "  2. nginx.conf: 添加 ip_hash"
echo
echo "备份位置:"
echo "  ${BACKUP_DIR}/"
echo
echo "下一步:"
echo "  1. 重启服务使修改生效:"
echo "     cd ${SCRIPT_DIR}"
echo "     sudo ./restart.sh"
echo
echo "  2. 验证修复:"
echo "     - 访问Web界面"
echo "     - 执行ARP Ban操作"
echo "     - 多次刷新页面，状态应保持一致"
echo
echo "  3. 查看进程数（应该只有1个worker）:"
echo "     ps aux | grep 'uvicorn app.main:app'"
echo
echo "如需回滚:"
echo "  cp ${BACKUP_DIR}/start.sh.bak ${SCRIPT_DIR}/start.sh"
echo "  cp ${BACKUP_DIR}/nginx.conf.bak ${NGINX_CONF}"
echo


