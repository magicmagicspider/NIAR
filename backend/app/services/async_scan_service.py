import asyncio
import json
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from sqlmodel import Session

from app.models.scan_task import ScanTask
from app.repositories.scan_task_repo import ScanTaskRepository
from app.services.scan_service import upsert_devices_with_info, _parse_nmap_output
from app.services.bettercap_service import scan_bettercap
from app.utils.cidr import expand_cidr

logger = logging.getLogger(__name__)

# 全局任务存储（内存中，用于快速访问）
_running_tasks: Dict[str, asyncio.Task] = {}


async def scan_nmap_realtime(
    targets: List[str], 
    nmap_args: Optional[str],
    task_id: str,
    repo: 'ScanTaskRepository'
) -> Tuple[Dict[str, Dict[str, Optional[str]]], str]:
    """
    实时读取 nmap 输出的扫描函数
    
    与 scan_nmap 的区别：
    - 逐行读取输出，实时更新到数据库
    - 前端轮询时能看到实时输出
    """
    nmap_bin = shutil.which("nmap")
    if not nmap_bin:
        raise RuntimeError("nmap not found")
    
    # 构建 nmap 命令
    cmd = [nmap_bin]
    
    # 添加必要的参数以确保实时输出
    # --stats-every: 每1秒输出一次统计信息
    # -v: verbose 模式，输出详细信息
    # --reason: 显示端口状态原因
    cmd.extend(['--stats-every', '1s', '-v'])
    
    if nmap_args:
        # 用户自定义参数，但保留 --stats-every 和 -v
        cmd.extend(nmap_args.split())
    else:
        cmd.extend(["-sn"])
    
    cmd.extend(targets)
    
    # 执行 nmap，合并 stdout 和 stderr
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,  # 合并到 stdout
    )
    
    # 实时读取输出
    output_lines = []
    last_update_time = 0
    import time
    
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        
        decoded_line = line.decode('utf-8', errors='ignore')
        output_lines.append(decoded_line)
        
        # 每隔 0.5 秒更新一次数据库，避免过于频繁
        # 或者积累了 10 行以上也更新
        current_time = time.time()
        should_update = (
            current_time - last_update_time >= 0.5 or  # 0.5秒间隔
            len(output_lines) % 10 == 0  # 或每10行
        )
        
        if should_update:
            from app.models.db import engine
            with Session(engine) as session:
                task_repo = ScanTaskRepository(session)
                task = task_repo.get_by_task_id(task_id)
                if task:
                    # 限制输出大小，避免数据库过大
                    current_output = ''.join(output_lines)
                    task.raw_output = current_output[-50000:] if len(current_output) > 50000 else current_output
                    task_repo.update(task)
            last_update_time = current_time
    
    # 等待进程结束
    await proc.wait()
    
    # 最后确保更新一次完整输出
    from app.models.db import engine
    raw_output = ''.join(output_lines)
    with Session(engine) as session:
        task_repo = ScanTaskRepository(session)
        task = task_repo.get_by_task_id(task_id)
        if task:
            task.raw_output = raw_output[-50000:] if len(raw_output) > 50000 else raw_output
            task_repo.update(task)
    
    if proc.returncode != 0:
        raise RuntimeError(f"nmap exited with code {proc.returncode}")
    
    # 解析完整输出
    parsed_results = _parse_nmap_output(raw_output)
    
    return parsed_results, raw_output


