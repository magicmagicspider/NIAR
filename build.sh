#!/bin/bash
# NIAR 打包脚本
# 从 output/release-template 读取打包模板

set -e

VERSION="1.0.12"
OUTPUT_DIR="output"
RELEASE_NAME="niar-${VERSION}"
RELEASE_DIR="${OUTPUT_DIR}/${RELEASE_NAME}"
TEMPLATE_DIR="${OUTPUT_DIR}/release-template"
VERSION_FILE=".version"

echo "=========================================="
echo "  NIAR 项目打包脚本"
echo "  版本: ${VERSION}"
echo "=========================================="
echo

# 检查并更新版本号文件
echo "🔍 检查版本号文件..."
if [ -f "${VERSION_FILE}" ]; then
    CURRENT_VERSION=$(cat "${VERSION_FILE}")
    if [ "${CURRENT_VERSION}" != "${VERSION}" ]; then
        echo "  ⚠️  版本号不一致！"
        echo "     .version 文件: ${CURRENT_VERSION}"
        echo "     build.sh VERSION: ${VERSION}"
        echo "  ✓ 自动更新 .version 文件为: ${VERSION}"
        echo "${VERSION}" > "${VERSION_FILE}"
    else
        echo "  ✓ 版本号一致: ${VERSION}"
    fi
else
    echo "  ⚠️  .version 文件不存在，创建中..."
    echo "${VERSION}" > "${VERSION_FILE}"
    echo "  ✓ 已创建 .version 文件: ${VERSION}"
fi
echo "  💡 提示: 版本号将在前端构建时注入代码中"
echo

# 检查打包模板
if [ ! -d "${TEMPLATE_DIR}" ]; then
    echo "❌ 打包模板目录不存在: ${TEMPLATE_DIR}"
    echo "   请先准备打包模板文件"
    exit 1
fi

# 1. 清理旧的打包目录
if [ -d "${RELEASE_DIR}" ]; then
    echo "🧹 清理旧的打包目录..."
    rm -rf "${RELEASE_DIR}"
fi

# 2. 创建目录结构
echo "📁 创建目录结构..."
mkdir -p "${RELEASE_DIR}"/{backend,frontend,scripts,docs,packages}

# 3. 复制后端文件
echo "📦 打包后端..."
mkdir -p "${RELEASE_DIR}/backend"
cp -r backend/app "${RELEASE_DIR}/backend/"
cp backend/requirements.txt "${RELEASE_DIR}/backend/"
cp backend/main.py "${RELEASE_DIR}/backend/" 2>/dev/null || true
echo "  ✓ 后端文件已复制"

# 4. 复制前端文件
echo "📦 打包前端..."
if [ -d "frontend/dist" ]; then
    mkdir -p "${RELEASE_DIR}/frontend"
    cp -r frontend/dist "${RELEASE_DIR}/frontend/"
    cp frontend/package.json "${RELEASE_DIR}/frontend/" 2>/dev/null || true
    cp frontend/vite.config.ts "${RELEASE_DIR}/frontend/" 2>/dev/null || true
    cp frontend/tsconfig.json "${RELEASE_DIR}/frontend/" 2>/dev/null || true
    cp frontend/index.html "${RELEASE_DIR}/frontend/" 2>/dev/null || true
    
    # 显示前端文件信息
    DIST_SIZE=$(du -sh frontend/dist | cut -f1)
    DIST_TIME=$(stat -c %y frontend/dist 2>/dev/null | cut -d'.' -f1 || stat -f "%Sm" frontend/dist)
    echo "  ✓ 使用已构建的前端 dist 目录 (${DIST_SIZE})"
    echo "  构建时间: ${DIST_TIME}"
    echo "  💡 版本号 ${VERSION} 已在构建时注入前端代码"
else
    echo "  ⚠️  前端未构建，跳过"
    echo "  提示: 运行 cd frontend && npm run build 来构建前端"
fi

# 5. 复制本地依赖包
echo "📦 打包本地依赖..."

# Python 依赖
if [ -d "packages/python-site-packages" ]; then
    echo "  复制 Python 包..."
    cp -r packages/python-site-packages "${RELEASE_DIR}/packages/"
    echo "  ✓ Python 包已包含（$(du -sh packages/python-site-packages | cut -f1)）"
else
    echo "  ⚠️  本地 Python 包不存在，跳过"
fi

# Nmap 和 Bettercap 二进制
if [ -d "packages/binaries" ]; then
    echo "  复制 Nmap 和 Bettercap 二进制..."
    cp -r packages/binaries "${RELEASE_DIR}/packages/"
    echo "  ✓ 二进制文件已包含（$(du -sh packages/binaries | cut -f1)）"
    ls -lh packages/binaries/ | grep -v "^total" | awk '{print "    - " $9 " (" $5 ")"}'
