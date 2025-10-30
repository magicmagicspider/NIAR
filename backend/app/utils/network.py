import ipaddress
import socket
import subprocess
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def get_primary_network_cidr() -> str:
    """
    获取当前主网卡的 CIDR
    
    Returns:
        如 "192.168.1.0/24"
    """
    try:
        # 方法1: 通过连接外部地址获取本机 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # 假设是 /24 网段（最常见）
        # 实际生产环境可能需要更精确的子网掩码检测
        ip_parts = local_ip.split('.')
        network_prefix = '.'.join(ip_parts[:3]) + '.0'
        cidr = f"{network_prefix}/24"
        
        logger.info(f"检测到主网段: {cidr} (本机IP: {local_ip})")
        return cidr
        
    except Exception as e:
        logger.error(f"获取网卡 CIDR 失败: {e}")
        # 默认返回常见的内网网段
        return "192.168.1.0/24"


def expand_cidr_for_arp_ban(cidr: str) -> List[str]:
    """
    展开 CIDR 为完整 IP 列表，排除 .1 和 .254
    
    Args:
        cidr: 如 "192.168.1.0/24"
    
    Returns:
        IP 列表: ["192.168.1.2", "192.168.1.3", ..., "192.168.1.253"]
        排除了 .1（通常是网关）和 .254（保留地址）
    
    示例:
        cidr = "192.168.1.0/24"
        结果 = ["192.168.1.2", ..., "192.168.1.253"]  # 252个IP
    """
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        ips = []
        
        for ip in network.hosts():
            ip_str = str(ip)
            # 排除最后一位是 1 或 254 的地址
            last_octet = int(ip_str.split('.')[-1])
            if last_octet == 1 or last_octet == 254:
                continue
            ips.append(ip_str)
        
        logger.debug(f"展开 CIDR {cidr}: 共 {len(ips)} 个可用 IP")
        return ips
        
    except ValueError as e:
        logger.error(f"无效的 CIDR 格式 {cidr}: {e}")
        return []


def get_network_info() -> dict:
    """
    获取网络信息摘要
    
    Returns:
        {
            "cidr": "192.168.1.0/24",
            "local_ip": "192.168.1.100",
            "total_ips": 252
        }
    """
    cidr = get_primary_network_cidr()
    ips = expand_cidr_for_arp_ban(cidr)
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "未知"
    
    return {
        "cidr": cidr,
        "local_ip": local_ip,
        "total_ips": len(ips)
    }


def get_gateway_ip() -> str:
    """
    获取默认网关 IP
    
    Returns:
        网关 IP 地址，如 "192.168.1.1" 或 "10.3.61.1"
        如果检测失败，返回 "0.0.0.0"
    """
    try:
        # 方法1: Linux - ip route
        result = subprocess.run(
            ['ip', 'route', 'show', 'default'],
            capture_output=True, 
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout:
            # 输出格式: default via 10.3.61.1 dev eth0
            parts = result.stdout.split()
            if 'via' in parts:
                gateway = parts[parts.index('via') + 1]
                logger.info(f"检测到网关 IP: {gateway}")
                return gateway
        
        # 方法2: Linux - route -n
        result = subprocess.run(
            ['route', '-n'],
            capture_output=True, 
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('0.0.0.0'):
                    parts = line.split()
                    if len(parts) >= 2:
                        gateway = parts[1]
                        logger.info(f"检测到网关 IP (route): {gateway}")
                        return gateway
    
    except subprocess.TimeoutExpired:
        logger.error("检测网关超时")
    except FileNotFoundError as e:
        logger.error(f"命令不存在: {e}")
    except Exception as e:
        logger.error(f"检测网关失败: {e}")
    
    logger.warning("无法检测网关，返回默认值")
    return "0.0.0.0"


def get_local_ip_from_socket() -> str:
    """
    获取本机 IP 地址（通过建立 socket 连接）
    
    Returns:
        本机 IP 地址，如 "192.168.1.100" 或 "10.3.61.50"
        如果检测失败，返回 "127.0.0.1"
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        logger.info(f"检测到本机 IP: {local_ip}")
        return local_ip
    except Exception as e:
        logger.error(f"获取本机 IP 失败: {e}")
        return "127.0.0.1"

