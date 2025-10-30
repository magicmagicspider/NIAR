import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.devices import router as devices_router
from app.api.scan import router as scan_router
from app.api.scheduled_tasks import router as tasks_router
from app.api.settings import router as settings_router
from app.api.arp_ban import router as arp_ban_router
from app.api.system_logs import router as system_logs_router
from app.api.auth import router as auth_router
from app.models.db import init_db
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.api.ip_requests import router as ip_requests_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log')
    ]
)
logger = logging.getLogger(__name__)


def _migrate_bettercap_config():
    """配置迁移：为现有Bettercap配置添加双实例URL"""
    try:
        from sqlmodel import Session
        from app.models.db import engine
        from app.repositories.app_config_repo import AppConfigRepository
        import json
        
        with Session(engine) as session:
            config_repo = AppConfigRepository(session)
            config = config_repo.get_by_key("bettercap_config")
            
            if config:
                config_dict = json.loads(config.value)
                modified = False
                
                # 如果没有scan_url，从url迁移或使用默认值
                if 'scan_url' not in config_dict:
                    config_dict['scan_url'] = config_dict.get('url', 'http://127.0.0.1:8081')
                    logger.info(f"[Config Migration] 添加 scan_url: {config_dict['scan_url']}")
                    modified = True
                
                # 如果没有ban_url，添加默认值
                if 'ban_url' not in config_dict:
                    config_dict['ban_url'] = 'http://127.0.0.1:8082'
                    logger.info(f"[Config Migration] 添加 ban_url: {config_dict['ban_url']}")
                    modified = True
                
                # 保存修改
                if modified:
                    config.value = json.dumps(config_dict)
                    session.add(config)
                    session.commit()
                    logger.info("[Config Migration] Bettercap配置已更新（双实例支持）")
            else:
                logger.info("[Config Migration] 未找到Bettercap配置，跳过迁移")
    except Exception as e:
        logger.error(f"[Config Migration] 配置迁移失败: {e}")


def create_app() -> FastAPI:
    app = FastAPI(title="NIAR API", version="0.1.0", description="Network Infrastructure Asset Registry")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    app.include_router(auth_router, prefix="/api/auth", tags=["认证"])
    app.include_router(devices_router)
    app.include_router(scan_router)
    app.include_router(tasks_router)
    app.include_router(settings_router)
    app.include_router(arp_ban_router, prefix="/api/arp-ban", tags=["网络管控"])
    app.include_router(system_logs_router, prefix="/api")
    app.include_router(ip_requests_router)

    @app.on_event("startup")
    def _on_startup():
        import os
        logger.info("=" * 60)
        logger.info("Application starting up...")
        logger.info(f"Process ID: {os.getpid()}")
        logger.info(f"Worker Info: Single worker mode (recommended for state consistency)")
        logger.info("=" * 60)
        init_db()
        logger.info("Database initialized")
        
        # 初始化默认用户
        from app.utils.auth import init_default_user
        init_default_user()
        logger.info("Default user initialized")
        
        # 配置迁移：添加ban_url到现有配置
        _migrate_bettercap_config()
        
        start_scheduler()
        logger.info("Scheduler startup completed")

    @app.on_event("shutdown")
    def _on_shutdown():
        logger.info("Application shutting down...")
        stop_scheduler()
        logger.info("Shutdown completed")

    return app


app = create_app()


