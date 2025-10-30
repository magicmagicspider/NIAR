from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class DeviceCreate(BaseModel):
    ip: str
    mac: Optional[str] = None
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None


class DeviceUpdate(BaseModel):
    mac: Optional[str] = None
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None


class DeviceRead(BaseModel):
    id: int
    ip: str
    mac: Optional[str] = None
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    os: Optional[str] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    firstSeenAt: datetime
    lastSeenAt: Optional[datetime] = None
    offline_at: Optional[datetime] = None  # 兼容旧版
    lastScanTaskId: Optional[int] = None
    
    # 双状态字段
    nmap_last_seen: Optional[datetime] = None
    nmap_offline_at: Optional[datetime] = None
    bettercap_last_seen: Optional[datetime] = None
    bettercap_offline_at: Optional[datetime] = None
    
    # 综合在线状态（计算属性）
    is_online: bool = True  # 默认值，会被覆盖

    class Config:
        from_attributes = True


