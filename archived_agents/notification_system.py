#!/usr/bin/env python3
"""
通知系统
负责实时状态更新和通知机制
"""
import uuid
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import threading
import queue

from config import get_logger

logger = get_logger("notification_system")


class NotificationType(Enum):
    """通知类型"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"
    ALERT = "alert"


class NotificationChannel(Enum):
    """通知渠道"""
    WEBSOCKET = "websocket"
    HTTP_CALLBACK = "http_callback"
    EMAIL = "email"
    CONSOLE = "console"
    FILE = "file"
    DATABASE = "database"


@dataclass
class Notification:
    """通知消息"""
    notification_id: str
    type: NotificationType
    title: str
    message: str
    timestamp: datetime
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_name: Optional[str] = None
    priority: int = 0  # 0=低, 1=中, 2=高, 3=紧急
    channels: List[NotificationChannel] = None
    metadata: Dict[str, Any] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = [NotificationChannel.CONSOLE]
        if self.metadata is None:
            self.metadata = {}


@dataclass
class NotificationSubscription:
    """通知订阅"""
    subscription_id: str
    subscriber_id: str
    channels: List[NotificationChannel]
    notification_types: List[NotificationType]
    workflow_filters: List[str] = None  # 工作流ID过滤
    agent_filters: List[str] = None     # Agent名称过滤
    priority_threshold: int = 0         # 优先级阈值
    callback_url: Optional[str] = None  # HTTP回调URL
    email_address: Optional[str] = None # 邮箱地址
    active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.workflow_filters is None:
            self.workflow_filters = []
        if self.agent_filters is None:
            self.agent_filters = []
        if self.created_at is None:
            self.created_at = datetime.now()


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.connections: Dict[str, Any] = {}  # connection_id -> websocket
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # subscription_id -> connection_ids
        
    def add_connection(self, connection_id: str, websocket):
        """添加WebSocket连接"""
        self.connections[connection_id] = websocket
        logger.debug("WebSocket连接已添加", connection_id=connection_id)
    
    def remove_connection(self, connection_id: str):
        """移除WebSocket连接"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            
            # 清理订阅关联
            for subscription_id, conn_ids in self.subscriptions.items():
                conn_ids.discard(connection_id)
            
            logger.debug("WebSocket连接已移除", connection_id=connection_id)
    
    def subscribe_connection(self, connection_id: str, subscription_id: str):
        """订阅连接到通知"""
        if connection_id in self.connections:
            self.subscriptions[subscription_id].add(connection_id)
            logger.debug("连接已订阅通知", 
                        connection_id=connection_id, 
                        subscription_id=subscription_id)
    
    async def send_to_connections(self, subscription_id: str, message: Dict[str, Any]):
        """发送消息到订阅的连接"""
        connection_ids = self.subscriptions.get(subscription_id, set())
        
        for connection_id in list(connection_ids):  # 使用副本避免修改时迭代
            if connection_id in self.connections:
                try:
                    websocket = self.connections[connection_id]
                    await websocket.send(json.dumps(message, default=str, ensure_ascii=False))
                except Exception as e:
                    logger.warning("WebSocket发送失败", 
                                 connection_id=connection_id, 
                                 error=str(e))
                    # 移除失效连接
                    self.remove_connection(connection_id)


