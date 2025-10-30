from typing import Generator

from sqlmodel import SQLModel, create_engine, Session
import os

# Import all models to ensure they are registered
from app.models.device import Device
from app.models.scheduled_task import ScheduledTask
from app.models.task_execution import TaskExecution
from app.models.scan_task import ScanTask
from app.models.app_config import AppConfig
from app.models.arp_ban_target import ArpBanTarget
from app.models.arp_ban_log import ArpBanLog
from app.models.system_event_log import SystemEventLog
from app.models.user import User
from app.models.ip_request import IPRequest


DB_URL = os.getenv("DATABASE_URL", "sqlite:///./ip_daemon.db")
connect_args = {
    "check_same_thread": False,
    "timeout": 30  # 增加超时时间
} if DB_URL.startswith("sqlite") else {}
engine = create_engine(
    DB_URL, 
    echo=False, 
    connect_args=connect_args,
    pool_pre_ping=True,  # 连接前检查
    pool_recycle=3600   # 每小时回收连接
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


