from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
import asyncio

from app.models.db import get_session
from app.services.scan_service import (
    scan_ping, 
    scan_nmap, 
    upsert_devices, 
    upsert_devices_with_info
)
from app.services.async_scan_service import (
    start_scan_task,
    get_task_status,
    get_recent_tasks
)
from app.utils.cidr import expand_cidrs


router = APIRouter(prefix="/api/scan", tags=["scan"])


class ScanRequest(BaseModel):
    cidrs: List[str]
    concurrency: int = 128
    timeout: float = 1.0
    scan_tool: str = "nmap"  # 扫描工具: "nmap" 或 "bettercap"
    nmap_args: Optional[str] = None  # 自定义 nmap 参数
    
    # Bettercap 配置
    bettercap_url: Optional[str] = None
    bettercap_username: str = "user"
    bettercap_password: str = "pass"
    bettercap_duration: int = 60  # 扫描持续时间（秒）


@router.post("/start")
async def start_scan(req: ScanRequest):
    """
    启动异步扫描任务（立即返回任务ID，不等待扫描完成）
    
    - 支持 nmap 和 bettercap 两种扫描工具
    - nmap: 详细扫描，支持 OS 检测，但跨网段较慢
    - bettercap: 快速发现，跨网段扫描快，自动探测多种协议
    - 任务在后台执行，前端通过轮询 /scan/status/{task_id} 查询进度
    """
    try:
        # 验证 bettercap 配置
        if req.scan_tool == "bettercap":
            if not req.bettercap_url:
                raise HTTPException(
                    status_code=400, 
                    detail="使用 bettercap 时必须提供 bettercap_url"
                )
        
        task_id = start_scan_task(
            cidrs=req.cidrs,
            scan_tool=req.scan_tool,
            nmap_args=req.nmap_args,
            bettercap_url=req.bettercap_url,
            bettercap_username=req.bettercap_username,
            bettercap_password=req.bettercap_password,
            bettercap_duration=req.bettercap_duration
        )
        
        if req.scan_tool == "bettercap":
            message = f"Bettercap 扫描任务已启动（{req.bettercap_duration}秒）"
        else:
            message = "Nmap 扫描任务已启动"
        
        return {
            "task_id": task_id,
            "status": "started",
            "message": message,
            "scan_tool": req.scan_tool,
            "nmap_args": req.nmap_args if req.scan_tool == "nmap" else None,
            "bettercap_duration": req.bettercap_duration if req.scan_tool == "bettercap" else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动扫描任务失败: {str(e)}")


@router.get("/status/{task_id}")
async def get_scan_status(task_id: str):
    """
    查询扫描任务状态
    
    返回任务的实时状态、进度和结果
    """
    task_status = get_task_status(task_id)
    if not task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_status


@router.get("/tasks")
async def list_scan_tasks(limit: int = 50):
    """
    获取最近的扫描任务列表
    """
    return get_recent_tasks(limit)