class NotificationSystem:
    """通知系统
    
    负责：
    1. 实时状态更新和通知
    2. 多渠道通知分发
    3. 订阅管理
    4. 通知历史记录
    """
    
    def __init__(self, system_id: str = None):
        self.system_id = system_id or f"notification_system_{uuid.uuid4().hex[:8]}"
        
        # 通知数据
        self.notifications: deque = deque(maxlen=10000)  # 保留最近10000条通知
        self.subscriptions: Dict[str, NotificationSubscription] = {}
        
        # 通知队列和处理
        self.notification_queue = queue.Queue()
        self.processing_active = True
        self.processing_thread = threading.Thread(target=self._notification_processing_loop, daemon=True)\n        self.processing_thread.start()\n        \n        # WebSocket管理器\n        self.websocket_manager = WebSocketManager()\n        \n        # 通知统计\n        self.notification_stats = {\n            \"total_sent\": 0,\n            \"sent_by_type\": defaultdict(int),\n            \"sent_by_channel\": defaultdict(int),\n            \"failed_deliveries\": 0,\n            \"active_subscriptions\": 0\n        }\n        \n        # 通知配置\n        self.config = {\n            \"max_retry_attempts\": 3,\n            \"retry_delay_seconds\": 5,\n            \"notification_ttl_hours\": 24,\n            \"batch_size\": 100,\n            \"rate_limit_per_minute\": 1000\n        }\n        \n        # 速率限制\n        self.rate_limiter = {\n            \"requests\": deque(maxlen=self.config[\"rate_limit_per_minute\"]),\n            \"last_cleanup\": datetime.now()\n        }\n        \n        logger.info(\"通知系统初始化完成\", system_id=self.system_id)\n    \n    def create_subscription(self, subscriber_id: str, \n                          channels: List[NotificationChannel],\n                          notification_types: List[NotificationType],\n                          workflow_filters: List[str] = None,\n                          agent_filters: List[str] = None,\n                          priority_threshold: int = 0,\n                          callback_url: str = None,\n                          email_address: str = None) -> str:\n        \"\"\"创建通知订阅\"\"\"\n        subscription_id = f\"sub_{uuid.uuid4().hex[:8]}\"\n        \n        subscription = NotificationSubscription(\n            subscription_id=subscription_id,\n            subscriber_id=subscriber_id,\n            channels=channels,\n            notification_types=notification_types,\n            workflow_filters=workflow_filters or [],\n            agent_filters=agent_filters or [],\n            priority_threshold=priority_threshold,\n            callback_url=callback_url,\n            email_address=email_address\n        )\n        \n        self.subscriptions[subscription_id] = subscription\n        self.notification_stats[\"active_subscriptions\"] = len(self.subscriptions)\n        \n        logger.info(\"通知订阅已创建\", \n                   subscription_id=subscription_id,\n                   subscriber_id=subscriber_id,\n                   channels=[c.value for c in channels],\n                   types=[t.value for t in notification_types])\n        \n        return subscription_id\n    \n    def update_subscription(self, subscription_id: str, **kwargs) -> bool:\n        \"\"\"更新通知订阅\"\"\"\n        if subscription_id not in self.subscriptions:\n            logger.warning(\"尝试更新不存在的订阅\", subscription_id=subscription_id)\n            return False\n        \n        subscription = self.subscriptions[subscription_id]\n        \n        for key, value in kwargs.items():\n            if hasattr(subscription, key):\n                setattr(subscription, key, value)\n        \n        logger.info(\"通知订阅已更新\", subscription_id=subscription_id)\n        return True\n    \n    def delete_subscription(self, subscription_id: str) -> bool:\n        \"\"\"删除通知订阅\"\"\"\n        if subscription_id in self.subscriptions:\n            del self.subscriptions[subscription_id]\n            self.notification_stats[\"active_subscriptions\"] = len(self.subscriptions)\n            \n            logger.info(\"通知订阅已删除\", subscription_id=subscription_id)\n            return True\n        \n        return False\n    \n    def send_notification(self, notification_type: NotificationType,\n                         title: str, message: str,\n                         workflow_id: str = None,\n                         task_id: str = None,\n                         agent_name: str = None,\n                         priority: int = 0,\n                         channels: List[NotificationChannel] = None,\n                         metadata: Dict[str, Any] = None,\n                         expires_in_hours: int = None) -> str:\n        \"\"\"发送通知\"\"\"\n        # 速率限制检查\n        if not self._check_rate_limit():\n            logger.warning(\"通知发送被速率限制\")\n            return None\n        \n        notification_id = f\"notif_{uuid.uuid4().hex[:8]}\"\n        \n        expires_at = None\n        if expires_in_hours:\n            expires_at = datetime.now() + timedelta(hours=expires_in_hours)\n        elif self.config[\"notification_ttl_hours\"]:\n            expires_at = datetime.now() + timedelta(hours=self.config[\"notification_ttl_hours\"])\n        \n        notification = Notification(\n            notification_id=notification_id,\n            type=notification_type,\n            title=title,\n            message=message,\n            timestamp=datetime.now(),\n            workflow_id=workflow_id,\n            task_id=task_id,\n            agent_name=agent_name,\n            priority=priority,\n            channels=channels or [NotificationChannel.CONSOLE],\n            metadata=metadata or {},\n            expires_at=expires_at\n        )\n        \n        # 添加到队列进行异步处理\n        self.notification_queue.put(notification)\n        \n        logger.debug(\"通知已加入队列\", \n                    notification_id=notification_id,\n                    type=notification_type.value,\n                    title=title)\n        \n        return notification_id\n    \n    def send_progress_notification(self, workflow_id: str, task_id: str = None,\n                                 progress_percentage: float = None,\n                                 stage: str = None, message: str = None,\n                                 agent_name: str = None,\n                                 metadata: Dict[str, Any] = None):\n        \"\"\"发送进度通知\"\"\"\n        title = f\"进度更新: {workflow_id}\"\n        if task_id:\n            title += f\" - {task_id}\"\n        \n        progress_msg = message or f\"当前进度: {progress_percentage:.1f}%\"\n        if stage:\n            progress_msg += f\" (阶段: {stage})\"\n        \n        progress_metadata = metadata or {}\n        progress_metadata.update({\n            \"progress_percentage\": progress_percentage,\n            \"stage\": stage\n        })\n        \n        return self.send_notification(\n            NotificationType.PROGRESS,\n            title,\n            progress_msg,\n            workflow_id=workflow_id,\n            task_id=task_id,\n            agent_name=agent_name,\n            priority=0,\n            channels=[NotificationChannel.WEBSOCKET, NotificationChannel.CONSOLE],\n            metadata=progress_metadata\n        )\n    \n    def send_alert_notification(self, alert_type: str, message: str,\n                              workflow_id: str = None,\n                              agent_name: str = None,\n                              metadata: Dict[str, Any] = None):\n        \"\"\"发送告警通知\"\"\"\n        return self.send_notification(\n            NotificationType.ALERT,\n            f\"系统告警: {alert_type}\",\n            message,\n            workflow_id=workflow_id,\n            agent_name=agent_name,\n            priority=2,  # 高优先级\n            channels=[NotificationChannel.WEBSOCKET, NotificationChannel.CONSOLE, NotificationChannel.EMAIL],\n            metadata=metadata\n        )\n    \n    def _check_rate_limit(self) -> bool:\n        \"\"\"检查速率限制\"\"\"\n        now = datetime.now()\n        \n        # 清理过期请求\n        if (now - self.rate_limiter[\"last_cleanup\"]).total_seconds() > 60:\n            cutoff_time = now - timedelta(minutes=1)\n            while (self.rate_limiter[\"requests\"] and \n                   self.rate_limiter[\"requests\"][0] < cutoff_time):\n                self.rate_limiter[\"requests\"].popleft()\n            self.rate_limiter[\"last_cleanup\"] = now\n        \n        # 检查是否超过限制\n        if len(self.rate_limiter[\"requests\"]) >= self.config[\"rate_limit_per_minute\"]:\n            return False\n        \n        # 记录请求\n        self.rate_limiter[\"requests\"].append(now)\n        return True\n    \n    def _notification_processing_loop(self):\n        \"\"\"通知处理循环\"\"\"\n        while self.processing_active:\n            try:\n                # 批量处理通知\n                notifications_batch = []\n                \n                # 收集一批通知\n                try:\n                    # 等待第一个通知\n                    first_notification = self.notification_queue.get(timeout=1.0)\n                    notifications_batch.append(first_notification)\n                    \n                    # 收集更多通知（非阻塞）\n                    for _ in range(self.config[\"batch_size\"] - 1):\n                        try:\n                            notification = self.notification_queue.get_nowait()\n                            notifications_batch.append(notification)\n                        except queue.Empty:\n                            break\n                            \n                except queue.Empty:\n                    continue\n                \n                # 处理批量通知\n                asyncio.run(self._process_notifications_batch(notifications_batch))\n                \n            except Exception as e:\n                logger.error(\"通知处理循环异常\", error=str(e))\n                time.sleep(1.0)\n    \n    async def _process_notifications_batch(self, notifications: List[Notification]):\n        \"\"\"处理通知批次\"\"\"\n        for notification in notifications:\n            try:\n                await self._process_single_notification(notification)\n            except Exception as e:\n                logger.error(\"单个通知处理失败\", \n                           notification_id=notification.notification_id,\n                           error=str(e))\n    \n    async def _process_single_notification(self, notification: Notification):\n        \"\"\"处理单个通知\"\"\"\n        # 检查通知是否过期\n        if notification.expires_at and datetime.now() > notification.expires_at:\n            logger.debug(\"通知已过期，跳过处理\", notification_id=notification.notification_id)\n            return\n        \n        # 保存通知到历史记录\n        self.notifications.append(notification)\n        \n        # 查找匹配的订阅\n        matching_subscriptions = self._find_matching_subscriptions(notification)\n        \n        if not matching_subscriptions:\n            logger.debug(\"没有找到匹配的订阅\", notification_id=notification.notification_id)\n            return\n        \n        # 按渠道分发通知\n        delivery_tasks = []\n        \n        for subscription in matching_subscriptions:\n            for channel in notification.channels:\n                if channel in subscription.channels:\n                    task = self._deliver_notification(notification, subscription, channel)\n                    delivery_tasks.append(task)\n        \n        # 并发执行分发任务\n        if delivery_tasks:\n            await asyncio.gather(*delivery_tasks, return_exceptions=True)\n        \n        # 更新统计\n        self.notification_stats[\"total_sent\"] += 1\n        self.notification_stats[\"sent_by_type\"][notification.type.value] += 1\n        \n        logger.debug(\"通知处理完成\", \n                    notification_id=notification.notification_id,\n                    subscriptions_count=len(matching_subscriptions))\n    \n    def _find_matching_subscriptions(self, notification: Notification) -> List[NotificationSubscription]:\n        \"\"\"查找匹配的订阅\"\"\"\n        matching = []\n        \n        for subscription in self.subscriptions.values():\n            if not subscription.active:\n                continue\n            \n            # 检查通知类型\n            if notification.type not in subscription.notification_types:\n                continue\n            \n            # 检查优先级阈值\n            if notification.priority < subscription.priority_threshold:\n                continue\n            \n            # 检查工作流过滤\n            if (subscription.workflow_filters and \n                notification.workflow_id and \n                notification.workflow_id not in subscription.workflow_filters):\n                continue\n            \n            # 检查Agent过滤\n            if (subscription.agent_filters and \n                notification.agent_name and \n                notification.agent_name not in subscription.agent_filters):\n                continue\n            \n            matching.append(subscription)\n        \n        return matching\n    \n    async def _deliver_notification(self, notification: Notification, \n                                  subscription: NotificationSubscription,\n                                  channel: NotificationChannel):\n        \"\"\"分发通知到指定渠道\"\"\"\n        try:\n            if channel == NotificationChannel.CONSOLE:\n                await self._deliver_to_console(notification)\n            elif channel == NotificationChannel.WEBSOCKET:\n                await self._deliver_to_websocket(notification, subscription)\n            elif channel == NotificationChannel.HTTP_CALLBACK:\n                await self._deliver_to_http_callback(notification, subscription)\n            elif channel == NotificationChannel.EMAIL:\n                await self._deliver_to_email(notification, subscription)\n            elif channel == NotificationChannel.FILE:\n                await self._deliver_to_file(notification)\n            \n            self.notification_stats[\"sent_by_channel\"][channel.value] += 1\n            \n        except Exception as e:\n            self.notification_stats[\"failed_deliveries\"] += 1\n            logger.error(\"通知分发失败\", \n                        notification_id=notification.notification_id,\n                        channel=channel.value,\n                        subscription_id=subscription.subscription_id,\n                        error=str(e))\n    \n    async def _deliver_to_console(self, notification: Notification):\n        \"\"\"分发到控制台\"\"\"\n        level_map = {\n            NotificationType.INFO: \"INFO\",\n            NotificationType.SUCCESS: \"SUCCESS\",\n            NotificationType.WARNING: \"WARNING\",\n            NotificationType.ERROR: \"ERROR\",\n            NotificationType.PROGRESS: \"PROGRESS\",\n            NotificationType.ALERT: \"ALERT\"\n        }\n        \n        level = level_map.get(notification.type, \"INFO\")\n        timestamp = notification.timestamp.strftime(\"%Y-%m-%d %H:%M:%S\")\n        \n        console_message = f\"[{timestamp}] [{level}] {notification.title}: {notification.message}\"\n        \n        if notification.workflow_id:\n            console_message += f\" (工作流: {notification.workflow_id})\"\n        \n        if notification.agent_name:\n            console_message += f\" (Agent: {notification.agent_name})\"\n        \n        print(console_message)\n    \n    async def _deliver_to_websocket(self, notification: Notification, \n                                   subscription: NotificationSubscription):\n        \"\"\"分发到WebSocket\"\"\"\n        message = {\n            \"type\": \"notification\",\n            \"notification\": {\n                \"id\": notification.notification_id,\n                \"type\": notification.type.value,\n                \"title\": notification.title,\n                \"message\": notification.message,\n                \"timestamp\": notification.timestamp.isoformat(),\n                \"workflow_id\": notification.workflow_id,\n                \"task_id\": notification.task_id,\n                \"agent_name\": notification.agent_name,\n                \"priority\": notification.priority,\n                \"metadata\": notification.metadata\n            }\n        }\n        \n        await self.websocket_manager.send_to_connections(subscription.subscription_id, message)\n    \n    async def _deliver_to_http_callback(self, notification: Notification,\n                                       subscription: NotificationSubscription):\n        \"\"\"分发到HTTP回调\"\"\"\n        if not subscription.callback_url:\n            return\n        \n        try:\n            import aiohttp\n            \n            payload = {\n                \"notification_id\": notification.notification_id,\n                \"type\": notification.type.value,\n                \"title\": notification.title,\n                \"message\": notification.message,\n                \"timestamp\": notification.timestamp.isoformat(),\n                \"workflow_id\": notification.workflow_id,\n                \"task_id\": notification.task_id,\n                \"agent_name\": notification.agent_name,\n                \"priority\": notification.priority,\n                \"metadata\": notification.metadata,\n                \"subscription_id\": subscription.subscription_id\n            }\n            \n            async with aiohttp.ClientSession() as session:\n                async with session.post(\n                    subscription.callback_url,\n                    json=payload,\n                    timeout=aiohttp.ClientTimeout(total=10)\n                ) as response:\n                    if response.status >= 400:\n                        logger.warning(\"HTTP回调返回错误状态\", \n                                     status=response.status,\n                                     url=subscription.callback_url)\n                        \n        except ImportError:\n            logger.warning(\"aiohttp不可用，跳过HTTP回调\")\n        except Exception as e:\n            logger.error(\"HTTP回调发送失败\", \n                        url=subscription.callback_url,\n                        error=str(e))\n    \n    async def _deliver_to_email(self, notification: Notification,\n                               subscription: NotificationSubscription):\n        \"\"\"分发到邮箱（简化实现）\"\"\"\n        if not subscription.email_address:\n            return\n        \n        # 这里应该集成真实的邮件发送服务\n        logger.info(\"邮件通知（模拟）\", \n                   email=subscription.email_address,\n                   title=notification.title,\n                   message=notification.message)\n    \n    async def _deliver_to_file(self, notification: Notification):\n        \"\"\"分发到文件\"\"\"\n        log_file = f\"notifications_{datetime.now().strftime('%Y%m%d')}.log\"\n        \n        log_entry = {\n            \"timestamp\": notification.timestamp.isoformat(),\n            \"id\": notification.notification_id,\n            \"type\": notification.type.value,\n            \"title\": notification.title,\n            \"message\": notification.message,\n            \"workflow_id\": notification.workflow_id,\n            \"task_id\": notification.task_id,\n            \"agent_name\": notification.agent_name,\n            \"priority\": notification.priority,\n            \"metadata\": notification.metadata\n        }\n        \n        try:\n            with open(log_file, 'a', encoding='utf-8') as f:\n                f.write(json.dumps(log_entry, ensure_ascii=False) + \"\\n\")\n        except Exception as e:\n            logger.error(\"文件通知写入失败\", file=log_file, error=str(e))\n    \n    def get_notifications(self, limit: int = 100, \n                         notification_types: List[NotificationType] = None,\n                         workflow_id: str = None,\n                         since: datetime = None) -> List[Notification]:\n        \"\"\"获取通知历史\"\"\"\n        notifications = list(self.notifications)\n        \n        # 过滤条件\n        if notification_types:\n            notifications = [n for n in notifications if n.type in notification_types]\n        \n        if workflow_id:\n            notifications = [n for n in notifications if n.workflow_id == workflow_id]\n        \n        if since:\n            notifications = [n for n in notifications if n.timestamp >= since]\n        \n        # 按时间倒序排列\n        notifications.sort(key=lambda x: x.timestamp, reverse=True)\n        \n        return notifications[:limit]\n    \n    def get_subscription(self, subscription_id: str) -> Optional[NotificationSubscription]:\n        \"\"\"获取订阅信息\"\"\"\n        return self.subscriptions.get(subscription_id)\n    \n    def list_subscriptions(self, subscriber_id: str = None) -> List[NotificationSubscription]:\n        \"\"\"列出订阅\"\"\"\n        subscriptions = list(self.subscriptions.values())\n        \n        if subscriber_id:\n            subscriptions = [s for s in subscriptions if s.subscriber_id == subscriber_id]\n        \n        return subscriptions\n    \n    def get_notification_stats(self) -> Dict[str, Any]:\n        \"\"\"获取通知统计\"\"\"\n        return {\n            \"timestamp\": datetime.now(),\n            \"system_id\": self.system_id,\n            \"total_notifications\": len(self.notifications),\n            \"active_subscriptions\": len(self.subscriptions),\n            \"queue_size\": self.notification_queue.qsize(),\n            \"stats\": self.notification_stats.copy(),\n            \"rate_limit_status\": {\n                \"requests_in_last_minute\": len(self.rate_limiter[\"requests\"]),\n                \"limit\": self.config[\"rate_limit_per_minute\"]\n            }\n        }\n    \n    def cleanup_expired_notifications(self):\n        \"\"\"清理过期通知\"\"\"\n        now = datetime.now()\n        original_count = len(self.notifications)\n        \n        # 过滤未过期的通知\n        self.notifications = deque(\n            (n for n in self.notifications if not n.expires_at or n.expires_at > now),\n            maxlen=self.notifications.maxlen\n        )\n        \n        cleaned_count = original_count - len(self.notifications)\n        \n        if cleaned_count > 0:\n            logger.info(\"已清理过期通知\", cleaned_count=cleaned_count)\n    \n    def stop_processing(self):\n        \"\"\"停止通知处理\"\"\"\n        self.processing_active = False\n        if self.processing_thread.is_alive():\n            self.processing_thread.join(timeout=5.0)\n        \n        logger.info(\"通知系统已停止\", system_id=self.system_id)\n    \n    def __del__(self):\n        \"\"\"析构函数\"\"\"\n        self.stop_processing()\n\n\nif __name__ == \"__main__\":\n    # 测试代码\n    import time\n    \n    def test_notification_system():\n        # 创建通知系统\n        notification_system = NotificationSystem(\"test_system\")\n        \n        # 创建订阅\n        subscription_id = notification_system.create_subscription(\n            subscriber_id=\"test_user\",\n            channels=[NotificationChannel.CONSOLE, NotificationChannel.WEBSOCKET],\n            notification_types=[NotificationType.INFO, NotificationType.PROGRESS, NotificationType.ALERT],\n            priority_threshold=0\n        )\n        \n        print(f\"创建订阅: {subscription_id}\")\n        \n        # 发送各种类型的通知\n        notification_system.send_notification(\n            NotificationType.INFO,\n            \"系统启动\",\n            \"字幕翻译系统已成功启动\",\n            priority=1\n        )\n        \n        notification_system.send_progress_notification(\n            workflow_id=\"test_workflow\",\n            task_id=\"test_task\",\n            progress_percentage=50.0,\n            stage=\"translation\",\n            message=\"翻译进度50%\",\n            agent_name=\"translator\"\n        )\n        \n        notification_system.send_alert_notification(\n            alert_type=\"high_cpu\",\n            message=\"CPU使用率过高: 85%\",\n            workflow_id=\"test_workflow\",\n            agent_name=\"system_monitor\"\n        )\n        \n        # 等待处理完成\n        time.sleep(2)\n        \n        # 获取统计信息\n        stats = notification_system.get_notification_stats()\n        print(\"\\n通知统计:\")\n        print(json.dumps(stats, indent=2, default=str, ensure_ascii=False))\n        \n        # 获取通知历史\n        notifications = notification_system.get_notifications(limit=10)\n        print(f\"\\n通知历史 ({len(notifications)} 条):\")\n        for notif in notifications:\n            print(f\"  {notif.timestamp} [{notif.type.value}] {notif.title}: {notif.message}\")\n        \n        # 停止系统\n        notification_system.stop_processing()\n    \n    test_notification_system()\n"