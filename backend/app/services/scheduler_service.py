import asyncio
import json
import logging
import fcntl
import os
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter
from sqlmodel import Session

from app.models.db import engine
from app.models.scheduled_task import ScheduledTask
from app.models.task_execution import TaskExecution
from app.repositories.scheduled_task_repo import ScheduledTaskRepository
from app.repositories.task_execution_repo import TaskExecutionRepository
from app.repositories.app_config_repo import AppConfigRepository
from app.services.scan_service import scan_nmap, upsert_devices_with_info
from app.services.bettercap_service import BettercapClientManager
from app.repositories.system_event_log_repo import SystemEventLogRepository

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler: Optional[BackgroundScheduler] = None
_running_tasks = set()  # 正在运行的任务ID，防止并发执行
_scheduler_lock_file = None  # 调度器文件锁
_bettercap_continuous_tasks = {}  # 存储持续运行的 Bettercap 任务
_bettercap_task_logs = {}  # 存储 Bettercap 任务的原始日志（task_id -> list of log lines）
_bettercap_task_friendly_logs = {}  # 存储 Bettercap 任务的友好日志，用于历史记录（task_id -> list of log lines）


def _log_system_event(event_type: str, message: str, details: str = None, severity: str = "info"):
    """记录系统事件日志到数据库"""
    try:
        with Session(engine) as session:
            repo = SystemEventLogRepository(session)
            repo.create(
                event_type=event_type,
                message=message,
                details=details,
                severity=severity
            )
            logger.info(f"System event logged: {event_type} - {message}")
    except Exception as e:
        logger.error(f"Failed to log system event: {e}")


def _cleanup_old_system_logs():
    """清理30天前的系统事件日志"""
    try:
        with Session(engine) as session:
            repo = SystemEventLogRepository(session)
            deleted_count = repo.cleanup_old_logs(days=30)
            logger.info(f"[System Log Cleanup] Deleted {deleted_count} old system logs")
            
            # 记录清理操作本身
            if deleted_count > 0:
                repo.create(
                    event_type="system_log_cleanup",
                    message=f"自动清理了{deleted_count}条30天前的系统日志",
                    details=json.dumps({"deleted_count": deleted_count}),
                    severity="info"
                )
    except Exception as e:
        logger.error(f"[System Log Cleanup] Failed to cleanup old logs: {e}")


def validate_cron_expression(cron_expr: str) -> bool:
    """验证cron表达式是否有效"""
    try:
        croniter(cron_expr)
        return True
    except Exception:
        return False


def _add_bettercap_log(task_id: int, message: str, friendly_message: str = None, max_lines: int = 1000, add_timestamp: bool = True):
    """
    添加 Bettercap 任务日志
    
    Args:
        task_id: 任务ID
        message: 原始日志消息
        friendly_message: 友好格式的日志消息（用于历史记录），如果为None则使用message
        max_lines: 最大日志行数
        add_timestamp: 是否添加时间戳
    """
    if task_id not in _bettercap_task_logs:
        _bettercap_task_logs[task_id] = []
    if task_id not in _bettercap_task_friendly_logs:
        _bettercap_task_friendly_logs[task_id] = []
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 原始日志：根据参数决定是否添加时间戳
    if add_timestamp:
        raw_log_line = f"[{timestamp}] {message}"
    else:
        raw_log_line = message
    
    _bettercap_task_logs[task_id].append(raw_log_line)
    
    # 友好日志：始终添加时间戳
    friendly_log_line = f"[{timestamp}] {friendly_message if friendly_message else message}"
    _bettercap_task_friendly_logs[task_id].append(friendly_log_line)
    
    # 保持日志数量在限制内
    if len(_bettercap_task_logs[task_id]) > max_lines:
        _bettercap_task_logs[task_id] = _bettercap_task_logs[task_id][-max_lines:]
    if len(_bettercap_task_friendly_logs[task_id]) > max_lines:
        _bettercap_task_friendly_logs[task_id] = _bettercap_task_friendly_logs[task_id][-max_lines:]


