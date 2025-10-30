from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class ArpBanTarget(SQLModel, table=True):
    """ARP Ban 目标设备"""
    __tablename__ = "arp_ban_target"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ip: str = Field(index=True, unique=True, description="目标 IP 地址")
    mac: Optional[str] = Field(default=None, description="MAC 地址")
    hostname: Optional[str] = Field(default=None, description="主机名")
    note: Optional[str] = Field(default=None, description="备注")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    created_by: str = Field(default="admin", description="创建人")

