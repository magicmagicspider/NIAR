import asyncio
import json
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.models.db import get_session
from app.models.scheduled_task import ScheduledTask
from app.repositories.scheduled_task_repo import ScheduledTaskRepository
from app.repositories.task_execution_repo import TaskExecutionRepository
from app.repositories.app_config_repo import AppConfigRepository
from app.services.scheduler_service import (
    validate_cron_expression,
    reload_task,
    remove_task,
    execute_scheduled_task,
    get_scheduler_status,
    get_bettercap_task_logs
)


router = APIRouter(prefix="/api/tasks", tags=["scheduled_tasks"])


@router.get("/scheduler/status")
async def scheduler_status():
    """获取调度器状态"""
    return get_scheduler_status()


class TaskCreate(BaseModel):
    name: str
    cidrs: List[str]
    scan_tool: str = "nmap"  # nmap 或 bettercap
    nmap_args: str | None = None
    bettercap_duration: int | None = None
    cron_expression: str
    enabled: bool = True


class TaskUpdate(BaseModel):
    name: str | None = None
    cidrs: List[str] | None = None
    scan_tool: str | None = None
    nmap_args: str | None = None
    bettercap_duration: int | None = None
    cron_expression: str | None = None
    enabled: bool | None = None


@router.get("/")
async def list_tasks(session: Session = Depends(get_session)):
    """获取所有定时任务"""
    repo = ScheduledTaskRepository(session)
    tasks = repo.get_all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "cidrs": json.loads(t.cidrs),
            "scan_tool": t.scan_tool,
            "nmap_args": t.nmap_args,
            "bettercap_duration": t.bettercap_duration,
            "cron_expression": t.cron_expression,
            "enabled": t.enabled,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
            "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None
        }
        for t in tasks
    ]


