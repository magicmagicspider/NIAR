from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime

from app.models.scheduled_task import ScheduledTask


class ScheduledTaskRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> List[ScheduledTask]:
        """获取所有定时任务"""
        stmt = select(ScheduledTask).order_by(ScheduledTask.id)
        return list(self.session.exec(stmt).all())

    def get_enabled(self) -> List[ScheduledTask]:
        """获取所有启用的定时任务"""
        stmt = select(ScheduledTask).where(ScheduledTask.enabled == True)
        return list(self.session.exec(stmt).all())

    def get_by_id(self, task_id: int) -> Optional[ScheduledTask]:
        """根据ID获取任务"""
        return self.session.get(ScheduledTask, task_id)

    def create(self, task: ScheduledTask) -> ScheduledTask:
        """创建任务"""
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def update(self, task: ScheduledTask) -> ScheduledTask:
        """更新任务"""
        task.updated_at = datetime.now()
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete(self, task_id: int) -> bool:
        """删除任务"""
        task = self.get_by_id(task_id)
        if task:
            self.session.delete(task)
            self.session.commit()
            return True
        return False

