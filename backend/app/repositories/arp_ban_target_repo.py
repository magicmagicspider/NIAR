from sqlmodel import Session, select
from app.models.arp_ban_target import ArpBanTarget
from typing import List, Optional


class ArpBanTargetRepository:
    """ARP Ban 目标设备仓储"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_all(self) -> List[ArpBanTarget]:
        """获取所有目标"""
        return list(self.session.exec(select(ArpBanTarget)).all())
    
    def get_by_id(self, target_id: int) -> Optional[ArpBanTarget]:
        """根据 ID 获取目标"""
        return self.session.get(ArpBanTarget, target_id)
    
    def get_by_ip(self, ip: str) -> Optional[ArpBanTarget]:
        """根据 IP 获取目标"""
        return self.session.exec(
            select(ArpBanTarget).where(ArpBanTarget.ip == ip)
        ).first()
    
    def create(self, target: ArpBanTarget) -> ArpBanTarget:
        """创建目标"""
        self.session.add(target)
        self.session.commit()
        self.session.refresh(target)
        return target
    
    def update(self, target: ArpBanTarget) -> ArpBanTarget:
        """更新目标"""
        self.session.add(target)
        self.session.commit()
        self.session.refresh(target)
        return target
    
    def delete(self, target_id: int) -> bool:
        """删除目标"""
        target = self.session.get(ArpBanTarget, target_id)
        if target:
            self.session.delete(target)
            self.session.commit()
            return True
        return False
    
    def delete_by_ip(self, ip: str) -> bool:
        """根据 IP 删除目标"""
        target = self.get_by_ip(ip)
        if target:
            self.session.delete(target)
            self.session.commit()
            return True
        return False

