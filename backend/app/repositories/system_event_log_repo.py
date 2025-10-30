from sqlmodel import Session, select
from app.models.system_event_log import SystemEventLog
from datetime import datetime, timedelta
from typing import Optional, List


class SystemEventLogRepository:
    """系统事件日志Repository"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(
        self,
        event_type: str,
        message: str,
        event_category: str = "system",
        details: Optional[str] = None,
        severity: str = "info"
    ) -> SystemEventLog:
        """创建系统事件日志"""
        log = SystemEventLog(
            event_type=event_type,
            event_category=event_category,
            message=message,
            details=details,
            severity=severity
        )
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log
    
    def get_recent(
        self,
        limit: int = 100,
        days: int = 30,
        event_type: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[SystemEventLog]:
        """获取最近的日志（默认30天内）"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        statement = select(SystemEventLog).where(
            SystemEventLog.created_at >= cutoff_date
        )
        
        if event_type:
            statement = statement.where(SystemEventLog.event_type == event_type)
        
        if severity:
            statement = statement.where(SystemEventLog.severity == severity)
        
        statement = statement.order_by(SystemEventLog.created_at.desc()).limit(limit)
        
        results = self.session.exec(statement)
        return list(results.all())
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """清理指定天数前的旧日志，返回删除的数量"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        statement = select(SystemEventLog).where(
            SystemEventLog.created_at < cutoff_date
        )
        
        old_logs = self.session.exec(statement).all()
        count = len(old_logs)
        
        for log in old_logs:
            self.session.delete(log)
        
        self.session.commit()
        return count
    
    def get_stats(self, days: int = 30) -> dict:
        """获取日志统计信息"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        statement = select(SystemEventLog).where(
            SystemEventLog.created_at >= cutoff_date
        )
        
        all_logs = self.session.exec(statement).all()
        
        total = len(all_logs)
        by_severity = {}
        by_type = {}
        
        for log in all_logs:
            # 按严重程度统计
            by_severity[log.severity] = by_severity.get(log.severity, 0) + 1
            # 按事件类型统计
            by_type[log.event_type] = by_type.get(log.event_type, 0) + 1
        
        return {
            "total": total,
            "by_severity": by_severity,
            "by_type": by_type,
            "days": days
        }


