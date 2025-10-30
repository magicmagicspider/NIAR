from datetime import datetime
from sqlmodel import Session, select
from app.models.app_config import AppConfig
from typing import Optional


class AppConfigRepository:
    """应用配置仓库"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_by_key(self, key: str) -> Optional[AppConfig]:
        """根据键获取配置"""
        return self.session.exec(
            select(AppConfig).where(AppConfig.key == key)
        ).first()
    
    def upsert(self, key: str, value: str, description: str = None) -> AppConfig:
        """创建或更新配置"""
        config = self.get_by_key(key)
        if config:
            config.value = value
            if description:
                config.description = description
            config.updated_at = datetime.now()
            self.session.add(config)
        else:
            config = AppConfig(
                key=key, 
                value=value, 
                description=description,
                updated_at=datetime.now()
            )
            self.session.add(config)
        self.session.commit()
        self.session.refresh(config)
        return config
    
    def delete(self, key: str) -> bool:
        """删除配置"""
        config = self.get_by_key(key)
        if config:
            self.session.delete(config)
            self.session.commit()
            return True
        return False

