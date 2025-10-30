from fastapi import APIRouter, HTTPException
from sqlmodel import Session
from app.models.db import engine
from app.repositories.app_config_repo import AppConfigRepository
from pydantic import BaseModel
import json

router = APIRouter(prefix="/api/settings", tags=["settings"])


class BettercapConfig(BaseModel):
    """Bettercap 配置模型（双实例架构）"""
    url: str  # 向后兼容，默认为scan_url
    scan_url: str = "http://127.0.0.1:8081"  # 扫描实例API地址（端口8081）
    ban_url: str = "http://127.0.0.1:8082"  # Ban实例API地址（端口8082）
    username: str
    password: str
    probe_throttle: int = 5  # 探测间隔（秒），默认 5
    probe_mode: str = 'active'  # 探测模式：active（主动）/passive（被动），默认 active


@router.get("/bettercap")
def get_bettercap_config():
    """获取 Bettercap 全局配置（双实例架构）"""
    # 默认配置
    default_config = {
        "url": "http://127.0.0.1:8081",
        "scan_url": "http://127.0.0.1:8081",
        "ban_url": "http://127.0.0.1:8082",
        "username": "user",
        "password": "pass",
        "probe_throttle": 5,
        "probe_mode": "active"
    }
    
    with Session(engine) as session:
        repo = AppConfigRepository(session)
        config = repo.get_by_key("bettercap_config")
        if config:
            saved_config = json.loads(config.value)
            # 合并配置，确保新字段有默认值
            merged_config = {**default_config, **saved_config}
            # 确保url字段与scan_url保持同步（向后兼容）
            if "scan_url" in merged_config:
                merged_config["url"] = merged_config["scan_url"]
            return merged_config
        # 返回默认配置
        return default_config


@router.post("/bettercap")
async def save_bettercap_config(config: BettercapConfig):
    """保存 Bettercap 全局配置，并自动重启所有运行中的 Bettercap 任务"""
    from app.repositories.scheduled_task_repo import ScheduledTaskRepository
    from app.repositories.system_event_log_repo import SystemEventLogRepository
    from app.services.scheduler_service import (
        stop_bettercap_continuous_monitoring,
        start_bettercap_continuous_monitoring,
        reload_task
    )
    import asyncio
    import logging
    
    logger = logging.getLogger(__name__)
    
    with Session(engine) as session:
        repo = AppConfigRepository(session)
        repo.upsert(
            "bettercap_config",
            json.dumps(config.dict()),
            "Bettercap REST API 配置"
        )
        
        # 查找所有启用的 Bettercap 任务
        task_repo = ScheduledTaskRepository(session)
        all_tasks = task_repo.get_all()
        bettercap_tasks = [t for t in all_tasks if t.scan_tool == 'bettercap' and t.enabled]
        
        if bettercap_tasks:
            logger.info(f"配置已保存，准备重启 {len(bettercap_tasks)} 个 Bettercap 任务")
            
            restarted_tasks = []
            for task in bettercap_tasks:
                try:
                    # 停止任务
                    logger.info(f"停止任务 {task.id}: {task.name}")
                    stop_bettercap_continuous_monitoring(task.id)
                    
                    # 等待一下确保完全停止
                    await asyncio.sleep(1)
                    
                    # 重新启动任务
                    logger.info(f"重新启动任务 {task.id}: {task.name}")
                    cidrs = json.loads(task.cidrs)
                    loop = asyncio.get_event_loop()
                    
                    # 导入必要的变量
                    from app.services.scheduler_service import _bettercap_continuous_tasks
                    
                    continuous_task = loop.create_task(
                        start_bettercap_continuous_monitoring(task.id, cidrs)
                    )
                    _bettercap_continuous_tasks[task.id] = continuous_task
                    
                    restarted_tasks.append(task.name)
                    logger.info(f"任务 {task.id} 已重启")
                except Exception as e:
                    logger.error(f"重启任务 {task.id} 失败: {e}")
            
            if restarted_tasks:
                # 记录系统事件日志
                event_repo = SystemEventLogRepository(session)
                event_repo.create(
                    event_type="bettercap_config_restart",
                    message=f"Bettercap配置更新，重启了{len(restarted_tasks)}个任务",
                    details=json.dumps({"restarted_tasks": restarted_tasks, "task_count": len(restarted_tasks)}),
                    severity="info"
                )
                return {
                    "message": "配置已保存并重启任务",
                    "restarted_tasks": restarted_tasks,
                    "count": len(restarted_tasks)
                }
        
        return {"message": "配置已保存"}

