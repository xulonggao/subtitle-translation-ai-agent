#!/usr/bin/env python3
"""
API认证管理模块
"""

import os
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import structlog

logger = structlog.get_logger()

class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        # JWT配置
        self.secret_key = os.getenv("JWT_SECRET_KEY", self._generate_secret_key())
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        self.refresh_token_expire_days = 7
        
        # 用户数据库（生产环境应使用真实数据库）
        self.users_db = {
            "admin": {
                "user_id": "user_001",
                "username": "admin",
                "password_hash": self._hash_password("admin123"),
                "email": "admin@example.com",
                "role": "admin",
                "is_active": True,
                "created_at": datetime.now(),
                "last_login": None
            },
            "user": {
                "user_id": "user_002",
                "username": "user",
                "password_hash": self._hash_password("user123"),
                "email": "user@example.com",
                "role": "user",
                "is_active": True,
                "created_at": datetime.now(),
                "last_login": None
            }
        }
        
        # 刷新令牌存储
        self.refresh_tokens = {}
        
        logger.info("认证管理器初始化完成")
    
    def _generate_secret_key(self) -> str:
        """生成密钥"""
        return secrets.token_urlsafe(32)
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        return self._hash_password(password) == password_hash
    
    def _create_access_token(self, user_data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        payload = {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "role": user_data["role"],
            "exp": datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _create_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        payload = {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "exp": datetime.utcnow() + timedelta(days=self.refresh_token_expire_days),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # 存储刷新令牌
        self.refresh_tokens[user_data["user_id"]] = {
            "token": token,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        }
        
        return token
    
    async def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """用户认证"""
        try:
            # 查找用户
            user_data = self.users_db.get(username)
            if not user_data:
                logger.warning("用户不存在", username=username)
                return None
            
            # 检查用户状态
            if not user_data["is_active"]:
                logger.warning("用户已禁用", username=username)
                return None
            
            # 验证密码
            if not self._verify_password(password, user_data["password_hash"]):
                logger.warning("密码错误", username=username)
                return None
            
            # 更新最后登录时间
            user_data["last_login"] = datetime.now()
            
            # 创建令牌
            access_token = self._create_access_token(user_data)
            refresh_token = self._create_refresh_token(user_data)
            
            logger.info("用户认证成功", username=username, user_id=user_data["user_id"])
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
                "user_info": {
                    "user_id": user_data["user_id"],
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "role": user_data["role"]
                }
            }
            
        except Exception as e:
            logger.error("认证过程出错", error=str(e))
            return None
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证访问令牌"""
        try:
            # 解码令牌
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌类型
            if payload.get("type") != "access":
                logger.warning("无效的令牌类型", token_type=payload.get("type"))
                return None
            
            # 检查用户是否存在且激活
            user_id = payload.get("user_id")
            username = payload.get("username")
            
            user_data = None
            for user in self.users_db.values():
                if user["user_id"] == user_id:
                    user_data = user
                    break
            
            if not user_data or not user_data["is_active"]:
                logger.warning("用户不存在或已禁用", user_id=user_id)
                return None
            
            return {
                "user_id": payload["user_id"],
                "username": payload["username"],
                "role": payload["role"]
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("无效的令牌", error=str(e))
            return None
        except Exception as e:
            logger.error("令牌验证出错", error=str(e))
            return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """刷新访问令牌"""
        try:
            # 解码刷新令牌
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌类型
            if payload.get("type") != "refresh":
                logger.warning("无效的刷新令牌类型")
                return None
            
            user_id = payload.get("user_id")
            
            # 检查刷新令牌是否存在且有效
            stored_token = self.refresh_tokens.get(user_id)
            if not stored_token or stored_token["token"] != refresh_token:
                logger.warning("刷新令牌不存在或无效", user_id=user_id)
                return None
            
            # 检查是否过期
            if datetime.utcnow() > stored_token["expires_at"]:
                logger.warning("刷新令牌已过期", user_id=user_id)
                del self.refresh_tokens[user_id]
                return None
            
            # 查找用户数据
            user_data = None
            for user in self.users_db.values():
                if user["user_id"] == user_id:
                    user_data = user
                    break
            
            if not user_data or not user_data["is_active"]:
                logger.warning("用户不存在或已禁用", user_id=user_id)
                return None
            
            # 创建新的访问令牌
            access_token = self._create_access_token(user_data)
            
            logger.info("令牌刷新成功", user_id=user_id)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("刷新令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("无效的刷新令牌", error=str(e))
            return None
        except Exception as e:
            logger.error("令牌刷新出错", error=str(e))
            return None
    
    async def revoke_token(self, user_id: str) -> bool:
        """撤销用户的刷新令牌"""
        try:
            if user_id in self.refresh_tokens:
                del self.refresh_tokens[user_id]
                logger.info("令牌已撤销", user_id=user_id)
                return True
            return False
        except Exception as e:
            logger.error("撤销令牌出错", error=str(e))
            return False
    
    async def create_user(self, username: str, password: str, email: str = None, role: str = "user") -> Optional[Dict[str, Any]]:
        """创建用户"""
        try:
            # 检查用户是否已存在
            if username in self.users_db:
                logger.warning("用户已存在", username=username)
                return None
            
            # 创建用户数据
            user_id = f"user_{len(self.users_db) + 1:03d}"
            user_data = {
                "user_id": user_id,
                "username": username,
                "password_hash": self._hash_password(password),
                "email": email,
                "role": role,
                "is_active": True,
                "created_at": datetime.now(),
                "last_login": None
            }
            
            # 保存用户
            self.users_db[username] = user_data
            
            logger.info("用户创建成功", username=username, user_id=user_id)
            
            return {
                "user_id": user_id,
                "username": username,
                "email": email,
                "role": role,
                "created_at": user_data["created_at"]
            }
            
        except Exception as e:
            logger.error("创建用户出错", error=str(e))
            return None
    
    async def update_user(self, user_id: str, **kwargs) -> bool:
        """更新用户信息"""
        try:
            # 查找用户
            user_data = None
            username = None
            for uname, udata in self.users_db.items():
                if udata["user_id"] == user_id:
                    user_data = udata
                    username = uname
                    break
            
            if not user_data:
                logger.warning("用户不存在", user_id=user_id)
                return False
            
            # 更新允许的字段
            allowed_fields = ["email", "role", "is_active"]
            for field, value in kwargs.items():
                if field in allowed_fields:
                    user_data[field] = value
            
            # 特殊处理密码更新
            if "password" in kwargs:
                user_data["password_hash"] = self._hash_password(kwargs["password"])
            
            logger.info("用户信息更新成功", user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("更新用户信息出错", error=str(e))
            return False
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        try:
            # 查找并删除用户
            username_to_delete = None
            for username, user_data in self.users_db.items():
                if user_data["user_id"] == user_id:
                    username_to_delete = username
                    break
            
            if username_to_delete:
                del self.users_db[username_to_delete]
                # 同时撤销刷新令牌
                await self.revoke_token(user_id)
                logger.info("用户删除成功", user_id=user_id)
                return True
            
            logger.warning("用户不存在", user_id=user_id)
            return False
            
        except Exception as e:
            logger.error("删除用户出错", error=str(e))
            return False
    
    async def list_users(self) -> List[Dict[str, Any]]:
        """获取用户列表"""
        try:
            users = []
            for user_data in self.users_db.values():
                users.append({
                    "user_id": user_data["user_id"],
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "role": user_data["role"],
                    "is_active": user_data["is_active"],
                    "created_at": user_data["created_at"],
                    "last_login": user_data["last_login"]
                })
            
            return users
            
        except Exception as e:
            logger.error("获取用户列表出错", error=str(e))
            return []
    
    def get_user_permissions(self, role: str) -> List[str]:
        """获取用户权限"""
        permissions = {
            "admin": [
                "project:create", "project:read", "project:update", "project:delete",
                "file:upload", "file:download", "file:delete",
                "task:create", "task:read", "task:cancel",
                "user:create", "user:read", "user:update", "user:delete",
                "system:monitor", "system:config"
            ],
            "user": [
                "project:create", "project:read", "project:update",
                "file:upload", "file:download",
                "task:create", "task:read"
            ]
        }
        
        return permissions.get(role, [])
    
    def check_permission(self, user_role: str, permission: str) -> bool:
        """检查用户权限"""
        user_permissions = self.get_user_permissions(user_role)
        return permission in user_permissions