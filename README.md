# NIAR - 网络设备监控系统

版本: 1.0（开发版）
<img width="1545" height="870" alt="image" src="https://github.com/user-attachments/assets/34f01ec9-f0fc-4865-bc4e-5b7c49ef2653" />
<img width="1545" height="870" alt="image" src="https://github.com/user-attachments/assets/e427824f-2d36-4481-8721-b93b8671fe5f" />
<img width="1545" height="870" alt="image" src="https://github.com/user-attachments/assets/7c1d063a-006f-416a-8200-3200de5bb85c" />
<img width="1545" height="870" alt="image" src="https://github.com/user-attachments/assets/cdf77f10-5c56-4089-9dee-3a0e40aab7f5" />
<img width="1545" height="870" alt="image" src="https://github.com/user-attachments/assets/dd1c2543-edbf-4d48-bfa6-a89e92676773" />

## 📋 项目说明

这是 NIAR 网络设备监控系统的开发目录。

## 🗂️ 目录结构

```
niar/
├── backend/                 后端源代码
├── frontend/                前端源代码
├── packages/                本地依赖包
├── output/                  打包输出目录
│   └── release-template/   打包模板
├── logs/                    运行日志目录
├── start.sh                 启动开发环境 ⭐
├── stop.sh                  停止开发环境 ⭐
├── restart.sh               重启开发环境 ⭐
├── check.sh                 检查服务状态 ⭐
├── build.sh                 打包脚本
├── BUILD_REQUIREMENTS.md    打包要求文档
├── FINAL_VERSION.md         版本说明文档
└── README.md                本文件
```

## 🚀 快速开始

### 开发环境（推荐方式 ⭐）

使用项目提供的启停脚本，一键启动所有服务：

```bash
# 启动所有服务（包括 Bettercap）
./start.sh

# 不启动 Bettercap
./start.sh --no-bettercap

# 停止所有服务
./stop.sh

# 重启所有服务
./restart.sh

# 检查服务状态
./check.sh
```

服务访问地址：
- 前端开发服务器: http://localhost:5173
- 后端 API: http://127.0.0.1:8000
- API 文档: http://127.0.0.1:8000/docs
- Bettercap API: http://127.0.0.1:8081

### 手动启动（单独调试）

1. **后端开发**
   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn app.main:app --reload --port 8000
   ```

2. **前端开发**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Bettercap (可选)**
   ```bash
   sudo bettercap \
       -eval "set api.rest.address 127.0.0.1" \
       -eval "set api.rest.port 8081" \
       -eval "set api.rest.username user" \
       -eval "set api.rest.password pass" \
       -eval "api.rest on"
   ```

### 打包发布

1. **准备前端构建**
   ```bash
   cd frontend
   npm run build
   ```

2. **执行打包**
   ```bash
   ./build.sh
   ```

3. **输出文件**
   ```
   output/niar-1.0.tar.gz      # 发布包
   output/niar-1.0.tar.gz.md5  # 校验文件
   ```

## 📦 打包说明

### 打包模板

所有打包相关文件在 `output/release-template/`:
- `install.sh` - 安装脚本
- `nginx.conf` - Nginx 配置
- `scripts/` - 启停脚本
- `docs/` - 文档

### 修改打包内容

1. 修改模板文件:
   ```bash
   vim output/release-template/install.sh
   ```

2. 重新打包:
   ```bash
   ./build.sh
   ```

### 详细打包要求

请阅读 `BUILD_REQUIREMENTS.md` 了解完整的打包流程和要求。

## 📚 文档

- `BUILD_REQUIREMENTS.md` - 打包要求和流程
- `PROJECT_RESTRUCTURE_COMPLETE.md` - 项目重组说明
- `output/release-template/docs/NGINX_DEPLOYMENT.md` - Nginx 部署指南

## 🔧 维护

### 修改安装脚本
```bash
vim output/release-template/install.sh
```

### 修改启停脚本
```bash
vim output/release-template/scripts/start.sh
```

### 修改 Nginx 配置
```bash
vim output/release-template/nginx.conf
```

## ⚠️ 注意事项

1. **开发目录**: 只包含源代码，不包含安装和启停脚本
2. **打包模板**: 所有打包文件在 `output/release-template/`
3. **打包输出**: 发布包在 `output/niar-1.0.tar.gz`

## 🎯 工作流程

```
开发 → 构建前端 → 打包 → 发布
  ↓        ↓         ↓       ↓
编码   npm build  build.sh  发送给用户
```

## 📞 获取帮助

- 打包问题: 查看 `BUILD_REQUIREMENTS.md`
- 项目结构: 查看 `PROJECT_RESTRUCTURE_COMPLETE.md`
- 部署问题: 查看 `output/release-template/docs/NGINX_DEPLOYMENT.md`

---

**开发愉快！** 🚀