async def start_bettercap_continuous_monitoring(task_id: int, cidrs: list):
    """启动 Bettercap 持续监控（net.recon/net.probe 持续开启），支持自动重启"""
    logger.info(f"Starting Bettercap continuous monitoring for task {task_id}")
    target_cidr = cidrs[0] if cidrs and len(cidrs) > 0 else "本地网络"
    _add_bettercap_log(
        task_id, 
        f"[启动] Bettercap 持续监控，目标网段: {target_cidr}",
        friendly_message=f"🚀 启动 Bettercap 持续监控，目标网段: {target_cidr}",
        add_timestamp=True
    )
    
    # 加载配置
    try:
        with Session(engine) as session:
            config_repo = AppConfigRepository(session)
            config = config_repo.get_by_key("bettercap_config")
            if not config:
                # 配置不存在时记录错误并返回
                error_msg = "Bettercap 配置不存在，请先在设置页面配置"
                logger.error(f"Task {task_id}: {error_msg}")
                _add_bettercap_log(
                    task_id,
                    f"[错误] {error_msg}",
                    friendly_message=f"❌ {error_msg}",
                    add_timestamp=True
                )
                return
            
            config_dict = json.loads(config.value)
            # 显示扫描实例URL（端口8081）
            scan_url = config_dict.get('scan_url', config_dict.get('url', 'http://127.0.0.1:8081'))
            _add_bettercap_log(
                task_id, 
                f"[配置] 已加载 Bettercap 扫描配置: {scan_url}",
                friendly_message=f"⚙️ 已加载 Bettercap 扫描配置: {scan_url}",
                add_timestamp=True
            )
    except Exception as e:
        error_msg = f"加载 Bettercap 配置失败: {e}"
        logger.error(f"Task {task_id}: {error_msg}")
        _add_bettercap_log(
            task_id, 
            f"[错误] {error_msg}",
            friendly_message=f"❌ 错误: {error_msg}",
            add_timestamp=True
        )
        return
    
    retry_count = 0
    max_retries = 10  # 最大重试次数
    retry_delay = 10  # 重试延迟（秒）
    
    # 自动重启循环
    while task_id in _bettercap_continuous_tasks and retry_count < max_retries:
        try:
            # 使用单例管理器获取客户端
            _add_bettercap_log(
                task_id,
                f"[客户端] 获取Bettercap客户端实例...",
                friendly_message="⚙️ 获取Bettercap客户端实例...",
                add_timestamp=True
            )
            client = await BettercapClientManager.get_client()
            _add_bettercap_log(
                task_id,
                f"[客户端] 客户端实例获取成功",
                friendly_message="✓ 客户端实例获取成功",
                add_timestamp=True
            )
        except Exception as e:
            error_msg = f"获取Bettercap客户端失败: {e}"
            logger.error(f"Task {task_id}: {error_msg}")
            _add_bettercap_log(
                task_id,
                f"[错误] {error_msg}",
                friendly_message=f"❌ 错误: {error_msg}",
                add_timestamp=True
            )
            retry_count += 1
            if retry_count < max_retries:
                await asyncio.sleep(retry_delay)
                continue
            else:
                break
        
        try:
            # 启动 net.recon 和 net.probe
            if retry_count > 0:
                _add_bettercap_log(
                    task_id, 
                    f"[重试] 第 {retry_count} 次重启尝试...",
                    friendly_message=f"🔄 第 {retry_count} 次重启尝试...",
                    add_timestamp=True
                )
                # 记录系统事件日志
                _log_system_event(
                    event_type="bettercap_restart",
                    message=f"Bettercap扫描实例自动重启（任务ID: {task_id}, 第{retry_count}次重试）",
                    details=json.dumps({"task_id": task_id, "retry_count": retry_count, "target_cidr": target_cidr}),
                    severity="warning"
                )
            
            # 清空之前的主机缓存
            result = await client.execute_command("net.clear")
            
            # 配置扫描目标网段（如果指定了 CIDR）
            if cidrs and len(cidrs) > 0:
                # Bettercap 使用单个网段
                target = cidrs[0]
                result = await client.execute_command(f"set net.recon.targets {target}")
                _add_bettercap_log(
                    task_id, 
                    f"[配置] 设置扫描目标: {target}",
                    friendly_message=f"🎯 设置扫描目标: {target}",
                    add_timestamp=True
                )
                logger.info(f"Task {task_id}: Set bettercap targets to {target}")
            
            # 获取探测模式配置
            probe_mode = config_dict.get('probe_mode', 'active')
            probe_throttle = config_dict.get('probe_throttle', 5)
            
            # 根据探测模式配置和启动模块
            if probe_mode == 'active':
                # 主动探测模式：先启动net.recon，再启动net.probe
                await client.execute_command(f"set net.probe.throttle {probe_throttle}")
                await client.execute_command("set net.probe.mdns true")
                await client.execute_command("set net.probe.timeout 3")
                
                _add_bettercap_log(
                    task_id, 
                    f"[配置] 主动探测模式: 间隔{probe_throttle}秒, 超时3秒, mDNS启用",
                    friendly_message=f"⚡ 主动探测模式: 间隔{probe_throttle}秒（快速检测设备上下线）",
                    add_timestamp=True
                )
                
                # 先启动net.recon（被动侦察）
                await client.execute_command("net.recon on")
                logger.info(f"Task {task_id}: Bettercap net.recon started")
                
                # 再启动net.probe（主动探测）
                await client.execute_command("net.probe on")
                logger.info(f"Task {task_id}: Bettercap net.probe started (active mode)")
                
                # 记录到系统事件日志
                _log_system_event(
                    event_type="bettercap_modules_started",
                    message=f"Bettercap扫描模块已启动（任务ID: {task_id}）",
                    details=json.dumps({
                        "task_id": task_id,
                        "mode": "active",
                        "modules": ["net.recon", "net.probe"],
                        "target_cidr": target_cidr,
                        "probe_throttle": probe_throttle
                    }),
                    severity="info"
                )
                
            else:  # passive
                # 被动侦察模式
                _add_bettercap_log(
                    task_id, 
                    "[配置] 被动侦察模式: 监听网络流量",
                    friendly_message="👁️ 被动侦察模式: 完全隐蔽，通过流量发现设备",
                    add_timestamp=True
                )
                
                await client.execute_command("net.recon on")
                logger.info(f"Task {task_id}: Bettercap passive recon started")
                
                # 记录到系统事件日志
                _log_system_event(
                    event_type="bettercap_modules_started",
                    message=f"Bettercap扫描模块已启动（任务ID: {task_id}）",
                    details=json.dumps({
                        "task_id": task_id,
                        "mode": "passive",
                        "modules": ["net.recon"],
                        "target_cidr": target_cidr
                    }),
                    severity="info"
                )
            
            _add_bettercap_log(
                task_id, 
                f"[启动完成] Bettercap {probe_mode} 模式已启动",
                friendly_message=f"✓ Bettercap 已启动，开始持续监控（{probe_mode} 模式）",
                add_timestamp=True
            )
            
            # 重置重试计数（启动成功）
            retry_count = 0
            last_event_time = datetime.now()
            
            # 持续拉取并显示 Bettercap 原始事件日志
            last_event_id = None
            poll_interval = 2  # 每2秒拉取一次事件
            
            while task_id in _bettercap_continuous_tasks:
                try:
                    # 获取最新的 Bettercap 事件
                    try:
                        events = await client.get_events(limit=100)
                        if events:
                            # 过滤出新事件（避免重复显示）
                            new_events = []
                            for event in reversed(events):  # 从旧到新排序
                                event_id = event.get('id')
                                if last_event_id is None or (event_id and event_id > last_event_id):
                                    new_events.append(event)
                                    if event_id:
                                        last_event_id = max(last_event_id or 0, event_id)
                            
                            # 显示所有新事件（原始格式）
                            for event in new_events:
                                # 获取事件信息
                                tag = event.get('tag', '')
                                time_str = event.get('time', '')
                                
                                # 格式化时间（只显示时:分:秒）
                                if 'T' in time_str:
                                    time_display = time_str.split('T')[1].split('.')[0] if 'T' in time_str else time_str
                                else:
                                    time_display = time_str
                                
                                # 获取事件数据
                                data = event.get('data', {})
                                
                                # 根据事件类型格式化输出（模拟 bettercap 原始输出）
                                if tag == 'endpoint.new':
                                    endpoint = data.get('endpoint', {})
                                    ip = endpoint.get('ipv4', '')
                                    mac = endpoint.get('mac', '')
                                    hostname = endpoint.get('hostname', '')
                                    vendor = endpoint.get('vendor', '')
                                    
                                    # 构建类似 bettercap 原始输出的格式
                                    raw_output = f"[{time_display}] [sys.log] [inf] endpoint.new {ip}"
                                    if mac:
                                        raw_output += f" {mac}"
                                    if hostname:
                                        raw_output += f" {hostname}"
                                    if vendor:
                                        raw_output += f" ({vendor})"
                                    
                                    # 构建友好格式
                                    device_name = hostname or vendor or mac[:17] if mac else ip
                                    friendly_output = f"🟢 设备上线: {ip} ({device_name})"
                                    
                                    _add_bettercap_log(task_id, raw_output, friendly_message=friendly_output, add_timestamp=False)
                                    
                                    # 立即在数据库中更新该设备为在线
                                    if ip and (mac or hostname):
                                        try:
                                            with Session(engine) as db_session:
                                                from app.repositories.device_repo import DeviceRepository
                                                from app.models.device import Device
                                                device_repo = DeviceRepository(db_session)
                                                device = device_repo.get_by_ip(ip)
                                                if device:
                                                    # 更新现有设备
                                                    device.lastSeenAt = datetime.now()
                                                    device.bettercap_last_seen = datetime.now()
                                                    device.bettercap_offline_at = None
                                                    device.offline_at = None
                                                    if mac:
                                                        device.mac = mac
                                                    if hostname:
                                                        device.hostname = hostname
                                                    if vendor:
                                                        device.vendor = vendor
                                                    device_repo.update(device)
                                                else:
                                                    # 创建新设备
                                                    now = datetime.now()
                                                    device = Device(
                                                        ip=ip,
                                                        mac=mac,
                                                        hostname=hostname,
                                                        vendor=vendor,
                                                        firstSeenAt=now,
                                                        lastSeenAt=now,
                                                        bettercap_last_seen=now
                                                    )
                                                    device_repo.create(device)
                                                logger.info(f"Task {task_id}: Updated/created device {ip} as online immediately")
                                        except Exception as e:
                                            logger.error(f"Task {task_id}: Failed to update device {ip} online: {e}")
                                    
                                elif tag == 'endpoint.lost':
                                    endpoint = data.get('endpoint', {})
                                    ip = endpoint.get('ipv4', '')
                                    mac = endpoint.get('mac', '')
                                    hostname = endpoint.get('hostname', '')
                                    vendor = endpoint.get('vendor', '')
                                    
                                    raw_output = f"[{time_display}] [sys.log] [inf] endpoint.lost {ip}"
                                    if mac:
                                        raw_output += f" {mac}"
                                    
                                    # 构建友好格式
                                    device_name = hostname or vendor or mac[:17] if mac else ip
                                    friendly_output = f"🔴 设备离线: {ip} ({device_name})"
                                    
                                    _add_bettercap_log(task_id, raw_output, friendly_message=friendly_output, add_timestamp=False)
                                    
                                    # 立即在数据库中标记该设备为离线
                                    if ip:
                                        try:
                                            with Session(engine) as db_session:
                                                from app.repositories.device_repo import DeviceRepository
                                                device_repo = DeviceRepository(db_session)
                                                device = device_repo.get_by_ip(ip)
                                                if device:
                                                    device.bettercap_offline_at = datetime.now()
                                                    device.offline_at = datetime.now()  # 兼容旧字段
                                                    device_repo.update(device)
                                                    logger.info(f"Task {task_id}: Marked device {ip} as offline immediately")
                                        except Exception as e:
                                            logger.error(f"Task {task_id}: Failed to mark device {ip} offline: {e}")
                                    
                                elif tag.startswith('wifi.') or tag.startswith('ble.') or tag.startswith('hid.'):
                                    # 无线相关事件
                                    raw_output = f"[{time_display}] [sys.log] [inf] {tag} {json.dumps(data)}"
                                    friendly_output = f"📡 {tag}"
                                    _add_bettercap_log(task_id, raw_output, friendly_message=friendly_output, add_timestamp=False)
                                    
                                elif tag == 'sys.log':
                                    # 系统日志
                                    message = data.get('Message', '')
                                    level = data.get('Level', 'inf')
                                    raw_output = f"[{time_display}] [sys.log] [{level}] {message}"
                                    friendly_output = f"ℹ️ {message}"
                                    _add_bettercap_log(task_id, raw_output, friendly_message=friendly_output, add_timestamp=False)
                                    
                                else:
                                    # 其他事件，显示原始 JSON
                                    raw_output = f"[{time_display}] [{tag}] {json.dumps(data)}"
                                    friendly_output = f"📋 {tag}"
                                    _add_bettercap_log(task_id, raw_output, friendly_message=friendly_output, add_timestamp=False)
                                    
                    except Exception as e:
                        logger.debug(f"Task {task_id}: Failed to get events: {e}")
                    
                    # 每60秒更新一次主机列表到数据库
                    if (datetime.now() - last_event_time).total_seconds() > 60:
                        # 获取主机列表
                        hosts_list = await client.get_lan_hosts()
                        logger.debug(f"Task {task_id}: Bettercap found {len(hosts_list)} hosts")
                        
                        # 转换为字典格式
                        from app.services.bettercap_service import convert_bettercap_host_to_device_info
                        hosts_dict = {}
                        for host in hosts_list:
                            ip = host.get("ipv4")
                            if ip:
                                hosts_dict[ip] = convert_bettercap_host_to_device_info(host)
                        
                        # 更新设备记录
                        with Session(engine) as session:
                            updated, new_count, offline_count = upsert_devices_with_info(
                                session, 
                                hosts_dict,
                                mark_offline=True,
                                target_cidrs=cidrs,
                                scan_tool="bettercap"  # Bettercap 扫描
                            )
                            logger.info(f"Task {task_id}: Updated {updated} devices, {new_count} new, {offline_count} offline")
                            _add_bettercap_log(
                                task_id, 
                                f"[DB更新] 发现 {len(hosts_dict)} 台主机，更新 {updated} 条记录（新增 {new_count}，离线 {offline_count}）",
                                friendly_message=f"✓ 发现 {len(hosts_dict)} 台主机，更新 {updated} 条记录（新增 {new_count}，离线 {offline_count}）",
                                add_timestamp=True
                            )
                        last_event_time = datetime.now()
                    
                    await asyncio.sleep(poll_interval)  # 按事件轮询间隔休眠
                    
                except asyncio.CancelledError:
                    logger.info(f"Task {task_id}: Bettercap monitoring cancelled")
                    _add_bettercap_log(
                        task_id, 
                        "[停止] 监控已停止",
                        friendly_message="✓ 监控已停止",
                        add_timestamp=True
                    )
                    raise  # 重新抛出以退出外层循环
                except Exception as e:
                    logger.error(f"Task {task_id}: Bettercap monitoring error: {e}")
                    _add_bettercap_log(
                        task_id, 
                        f"[警告] 监控循环错误: {e}",
                        friendly_message=f"⚠ 监控循环错误: {e}",
                        add_timestamp=True
                    )
                    # 小错误继续运行
                    await asyncio.sleep(60)
                    
        except asyncio.CancelledError:
            # 任务被取消，正常退出
            break
        except Exception as e:
            error_msg = f"Bettercap 监控异常: {e}"
            logger.error(f"Task {task_id}: {error_msg}")
            _add_bettercap_log(
                task_id, 
                f"[错误] {error_msg}",
                friendly_message=f"❌ 错误: {error_msg}",
                add_timestamp=True
            )
            
            retry_count += 1
            if retry_count < max_retries and task_id in _bettercap_continuous_tasks:
                _add_bettercap_log(
                    task_id, 
                    f"[重试] {retry_delay} 秒后自动重启...",
                    friendly_message=f"⏳ {retry_delay} 秒后自动重启...",
                    add_timestamp=True
                )
                await asyncio.sleep(retry_delay)
            else:
                _add_bettercap_log(
                    task_id, 
                    f"[错误] 已达到最大重试次数 ({max_retries})，停止监控",
                    friendly_message=f"❌ 已达到最大重试次数 ({max_retries})，停止监控",
                    add_timestamp=True
                )
                break
        finally:
            # 停止 Bettercap 模块（安全停止所有可能启动的模块）
            try:
                # 尝试停止主动探测
                try:
                    await client.execute_command("net.probe off")
                    logger.debug(f"Task {task_id}: net.probe stopped")
                except Exception:
                    pass
                
                # 尝试停止被动侦察
                try:
                    await client.execute_command("net.recon off")
                    logger.debug(f"Task {task_id}: net.recon stopped")
                except Exception:
                    pass
                
                logger.info(f"Task {task_id}: Bettercap modules stopped")
                _add_bettercap_log(
                    task_id, 
                    "[停止] Bettercap 模块已停止",
                    friendly_message="✓ Bettercap 已停止",
                    add_timestamp=True
                )
            except Exception as e:
                logger.error(f"Task {task_id}: Failed to stop Bettercap modules: {e}")
                _add_bettercap_log(
                    task_id, 
                    f"[警告] 停止模块时出错: {e}",
                    friendly_message=f"⚠ 停止模块时出错: {e}",
                    add_timestamp=True
                )


