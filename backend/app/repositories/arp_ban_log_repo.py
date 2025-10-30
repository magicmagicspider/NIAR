from sqlmodel import Session, select
from app.models.arp_ban_log import ArpBanLog
from typing import List


class ArpBanLogRepository:
    """ARP Ban 操作日志仓储"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, log: ArpBanLog) -> ArpBanLog:
        """创建日志"""
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log
    
    def get_recent(self, limit: int = 100) -> List[ArpBanLog]:
        """获取最近的日志"""
        return list(
            self.session.exec(
                select(ArpBanLog)
                .order_by(ArpBanLog.created_at.desc())
                .limit(limit)
            ).all()
        )
    
    def get_by_action(self, action: str, limit: int = 50) -> List[ArpBanLog]:
        """根据操作类型获取日志"""
        return list(
            self.session.exec(
                select(ArpBanLog)
                .where(ArpBanLog.action == action)
                .order_by(ArpBanLog.created_at.desc())
                .limit(limit)
            ).all()
        )