async def execute_scan_task(
    task_id: str, 
    cidrs: List[str], 
    scan_tool: str = "nmap",
    nmap_args: str = None,
    bettercap_url: str = None,
    bettercap_username: str = "user",
    bettercap_password: str = "pass",
    bettercap_duration: int = 60
):
    """
    执行异步扫描任务
    
    这个函数在后台运行，不会阻塞 API 响应
    """
    from app.models.db import engine
    
    logger.info(f"[Task {task_id}] Starting scan")
    logger.info(f"  CIDRs: {cidrs}")
    logger.info(f"  Scan tool: {scan_tool}")
    if scan_tool == "nmap":
        logger.info(f"  Nmap args: {nmap_args or 'default'}")
    else:
        logger.info(f"  Bettercap URL: {bettercap_url}")
        logger.info(f"  Bettercap duration: {bettercap_duration}s")
    
    # 创建新的 session（后台任务需要独立的数据库连接）
    with Session(engine) as session:
        repo = ScanTaskRepository(session)
        task = repo.get_by_task_id(task_id)
        
        if not task:
            logger.error(f"[Task {task_id}] Task not found in database")
            return
        
        try:
            # 更新状态为 running
            task.status = "running"
            task.started_at = datetime.now()
            task.progress = 5
            repo.update(task)
            
            # 根据扫描工具类型执行不同的扫描
            if scan_tool == "bettercap":
                # 使用 bettercap 扫描
                parsed_results = await execute_bettercap_scan(
                    task_id, cidrs, bettercap_url, 
                    bettercap_username, bettercap_password, 
                    bettercap_duration, repo, task
                )
                raw_output = f"Bettercap scan completed. Found {len(parsed_results)} hosts."
            else:
                # 使用 nmap 扫描（默认）
                parsed_results, raw_output = await execute_nmap_scan(
                    task_id, cidrs, nmap_args, repo, task
                )
            
            task.progress = 70
            task.raw_output = raw_output[-50000:] if len(raw_output) > 50000 else raw_output
            repo.update(task)
            
            logger.info(f"[Task {task_id}] Scan completed, found {len(parsed_results)} online hosts")
            
            # 更新设备数据库
            task.progress = 80
            repo.update(task)
            
            total_count, new_count, offline_count = upsert_devices_with_info(
                session=session,
                devices_info=parsed_results,
                mark_offline=True,  # 手动扫描也要标记离线设备
                target_cidrs=cidrs,
                scan_tool=scan_tool  # 传递扫描工具类型
            )
            
            # 更新任务统计
            task.status = "completed"
            task.progress = 100
            task.completed_at = datetime.now()
            task.online_count = len(parsed_results)  # 在线设备数
            task.new_count = new_count
            task.offline_count = offline_count
            repo.update(task)
            
            logger.info(f"[Task {task_id}] Task completed successfully")
            logger.info(f"  Online: {task.online_count}, New: {task.new_count}")
            
        except Exception as e:
            logger.error(f"[Task {task_id}] Task failed: {str(e)}", exc_info=True)
            task.status = "failed"
            task.error_message = str(e)[:1000]  # 限制错误信息长度
            task.completed_at = datetime.now()
            repo.update(task)
        
        finally:
            # 从运行列表中移除
            if task_id in _running_tasks:
                del _running_tasks[task_id]


async def execute_nmap_scan(
    task_id: str,
    cidrs: List[str],
    nmap_args: str,
    repo: 'ScanTaskRepository',
    task: ScanTask
) -> Tuple[Dict[str, Dict[str, Optional[str]]], str]:
    """执行 nmap 扫描"""
    # 展开所有 CIDR
    all_hosts = []
    for cidr in cidrs:
        all_hosts.extend(expand_cidr(cidr))
    
    task.total_hosts = len(all_hosts)
    task.progress = 10
    repo.update(task)
    
    logger.info(f"[Task {task_id}] Total hosts to scan: {len(all_hosts)}")
    
    # 执行 nmap 扫描（实时读取输出）
    task.progress = 20
    repo.update(task)
    
    # 使用实时扫描函数，每读取一行就更新数据库
    parsed_results, raw_output = await scan_nmap_realtime(all_hosts, nmap_args, task_id, repo)
    
    return parsed_results, raw_output