def stop_bettercap_continuous_monitoring(task_id: int):
    """停止 Bettercap 持续监控"""
    if task_id in _bettercap_continuous_tasks:
        task = _bettercap_continuous_tasks[task_id]
        task.cancel()
        del _bettercap_continuous_tasks[task_id]
        logger.info(f"Stopped Bettercap continuous monitoring for task {task_id}")


def get_bettercap_task_logs(task_id: int, log_type: str = "raw") -> list:
    """
    获取 Bettercap 任务的日志
    
    Args:
        task_id: 任务ID
        log_type: 日志类型，"raw" 为原始日志（实时查看），"friendly" 为友好日志（历史记录）
    
    Returns:
        日志列表
    """
    if log_type == "friendly":
        return _bettercap_task_friendly_logs.get(task_id, [])
    else:
        return _bettercap_task_logs.get(task_id, [])


async def execute_scheduled_task(task_id: int):
    """执行定时扫描任务"""
    logger.info("=" * 60)
    logger.info(f"TASK EXECUTION TRIGGERED: Task ID {task_id}")
    logger.info(f"Time: {datetime.now().isoformat()}")
    
    # 防止同一任务并发执行
    if task_id in _running_tasks:
        logger.warning(f"Task {task_id} is already running, skipping")
        logger.info("=" * 60)
        return
    
    _running_tasks.add(task_id)
    logger.info(f"Added task {task_id} to running tasks. Current running: {_running_tasks}")
    
    try:
        # 每次执行时创建新的Session，避免线程冲突
        session = Session(engine, expire_on_commit=False)
        try:
            # 获取任务信息
            task_repo = ScheduledTaskRepository(session)
            task = task_repo.get_by_id(task_id)
            
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return
            
            if not task.enabled:
                logger.warning(f"Task {task_id} is disabled, skipping execution")
                return
            
            # 如果是 Bettercap 任务，不在这里执行（由持续监控处理）
            if task.scan_tool == "bettercap":
                logger.info(f"Task {task_id} uses Bettercap continuous mode, skipping cron execution")
                return
            
            logger.info(f"Task details: {task.name}")
            logger.info(f"  CIDRs: {task.cidrs}")
            logger.info(f"  Scan tool: {task.scan_tool}")
            logger.info(f"  Nmap args: {task.nmap_args or 'default'}")
            logger.info(f"  Cron: {task.cron_expression}")
            
            # 创建执行记录
            exec_repo = TaskExecutionRepository(session)
            execution = TaskExecution(
                task_id=task_id,
                started_at=datetime.now(),
                status="running"
            )
            execution = exec_repo.create(execution)
            
            try:
                # 解析网段列表
                cidrs = json.loads(task.cidrs)
                logger.info(f"Starting scan for {len(cidrs)} CIDR(s): {cidrs}")
                
                # 执行扫描
                logger.info(f"Executing nmap scan...")
                devices_info, raw_output = await scan_nmap(cidrs, task.nmap_args)
                logger.info(f"Scan completed, found {len(devices_info)} online devices")
                
                # 更新设备记录并标记离线设备
                logger.info(f"Updating device records...")
                updated, new_count, offline_count = upsert_devices_with_info(
                    session, 
                    devices_info,
                    mark_offline=True,
                    target_cidrs=cidrs,
                    scan_tool="nmap"  # Nmap 扫描
                )
                logger.info(f"Device records updated: {updated} total, {new_count} new, {offline_count} offline")
                
                # 更新执行记录
                execution.completed_at = datetime.now()
                execution.status = "success"
                execution.online_count = len(devices_info)
                execution.offline_count = offline_count
                execution.new_count = new_count
                execution.raw_output = raw_output  # 保存Nmap原始输出
                exec_repo.update(execution)
                
                # 更新任务的最后执行时间
                task.last_run_at = datetime.now()
                task_repo.update(task)
                
                # 提交所有更改
                session.commit()
                
                logger.info(f"✓ Task {task_id} completed successfully")
                logger.info(f"  Online: {len(devices_info)}, Offline: {offline_count}, New: {new_count}")
                logger.info("=" * 60)
                
            except Exception as e:
                # 记录错误
                logger.error(f"✗ Task {task_id} failed with error: {str(e)}", exc_info=True)
                execution.completed_at = datetime.now()
                execution.status = "failed"
                execution.error_message = str(e)
                exec_repo.update(execution)
                session.commit()
                logger.info("=" * 60)
        
        finally:
            session.close()
                
    finally:
        _running_tasks.discard(task_id)


