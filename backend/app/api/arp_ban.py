from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from pydantic import BaseModel
from typing import Optional, List

from app.models.db import get_session
from app.models.arp_ban_target import ArpBanTarget
from app.models.arp_ban_log import ArpBanLog
from app.repositories.arp_ban_target_repo import ArpBanTargetRepository
from app.repositories.arp_ban_log_repo import ArpBanLogRepository
from app.repositories.device_repo import DeviceRepository
from app.services.arp_ban_service import ArpBanService
from app.utils.network import get_primary_network_cidr, expand_cidr_for_arp_ban, get_network_info

router = APIRouter()


class AddTargetRequest(BaseModel):
    ip: str
    mac: Optional[str] = None
    hostname: Optional[str] = None
    note: Optional[str] = None


@router.get("/status")
async def get_arp_ban_status():
    """获取 ARP Ban 运行状态"""
    return {
        "running": ArpBanService.is_running(),
        "target_count": len(ArpBanService.get_targets()),
        "targets": ArpBanService.get_targets()
    }


@router.get("/network-info")
async def get_network_info_api():
    """获取网络信息"""
    return get_network_info()


@router.get("/available-hosts")
async def get_available_hosts(session: Session = Depends(get_session)):
    """
    获取网段内所有可用主机（基于网段生成，不管是否在线）
    
    Returns:
        {
            "cidr": "192.168.1.0/24",
            "total": 252,
            "hosts": [...],
            "whitelist": ["192.168.1.1", "192.168.1.10"]
        }
    """
    # 1. 获取当前网段
    cidr = get_primary_network_cidr()
    
    # 2. 获取白名单（网关和本机）
    from app.utils.network import get_gateway_ip, get_local_ip_from_socket
    gateway_ip = get_gateway_ip()
    local_ip = get_local_ip_from_socket()
    whitelist = [gateway_ip, local_ip]
    
    # 3. 展开所有 IP（排除 .1 和 .254）
    all_ips = expand_cidr_for_arp_ban(cidr)
    
    # 4. 尝试从数据库匹配设备信息（可选，增强显示）
    device_repo = DeviceRepository(session)
    hosts = []
    
    for ip in all_ips:
        device = device_repo.get_by_ip(ip)
        # 判断在线状态：如果有最近被发现的记录且没有离线记录
        is_online = False
        if device:
            has_recent_seen = device.nmap_last_seen or device.bettercap_last_seen
            has_offline = device.nmap_offline_at or device.bettercap_offline_at
            is_online = bool(has_recent_seen and not has_offline)
        
        # 判断是否在白名单
        is_whitelist = ip in whitelist
        
        hosts.append({
            "ip": ip,
            "mac": device.mac if device else None,
            "hostname": device.hostname if device else None,
            "vendor": device.vendor if device else None,
            "online": is_online,  # 仅供参考
            "last_seen": device.lastSeenAt.isoformat() if device and device.lastSeenAt else None,
            "is_whitelist": is_whitelist  # 新增：是否在白名单
        })
    
    return {
        "cidr": cidr,
        "total": len(hosts),
        "hosts": hosts,
        "whitelist": whitelist,  # 新增：白名单列表
        "gateway_ip": gateway_ip,  # 新增：网关IP
        "local_ip": local_ip  # 新增：本机IP
    }


@router.get("/targets")
async def list_targets(session: Session = Depends(get_session)):
    """获取所有目标设备"""
    repo = ArpBanTargetRepository(session)
    targets = repo.get_all()
    return {"targets": targets}


@router.post("/targets")
async def add_target(req: AddTargetRequest, session: Session = Depends(get_session)):
    """添加目标设备"""
    repo = ArpBanTargetRepository(session)
    log_repo = ArpBanLogRepository(session)
    
    # 检查是否在白名单（网关、本机等受保护设备）
    from app.utils.network import get_gateway_ip, get_local_ip_from_socket
    gateway_ip = get_gateway_ip()
    local_ip = get_local_ip_from_socket()
    whitelist = [gateway_ip, local_ip]
    
    if req.ip in whitelist:
        ip_type = "网关" if req.ip == gateway_ip else "本机"
        raise HTTPException(
            status_code=400,
            detail=f"无法添加 {req.ip}：该IP是{ip_type}，禁止Ban以保证网络正常运行"
        )
    
    # 检查是否已存在
    existing = repo.get_by_ip(req.ip)
    if existing:
        raise HTTPException(status_code=400, detail=f"IP {req.ip} 已在目标列表中")
    
    # 创建目标
    target = ArpBanTarget(
        ip=req.ip,
        mac=req.mac,
        hostname=req.hostname,
        note=req.note
    )
    repo.create(target)
    
    # 记录日志
    log_repo.create(ArpBanLog(
        action="add",
        ip=req.ip,
        message=f"添加目标设备: {req.ip}",
        operator="admin"
    ))
    
    # 如果 ARP Ban 正在运行，动态更新目标
    if ArpBanService.is_running():
        all_targets = repo.get_all()
        target_ips = [t.ip for t in all_targets]
        await ArpBanService.update_targets(target_ips)
    
    return {"success": True, "target": target}


@router.delete("/targets/{ip}")
async def remove_target(ip: str, session: Session = Depends(get_session)):
    """移除目标设备"""
    repo = ArpBanTargetRepository(session)
    log_repo = ArpBanLogRepository(session)
    
    # 检查是否存在
    target = repo.get_by_ip(ip)
    if not target:
        raise HTTPException(status_code=404, detail=f"目标 {ip} 不存在")
    
    # 删除目标
    repo.delete_by_ip(ip)
    
    # 记录日志
    log_repo.create(ArpBanLog(
        action="remove",
        ip=ip,
        message=f"移除目标设备: {ip}",
        operator="admin"
    ))
    
    # 如果 ARP Ban 正在运行，动态更新目标
    if ArpBanService.is_running():
        all_targets = repo.get_all()
        target_ips = [t.ip for t in all_targets]
        await ArpBanService.update_targets(target_ips)
    
    return {"success": True, "message": f"已移除目标 {ip}"}


class StartBanRequest(BaseModel):
    gateway: Optional[str] = None
    whitelist: Optional[List[str]] = None


@router.post("/start")
async def start_ban(req: StartBanRequest = None, session: Session = Depends(get_session)):
    """启动 ARP Ban"""
    try:
        # 获取白名单配置
        gateway_ip = req.gateway if req and req.gateway else None
        whitelist_ips = req.whitelist if req and req.whitelist else []
        
        await ArpBanService.start_arp_ban(gateway_ip=gateway_ip, whitelist_ips=whitelist_ips)
        return {"success": True, "message": "ARP Ban 已启动"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@router.post("/stop")
async def stop_ban(session: Session = Depends(get_session)):
    """停止 ARP Ban"""
    try:
        await ArpBanService.stop_arp_ban()
        return {"success": True, "message": "ARP Ban 已停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")


@router.get("/logs")
async def get_logs(limit: int = 100, session: Session = Depends(get_session)):
    """获取操作日志"""
    repo = ArpBanLogRepository(session)
    logs = repo.get_recent(limit)
    return {"logs": logs}

