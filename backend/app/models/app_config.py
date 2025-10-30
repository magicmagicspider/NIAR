from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class AppConfig(SQLModel, table=True):
    """全局应用配置"""
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)  # 配置键
    value: str  # 配置值（JSON 字符串）
    description: Optional[str] = None  # 配置说明
    updated_at: datetime = Field(default_factory=datetime.now)