def _execute_task_wrapper(task_id: int):
    """任务执行包装器，在新的事件循环中运行"""
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(execute_scheduled_task(task_id))
    finally:
        loop.close()


def _schedule_task(task: ScheduledTask):
    """将任务添加到调度器"""
    if not _scheduler:
        return
    
    job_id = f"task_{task.id}"
    
    # 如果是 Bettercap 任务，启动持续监控
    if task.scan_tool == "bettercap":
        # 停止可能已存在的监控
        stop_bettercap_continuous_monitoring(task.id)
        
        # 启动新的持续监控
        try:
            cidrs = json.loads(task.cidrs)
            loop = asyncio.get_event_loop()
            continuous_task = loop.create_task(
                start_bettercap_continuous_monitoring(task.id, cidrs)
            )
            _bettercap_continuous_tasks[task.id] = continuous_task
            logger.info(f"Started Bettercap continuous monitoring for task {task.id}: {task.name}")
        except Exception as e:
            logger.error(f"Failed to start Bettercap monitoring for task {task.id}: {e}")
    else:
        # Nmap 任务：使用 cron 调度
        # 移除已存在的任务
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
        
        # 添加新任务
        trigger = CronTrigger.from_crontab(task.cron_expression)
        _scheduler.add_job(
            func=_execute_task_wrapper,
            args=[task.id],
            trigger=trigger,
            id=job_id,
            name=task.name,
            replace_existing=True
        )
        logger.info(f"Scheduled task {task.id}: {task.name} with cron {task.cron_expression}")