else
    echo "  ⚠️  本地二进制文件不存在，跳过"
fi

# 系统依赖 deb 包（完全离线安装）
if [ -d "packages/system-debs" ]; then
    echo "  复制系统依赖包（离线安装支持）..."
    cp -r packages/system-debs "${RELEASE_DIR}/packages/"
    DEB_COUNT=$(ls packages/system-debs/*.deb 2>/dev/null | wc -l)
    echo "  ✓ 系统依赖包已包含（$(du -sh packages/system-debs | cut -f1)，${DEB_COUNT} 个包）"
else
    echo "  ⚠️  系统依赖包不存在，将使用在线安装"
fi

# 6. 从模板复制文件
echo "📦 从模板复制文件..."

# 复制安装脚本
if [ -f "${TEMPLATE_DIR}/install.sh" ]; then
    cp "${TEMPLATE_DIR}/install.sh" "${RELEASE_DIR}/"
    chmod +x "${RELEASE_DIR}/install.sh"
    echo "  ✓ install.sh"
else
    echo "  ❌ install.sh 不存在于模板"
    exit 1
fi

# 复制 Nginx 配置
if [ -f "${TEMPLATE_DIR}/nginx.conf" ]; then
    cp "${TEMPLATE_DIR}/nginx.conf" "${RELEASE_DIR}/"
    echo "  ✓ nginx.conf"
else
    echo "  ❌ nginx.conf 不存在于模板"
    exit 1
fi

# 复制 scripts 目录
if [ -d "${TEMPLATE_DIR}/scripts" ]; then
    cp -r "${TEMPLATE_DIR}/scripts" "${RELEASE_DIR}/"
    chmod +x "${RELEASE_DIR}"/scripts/*.sh
    echo "  ✓ scripts/ 目录"
else
    echo "  ❌ scripts/ 不存在于模板"
    exit 1
fi

# 复制模板中的文档
if [ -d "${TEMPLATE_DIR}/docs" ]; then
    cp -r "${TEMPLATE_DIR}"/docs/* "${RELEASE_DIR}/docs/" 2>/dev/null || true
    echo "  ✓ 模板文档"
fi

# 7. 生成文档
echo "📝 生成文档..."

# README.md
cat > "${RELEASE_DIR}/README.md" << 'EOF'
# NIAR - 网络设备监控系统

版本: 1.0

## 功能特点

- 🔍 **网络扫描**: 支持 Nmap 和 Bettercap 双引擎扫描
- 📊 **设备监控**: 实时监控网络设备上下线状态
- 🕐 **定时任务**: 灵活的定时扫描任务配置
- 🎯 **双模式**: 
  - 主动探测：快速发现设备（推荐）
  - 被动侦察：完全隐蔽监听
- 📈 **历史记录**: 完整的扫描历史和设备变更记录
- 🌐 **Web界面**: 现代化的 Vue3 + Element Plus 界面

## 系统要求

### 完全离线安装 ⭐
安装包已包含所有依赖，支持在无网络环境下完成部署！

**必需（仅操作系统）：**
- Ubuntu 20.04+ / Debian 11+（或兼容的发行版）
- root 权限

**已包含（自动安装）：**
- Python 3.10+（系统 deb 包）
- python3-venv、python3-pip（系统 deb 包）
- Nginx 1.18+（系统 deb 包）
- rsync、curl、lsof（系统 deb 包）
- Nmap（本地 deb 包）
- Bettercap（本地二进制文件）
- Python 依赖包（离线安装）

**安装方式：**
- 有网络：自动在线安装系统包，离线安装应用依赖
- 无网络：完全离线安装所有依赖（包括系统包）⭐

### 可选
- Node.js 18+ 和 npm（仅在需要重新构建前端时）

## 快速开始

详细安装步骤请查看 `docs/INSTALL.md`

### 基本步骤

1. **安装基础依赖**
   ```bash
   # 只需安装 Python 和 Nginx（其他已包含）⭐
   sudo apt-get update
   sudo apt-get install -y python3 python3-venv nginx rsync
   ```
   
   **注意**: Nmap 和 Bettercap 已包含在安装包中，无需预先安装！

2. **安装系统（自动配置）**
   ```bash
   # 一键安装：依赖、Nginx配置、初始化
   sudo ./install.sh
   ```
   
   **注意**: 本安装包已包含所有 Python 依赖，支持完全离线安装！

3. **启动服务**
   ```bash
   cd scripts
   sudo ./start.sh
   ```
   
   服务将通过 Nginx 部署，自动启动后端和 Bettercap

4. **访问系统**
   ```
   前端: http://localhost:80
   后端: http://localhost:8000
   API文档: http://localhost:8000/docs
   ```

5. **停止服务**
   ```bash
   cd scripts
   sudo ./stop.sh
   ```

## 部署架构

```
客户端
  ↓
Nginx (80/443)
  ↓
  ├─→ 前端静态文件 (frontend/dist/)
  └─→ 后端 API (127.0.0.1:8000)
       └─→ Bettercap (127.0.0.1:8081)
```

**特点:**
- ✅ Nginx 高性能静态文件服务
- ✅ 后端隐藏在 127.0.0.1，安全可靠
- ✅ 支持 HTTPS 配置
- ✅ 完整的访问日志
- ✅ 静态资源缓存优化

详细配置请查看 `docs/NGINX_DEPLOYMENT.md`

## 配置说明

### Bettercap 配置

在 Web 界面的"设置"页面配置：
- API 地址: http://127.0.0.1:8081
- 用户名: user
- 密码: pass
- 探测间隔: 5秒（可调整）
- 探测模式: 主动探测 / 被动侦察

### 网络扫描配置

支持两种扫描方式：
1. **定时任务**: 周期性自动扫描
2. **手动扫描**: 即时执行扫描

## 目录结构

```
niar-1.0/
├── install.sh              安装脚本（依赖+Nginx+配置）
├── nginx.conf              Nginx 配置文件
├── backend/                后端代码
├── frontend/               前端代码
├── packages/               本地依赖包
├── scripts/                启停脚本
│   ├── start.sh           启动服务
│   ├── stop.sh            停止服务
│   ├── restart.sh         重启服务
│   └── check_mode.sh      查看 Bettercap 状态
└── docs/                   文档
    ├── INSTALL.md         安装指南
    ├── USER_GUIDE.md      使用指南
    └── NGINX_DEPLOYMENT.md Nginx 部署指南
```

## 常见问题

### 1. Bettercap 未安装
需要预先安装 Bettercap 到 `/usr/local/bin/bettercap`

### 2. 端口被占用
- 前端需要端口 80（Nginx）
- 后端需要端口 8000
- Bettercap 需要端口 8081

### 3. 权限问题
启动脚本需要 `sudo` 权限

## 技术栈

### 后端
- FastAPI - 现代化的 Python Web 框架
- SQLModel - 数据库 ORM
- APScheduler - 定时任务调度
- httpx - 异步 HTTP 客户端

### 前端
- Vue 3 - 渐进式 JavaScript 框架
- TypeScript - 类型安全
- Element Plus - UI 组件库
- Vite - 构建工具

### 扫描引擎
- Nmap - 网络扫描
- Bettercap - 网络监控和嗅探

## 文档

- `docs/INSTALL.md` - 详细安装步骤
- `docs/USER_GUIDE.md` - 使用指南
- `docs/NGINX_DEPLOYMENT.md` - Nginx 部署指南

## 版本信息

- 版本: 1.0
- 发布日期: 2025-10-26

## 许可证

请查看项目许可证文件

---

**祝使用愉快！**
EOF

# VERSION 文件
cat > "${RELEASE_DIR}/VERSION" << EOF
NIAR - 网络设备监控系统
版本: ${VERSION}
发布日期: $(date +%Y-%m-%d)
EOF

# 8. 创建文件清单
echo "📋 生成文件清单..."
cd "${RELEASE_DIR}"
find . -type f | sort > MANIFEST.txt
cd - > /dev/null

# 9. 打包为 tar.gz
echo "📦 压缩打包..."
cd "${OUTPUT_DIR}"
tar -czf "${RELEASE_NAME}.tar.gz" "${RELEASE_NAME}/"
cd ..

# 10. 生成 MD5 校验
echo "🔐 生成校验和..."
cd "${OUTPUT_DIR}"
md5sum "${RELEASE_NAME}.tar.gz" > "${RELEASE_NAME}.tar.gz.md5"
cd ..

# 11. 清理临时目录（可选）
# rm -rf "${RELEASE_DIR}"

echo
echo "=========================================="
echo "  打包完成！"
echo "=========================================="
echo
echo "输出文件:"
echo "  📦 ${OUTPUT_DIR}/${RELEASE_NAME}.tar.gz"
echo "  🔐 ${OUTPUT_DIR}/${RELEASE_NAME}.tar.gz.md5"
echo
echo "目录结构:"
ls -lh "${OUTPUT_DIR}/${RELEASE_NAME}.tar.gz"
echo
echo "校验和:"
cat "${OUTPUT_DIR}/${RELEASE_NAME}.tar.gz.md5"
echo
echo "=========================================="
echo "发布说明:"
echo "  1. 将 ${RELEASE_NAME}.tar.gz 发送给用户"
echo "  2. 提供 .md5 文件用于校验完整性"
echo "  3. 用户解压后运行: sudo ./install.sh"
echo "=========================================="
echo

