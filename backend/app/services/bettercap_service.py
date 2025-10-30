import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import hashlib
import json

import httpx

logger = logging.getLogger(__name__)


class BettercapClientManager:
    """Bettercap客户端管理器（双实例模式，分别用于扫描和Ban）"""
    _scan_instance: Optional['BettercapClient'] = None
    _ban_instance: Optional['BettercapClient'] = None
    _config_hash: Optional[str] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_scan_client(cls) -> 'BettercapClient':
        """获取扫描专用客户端实例（端口8081）"""
        async with cls._lock:
            # 从数据库加载配置
            from app.models.db import engine
            from sqlmodel import Session
            from app.repositories.app_config_repo import AppConfigRepository
            
            with Session(engine) as session:
                config_repo = AppConfigRepository(session)
                config = config_repo.get_by_key("bettercap_config")
                
                if not config:
                    raise ValueError("Bettercap配置不存在，请先在设置页面配置")
                
                config_dict = json.loads(config.value)
                
                # 获取扫描实例URL（默认8081）
                scan_url = config_dict.get('scan_url', config_dict.get('url', 'http://127.0.0.1:8081'))
                
                # 计算配置哈希
                config_str = f"{scan_url}:{config_dict['username']}:{config_dict['password']}"
                current_hash = hashlib.md5(config_str.encode()).hexdigest()
                
                # 如果配置变更或实例不存在，创建新实例
                if cls._scan_instance is None or cls._config_hash != current_hash:
                    logger.info("=" * 60)
                    logger.info(f"[Bettercap Manager] 创建扫描客户端实例")
                    logger.info(f"[Bettercap Manager] URL: {scan_url}")
                    logger.info("=" * 60)
                    cls._scan_instance = BettercapClient(
                        scan_url,
                        config_dict['username'],
                        config_dict['password']
                    )
                    cls._config_hash = current_hash
                else:
                    logger.debug(f"[Bettercap Manager] 复用扫描客户端实例")
                
                return cls._scan_instance
    
    @classmethod
    async def get_ban_client(cls) -> 'BettercapClient':
        """获取Ban专用客户端实例（端口8082）"""
        async with cls._lock:
            # 从数据库加载配置
            from app.models.db import engine
            from sqlmodel import Session
            from app.repositories.app_config_repo import AppConfigRepository
            
            with Session(engine) as session:
                config_repo = AppConfigRepository(session)
                config = config_repo.get_by_key("bettercap_config")
                
                if not config:
                    raise ValueError("Bettercap配置不存在，请先在设置页面配置")
                
                config_dict = json.loads(config.value)
                
                # 获取Ban实例URL（默认8082）
                ban_url = config_dict.get('ban_url', 'http://127.0.0.1:8082')
                
                # 如果Ban实例不存在，创建
                if cls._ban_instance is None:
                    logger.info("=" * 60)
                    logger.info(f"[Bettercap Manager] 创建Ban客户端实例")
                    logger.info(f"[Bettercap Manager] URL: {ban_url}")
                    logger.info("=" * 60)
                    cls._ban_instance = BettercapClient(
                        ban_url,
                        config_dict['username'],
                        config_dict['password']
                    )
                else:
                    logger.debug(f"[Bettercap Manager] 复用Ban客户端实例")
                
                return cls._ban_instance
    
    @classmethod
    async def get_client(cls) -> 'BettercapClient':
        """向后兼容：默认返回扫描客户端"""
        return await cls.get_scan_client()
    
    @classmethod
    def invalidate(cls):
        """使客户端实例失效（配置更改时调用）"""
        logger.info("[Bettercap Manager] 客户端实例已失效，下次将重新创建")
        cls._scan_instance = None
        cls._ban_instance = None
        cls._config_hash = None


class BettercapClient:
    """Bettercap REST API 客户端"""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.auth = (username, password)
        self.timeout = httpx.Timeout(10.0, connect=5.0)
    
    async def health_check(self) -> bool:
        """检查Bettercap连接是否正常"""
        try:
            url = f"{self.base_url}/api/session"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, auth=self.auth)
                response.raise_for_status()
                logger.debug(f"[Bettercap] 健康检查通过: {self.base_url}")
                return True
        except httpx.HTTPStatusError as e:
            logger.warning(f"[Bettercap] 健康检查失败 - HTTP {e.response.status_code}: {e.response.text}")
            return False
        except httpx.ConnectError as e:
            logger.warning(f"[Bettercap] 健康检查失败 - 连接错误: {e}")
            return False
        except Exception as e:
            logger.warning(f"[Bettercap] 健康检查失败 - 未知错误: {e}")
            return False
    
    async def execute_command(self, command: str) -> dict:
        """执行 bettercap 命令"""
        url = f"{self.base_url}/api/session"
        payload = {"cmd": command}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=payload,
                auth=self.auth
            )
            response.raise_for_status()
            return response.json()
    
    async def get_lan_hosts(self) -> List[dict]:
        """获取 LAN 主机列表"""
        url = f"{self.base_url}/api/session/lan"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, auth=self.auth)
            response.raise_for_status()
            data = response.json()
            return data.get("hosts", [])
    
    async def get_events(self, limit: int = 50) -> List[dict]:
        """获取最近的事件日志"""
        url = f"{self.base_url}/api/events"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, auth=self.auth, params={"n": limit})
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
    
    async def start_scan(self):
        """启动主动扫描模块"""
        logger.info("Starting bettercap active probe (net.probe)")
        # 只启用主动探测，不启用被动侦察
        await self.execute_command("net.probe on")
    
    async def stop_scan(self):
        """停止主动扫描模块"""
        logger.info("Stopping bettercap active probe (net.probe)")
        try:
            await self.execute_command("net.probe off")
        except Exception as e:
            logger.warning(f"Failed to stop net.probe: {e}")
    
    async def clear_hosts(self):
        """清空主机列表"""
        logger.info("Clearing bettercap host cache")
        try:
            await self.execute_command("net.clear")
        except Exception as e:
            logger.warning(f"Failed to clear hosts: {e}")


