# NIAR 打包要求文档

版本: 1.0.2  
更新日期: 2025-10-26 (最新打包)  
最新功能: 修复 ARP Ban 自动停止问题

## ✨ 最新更新

### v1.0.2 - 2025-10-26 ⭐ 最新版本
- ✅ **关键Bug修复：ARP Ban 逻辑冲突**
  - 移除"目标为空自动停止"的错误逻辑
  - 确保只有手动停止才会停止服务
  - Ban的目的就是让设备离线，离线是预期结果
- ✅ **日志增强**
  - 启动/停止/更新时的详细日志
  - 目标为空时的警告提示
  - 便于调试和监控
- ✅ 打包大小：约 61MB (压缩后)

### v1.0.1 - 2025-10-26
- ✅ **白名单配置功能升级**
  - 用户可手动配置网关IP（不再硬编码）
  - 支持添加多个白名单设备（DNS、NAS等）
  - 白名单持久化保存（localStorage）
  - 自动检测网关功能
- ✅ **界面优化**
  - 左右两侧表格高度统一（350px）
  - 新增白名单配置卡片
  - 增强启动确认对话框（显示完整保护列表）
- ✅ **后端改进**
  - 支持接收用户配置的白名单
  - 自动合并：网关 + 本机 + 用户自定义
  - 详细的日志记录
- ✅ 打包大小：约 61MB (压缩后)
- ✅ 前端构建时间：2025-10-26 23:24

### v1.0 - 2025-10-26
- ✅ 新增网络管控功能 (ARP Ban)
  - 左右分栏界面：可用IP列表 / 目标设备管理
  - 目标设备持久化存储（数据库）
  - 全局后端运行（关闭页面仍运行）
  - 实时状态显示和操作日志
- ✅ 完整离线安装支持

### 文件变更统计（v1.0.1）
- **前端新增/修改**: 约 250 行（白名单配置界面）
- **后端修改**: 约 80 行（支持用户白名单）
- **文档新增**: 2 个文件（WHITELIST_CONFIG_UPDATE.md, verify_whitelist_ui.md）

## 📋 目录结构说明

### 开发目录（项目根目录）
```
niar/
├── backend/                  后端源代码（开发用）
├── frontend/                 前端源代码（开发用）
├── packages/                 本地依赖包（打包时使用）
│   └── python-site-packages/  Python 离线依赖
├── output/                   打包输出目录 ⭐
│   ├── release-template/    打包模板文件 ⭐
│   │   ├── install.sh       安装脚本
│   │   ├── nginx.conf       Nginx 配置
│   │   ├── scripts/         启停脚本
│   │   │   ├── start.sh
│   │   │   ├── stop.sh
│   │   │   ├── restart.sh
│   │   │   └── check_mode.sh
│   │   └── docs/            文档
│   │       └── NGINX_DEPLOYMENT.md
│   └── niar-1.0.tar.gz      打包后的发布文件
├── build.sh                  打包脚本 ⭐
└── BUILD_REQUIREMENTS.md     本文档 ⭐
```

**关键点:**
- ✅ 开发目录只保留源代码
- ✅ 打包相关文件都在 `output/` 下
- ✅ `output/release-template/` 是打包模板
- ✅ 打包后的文件也输出到 `output/`

### 打包后目录（发布给用户）
```
niar-1.0/
├── install.sh                安装脚本（依赖+Nginx+配置）⭐
├── nginx.conf                Nginx 配置文件
├── backend/                  后端代码
├── frontend/                 前端构建产物
├── packages/                 本地依赖包
│   └── python-site-packages/
├── scripts/                  启停脚本 ⭐
│   ├── start.sh             启动服务
│   ├── stop.sh              停止服务
│   ├── restart.sh           重启服务
│   └── check_mode.sh        查看 Bettercap 状态
├── docs/                     文档
├── README.md                 项目说明
└── VERSION                   版本信息
```

## 🎯 打包原则

### 1. 职责分离
- **install.sh**: 负责安装和配置（一次性）
  - 检查系统依赖
  - 安装 Python 依赖（离线）
  - 配置 Nginx
  - 创建目录和权限