@router.post("/")
async def create_task(req: TaskCreate, session: Session = Depends(get_session)):
    """创建定时任务"""
    # 验证 cron 表达式
    if not validate_cron_expression(req.cron_expression):
        raise HTTPException(status_code=400, detail="Invalid cron expression")
    
    repo = ScheduledTaskRepository(session)
    
    # 检查 Bettercap 任务唯一性：如果是 Bettercap 且启用，检查是否已有其他启用的 Bettercap 任务
    if req.scan_tool == "bettercap" and req.enabled:
        existing_tasks = repo.get_all()
        for t in existing_tasks:
            if t.scan_tool == "bettercap" and t.enabled:
                raise HTTPException(
                    status_code=400,
                    detail=f"已存在启用的 Bettercap 任务「{t.name}」，同时只能运行一个 Bettercap 任务。请先禁用或删除现有任务。"
                )
    
    # 如果是 Bettercap 任务，检查配置是否存在
    if req.scan_tool == "bettercap":
        config_repo = AppConfigRepository(session)
        config = config_repo.get_by_key("bettercap_config")
        if not config:
            raise HTTPException(
                status_code=400,
                detail="请先在「设置」页面配置 Bettercap 全局参数后再创建任务"
            )
    
    task = ScheduledTask(
        name=req.name,
        cidrs=json.dumps(req.cidrs),
        scan_tool=req.scan_tool,
        nmap_args=req.nmap_args,
        bettercap_duration=req.bettercap_duration,
        cron_expression=req.cron_expression,
        enabled=req.enabled,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    task = repo.create(task)
    
    # 如果启用，添加到调度器
    if task.enabled:
        reload_task(task.id)
    
    return {"success": True, "task_id": task.id}


@router.put("/{task_id}")
async def update_task(
    task_id: int, 
    req: TaskUpdate, 
    session: Session = Depends(get_session)
):
    """更新定时任务"""
    repo = ScheduledTaskRepository(session)
    task = repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 验证 cron 表达式（如果提供）
    if req.cron_expression and not validate_cron_expression(req.cron_expression):
        raise HTTPException(status_code=400, detail="Invalid cron expression")
    
    # 检查 Bettercap 任务唯一性
    # 判断更新后是否会成为启用的 Bettercap 任务
    will_be_bettercap = req.scan_tool if req.scan_tool is not None else task.scan_tool
    will_be_enabled = req.enabled if req.enabled is not None else task.enabled
    
    if will_be_bettercap == "bettercap" and will_be_enabled:
        # 检查是否已有其他启用的 Bettercap 任务
        existing_tasks = repo.get_all()
        for t in existing_tasks:
            if t.id != task_id and t.scan_tool == "bettercap" and t.enabled:
                raise HTTPException(
                    status_code=400,
                    detail=f"已存在启用的 Bettercap 任务「{t.name}」，同时只能运行一个 Bettercap 任务。请先禁用或删除现有任务。"
                )
    
    # 更新字段
    if req.name is not None:
        task.name = req.name
    if req.cidrs is not None:
        task.cidrs = json.dumps(req.cidrs)
    if req.scan_tool is not None:
        task.scan_tool = req.scan_tool
    if req.nmap_args is not None:
        task.nmap_args = req.nmap_args
    if req.bettercap_duration is not None:
        task.bettercap_duration = req.bettercap_duration
    if req.cron_expression is not None:
        task.cron_expression = req.cron_expression
    if req.enabled is not None:
        task.enabled = req.enabled
    
    repo.update(task)
    
    # 重新加载调度
    reload_task(task_id)
    
    return {"success": True}


@router.delete("/{task_id}")
async def delete_task(task_id: int, session: Session = Depends(get_session)):
    """删除定时任务"""
    repo = ScheduledTaskRepository(session)
    
    if not repo.get_by_id(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 从调度器中移除
    remove_task(task_id)
    
    # 删除任务
    repo.delete(task_id)
    
    return {"success": True}


@router.post("/{task_id}/toggle")
async def toggle_task(task_id: int, session: Session = Depends(get_session)):
    """启用/禁用任务"""
    repo = ScheduledTaskRepository(session)
    task = repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 如果要启用 Bettercap 任务，检查唯一性
    if not task.enabled and task.scan_tool == "bettercap":
        existing_tasks = repo.get_all()
        for t in existing_tasks:
            if t.id != task_id and t.scan_tool == "bettercap" and t.enabled:
                raise HTTPException(
                    status_code=400,
                    detail=f"已存在启用的 Bettercap 任务「{t.name}」，同时只能运行一个 Bettercap 任务。请先禁用或删除现有任务。"
                )
    
    # 切换状态
    task.enabled = not task.enabled
    repo.update(task)
    
    # 重新加载调度
    reload_task(task_id)
    
    return {"success": True, "enabled": task.enabled}


@router.post("/{task_id}/trigger")
async def trigger_task(task_id: int, session: Session = Depends(get_session)):
    """手动触发任务执行"""
    repo = ScheduledTaskRepository(session)
    task = repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 在后台执行任务
    asyncio.create_task(execute_scheduled_task(task_id))
    
    return {"success": True, "message": "Task triggered"}


@router.get("/{task_id}/executions")
async def get_task_executions(
    task_id: int, 
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """获取任务执行历史"""
    # 验证任务是否存在
    task_repo = ScheduledTaskRepository(session)
    task = task_repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 如果是 Bettercap 任务，返回友好格式的实时日志（作为"历史"）
    if task.scan_tool == "bettercap":
        logs = get_bettercap_task_logs(task_id, log_type="friendly")
        status = get_scheduler_status()
        is_running = task_id in status.get("bettercap_tasks", [])
        
        # 将日志包装成类似执行历史的格式
        return [{
            "id": 1,
            "task_id": task_id,
            "started_at": task.last_run_at.isoformat() if task.last_run_at else None,
            "completed_at": None,  # 持续运行中
            "status": "running" if is_running else "stopped",
            "online_count": 0,
            "offline_count": 0,
            "new_count": 0,
            "error_message": None,
            "duration": None,
            "logs": logs,  # 添加友好格式的日志
            "scan_tool": "bettercap"
        }]
    
    # Nmap 任务：获取执行历史
    exec_repo = TaskExecutionRepository(session)
    executions = exec_repo.get_by_task_id(task_id, limit)
    
    return [
        {
            "id": e.id,
            "task_id": e.task_id,
            "started_at": e.started_at.isoformat(),
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "status": e.status,
            "online_count": e.online_count,
            "offline_count": e.offline_count,
            "new_count": e.new_count,
            "error_message": e.error_message,
            "duration": (
                (e.completed_at - e.started_at).total_seconds() 
                if e.completed_at else None
            ),
            "scan_tool": "nmap"
        }
        for e in executions
    ]


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: int,
    session: Session = Depends(get_session)
):
    """获取任务日志（Bettercap 持续监控日志或 Nmap 最后一次执行日志）"""
    # 验证任务是否存在
    task_repo = ScheduledTaskRepository(session)
    task = task_repo.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.scan_tool == "bettercap":
        # Bettercap 任务：返回持续监控的实时日志
        logs = get_bettercap_task_logs(task_id)
        status = get_scheduler_status()
        is_running = task_id in status.get("bettercap_tasks", [])
        return {
            "task_id": task_id,
            "task_name": task.name,
            "scan_tool": "bettercap",
            "log_type": "continuous",
            "logs": logs,
            "is_running": is_running
        }
    else:
        # Nmap 任务：返回最后一次执行记录的输出
        exec_repo = TaskExecutionRepository(session)
        executions = exec_repo.get_by_task_id(task_id, limit=1)
        
        if not executions:
            return {
                "task_id": task_id,
                "task_name": task.name,
                "scan_tool": "nmap",
                "log_type": "last_execution",
                "logs": ["任务尚未执行过"],
                "last_execution": None
            }
        
        last_exec = executions[0]
        # 构建日志输出
        logs = []
        logs.append(f"执行时间: {last_exec.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        logs.append(f"状态: {last_exec.status}")
        if last_exec.completed_at:
            duration = (last_exec.completed_at - last_exec.started_at).total_seconds()
            logs.append(f"耗时: {duration:.2f} 秒")
        logs.append(f"在线设备: {last_exec.online_count}")
        logs.append(f"离线设备: {last_exec.offline_count}")
        logs.append(f"新增设备: {last_exec.new_count}")
        logs.append("")
        
        # 添加Nmap原始输出
        if last_exec.raw_output:
            logs.append("=" * 50)
            logs.append("Nmap 扫描输出:")
            logs.append("=" * 50)
            logs.extend(last_exec.raw_output.split('\n'))
        
        if last_exec.error_message:
            logs.append("")
            logs.append("=" * 50)
            logs.append("❌ 错误信息:")
            logs.append("=" * 50)
            logs.append(last_exec.error_message)
        
        return {
            "task_id": task_id,
            "task_name": task.name,
            "scan_tool": "nmap",
            "log_type": "last_execution",
            "logs": logs,
            "last_execution": {
                "started_at": last_exec.started_at.isoformat(),
                "completed_at": last_exec.completed_at.isoformat() if last_exec.completed_at else None,
                "status": last_exec.status
            }
        }


@router.get("/{task_id}/bettercap-status")
async def get_bettercap_task_status(task_id: int, session: Session = Depends(get_session)):
    """获取 Bettercap 任务的实际运行状态（从 Bettercap API 读取）"""
    import httpx
    from app.repositories.app_config_repo import AppConfigRepository
    
    # 获取任务信息
    task_repo = ScheduledTaskRepository(session)
    task = task_repo.get_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task.scan_tool != "bettercap":
        raise HTTPException(status_code=400, detail="只支持 Bettercap 任务")
    
    # 获取 Bettercap 配置
    config_repo = AppConfigRepository(session)
    config = config_repo.get_by_key("bettercap_config")
    
    if not config:
        # 配置不存在时返回错误状态
        return {
            "task_id": task_id,
            "task_enabled": task.enabled,
            "bettercap_connected": False,
            "probe_mode": None,
            "mode_display": "未配置",
            "error": "Bettercap 未配置，请先在设置页面配置"
        }
    
    config_dict = json.loads(config.value)
    # 使用scan_url（扫描实例），向后兼容url字段
    bettercap_url = config_dict.get('scan_url', config_dict.get('url', 'http://127.0.0.1:8081'))
    username = config_dict.get('username', 'user')
    password = config_dict.get('password', 'pass')
    
    # 查询 Bettercap 实际运行状态
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{bettercap_url}/api/session",
                auth=(username, password)
            )
            
            if response.status_code != 200:
                return {
                    "task_id": task_id,
                    "task_enabled": task.enabled,
                    "bettercap_connected": False,
                    "probe_mode": None,
                    "error": f"Bettercap API 返回错误: {response.status_code}"
                }
            
            session_data = response.json()
            modules = session_data.get('modules', [])
            
            # 检查哪些模块在运行
            probe_running = False
            recon_running = False
            
            for module in modules:
                if isinstance(module, dict):
                    name = module.get('name', '')
                    running = module.get('running', False)
                    
                    if name == 'net.probe' and running:
                        probe_running = True
                    elif name == 'net.recon' and running:
                        recon_running = True
            
            # 判断模式
            if probe_running and recon_running:
                actual_mode = 'active'
                mode_display = '主动探测'
            elif recon_running and not probe_running:
                actual_mode = 'passive'
                mode_display = '被动侦察'
            elif not recon_running and not probe_running:
                actual_mode = None
                mode_display = '未运行'
            else:
                actual_mode = 'unknown'
                mode_display = '未知状态'
            
            # 获取探测参数
            env = session_data.get('env', {})
            probe_throttle = env.get('net.probe.throttle', None)
            
            return {
                "task_id": task_id,
                "task_enabled": task.enabled,
                "bettercap_connected": True,
                "probe_mode": actual_mode,
                "mode_display": mode_display,
                "modules": {
                    "net_probe": probe_running,
                    "net_recon": recon_running
                },
                "probe_throttle": probe_throttle,
                "configured_mode": config_dict.get('probe_mode', 'active')
            }
            
    except httpx.TimeoutException:
        return {
            "task_id": task_id,
            "task_enabled": task.enabled,
            "bettercap_connected": False,
            "probe_mode": None,
            "error": "连接 Bettercap 超时"
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "task_enabled": task.enabled,
            "bettercap_connected": False,
            "probe_mode": None,
            "error": str(e)
        }

