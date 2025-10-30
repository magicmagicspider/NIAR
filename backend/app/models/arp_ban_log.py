from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class ArpBanLog(SQLModel, table=True):
    """ARP Ban 操作日志"""
    __tablename__ = "arp_ban_log"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    action: str = Field(description="操作类型: start/stop/add/remove")
    ip: Optional[str] = Field(default=None, description="相关 IP")
    message: str = Field(description="日志信息")
    operator: str = Field(default="admin", description="操作人")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