def convert_bettercap_host_to_device_info(host: dict) -> Dict[str, Optional[str]]:
    """
    将 bettercap Endpoint 转换为 niar Device 格式
    
    bettercap Endpoint 格式：
    {
        "ipv4": "192.168.1.1",
        "ipv6": "",
        "mac": "aa:bb:cc:dd:ee:ff",
        "hostname": "router.local",
        "vendor": "Vendor Name",
        "first_seen": "2024-01-01T12:00:00Z",
        "last_seen": "2024-01-01T12:30:00Z",
        "meta": {...}
    }
    
    niar Device 格式：
    {
        "mac": "AA:BB:CC:DD:EE:FF",
        "hostname": "router.local",
        "vendor": "Vendor Name",
        "os": None
    }
    """
    return {
        "mac": host.get("mac", "").upper() if host.get("mac") else None,
        "hostname": host.get("hostname") or None,
        "vendor": host.get("vendor") or None,
        "os": None  # bettercap 不提供 OS 检测
    }


async def scan_bettercap(
    target_cidrs: List[str],
    bettercap_url: str,
    username: str,
    password: str,
    scan_duration: int = 60,
    progress_callback=None
) -> Dict[str, Dict[str, Optional[str]]]:
    """
    使用 bettercap 扫描网络
    
    Args:
        target_cidrs: 目标 CIDR 列表（用于过滤结果）
        bettercap_url: bettercap REST API 地址（已废弃，从配置读取）
        username: 认证用户名（已废弃，从配置读取）
        password: 认证密码（已废弃，从配置读取）
        scan_duration: 扫描持续时间（秒）
        progress_callback: 进度回调函数 callback(progress: int, message: str)
        
    Returns:
        解析结果字典 {ip: {mac, hostname, vendor, os}}
    """
    from app.utils.cidr import expand_cidrs
    
    # 展开 CIDR 得到目标 IP 集合
    target_ips = set(expand_cidrs(target_cidrs)) if target_cidrs else set()
    
    # 使用单例管理器获取客户端
    logger.info("[Bettercap Scan] 获取Bettercap客户端实例")
    client = await BettercapClientManager.get_client()
    
    try:
        # 1. 清空之前的主机缓存
        if progress_callback:
            progress_callback(5, "清空 bettercap 主机缓存...")
        await client.clear_hosts()
        
        # 2. 启动扫描
        if progress_callback:
            progress_callback(10, "启动 bettercap 扫描模块...")
        await client.start_scan()
        
        # 3. 等待扫描完成，期间定期获取主机列表
        logger.info(f"Scanning for {scan_duration} seconds...")
        
        poll_interval = 2  # 每2秒轮询一次
        total_polls = scan_duration // poll_interval
        discovered_hosts = {}
        
        for i in range(total_polls):
            await asyncio.sleep(poll_interval)
            
            # 获取当前发现的主机
            hosts = await client.get_lan_hosts()
            
            # 更新发现的主机
            for host in hosts:
                ip = host.get("ipv4")
                if not ip:
                    continue
                
                # 如果指定了目标 CIDR，则只保留目标范围内的 IP
                if target_ips and ip not in target_ips:
                    continue
                
                discovered_hosts[ip] = host
            
            # 更新进度
            progress = 10 + int((i + 1) / total_polls * 60)  # 10-70%
            if progress_callback:
                progress_callback(
                    progress,
                    f"扫描中... 已发现 {len(discovered_hosts)} 台主机"
                )
            
            logger.info(f"Poll {i+1}/{total_polls}: Found {len(discovered_hosts)} hosts")
        
        # 4. 停止扫描
        if progress_callback:
            progress_callback(75, "停止 bettercap 扫描模块...")
        await client.stop_scan()
        
        # 5. 转换为 niar 格式
        if progress_callback:
            progress_callback(80, "转换扫描结果...")
        
        results = {}
        for ip, host in discovered_hosts.items():
            results[ip] = convert_bettercap_host_to_device_info(host)
        
        logger.info(f"Scan completed: {len(results)} hosts found")
        return results
        
    except httpx.HTTPError as e:
        logger.error(f"Bettercap HTTP error: {e}")
        raise RuntimeError(f"连接 bettercap API 失败: {str(e)}")
    except Exception as e:
        logger.error(f"Bettercap scan error: {e}", exc_info=True)
        # 确保停止扫描
        try:
            await client.stop_scan()
        except:
            pass
        raise RuntimeError(f"Bettercap 扫描失败: {str(e)}")


