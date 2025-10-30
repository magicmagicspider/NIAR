# NIAR Nginx 生产环境部署指南

本指南说明如何使用 Nginx 部署 NIAR 到生产环境。

## 📋 部署架构

```
客户端 
   ↓
Nginx (端口 80/443)
   ↓
   ├─→ 前端静态文件 (frontend/dist/)
   └─→ 后端 API (127.0.0.1:8000)
        └─→ Bettercap API (127.0.0.1:8081)
```

## 🎯 优势

使用 Nginx 部署的优势：
- ✅ **性能**: Nginx 高效处理静态文件
- ✅ **负载均衡**: 支持多个后端实例
- ✅ **SSL/TLS**: 方便配置 HTTPS
- ✅ **安全**: 隐藏后端端口，统一入口
- ✅ **缓存**: 静态资源缓存优化
- ✅ **压缩**: 自动 Gzip 压缩
- ✅ **监控**: 完善的日志和监控

## 📦 系统要求

### 必需软件
- Ubuntu 20.04+ / Debian 11+
- Python 3.10+
- Nginx 1.18+
- Nmap 7.80+
- Bettercap 2.32+ (可选)

### 硬件要求
- CPU: 2 核心+
- 内存: 2GB+
- 磁盘: 10GB+

## 🚀 快速部署

### 1. 安装系统依赖

```bash
# 更新包管理器
sudo apt-get update

# 安装必需软件
sudo apt-get install -y python3 python3-venv nmap nginx rsync

# 验证安装
nginx -v
python3 --version
```

### 2. 解压并安装

```bash
# 解压
tar -xzf niar-1.0.tar.gz
cd niar-1.0

# 离线安装 Python 依赖
./install_dependencies.sh
```

### 3. 配置 Nginx（可选）

如需自定义配置，编辑 `nginx.conf`：

```bash
nano nginx.conf

# 主要配置项：
# - server_name: 您的域名
# - root: 前端文件路径（自动设置）
# - upstream backend: 后端地址
```

### 4. 启动服务

```bash
# 使用 Nginx 启动（生产环境推荐）
sudo ./start_with_nginx.sh
```

### 5. 验证部署

```bash
# 检查服务状态
sudo systemctl status nginx

# 检查进程
ps aux | grep -E '(uvicorn|nginx|bettercap)'

# 访问测试
curl http://localhost/health
curl http://localhost/api/health  # 如果后端有健康检查接口
```

## 🔧 详细部署步骤

### 步骤 1: 准备项目目录

```bash
# 推荐部署到 /opt
sudo mkdir -p /opt/niar
sudo tar -xzf niar-1.0.tar.gz -C /opt/
cd /opt/niar-1.0
```

### 步骤 2: 安装依赖

```bash
# 离线安装（无需联网）
./install_dependencies.sh

# 或在线安装（需要联网）
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..
```

### 步骤 3: 配置 Nginx

编辑 `nginx.conf` 自定义配置：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 修改为您的域名
    
    # 前端静态文件路径（启动脚本会自动设置）
    location / {
        root /opt/niar-1.0/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        # ... 其他配置
    }
}
```

### 步骤 4: 启动服务

```bash
# 赋予执行权限
chmod +x start_with_nginx.sh stop_nginx.sh

# 启动
sudo ./start_with_nginx.sh
```

启动脚本会自动：
1. 检查并安装 Nginx 配置
2. 启动后端服务（4 个 worker）
3. 启动 Bettercap（如果已安装）
4. 重启 Nginx
5. 显示访问信息

### 步骤 5: 验证部署

```bash
# 1. 检查 Nginx 状态
sudo systemctl status nginx

# 2. 检查 Nginx 配置
sudo nginx -t

# 3. 检查后端进程
ps aux | grep uvicorn

# 4. 检查端口
sudo netstat -tlnp | grep -E '(80|8000|8081)'

# 5. 访问测试
curl http://localhost/
curl http://localhost/api/
```

## 📊 服务管理

### 启动服务

```bash
sudo ./start_with_nginx.sh
```

### 停止服务

```bash
sudo ./stop_nginx.sh
```

### 重启服务

```bash
# 重启所有服务
sudo ./stop_nginx.sh
sudo ./start_with_nginx.sh

# 仅重启 Nginx
sudo systemctl restart nginx

# 仅重启后端
pkill -f "uvicorn app.main:app"
cd backend
source .venv/bin/activate
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 > ../logs/backend.log 2>&1 &
```

### 查看日志

```bash
# 后端日志
tail -f logs/backend.log

# Nginx 访问日志
sudo tail -f /var/log/nginx/niar_access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/niar_error.log

# Bettercap 日志
tail -f logs/bettercap.log

# 系统日志
sudo journalctl -u nginx -f
```

### 查看服务状态

```bash
# Nginx 状态
sudo systemctl status nginx

# 进程状态
ps aux | grep -E '(uvicorn|nginx|bettercap)'

# 端口占用
sudo netstat -tlnp | grep -E '(80|8000|8081)'
```

## 🔐 HTTPS 配置

### 使用 Let's Encrypt（推荐）

```bash
# 1. 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 2. 获取证书（自动配置 Nginx）
sudo certbot --nginx -d your-domain.com

