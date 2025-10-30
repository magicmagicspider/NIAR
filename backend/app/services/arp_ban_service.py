import asyncio
import logging
from typing import Optional, List
from datetime import datetime
from sqlmodel import Session
import httpx

from app.models.db import engine
from app.models.arp_ban_target import ArpBanTarget
from app.models.arp_ban_log import ArpBanLog
from app.repositories.arp_ban_target_repo import ArpBanTargetRepository
from app.repositories.arp_ban_log_repo import ArpBanLogRepository
from app.repositories.app_config_repo import AppConfigRepository
from app.services.bettercap_service import BettercapClientManager
import json

logger = logging.getLogger(__name__)


class ArpBanService:
    """ARP Ban 服务管理"""
    
    _running: bool = False
    _task: Optional[asyncio.Task] = None
    _current_targets: List[str] = []
    
    @classmethod
    def is_running(cls) -> bool:
        """获取运行状态"""
        return cls._running
    
    @classmethod
    def get_targets(cls) -> List[str]:
        """获取当前目标列表"""
        return cls._current_targets.copy()
    
    @classmethod
    async def start_arp_ban(cls, gateway_ip: str = None, whitelist_ips: List[str] = None):
        """
        启动 ARP Ban
        
        Args:
            gateway_ip: 用户指定的网关IP，如果为None则自动检测
            whitelist_ips: 用户指定的白名单IP列表
        """
        if cls._running:
            logger.warning("ARP Ban 已在运行中")
            return
        
        try:
            with Session(engine) as session:
                # 获取目标列表
                target_repo = ArpBanTargetRepository(session)
                targets = target_repo.get_all()
                
                if not targets:
                    logger.warning("没有目标设备，无法启动 ARP Ban")
                    raise ValueError("请先添加目标设备")
                
                target_ips = [t.ip for t in targets]
                cls._current_targets = target_ips
                
                # 获取 Bettercap 配置
                config_repo = AppConfigRepository(session)
                config = config_repo.get_by_key("bettercap_config")
                
                if not config:
                    logger.error("Bettercap 配置不存在")
                    raise ValueError("Bettercap 未配置，请先在设置页面配置")
                
                config_dict = json.loads(config.value)
                
                # 日志：准备启动
                logger.info("=" * 60)
                logger.info(f"[ARP Ban] 准备启动")
                logger.info(f"[ARP Ban] 目标设备数: {len(target_ips)}")
                logger.info(f"[ARP Ban] 目标IP列表: {target_ips}")
                # 显示Ban实例URL（端口8082）
                ban_url = config_dict.get('ban_url', config_dict.get('url', 'http://127.0.0.1:8082'))
                logger.info(f"[ARP Ban] Bettercap Ban URL: {ban_url}")
                
                # 使用Ban专用客户端（端口8082）
                logger.info(f"[ARP Ban] 获取Bettercap Ban客户端实例...")
                client = await BettercapClientManager.get_ban_client()
                logger.info(f"[ARP Ban] Ban客户端实例获取成功")
                
                # 构建白名单
                from app.utils.network import get_gateway_ip, get_local_ip_from_socket
                
                # 使用用户指定的网关，如果没有则自动检测
                if not gateway_ip:
                    gateway_ip = get_gateway_ip()
                    logger.info(f"[ARP Ban] 自动检测网关: {gateway_ip}")
                else:
                    logger.info(f"[ARP Ban] 使用用户指定网关: {gateway_ip}")
                
                # 获取本机IP
                local_ip = get_local_ip_from_socket()
                logger.info(f"[ARP Ban] 本机IP: {local_ip}")
                
                # 合并白名单：网关 + 本机 + 用户指定的其他设备
                whitelist_items = [gateway_ip, local_ip]
                if whitelist_ips:
                    whitelist_items.extend(whitelist_ips)
                    logger.info(f"[ARP Ban] 用户指定白名单: {whitelist_ips}")
                
                # 去重
                whitelist_items = list(set(whitelist_items))
                logger.info(f"[ARP Ban] 受保护的设备（仅供参考）: {whitelist_items}")
                logger.info(f"[ARP Ban] 注意：白名单不传递给Bettercap，仅在应用层保护")
                
                # 设置目标（无需whitelist参数）
                targets_str = ','.join(target_ips)
                logger.info(f"[ARP Ban] 执行命令: set arp.spoof.targets {targets_str}")
                await client.execute_command(f"set arp.spoof.targets {targets_str}")
                logger.info(f"[ARP Ban] ✓ 目标设置成功")
                
                # 启动 ARP Ban
                logger.info(f"[ARP Ban] 执行命令: arp.ban on")
                result = await client.execute_command("arp.ban on")
                logger.info(f"[ARP Ban] ✓ ARP Ban 已启动，结果: {result}")
                
                cls._running = True
                logger.info(f"[ARP Ban] ========== 启动成功 ==========")
                logger.info(f"[ARP Ban] 运行状态: True")
                logger.info(f"[ARP Ban] 目标设备数: {len(target_ips)}")
                logger.info(f"[ARP Ban] 白名单设备数: {len(whitelist_items)}")
                logger.info("=" * 60)
                
                # 记录日志
                log_repo = ArpBanLogRepository(session)
                log_repo.create(ArpBanLog(
                    action="start",
                    message=f"启动 ARP Ban，目标: {len(target_ips)} 个设备",
                    operator="admin"
                ))
                
        except httpx.HTTPStatusError as e:
            logger.error("=" * 60)
            logger.error(f"[ARP Ban] HTTP状态错误")
            logger.error(f"[ARP Ban] 状态码: {e.response.status_code}")
            logger.error(f"[ARP Ban] 响应内容: {e.response.text[:500]}")  # 限制长度
            logger.error(f"[ARP Ban] 请求URL: {e.request.url}")
            logger.error("=" * 60)
            raise RuntimeError(f"启动失败: HTTP {e.response.status_code} - {e.response.text[:200]}")
        except httpx.ConnectError as e:
            logger.error("=" * 60)
            logger.error(f"[ARP Ban] 连接错误: 无法连接到Bettercap")
            logger.error(f"[ARP Ban] 错误详情: {e}")
            logger.error("=" * 60)
            raise RuntimeError(f"启动失败: 无法连接到Bettercap - {str(e)}")
        except httpx.TimeoutException as e:
            logger.error("=" * 60)
            logger.error(f"[ARP Ban] 超时错误: Bettercap响应超时")
            logger.error(f"[ARP Ban] 错误详情: {e}")
            logger.error("=" * 60)
            raise RuntimeError(f"启动失败: Bettercap响应超时")
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"[ARP Ban] 未知错误: {type(e).__name__}")
            logger.error(f"[ARP Ban] 错误详情: {e}")
            logger.error("=" * 60)
            raise
    
    @classmethod
    async def stop_arp_ban(cls):
        """停止 ARP Ban"""
        if not cls._running:
            logger.warning("[ARP Ban] 未在运行，无需停止")
            return
        
        try:
            logger.info("=" * 60)
            logger.info("[ARP Ban] 准备停止")
            
            with Session(engine) as session:
                # 使用Ban专用客户端
                logger.info("[ARP Ban] 获取Bettercap Ban客户端实例...")
                client = await BettercapClientManager.get_ban_client()
                logger.info("[ARP Ban] Ban客户端实例获取成功")
                
                # 停止 ARP Ban
                logger.info("[ARP Ban] 执行命令: arp.ban off")
                await client.execute_command("arp.ban off")
                logger.info("[ARP Ban] ✓ ARP Ban 已停止")
                
                # 清除目标配置
                logger.info("[ARP Ban] 执行命令: set arp.spoof.targets \"\"")
                await client.execute_command("set arp.spoof.targets \"\"")
                logger.info("[ARP Ban] ✓ 目标列表已清除")
                
                cls._running = False
                cls._current_targets = []
                logger.info("[ARP Ban] ========== 停止成功 ==========")
                logger.info("[ARP Ban] 运行状态: False")
                logger.info("=" * 60)
                
                # 记录日志
                log_repo = ArpBanLogRepository(session)
                log_repo.create(ArpBanLog(
                    action="stop",
                    message="停止 ARP Ban",
                    operator="admin"
                ))
                
        except httpx.HTTPStatusError as e:
            logger.error("=" * 60)
            logger.error(f"[ARP Ban] 停止失败 - HTTP状态错误")
            logger.error(f"[ARP Ban] 状态码: {e.response.status_code}")
            logger.error(f"[ARP Ban] 响应内容: {e.response.text[:500]}")
            logger.error("=" * 60)
            cls._running = False  # 即使失败也标记为停止
            raise RuntimeError(f"停止失败: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"[ARP Ban] 停止失败: {type(e).__name__}")
            logger.error(f"[ARP Ban] 错误详情: {e}")
            logger.error("=" * 60)
            cls._running = False  # 即使失败也标记为停止
            raise
    
    @classmethod
    async def update_targets(cls, target_ips: List[str]):
        """
        动态更新目标列表（ARP Ban 运行中时）
        
        Args:
            target_ips: 新的目标 IP 列表
        """
        if not cls._running:
            logger.info("ARP Ban 未运行，无需更新目标")
            return
        
        logger.info(f"[ARP Ban] 动态更新目标: 从 {cls._current_targets} 到 {target_ips}")
        
        try:
            # 使用Ban专用客户端
            logger.info("[ARP Ban] 获取Bettercap Ban客户端实例...")
            client = await BettercapClientManager.get_ban_client()
            logger.info("[ARP Ban] Ban客户端实例获取成功")
            
            # 更新目标（无需whitelist参数）
            if target_ips:
                targets_str = ','.join(target_ips)
                logger.info(f"[ARP Ban] 执行命令: set arp.spoof.targets {targets_str}")
                await client.execute_command(f"set arp.spoof.targets {targets_str}")
                logger.info(f"[ARP Ban] ✓ 目标更新成功")
                
                cls._current_targets = target_ips
                logger.info(f"[ARP Ban] 目标已更新: {len(target_ips)} 个设备")
            else:
                # ✅ 目标为空时不自动停止，只清空目标列表
                logger.info(f"[ARP Ban] 执行命令: set arp.spoof.targets \"\"")
                await client.execute_command(f"set arp.spoof.targets \"\"")
                logger.info(f"[ARP Ban] ✓ 目标列表已清空")
                
                cls._current_targets = []
                logger.warning("[ARP Ban] 目标列表已清空，但保持运行状态")
                logger.warning("[ARP Ban] 提示：如需停止，请手动点击'停止 Ban'按钮")
                
        except httpx.HTTPStatusError as e:
            logger.error("=" * 60)
            logger.error(f"[ARP Ban] 更新目标失败 - HTTP状态错误")
            logger.error(f"[ARP Ban] 状态码: {e.response.status_code}")
            logger.error(f"[ARP Ban] 响应内容: {e.response.text[:500]}")
            logger.error("=" * 60)
            raise RuntimeError(f"更新目标失败: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"[ARP Ban] 更新目标失败: {type(e).__name__}")
            logger.error(f"[ARP Ban] 错误详情: {e}")
            logger.error("=" * 60)
            raise