def start_scheduler():
    """启动调度器并加载所有启用的任务"""
    global _scheduler, _scheduler_lock_file
    
    if _scheduler is not None:
        logger.warning("Scheduler already started in this process")
        return
    
    # 尝试获取文件锁，确保只有一个进程启动调度器
    lock_file_path = '/tmp/niar_scheduler.lock'
    
    try:
        _scheduler_lock_file = open(lock_file_path, 'w')
        fcntl.flock(_scheduler_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info("=" * 60)
        logger.info("✓ Acquired scheduler lock, this process will run the scheduler")
        logger.info(f"Process ID: {os.getpid()}")
    except BlockingIOError:
        logger.info("=" * 60)
        logger.info("✗ Another process already has the scheduler lock")
        logger.info(f"Process ID: {os.getpid()}")
        logger.info("This process will NOT start a scheduler (to avoid conflicts)")
        logger.info("=" * 60)
        return
    except Exception as e:
        logger.error(f"Failed to acquire scheduler lock: {str(e)}")
        return
    
    logger.info("Starting APScheduler...")
    # 使用本地时区而不是UTC
    from tzlocal import get_localzone
    local_tz = get_localzone()
    logger.info(f"Using timezone: {local_tz}")
    _scheduler = BackgroundScheduler(timezone=local_tz)
    _scheduler.start()
    logger.info(f"Scheduler started successfully. Running: {_scheduler.running}")
    
    # 加载所有启用的任务
    with Session(engine) as session:
        task_repo = ScheduledTaskRepository(session)
        enabled_tasks = task_repo.get_enabled()
        
        logger.info(f"Found {len(enabled_tasks)} enabled tasks in database")
        
        for task in enabled_tasks:
            try:
                _schedule_task(task)
                logger.info(f"  ✓ Scheduled: {task.name} (ID: {task.id}, Cron: {task.cron_expression})")
            except Exception as e:
                logger.error(f"  ✗ Failed to schedule task {task.id}: {str(e)}")
    
    # 添加系统日志清理任务（每天凌晨3点执行）
    _scheduler.add_job(
        func=_cleanup_old_system_logs,
        trigger='cron',
        hour=3,
        minute=0,
        id='cleanup_system_logs',
        name='清理30天前的系统日志',
        replace_existing=True
    )
    logger.info("  ✓ Scheduled: 系统日志清理任务 (每天 03:00)")
    
    # 显示所有已加载的任务
    jobs = _scheduler.get_jobs()
    logger.info(f"Total jobs in scheduler: {len(jobs)}")
    for job in jobs:
        logger.info(f"  - Job: {job.id}, Next run: {job.next_run_time}")
    logger.info("=" * 60)


def stop_scheduler():
    """停止调度器"""
    global _scheduler, _scheduler_lock_file
    
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
    
    # 释放文件锁
    if _scheduler_lock_file:
        try:
            fcntl.flock(_scheduler_lock_file.fileno(), fcntl.LOCK_UN)
            _scheduler_lock_file.close()
            _scheduler_lock_file = None
            logger.info("Scheduler lock released")
        except Exception as e:
            logger.error(f"Failed to release scheduler lock: {str(e)}")


def reload_task(task_id: int):
    """重新加载指定任务"""
    with Session(engine) as session:
        task_repo = ScheduledTaskRepository(session)
        task = task_repo.get_by_id(task_id)
        
        if not task:
            return
        
        job_id = f"task_{task_id}"
        
        # 停止 Bettercap 持续监控（如果有）
        stop_bettercap_continuous_monitoring(task_id)
        
        # 移除 cron 任务（如果有）
        if _scheduler and _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
        
        # 如果任务已启用，重新添加
        if task.enabled:
            _schedule_task(task)
        else:
            logger.info(f"Task {task_id} is disabled, not scheduling")


def remove_task(task_id: int):
    """从调度器中移除任务"""
    # 停止 Bettercap 持续监控
    stop_bettercap_continuous_monitoring(task_id)
    
    # 移除 cron 任务
    if _scheduler:
        job_id = f"task_{task_id}"
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
            logger.info(f"Removed task {task_id} from scheduler")


def get_scheduler_status() -> dict:
    """获取调度器状态"""
    # 检查锁文件是否存在，判断是否有进程持有调度器
    lock_file_path = '/tmp/niar_scheduler.lock'
    scheduler_running = False
    
    # 尝试检查锁文件
    if os.path.exists(lock_file_path):
        try:
            # 尝试获取非阻塞锁来测试
            test_lock = open(lock_file_path, 'r')
            fcntl.flock(test_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # 如果成功获取，说明没有其他进程持有 → 调度器可能已停止
            fcntl.flock(test_lock.fileno(), fcntl.LOCK_UN)
            test_lock.close()
            scheduler_running = False
        except BlockingIOError:
            # 无法获取锁，说明有其他进程持有 → 调度器正在运行
            scheduler_running = True
        except Exception:
            scheduler_running = False
    
    # 如果本进程有调度器，返回详细信息
    if _scheduler and _scheduler.running:
        jobs = _scheduler.get_jobs()
        job_details = [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
        
        return {
            "running": True,
            "jobs": len(jobs),
            "job_details": job_details,
            "running_tasks": list(_running_tasks),
            "bettercap_tasks": list(_bettercap_continuous_tasks.keys()),
            "this_process_has_scheduler": True
        }
    
    # 本进程没有调度器，但通过锁文件判断整体状态
    return {
        "running": scheduler_running,
        "jobs": 0,  # 本进程不知道具体任务数
        "job_details": [],
        "running_tasks": [],
        "this_process_has_scheduler": False,
        "note": "Scheduler is running in another process" if scheduler_running else "Scheduler is not running"
    }

