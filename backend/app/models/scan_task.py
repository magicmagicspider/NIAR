from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class ScanTask(SQLModel, table=True):
    """扫描任务模型 - 用于异步扫描"""
    __tablename__ = "scan_tasks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(index=True, unique=True)  # UUID
    
    # 任务参数
    cidrs: str  # JSON 字符串，存储 CIDR 列表
    scan_tool: str = Field(default="nmap")  # 扫描工具: "nmap" 或 "bettercap"
    nmap_args: Optional[str] = None
    
    # Bettercap 参数
    bettercap_url: Optional[str] = None
    bettercap_duration: Optional[int] = None  # 扫描持续时间（秒）
    
    # 任务状态
    status: str = Field(default="pending")  # pending, running, completed, failed
    progress: int = Field(default=0)  # 0-100
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 结果统计
    total_hosts: int = Field(default=0)  # 总共扫描的主机数
    online_count: int = Field(default=0)
    offline_count: int = Field(default=0)
    new_count: int = Field(default=0)
    
    # 错误信息
    error_message: Optional[str] = None
    
    # nmap 原始输出（可选，可能很大）
    raw_output: Optional[str] = None