- **scripts/**: 负责启停控制（日常使用）
  - start.sh - 启动服务
  - stop.sh - 停止服务
  - restart.sh - 重启服务
  - check_mode.sh - 查看状态

### 2. 目录管理
- ✅ 开发目录干净：只保留源代码和打包脚本
- ✅ 打包模板集中：所有模板文件在 `output/release-template/`
- ✅ 输出集中：打包结果在 `output/`

### 3. 部署方式
- ✅ 统一使用 Nginx 部署
- ✅ 后端监听 127.0.0.1:8000（不暴露）
- ✅ Bettercap 监听 0.0.0.0:8081

## 📦 打包步骤

### 准备工作

1. **确保前端已构建**（重要：包含新的网络管控组件）
   ```bash
   cd frontend
   npm install
   npm run build
   # 生成 frontend/dist/ 目录
   # 前端包含所有新功能（网络管控、设备扫描等）
   ```

2. **确保依赖已下载到本地**
   ```bash
   # Python 依赖应在 packages/python-site-packages/
   ls -lh packages/python-site-packages/
   
   # Nmap 和 Bettercap 二进制应在 packages/binaries/
   ls -lh packages/binaries/
   # 应包含:
   # - bettercap (74MB)
   # - nmap_*.deb (1.7MB)
   
   # 系统依赖包应在 packages/system-debs/（完全离线安装）⭐
   ls -lh packages/system-debs/
   # 应包含约22个deb包:
   # - python3_*.deb, python3-venv_*.deb, python3-pip_*.deb
   # - nginx_*.deb, nginx-core_*.deb, nginx-common_*.deb
   # - rsync_*.deb, curl_*.deb, lsof_*.deb
   # - 以及相关依赖库
   ```

3. **确保打包模板完整**
   ```bash
   # 检查模板目录
   ls -la output/release-template/
   # 应包含:
   # - install.sh
   # - nginx.conf
   # - scripts/ (start.sh, stop.sh, restart.sh, check_mode.sh)
   # - docs/ (可选)
   ```

### 执行打包

```bash
# 在项目根目录执行
chmod +x build.sh
./build.sh
```

打包脚本会自动：
1. 清理旧的打包目录
2. 创建新的目录结构
3. 复制后端代码
4. 复制前端构建产物
5. 复制本地依赖包
6. 从模板复制安装和启停脚本
7. 生成文档
8. 打包为 tar.gz
9. 生成 MD5 校验

### 输出结果

```
output/
├── niar-1.0/                打包目录（临时）
├── niar-1.0.tar.gz          发布包 ⭐
└── niar-1.0.tar.gz.md5      校验文件 ⭐
```

## 🔧 维护打包模板

### 修改安装脚本

编辑 `output/release-template/install.sh`:
- 修改依赖检查逻辑
- 修改 Nginx 配置逻辑
- 修改初始化步骤

### 修改启停脚本

编辑 `output/release-template/scripts/` 下的脚本:
- `start.sh` - 修改启动逻辑
- `stop.sh` - 修改停止逻辑
- `restart.sh` - 修改重启逻辑
- `check_mode.sh` - 修改状态查询

### 修改 Nginx 配置

编辑 `output/release-template/nginx.conf`:
- 修改端口
- 修改路径
- 修改代理规则
- 修改缓存策略

### 添加文档

将文档放到 `output/release-template/docs/`:
- NGINX_DEPLOYMENT.md
- TROUBLESHOOTING.md
- FAQ.md

## ⚠️ 注意事项

### 1. 文件权限
确保脚本有执行权限：
```bash
chmod +x output/release-template/install.sh
chmod +x output/release-template/scripts/*.sh
```

### 2. 路径替换
`install.sh` 中会自动替换项目路径：
```bash
# 模板中使用占位符
/opt/niar

# 安装时会替换为实际路径
/root/xxx/niar-1.0
```

### 3. Python 版本
本地依赖包基于 Python 3.10 编译：
- 用户系统需要 Python 3.10+
- 其他版本可能需要在线安装

### 4. Bettercap 要求
需要预先安装 Bettercap：
- 安装路径：`/usr/local/bin/bettercap`
- 打包不包含 Bettercap 二进制

## 🚀 用户使用流程

```bash
# 1. 解压
tar -xzf niar-1.0.tar.gz
cd niar-1.0

# 2. 安装（一次性）
sudo ./install.sh

# 3. 启动
cd scripts
sudo ./start.sh

# 4. 停止
sudo ./stop.sh

# 5. 重启
sudo ./restart.sh
```

## 📊 文件大小参考

| 组件 | 大小 | 说明 |
|------|------|------|
| 后端代码 | ~600KB | Python 源代码（含网络管控模块）⭐ |
| 前端dist | ~1.4MB | 构建后的静态文件（含网络管控页面）⭐ |
| Python依赖 | ~83MB | 离线依赖包 |
| Bettercap | ~74MB | 二进制文件 |
| Nmap | ~1.7MB | deb 安装包 |
| 系统依赖 | ~11MB | 23个系统 deb 包 |
| 文档 | ~100KB | Markdown 文档 |
| **总计** | **~61MB** | 压缩后的 tar.gz（包含所有依赖）⭐ |

**注意**: v1.0 版本新增网络管控功能，前后端代码已更新。

## 🔍 验证清单

打包完成后验证：

```bash
# 1. 检查文件完整性
md5sum -c output/niar-1.0.tar.gz.md5

# 2. 解压测试
tar -tzf output/niar-1.0.tar.gz | head -20

# 3. 检查关键文件
tar -tzf output/niar-1.0.tar.gz | grep -E "(install\.sh|nginx\.conf|start\.sh)"

# 4. 检查依赖包
tar -tzf output/niar-1.0.tar.gz | grep "packages/python-site-packages" | wc -l

# 5. 检查文档
tar -tzf output/niar-1.0.tar.gz | grep "\.md$"

# 6. 检查网络管控新文件 ⭐
tar -tzf output/niar-1.0.tar.gz | grep -E "(arp_ban|NetworkControl)" | head -10
# 应该包含:
# - backend/app/models/arp_ban_target.py
# - backend/app/models/arp_ban_log.py
# - backend/app/services/arp_ban_service.py
# - backend/app/api/arp_ban.py
# - backend/app/utils/network.py
# - 以及前端相关文件

# 7. 检查打包大小
ls -lh output/niar-1.0.tar.gz
# 应该约为 61MB
```

### 当前版本验证结果 (v1.0.2 - 2025-10-26)
✅ **打包成功**: output/niar-1.0.2.tar.gz  
✅ **文件大小**: 61MB  
✅ **MD5校验**: 5a3da7c8ab1fa8dcee76fc7a37f07395  
✅ **关键修复**: ARP Ban 不再自动停止 ⭐⭐⭐  
✅ **后端修改**: update_targets 方法（移除自动停止逻辑）  
✅ **日志增强**: 启动/停止/更新详细日志  
✅ **前端构建**: 2025-10-26 23:24 (1.4MB dist)  
✅ **前端资源**: 
   - index-CCgR8Y6c.js (1.1MB) - 包含白名单配置界面
   - index-D1V35J2A.css (337KB)  
✅ **文件总数**: 约 4106 个文件  
✅ **测试文档**: test_arp_ban_fix.md, ARP_BAN_FIX_v1.0.2.md

## 🛠️ 故障排查

### 打包失败

**问题**: 打包模板不存在
```
❌ 打包模板目录不存在: output/release-template
```

**解决**: 确保模板目录存在并包含必要文件
```bash
ls -la output/release-template/
```

---

**问题**: 前端未构建
```
⚠️  前端未构建，跳过
```

**解决**: 构建前端
```bash
cd frontend
npm run build
```

---

**问题**: Python 依赖缺失
```
⚠️  本地 Python 包不存在，跳过
```

**解决**: 复制依赖到 packages 目录
```bash
cp -r backend/.venv/lib/python3.10/site-packages packages/python-site-packages
```

### 打包后问题

**问题**: 脚本无执行权限

**解决**: 打包后自动设置，如遇问题手动执行
```bash
chmod +x output/release-template/install.sh
chmod +x output/release-template/scripts/*.sh
```

---

**问题**: MD5 校验失败

**解决**: 文件传输损坏，重新下载

## 📝 版本变更

### 版本号管理规则
- 格式：`主版本.次版本.修订号` (如 1.0.1)
- 主版本：重大功能变更或架构调整
- 次版本：新增功能或较大改进
- 修订号：bug修复或小优化

### 打包新版本流程

**重要提示**: 每次打包前必须更新版本号！

#### 步骤 1: 更新版本号
```bash
# 编辑 build.sh，修改第7行
VERSION="1.0.2"  # 从 1.0.1 改为 1.0.2（示例）
```

#### 步骤 2: 重新编译前端（如有代码修改）
```bash
cd frontend
npm run build
cd ..
```

#### 步骤 3: 执行打包
```bash
chmod +x build.sh
./build.sh
```

#### 步骤 4: 验证打包结果
```bash
# 查看生成的文件
ls -lh output/niar-*.tar.gz

# 验证 MD5
cd output
md5sum -c niar-1.0.2.tar.gz.md5  # 使用对应版本号

# 检查版本文件
cat .version
```

#### 步骤 5: 更新文档
更新 `BUILD_REQUIREMENTS.md` 中的：
- 顶部版本号
- 最新更新章节
- 版本验证结果
- 版本记录

### 快速打包命令（适用于小修改）
```bash
# 一键打包（假设前端已构建）
./build.sh

# 完整打包（包括重新构建前端）
cd frontend && npm run build && cd .. && ./build.sh
```

### 最新版本记录
- **v1.0.2 (2025-10-26)**: ⭐ 当前版本
  - 🐛 修复 ARP Ban 自动停止的严重 Bug
  - 📝 增强日志记录
  - 📦 打包大小: 61MB
  - ⚡ 关键修复：删除目标不再自动停止服务

- **v1.0.1 (2025-10-26)**: 
  - ✨ 白名单用户可配置（网关+自定义设备）
  - 📦 打包大小: 61MB
  - 🎨 界面优化（左右对齐）
  - 🔧 前端资源: index-CCgR8Y6c.js (1.1MB) + index-D1V35J2A.css (337KB)

- **v1.0 (2025-10-26)**: 
  - ✨ 新增网络管控功能 (ARP Ban)
  - 📦 打包大小: 61MB
  - 🔧 包含 10 个新文件

## 🎯 最佳实践

### 1. 打包前检查
- ✅ 前端已构建（包含所有新功能）
- ✅ 前端 TypeScript 编译无错误
- ✅ 依赖已下载到 packages/
- ✅ 模板文件完整
- ✅ 代码已提交（包含网络管控新功能）

### 2. 打包后验证
- ✅ MD5 校验通过
- ✅ 解压测试
- ✅ 安装测试（推荐）
- ✅ 功能测试（推荐测试网络管控功能）
- ✅ 检查新功能文件是否包含

### 3. 发布前准备
- ✅ 更新 CHANGELOG（记录网络管控新特性）
- ✅ 标记 Git 版本
- ✅ 准备发布说明（包含新功能介绍）
- ✅ 通知用户（强调新增网络管控功能）

### 4. 网络管控功能说明
- ✨ **新增功能**: ARP Ban 网络管控
- 📍 **访问路径**: Web界面 -> 网络管控菜单
- 🔑 **核心能力**: 
  - 查看网段内所有可用IP
  - 添加/移除目标设备
  - 启动/停止 ARP Ban
  - 查看操作日志
- ⚠️ **使用要求**: 
  - 需要 root 权限运行
  - 确保 Bettercap 正常运行
  - 确保系统支持 ARP 欺骗

## 📞 联系方式

如有问题，请查阅：
- 项目 README
- 安装文档 (docs/INSTALL.md)
- Nginx 部署指南 (docs/NGINX_DEPLOYMENT.md)

---

**打包愉快！** 🚀

