from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import Optional
from app.models.db import get_session
from app.repositories.system_event_log_repo import SystemEventLogRepository

router = APIRouter(prefix="/system-logs", tags=["系统日志"])


@router.get("")
async def get_system_logs(
    limit: int = 100,
    days: int = 30,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """获取系统事件日志"""
    repo = SystemEventLogRepository(session)
    logs = repo.get_recent(
        limit=limit,
        days=days,
        event_type=event_type,
        severity=severity
    )
    
    return {
        "logs": logs,
        "count": len(logs),
        "limit": limit,
        "days": days
    }


@router.get("/stats")
async def get_system_logs_stats(
    days: int = 30,
    session: Session = Depends(get_session)
):
    """获取日志统计信息"""
    repo = SystemEventLogRepository(session)
    stats = repo.get_stats(days=days)
    return stats


