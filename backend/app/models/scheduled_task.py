from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class ScheduledTask(SQLModel, table=True):
    """定时扫描任务模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # 任务名称
    cidrs: str  # JSON字符串，存储扫描网段列表，如 '["192.168.1.0/24"]'
    scan_tool: str = Field(default="nmap")  # 扫描工具：nmap 或 bettercap
    nmap_args: Optional[str] = None  # nmap参数
    bettercap_duration: Optional[int] = None  # Bettercap 扫描持续时间（秒）
    cron_expression: str  # cron表达式，如 "0 2 * * *"
    enabled: bool = Field(default=True)  # 是否启用
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_run_at: Optional[datetime] = None  # 上次执行时间

