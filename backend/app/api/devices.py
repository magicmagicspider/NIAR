from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.models.db import get_session
from app.models.device import Device
from app.repositories.device_repo import DeviceRepository
from app.schemas.device import DeviceCreate, DeviceRead, DeviceUpdate
import json


router = APIRouter(prefix="/api/devices", tags=["devices"])


def serialize_tags(tags_json: str | None) -> Optional[list[str]]:
    if not tags_json:
        return None
    try:
        return json.loads(tags_json)
    except Exception:
        return None


def deserialize_tags(tags: Optional[list[str]]) -> Optional[str]:
    if tags is None:
        return None
    return json.dumps(tags, ensure_ascii=False)


@router.get("/", response_model=List[DeviceRead])
def list_devices(keyword: Optional[str] = None, session: Session = Depends(get_session)):
    repo = DeviceRepository(session)
    devices = repo.list(keyword)
    result: List[DeviceRead] = []
    for d in devices:
        # 计算综合在线状态：任一扫描工具发现在线即为在线
        nmap_online = bool(d.nmap_last_seen and not d.nmap_offline_at)
        bettercap_online = bool(d.bettercap_last_seen and not d.bettercap_offline_at)
        is_online = nmap_online or bettercap_online
        
        result.append(
            DeviceRead(
                id=d.id,
                ip=d.ip,
                mac=d.mac,
                hostname=d.hostname,
                vendor=d.vendor,
                os=d.os,
                tags=serialize_tags(d.tags),
                note=d.note,
                firstSeenAt=d.firstSeenAt,
                lastSeenAt=d.lastSeenAt,
                offline_at=d.offline_at,
                lastScanTaskId=d.lastScanTaskId,
                # 双状态
                nmap_last_seen=d.nmap_last_seen,
                nmap_offline_at=d.nmap_offline_at,
                bettercap_last_seen=d.bettercap_last_seen,
                bettercap_offline_at=d.bettercap_offline_at,
                is_online=is_online
            )
        )
    return result


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: int, session: Session = Depends(get_session)):
    repo = DeviceRepository(session)
    d = repo.get(device_id)
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # 计算综合在线状态
    nmap_online = bool(d.nmap_last_seen and not d.nmap_offline_at)
    bettercap_online = bool(d.bettercap_last_seen and not d.bettercap_offline_at)
    is_online = nmap_online or bettercap_online
    
    return DeviceRead(
        id=d.id,
        ip=d.ip,
        mac=d.mac,
        hostname=d.hostname,
        vendor=d.vendor,
        os=d.os,
        tags=serialize_tags(d.tags),
        note=d.note,
        firstSeenAt=d.firstSeenAt,
        lastSeenAt=d.lastSeenAt,
        offline_at=d.offline_at,
        lastScanTaskId=d.lastScanTaskId,
        # 双状态
        nmap_last_seen=d.nmap_last_seen,
        nmap_offline_at=d.nmap_offline_at,
        bettercap_last_seen=d.bettercap_last_seen,
        bettercap_offline_at=d.bettercap_offline_at,
        is_online=is_online
    )


@router.post("/", response_model=DeviceRead)
def create_device(payload: DeviceCreate, session: Session = Depends(get_session)):
    repo = DeviceRepository(session)
    exists = repo.get_by_ip(payload.ip)
    if exists:
        raise HTTPException(status_code=400, detail="IP already exists")
    d = Device(
        ip=payload.ip,
        mac=payload.mac,
        hostname=payload.hostname,
        vendor=payload.vendor,
        tags=deserialize_tags(payload.tags),
        note=payload.note,
    )
    d = repo.create(d)
    return DeviceRead.model_validate(d, from_attributes=True)


@router.put("/{device_id}", response_model=DeviceRead)
def update_device(device_id: int, payload: DeviceUpdate, session: Session = Depends(get_session)):
    repo = DeviceRepository(session)
    d = repo.get(device_id)
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")

    if payload.mac is not None:
        d.mac = payload.mac
    if payload.hostname is not None:
        d.hostname = payload.hostname
    if payload.vendor is not None:
        d.vendor = payload.vendor
    if payload.tags is not None:
        d.tags = deserialize_tags(payload.tags)
    if payload.note is not None:
        d.note = payload.note

    d = repo.update(d)
    return DeviceRead.model_validate(d, from_attributes=True)


@router.delete("/{device_id}")
def delete_device(device_id: int, session: Session = Depends(get_session)):
    repo = DeviceRepository(session)
    d = repo.get(device_id)
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")
    repo.delete(d)
    return {"success": True}


