from typing import List, Optional
from sqlmodel import Session, select
from app.models.scan_task import ScanTask


class ScanTaskRepository:
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, task: ScanTask) -> ScanTask:
        """创建新的扫描任务"""
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task
    
    def get_by_task_id(self, task_id: str) -> Optional[ScanTask]:
        """根据 task_id 获取任务"""
        stmt = select(ScanTask).where(ScanTask.task_id == task_id)
        return self.session.exec(stmt).first()
    
    def get_recent(self, limit: int = 50) -> List[ScanTask]:
        """获取最近的任务列表"""
        stmt = select(ScanTask).order_by(ScanTask.created_at.desc()).limit(limit)
        return list(self.session.exec(stmt).all())
    
    def update(self, task: ScanTask) -> ScanTask:
        """更新任务"""
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task
    
    def delete(self, task_id: str) -> bool:
        """删除任务"""
        task = self.get_by_task_id(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False