async def execute_bettercap_scan(
    task_id: str,
    cidrs: List[str],
    bettercap_url: str,
    username: str,
    password: str,
    duration: int,
    repo: 'ScanTaskRepository',
    task: ScanTask
) -> Dict[str, Dict[str, Optional[str]]]:
    """执行 bettercap 扫描"""
    from app.utils.cidr import expand_cidrs
    
    # 展开 CIDR 计算总主机数
    all_hosts = expand_cidrs(cidrs)
    task.total_hosts = len(all_hosts)
    task.progress = 10
    repo.update(task)
    
    logger.info(f"[Task {task_id}] Total hosts in range: {len(all_hosts)}")
    
    # 定义进度回调函数
    def update_progress(progress: int, message: str):
        from app.models.db import engine
        with Session(engine) as session:
            task_repo = ScanTaskRepository(session)
            t = task_repo.get_by_task_id(task_id)
            if t:
                t.progress = progress
                # 将 bettercap 的消息追加到 raw_output
                if t.raw_output:
                    t.raw_output += f"\n{message}"
                else:
                    t.raw_output = message
                # 限制输出大小
                if len(t.raw_output) > 50000:
                    t.raw_output = t.raw_output[-50000:]
                task_repo.update(t)
    
    # 执行 bettercap 扫描
    parsed_results = await scan_bettercap(
        target_cidrs=cidrs,
        bettercap_url=bettercap_url,
        username=username,
        password=password,
        scan_duration=duration,
        progress_callback=update_progress
    )
    
    return parsed_results


def start_scan_task(
    cidrs: List[str], 
    scan_tool: str = "nmap",
    nmap_args: str = None,
    bettercap_url: str = None,
    bettercap_username: str = "user",
    bettercap_password: str = "pass",
    bettercap_duration: int = 60
) -> str:
    """
    启动一个新的扫描任务（立即返回任务ID）
    
    Args:
        cidrs: CIDR 列表
        scan_tool: 扫描工具 ("nmap" 或 "bettercap")
        nmap_args: nmap 参数
        bettercap_url: bettercap REST API 地址
        bettercap_username: bettercap 用户名
        bettercap_password: bettercap 密码
        bettercap_duration: bettercap 扫描持续时间（秒）
        
    Returns:
        task_id: 任务ID
    """
    from app.models.db import engine
    
    # 生成任务ID
    task_id = str(uuid4())
    
    # 创建任务记录
    with Session(engine) as session:
        repo = ScanTaskRepository(session)
        task = ScanTask(
            task_id=task_id,
            cidrs=json.dumps(cidrs),
            scan_tool=scan_tool,
            nmap_args=nmap_args,
            bettercap_url=bettercap_url,
            bettercap_duration=bettercap_duration,
            status="pending",
            progress=0
        )
        repo.create(task)
    
    # 创建后台任务
    asyncio_task = asyncio.create_task(
        execute_scan_task(
            task_id, cidrs, scan_tool, nmap_args,
            bettercap_url, bettercap_username, bettercap_password,
            bettercap_duration
        )
    )
    _running_tasks[task_id] = asyncio_task
    
    logger.info(f"[Task {task_id}] Created and started with {scan_tool}")
    
    return task_id


def get_task_status(task_id: str) -> dict:
    """
    获取任务状态
    
    Returns:
        任务状态字典，包含所有任务信息
    """
    from app.models.db import engine
    
    with Session(engine) as session:
        repo = ScanTaskRepository(session)
        task = repo.get_by_task_id(task_id)
        
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "cidrs": json.loads(task.cidrs),
            "nmap_args": task.nmap_args,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "total_hosts": task.total_hosts,
            "online_count": task.online_count,
            "offline_count": task.offline_count,
            "new_count": task.new_count,
            "error_message": task.error_message,
            "raw_output": task.raw_output
        }


def get_recent_tasks(limit: int = 50) -> List[dict]:
    """获取最近的任务列表"""
    from app.models.db import engine
    
    with Session(engine) as session:
        repo = ScanTaskRepository(session)
        tasks = repo.get_recent(limit)
        
        return [
            {
                "task_id": task.task_id,
                "status": task.status,
                "progress": task.progress,
                "cidrs": json.loads(task.cidrs),
                "nmap_args": task.nmap_args,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "total_hosts": task.total_hosts,
                "online_count": task.online_count,
                "new_count": task.new_count,
                "error_message": task.error_message
            }
            for task in tasks
        ]

