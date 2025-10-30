"""
认证工具模块
包含JWT token生成、验证和密码加密
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# JWT配置
SECRET_KEY = "niar-secret-key-change-in-production-2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """加密密码"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解码JWT令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_from_db(username: str):
    """从数据库获取用户"""
    from sqlmodel import Session, select
    from app.models.db import engine
    from app.models.user import User
    
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        return user


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """认证用户"""
    user = get_user_from_db(username)
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return {
        "username": user.username,
        "role": user.role
    }


def change_user_password(username: str, new_password: str) -> bool:
    """修改用户密码"""
    from sqlmodel import Session, select
    from app.models.db import engine
    from app.models.user import User
    
    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        
        if not user:
            return False
        
        user.hashed_password = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        session.add(user)
        session.commit()
        return True


def init_default_user():
    """初始化默认admin用户"""
    from sqlmodel import Session, select
    from app.models.db import engine
    from app.models.user import User
    import logging
    
    logger = logging.getLogger(__name__)
    
    with Session(engine) as session:
        statement = select(User).where(User.username == "admin")
        existing_user = session.exec(statement).first()
        
        if not existing_user:
            default_user = User(
                username="admin",
                hashed_password=hash_password("000000"),
                role="admin",
                is_active=True
            )
            session.add(default_user)
            session.commit()
            logger.info("✓ 默认admin用户已创建（密码：000000）")
        else:
            logger.info("✓ admin用户已存在")
