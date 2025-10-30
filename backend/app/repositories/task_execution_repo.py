from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime

from app.models.task_execution import TaskExecution


class TaskExecutionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_task_id(self, task_id: int, limit: int = 50) -> List[TaskExecution]:
        """获取指定任务的执行历史"""
        stmt = (
            select(TaskExecution)
            .where(TaskExecution.task_id == task_id)
            .order_by(TaskExecution.started_at.desc())
            .limit(limit)
        )
        return list(self.session.exec(stmt).all())

    def create(self, execution: TaskExecution) -> TaskExecution:
        """创建执行记录"""
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution

    def update(self, execution: TaskExecution) -> TaskExecution:
        """更新执行记录"""
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution

