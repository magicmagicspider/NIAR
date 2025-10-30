from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class SystemEventLog(SQLModel, table=True):
    """系统事件日志模型（记录Bettercap重启等系统事件）"""
    __tablename__ = "system_event_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(index=True)  # 事件类型：bettercap_restart, bettercap_start, scheduler_start等
    event_category: str = Field(default="system")  # 分类：system, network, task等
    message: str  # 事件描述
    details: Optional[str] = Field(default=None)  # JSON格式的详细信息
    severity: str = Field(default="info")  # 严重程度：info, warning, error
    created_at: datetime = Field(default_factory=datetime.now, index=True)