# 3. 自动续期
sudo certbot renew --dry-run
```

### 手动配置 SSL

1. 准备证书文件：
   - `niar.crt` - 证书文件
   - `niar.key` - 私钥文件

2. 放置证书：
   ```bash
   sudo cp niar.crt /etc/ssl/certs/
   sudo cp niar.key /etc/ssl/private/
   sudo chmod 600 /etc/ssl/private/niar.key
   ```

3. 编辑 `nginx.conf`，取消 HTTPS 部分的注释：
   ```nginx
   server {
       listen 443 ssl http2;
       server_name your-domain.com;
       
       ssl_certificate /etc/ssl/certs/niar.crt;
       ssl_certificate_key /etc/ssl/private/niar.key;
       
       # ... 其他配置
   }
   ```

4. 重启 Nginx：
   ```bash
   sudo nginx -t
   sudo systemctl restart nginx
   ```

## ⚙️ 性能优化

### Nginx 优化

编辑 `/etc/nginx/nginx.conf`：

```nginx
# Worker 进程数（通常等于 CPU 核心数）
worker_processes auto;

# 每个 worker 的连接数
events {
    worker_connections 2048;
}

http {
    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss;
    
    # 缓存配置
    open_file_cache max=1000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
}
```

### 后端优化

修改 `start_with_nginx.sh` 中的 uvicorn 参数：

```bash
# 增加 worker 数量（推荐: CPU 核心数 * 2）
uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 8 \
    --worker-class uvicorn.workers.UvicornWorker
```

### 系统优化

```bash
# 增加文件描述符限制
sudo tee -a /etc/security/limits.conf << EOF
* soft nofile 65535
* hard nofile 65535
EOF

# 优化网络参数
sudo tee -a /etc/sysctl.conf << EOF
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
EOF
sudo sysctl -p
```

## 🔍 故障排查

### Nginx 无法启动

```bash
# 检查配置语法
sudo nginx -t

# 查看错误日志
sudo tail -n 50 /var/log/nginx/error.log

# 检查端口占用
sudo netstat -tlnp | grep :80

# 检查 SELinux（如果启用）
sudo setenforce 0  # 临时禁用
```

### 后端无法访问

```bash
# 检查后端进程
ps aux | grep uvicorn

# 检查后端日志
tail -n 50 logs/backend.log

# 手动启动测试
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 测试后端连接
curl http://127.0.0.1:8000/api/
```

### 前端页面空白

```bash
# 检查前端文件
ls -la frontend/dist/

# 检查 Nginx 日志
sudo tail -f /var/log/nginx/niar_error.log

# 检查文件权限
sudo chmod -R 755 frontend/dist/

# 检查浏览器控制台
# 按 F12 查看错误信息
```

### 502 Bad Gateway

```bash
# 原因 1: 后端未启动
ps aux | grep uvicorn

# 原因 2: 后端端口错误
grep "proxy_pass" /etc/nginx/sites-available/niar
netstat -tlnp | grep 8000

# 原因 3: SELinux 阻止
sudo setenforce 0
```

## 📈 监控和维护

### 日志轮转

创建 `/etc/logrotate.d/niar`：

```
/opt/niar-1.0/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        pkill -USR1 -f "uvicorn app.main:app"
    endscript
}
```

### 自动启动

创建 systemd 服务：

```bash
# 创建后端服务
sudo tee /etc/systemd/system/niar-backend.service << EOF
[Unit]
Description=NIAR Backend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/niar-1.0/backend
ExecStart=/opt/niar-1.0/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable niar-backend
sudo systemctl start niar-backend
```

### 健康检查

创建监控脚本 `health_check.sh`：

```bash
#!/bin/bash
if ! curl -sf http://localhost/health > /dev/null; then
    echo "NIAR 服务异常，尝试重启..."
    sudo systemctl restart niar-backend
    sudo systemctl restart nginx
fi
```

添加到 crontab：
```bash
# 每 5 分钟检查一次
*/5 * * * * /opt/niar-1.0/health_check.sh
```

## 🎯 最佳实践

1. **安全**
   - 使用 HTTPS
   - 定期更新系统
   - 配置防火墙
   - 限制 API 访问

2. **性能**
   - 启用 Gzip 压缩
   - 配置静态资源缓存
   - 使用多个 worker
   - CDN 加速（可选）

3. **可靠性**
   - 配置自动重启
   - 日志轮转
   - 健康检查
   - 定期备份数据库

4. **监控**
   - 日志监控
   - 性能监控
   - 告警通知
   - 访问统计

## 📞 技术支持

### 常见问题

**Q: 如何更改端口？**
```bash
# 修改 nginx.conf
listen 8080;  # 改为其他端口

# 重启 Nginx
sudo systemctl restart nginx
```

**Q: 如何增加后端性能？**
```bash
# 修改 start_with_nginx.sh 中的 worker 数量
--workers 8  # 增加到 8 个 worker
```

**Q: 如何查看实时日志？**
```bash
# 后端日志
tail -f logs/backend.log

# Nginx 日志
sudo tail -f /var/log/nginx/niar_access.log
```

---

**版本**: 1.0  
**更新日期**: 2025-10-26  
**适用系统**: Ubuntu 20.04+ / Debian 11+

