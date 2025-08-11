#!/usr/bin/env python3
"""
API速率限制模块
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from collections import defaultdict, deque
import structlog

logger = structlog.get_logger()

class RateLimiter:
    """速率限制器"""
    
    def __init__(self):
        # 速率限制配置
        self.rate_limits = {
            "default": {
                "requests_per_minute": 60,
                "requests_per_hour": 1000,
                "requests_per_day": 10000
            },
            "admin": {
                "requests_per_minute": 120,
                "requests_per_hour": 2000,
                "requests_per_day": 20000
            },
            "premium": {
                "requests_per_minute": 100,
                "requests_per_hour": 1500,
                "requests_per_day": 15000
            }
        }
        
        # 请求记录存储
        self.request_records = defaultdict(lambda: {
            "minute": deque(),
            "hour": deque(),
            "day": deque()
        })
        
        # 黑名单
        self.blacklist = set()
        
        # 白名单
        self.whitelist = set()
        
        # 清理任务
        self.cleanup_task = None
        self.start_cleanup_task()
        
        logger.info("速率限制器初始化完成")
    
    def start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_old_records():
            while True:
                try:
                    await self.cleanup_old_records()
                    await asyncio.sleep(300)  # 每5分钟清理一次
                except Exception as e:
                    logger.error("清理任务出错", error=str(e))
                    await asyncio.sleep(60)
        
        self.cleanup_task = asyncio.create_task(cleanup_old_records())
    
    async def cleanup_old_records(self):
        """清理过期记录"""
        current_time = time.time()
        
        for user_id, records in list(self.request_records.items()):
            # 清理分钟级记录（保留1分钟）
            while records["minute"] and current_time - records["minute"][0] > 60:
                records["minute"].popleft()
            
            # 清理小时级记录（保留1小时）
            while records["hour"] and current_time - records["hour"][0] > 3600:
                records["hour"].popleft()
            
            # 清理天级记录（保留1天）
            while records["day"] and current_time - records["day"][0] > 86400:
                records["day"].popleft()
            
            # 如果所有记录都为空，删除用户记录
            if not any([records["minute"], records["hour"], records["day"]]):
                del self.request_records[user_id]
    
    def get_user_rate_limit(self, user_id: str, user_role: str = "default") -> Dict[str, int]:
        """获取用户速率限制"""
        # 检查白名单
        if user_id in self.whitelist:
            return {
                "requests_per_minute": float('inf'),
                "requests_per_hour": float('inf'),
                "requests_per_day": float('inf')
            }
        
        # 根据用户角色获取限制
        return self.rate_limits.get(user_role, self.rate_limits["default"])
    
    async def check_limit(self, user_id: str, user_role: str = "default") -> bool:
        """检查速率限制"""
        try:
            # 检查黑名单
            if user_id in self.blacklist:
                logger.warning("用户在黑名单中", user_id=user_id)
                return False
            
            # 检查白名单
            if user_id in self.whitelist:
                return True
            
            current_time = time.time()
            records = self.request_records[user_id]
            limits = self.get_user_rate_limit(user_id, user_role)
            
            # 检查分钟级限制
            minute_requests = len([t for t in records["minute"] if current_time - t <= 60])
            if minute_requests >= limits["requests_per_minute"]:
                logger.warning("超过分钟级速率限制", 
                             user_id=user_id,
                             requests=minute_requests,
                             limit=limits["requests_per_minute"])
                return False
            
            # 检查小时级限制
            hour_requests = len([t for t in records["hour"] if current_time - t <= 3600])
            if hour_requests >= limits["requests_per_hour"]:
                logger.warning("超过小时级速率限制",
                             user_id=user_id,
                             requests=hour_requests,
                             limit=limits["requests_per_hour"])
                return False
            
            # 检查天级限制
            day_requests = len([t for t in records["day"] if current_time - t <= 86400])
            if day_requests >= limits["requests_per_day"]:
                logger.warning("超过天级速率限制",
                             user_id=user_id,
                             requests=day_requests,
                             limit=limits["requests_per_day"])
                return False
            
            # 记录请求
            records["minute"].append(current_time)
            records["hour"].append(current_time)
            records["day"].append(current_time)
            
            return True
            
        except Exception as e:
            logger.error("检查速率限制出错", error=str(e))
            return True  # 出错时允许请求
    
    async def get_remaining_requests(self, user_id: str, user_role: str = "default") -> Dict[str, int]:
        """获取剩余请求数"""
        try:
            if user_id in self.whitelist:
                return {
                    "minute": float('inf'),
                    "hour": float('inf'),
                    "day": float('inf')
                }
            
            if user_id in self.blacklist:
                return {
                    "minute": 0,
                    "hour": 0,
                    "day": 0
                }
            
            current_time = time.time()
            records = self.request_records[user_id]
            limits = self.get_user_rate_limit(user_id, user_role)
            
            # 计算剩余请求数
            minute_requests = len([t for t in records["minute"] if current_time - t <= 60])
            hour_requests = len([t for t in records["hour"] if current_time - t <= 3600])
            day_requests = len([t for t in records["day"] if current_time - t <= 86400])
            
            return {
                "minute": max(0, limits["requests_per_minute"] - minute_requests),
                "hour": max(0, limits["requests_per_hour"] - hour_requests),
                "day": max(0, limits["requests_per_day"] - day_requests)
            }
            
        except Exception as e:
            logger.error("获取剩余请求数出错", error=str(e))
            return {"minute": 0, "hour": 0, "day": 0}
    
    async def get_reset_time(self, user_id: str) -> Dict[str, datetime]:
        """获取重置时间"""
        try:
            current_time = time.time()
            records = self.request_records[user_id]
            
            # 计算重置时间
            minute_reset = None
            hour_reset = None
            day_reset = None
            
            if records["minute"]:
                oldest_minute = records["minute"][0]
                minute_reset = datetime.fromtimestamp(oldest_minute + 60)
            
            if records["hour"]:
                oldest_hour = records["hour"][0]
                hour_reset = datetime.fromtimestamp(oldest_hour + 3600)
            
            if records["day"]:
                oldest_day = records["day"][0]
                day_reset = datetime.fromtimestamp(oldest_day + 86400)
            
            return {
                "minute": minute_reset,
                "hour": hour_reset,
                "day": day_reset
            }
            
        except Exception as e:
            logger.error("获取重置时间出错", error=str(e))
            return {"minute": None, "hour": None, "day": None}
    
    async def add_to_blacklist(self, user_id: str, reason: str = None):
        """添加到黑名单"""
        self.blacklist.add(user_id)
        logger.warning("用户已添加到黑名单", user_id=user_id, reason=reason)
    
    async def remove_from_blacklist(self, user_id: str):
        """从黑名单移除"""
        self.blacklist.discard(user_id)
        logger.info("用户已从黑名单移除", user_id=user_id)
    
    async def add_to_whitelist(self, user_id: str, reason: str = None):
        """添加到白名单"""
        self.whitelist.add(user_id)
        logger.info("用户已添加到白名单", user_id=user_id, reason=reason)
    
    async def remove_from_whitelist(self, user_id: str):
        """从白名单移除"""
        self.whitelist.discard(user_id)
        logger.info("用户已从白名单移除", user_id=user_id)
    
    async def update_rate_limit(self, role: str, limits: Dict[str, int]):
        """更新速率限制"""
        try:
            self.rate_limits[role] = limits
            logger.info("速率限制已更新", role=role, limits=limits)
        except Exception as e:
            logger.error("更新速率限制出错", error=str(e))
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            current_time = time.time()
            
            # 统计活跃用户
            active_users = len(self.request_records)
            
            # 统计总请求数
            total_requests = 0
            for records in self.request_records.values():
                total_requests += len(records["day"])
            
            # 统计最近1小时的请求数
            recent_requests = 0
            for records in self.request_records.values():
                recent_requests += len([t for t in records["hour"] if current_time - t <= 3600])
            
            return {
                "active_users": active_users,
                "total_requests_today": total_requests,
                "requests_last_hour": recent_requests,
                "blacklisted_users": len(self.blacklist),
                "whitelisted_users": len(self.whitelist),
                "rate_limits": self.rate_limits
            }
            
        except Exception as e:
            logger.error("获取统计信息出错", error=str(e))
            return {}
    
    async def reset_user_limits(self, user_id: str):
        """重置用户限制"""
        try:
            if user_id in self.request_records:
                del self.request_records[user_id]
                logger.info("用户限制已重置", user_id=user_id)
        except Exception as e:
            logger.error("重置用户限制出错", error=str(e))
    
    def __del__(self):
        """析构函数"""
        if self.cleanup_task:
            self.cleanup_task.cancel()

class IPRateLimiter:
    """IP地址速率限制器"""
    
    def __init__(self):
        self.ip_records = defaultdict(lambda: deque())
        self.blocked_ips = set()
        self.requests_per_minute = 100
        
    async def check_ip_limit(self, ip_address: str) -> bool:
        """检查IP速率限制"""
        if ip_address in self.blocked_ips:
            return False
        
        current_time = time.time()
        records = self.ip_records[ip_address]
        
        # 清理过期记录
        while records and current_time - records[0] > 60:
            records.popleft()
        
        # 检查限制
        if len(records) >= self.requests_per_minute:
            logger.warning("IP超过速率限制", ip=ip_address)
            return False
        
        # 记录请求
        records.append(current_time)
        return True
    
    async def block_ip(self, ip_address: str, reason: str = None):
        """封禁IP"""
        self.blocked_ips.add(ip_address)
        logger.warning("IP已被封禁", ip=ip_address, reason=reason)
    
    async def unblock_ip(self, ip_address: str):
        """解封IP"""
        self.blocked_ips.discard(ip_address)
        logger.info("IP已解封", ip=ip_address)