from datetime import datetime
from typing import Optional, List

from sqlmodel import SQLModel, Field


class Device(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ip: str = Field(index=True, unique=True)
    mac: Optional[str] = Field(default=None, index=True)
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    os: Optional[str] = None  # 操作系统信息
    tags: Optional[str] = None  # JSON string of list
    note: Optional[str] = None
    firstSeenAt: datetime = Field(default_factory=datetime.now)
    lastSeenAt: Optional[datetime] = None
    offline_at: Optional[datetime] = None  # 离线时间（兼容旧版，已废弃）
    lastScanTaskId: Optional[int] = None
    
    # 双状态跟踪：分别记录 Nmap 和 Bettercap 的检测状态
    nmap_last_seen: Optional[datetime] = None  # Nmap最后发现时间
    nmap_offline_at: Optional[datetime] = None  # Nmap离线时间
    bettercap_last_seen: Optional[datetime] = None  # Bettercap最后发现时间
    bettercap_offline_at: Optional[datetime] = None  # Bettercap离线时间


