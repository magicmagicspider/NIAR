import asyncio
import contextlib
import re
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session

from app.models.device import Device
from app.repositories.device_repo import DeviceRepository


def _get_local_machine_info(ip: str) -> Optional[Dict[str, Optional[str]]]:
    """
    获取本机的网络接口信息（MAC 地址和厂商）
    仅当 IP 是本机地址时返回信息
    """
    try:
        # 获取所有网络接口的 IP 和 MAC 地址
        result = subprocess.run(
            ['ip', 'addr', 'show'],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode != 0:
            return None
        
        output = result.stdout
        lines = output.split('\n')
        
        # 查找匹配的 IP 地址和对应的 MAC 地址
        found_ip = False
        mac_address = None
        
        for i, line in enumerate(lines):
            # 检查是否包含目标 IP
            if f'inet {ip}/' in line:
                found_ip = True
                # 往回查找对应接口的 MAC 地址
                for j in range(i - 1, max(0, i - 10), -1):
                    if 'link/ether' in lines[j]:
                        parts = lines[j].strip().split()
                        if len(parts) >= 2:
                            mac_address = parts[1].upper()
                            break
                break
        
        if found_ip and mac_address:
            # 根据 MAC 地址前缀判断厂商
            vendor = None
            if mac_address.startswith('00:0C:29'):
                vendor = 'VMware'
            elif mac_address.startswith('00:50:56'):
                vendor = 'VMware'
            elif mac_address.startswith('08:00:27'):
                vendor = 'VirtualBox'
            
            return {
                'mac': mac_address,
                'hostname': None,  # 主机名由其他方式获取
                'vendor': vendor,
                'os': None  # OS 信息由其他方式获取
            }
    except Exception:
        pass
    
    return None


async def _ping(host: str, timeout: float = 1.0) -> bool:
    """使用系统 ping 命令检测主机是否在线"""
    ping_bin = shutil.which("ping")
    if not ping_bin:
        return False
    proc = await asyncio.create_subprocess_exec(
        ping_bin,
        "-c",
        "1",
        "-W",
        str(int(timeout)),
        host,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        rc = await asyncio.wait_for(proc.wait(), timeout=timeout + 0.5)
        return rc == 0
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        return False


async def scan_ping(hosts: List[str], concurrency: int = 128) -> List[str]:
    """使用 ping 扫描主机列表"""
    sem = asyncio.Semaphore(concurrency)
    online: List[str] = []

    async def worker(h: str):
        async with sem:
            if await _ping(h):
                online.append(h)

    await asyncio.gather(*(worker(h) for h in hosts))
    return online


async def scan_nmap(
    targets: List[str], 
    nmap_args: Optional[str] = None
) -> Tuple[Dict[str, Dict[str, Optional[str]]], str]:
    """
    使用 nmap 扫描主机，获取 IP、MAC 地址、主机名、操作系统等信息
    
    Args:
        targets: 目标 IP 或 CIDR 列表
        nmap_args: 自定义 nmap 参数，如 "-sn -T4"
        
    Returns:
        元组: (解析结果字典, nmap原始输出)
    """
    nmap_bin = shutil.which("nmap")
    if not nmap_bin:
        raise RuntimeError("nmap not found")
    
    # 构建 nmap 命令
    cmd = [nmap_bin]
    
    if nmap_args:
        # 使用用户自定义参数
        cmd.extend(nmap_args.split())
    else:
        # 默认参数：主机发现 + 获取 MAC 地址和主机名
        # -sn: ping scan (不进行端口扫描，只检测主机是否在线)
        # 会自动获取 MAC 地址（同网段）和主机名（如果有DNS记录）
        # 注意：-O (OS检测) 需要端口扫描，不能和 -sn 一起使用
        # 如需 OS 检测，请使用自定义参数如 "-sS -O" 或 "-sV -O"
        cmd.extend(["-sn"])
    
    cmd.extend(targets)
    
    # 执行 nmap (需要 root 权限进行 OS 检测)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        error_msg = stderr.decode('utf-8', errors='ignore')
        raise RuntimeError(f"nmap failed: {error_msg}")
    
    # 解析 nmap 输出
    raw_output = stdout.decode('utf-8', errors='ignore')
    parsed_results = _parse_nmap_output(raw_output)
    
    return parsed_results, raw_output


def _parse_nmap_output(output: str) -> Dict[str, Dict[str, Optional[str]]]:
    """
    解析 nmap 输出，提取 IP、MAC 地址、主机名、操作系统、厂商等信息
    
    只返回在线（host is up）的主机！
    
    示例输出:
    Nmap scan report for hostname.local (192.168.1.1)
    Host is up (0.0012s latency).
    MAC Address: AA:BB:CC:DD:EE:FF (Vendor Name)
    Device type: general purpose
    Running: Linux 3.X|4.X
    OS CPE: cpe:/o:linux:linux_kernel:3 cpe:/o:linux:linux_kernel:4
    OS details: Linux 3.2 - 4.9
    
    或者离线主机:
    Nmap scan report for 192.168.1.2
    [host down]
    """
    results = {}
    current_ip = None
    is_host_up = False  # 标记当前主机是否在线
    
    # 正则表达式
    ip_pattern = re.compile(r'Nmap scan report for (\d+\.\d+\.\d+\.\d+)')
    mac_pattern = re.compile(r'MAC Address: ([0-9A-Fa-f:]{17})(?: \((.+?)\))?')
    hostname_pattern = re.compile(r'Nmap scan report for (.+?) \((\d+\.\d+\.\d+\.\d+)\)')
    os_details_pattern = re.compile(r'OS details: (.+)')
    running_pattern = re.compile(r'Running: (.+)')
    host_up_pattern = re.compile(r'Host is up')  # 检测主机是否在线
    host_down_pattern = re.compile(r'\[host down\]')  # 检测主机是否离线
    
    for line in output.split('\n'):
        line = line.strip()
        
        # 匹配主机名和IP
        hostname_match = hostname_pattern.match(line)
        if hostname_match:
            hostname = hostname_match.group(1)
            ip = hostname_match.group(2)
            current_ip = ip
            is_host_up = False  # 重置状态，等待确认是否在线
            # 先不加入 results，等确认 host is up
            # 但保存主机名，以便后续使用
            if current_ip not in results:
                # 临时创建条目，但标记为未确认
                results[current_ip] = {'mac': None, 'hostname': hostname, 'vendor': None, 'os': None, '_unconfirmed': True}
            else:
                results[current_ip]['hostname'] = hostname
            continue
        
        # 匹配 IP
        ip_match = ip_pattern.match(line)
        if ip_match:
            current_ip = ip_match.group(1)
            is_host_up = False  # 重置状态，等待确认是否在线
            # 先不加入 results，等确认 host is up
            continue
        
        # 检测主机是否在线
        if current_ip and host_up_pattern.search(line):
            is_host_up = True
            # 确认在线，加入结果
            if current_ip not in results:
                results[current_ip] = {'mac': None, 'hostname': None, 'vendor': None, 'os': None}
            else:
                # 移除未确认标记
                results[current_ip].pop('_unconfirmed', None)
            continue
        
        # 检测主机是否离线
        if current_ip and host_down_pattern.search(line):
            is_host_up = False
            # 确认离线，从结果中删除（如果存在）
            if current_ip in results:
                del results[current_ip]
            current_ip = None
            continue
        
        # 只处理已确认在线的主机
        if current_ip and is_host_up:
            # 匹配 MAC 地址和厂商
            mac_match = mac_pattern.match(line)
            if mac_match:
                mac = mac_match.group(1).upper()
                vendor = mac_match.group(2) if mac_match.group(2) else None
                results[current_ip]['mac'] = mac
                results[current_ip]['vendor'] = vendor
                continue
            
            # 匹配操作系统详细信息 (优先级较高)
            os_details_match = os_details_pattern.match(line)
            if os_details_match:
                results[current_ip]['os'] = os_details_match.group(1)
                continue
            
            # 匹配操作系统类型 (如果没有详细信息，则使用这个)
            running_match = running_pattern.match(line)
            if running_match and not results[current_ip].get('os'):
                results[current_ip]['os'] = running_match.group(1)
                continue
    
    # 清理所有未确认的条目（没有收到 "Host is up" 的主机）
    results = {ip: info for ip, info in results.items() if not info.get('_unconfirmed')}
    
    # 清理所有条目的 _unconfirmed 标记
    for info in results.values():
        info.pop('_unconfirmed', None)
    
    return results


def upsert_devices(session: Session, online_ips: List[str]) -> int:
    """更新或创建设备记录（不包含 MAC 信息）"""
    repo = DeviceRepository(session)
    updated = 0
    now = datetime.now()
    for ip in online_ips:
        d = repo.get_by_ip(ip)
        if d:
            d.lastSeenAt = now
            repo.update(d)
        else:
            d = Device(ip=ip, firstSeenAt=now, lastSeenAt=now)
            repo.create(d)
        updated += 1
    return updated


def upsert_devices_with_info(
    session: Session, 
    devices_info: Dict[str, Dict[str, Optional[str]]],
    mark_offline: bool = False,
    target_cidrs: Optional[List[str]] = None,
    scan_tool: str = "nmap"  # 新增：扫描工具类型（nmap 或 bettercap）
) -> Tuple[int, int, int]:
    """
    更新或创建设备记录（包含 MAC 地址、主机名、操作系统等详细信息）
    
    Args:
        session: 数据库会话
        devices_info: 扫描到的设备信息
        mark_offline: 是否标记离线设备
        target_cidrs: 目标网段列表，用于确定哪些设备应该被标记为离线
        scan_tool: 扫描工具类型（nmap 或 bettercap），用于双状态跟踪
        
    Returns:
        (更新数量, 新设备数量, 离线数量)
    """
    from app.utils.cidr import expand_cidrs
    
    repo = DeviceRepository(session)
    updated = 0
    new_count = 0
    offline_count = 0
    now = datetime.now()
    
    online_ips = set(devices_info.keys())
    
    # 更新在线设备
    for ip, info in devices_info.items():
        # 如果设备没有 MAC 地址，尝试检测是否为本机
        if not info.get('mac'):
            local_info = _get_local_machine_info(ip)
            if local_info:
                # 合并本机信息
                if not info.get('mac'):
                    info['mac'] = local_info.get('mac')
                if not info.get('vendor'):
                    info['vendor'] = local_info.get('vendor')
        
        d = repo.get_by_ip(ip)
        if d:
            # 更新现有设备
            d.lastSeenAt = now
            d.offline_at = None  # 清除旧的离线标记（兼容）
            
            # 根据扫描工具更新对应的状态字段
            if scan_tool == "nmap":
                d.nmap_last_seen = now
                d.nmap_offline_at = None
            elif scan_tool == "bettercap":
                d.bettercap_last_seen = now
                d.bettercap_offline_at = None
            
            # 更新设备信息（两种扫描都可以更新）
            if info.get('mac'):
                d.mac = info['mac']
            if info.get('hostname'):
                d.hostname = info['hostname']
            if info.get('vendor'):
                d.vendor = info['vendor']
            if info.get('os'):
                d.os = info['os']
            repo.update(d)
            updated += 1
        else:
            # 只为有 MAC 地址或主机名的设备创建记录
            if info.get('mac') or info.get('hostname'):
                d = Device(
                    ip=ip,
                    mac=info.get('mac'),
                    hostname=info.get('hostname'),
                    vendor=info.get('vendor'),
                    os=info.get('os'),
                    firstSeenAt=now,
                    lastSeenAt=now,
                    # 初始化双状态
                    nmap_last_seen=now if scan_tool == "nmap" else None,
                    bettercap_last_seen=now if scan_tool == "bettercap" else None
                )
                repo.create(d)
                new_count += 1
    
    # 标记离线设备（按扫描工具分别标记）
    if mark_offline and target_cidrs:
        all_target_ips = set(expand_cidrs(target_cidrs))
        all_devices = repo.list()
        
        for device in all_devices:
            if device.ip in all_target_ips and device.ip not in online_ips:
                # 设备在目标网段内，但本次扫描未发现
                if scan_tool == "nmap":
                    if not device.nmap_offline_at:
                        device.nmap_offline_at = now
                        device.offline_at = now  # 同时更新旧字段
                        repo.update(device)
                        offline_count += 1
                elif scan_tool == "bettercap":
                    if not device.bettercap_offline_at:
                        device.bettercap_offline_at = now
                        device.offline_at = now  # 同时更新旧字段
                        repo.update(device)
                        offline_count += 1
    
    return updated + new_count, new_count, offline_count
