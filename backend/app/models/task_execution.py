from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class TaskExecution(SQLModel, table=True):
    """定时任务执行记录"""
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True)  # 关联的任务ID
    started_at: datetime = Field(default_factory=datetime.now)  # 开始时间
    completed_at: Optional[datetime] = None  # 完成时间
    status: str = Field(default="running")  # running/success/failed
    online_count: int = Field(default=0)  # 在线设备数
    offline_count: int = Field(default=0)  # 离线设备数
    new_count: int = Field(default=0)  # 新发现设备数
    error_message: Optional[str] = None  # 错误信息
    raw_output: Optional[str] = None  # Nmap原始输出（用于日志显示）

