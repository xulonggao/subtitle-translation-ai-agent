#!/usr/bin/env python3
"""
简化版通知系统
负责实时状态更新和通知机制
"""
import uuid
import time
import threading
import queue
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from collections import deque

from config import get_logger

logger = get_logger("notification_simple")


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
    CONSOLE = "console"
    WEBSOCKET = "websocket"
    EMAIL = "email"
    FILE = "file"


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
    priority: int = 0
    channels: List[NotificationChannel] = None
    metadata: Dict[str, Any] = None
    
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
    workflow_filters: List[str] = None
    agent_filters: List[str] = None
    priority_threshold: int = 0
    active: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.workflow_filters is None:
            self.workflow_filters = []
        if self.agent_filters is None:
            self.agent_filters = []
        if self.created_at is None:
            self.created_at = datetime.now()


class NotificationSystem:
    """简化版通知系统"""
    
    def __init__(self, system_id: str = None):
        self.system_id = system_id or f"notification_system_{uuid.uuid4().hex[:8]}"
        
        # 通知数据
        self.notifications: deque = deque(maxlen=1000)
        self.subscriptions: Dict[str, NotificationSubscription] = {}
        
        # 通知队列和处理
        self.notification_queue = queue.Queue()
        self.processing_active = True
        self.processing_thread = threading.Thread(target=self._notification_processing_loop, daemon=True)
        self.processing_thread.start()
        
        # 通知统计
        self.notification_stats = {
            "total_sent": 0,
            "sent_by_type": {},
            "sent_by_channel": {},
            "failed_deliveries": 0,
            "active_subscriptions": 0
        }
        
        logger.info("通知系统初始化完成", system_id=self.system_id)
    
    def create_subscription(self, subscriber_id: str, 
                          channels: List[NotificationChannel],
                          notification_types: List[NotificationType],
                          workflow_filters: List[str] = None,
                          agent_filters: List[str] = None,
                          priority_threshold: int = 0) -> str:
        """创建通知订阅"""
        subscription_id = f"sub_{uuid.uuid4().hex[:8]}"
        
        subscription = NotificationSubscription(
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            channels=channels,
            notification_types=notification_types,
            workflow_filters=workflow_filters or [],
            agent_filters=agent_filters or [],
            priority_threshold=priority_threshold
        )
        
        self.subscriptions[subscription_id] = subscription
        self.notification_stats["active_subscriptions"] = len(self.subscriptions)
        
        logger.info("通知订阅已创建", 
                   subscription_id=subscription_id,
                   subscriber_id=subscriber_id)
        
        return subscription_id
    
    def update_subscription(self, subscription_id: str, **kwargs) -> bool:
        """更新通知订阅"""
        if subscription_id not in self.subscriptions:
            logger.warning("尝试更新不存在的订阅", subscription_id=subscription_id)
            return False
        
        subscription = self.subscriptions[subscription_id]
        
        for key, value in kwargs.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)
        
        logger.info("通知订阅已更新", subscription_id=subscription_id)
        return True
    
    def delete_subscription(self, subscription_id: str) -> bool:
        """删除通知订阅"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            self.notification_stats["active_subscriptions"] = len(self.subscriptions)
            
            logger.info("通知订阅已删除", subscription_id=subscription_id)
            return True
        
        return False
    
    def send_notification(self, notification_type: NotificationType,
                         title: str, message: str,
                         workflow_id: str = None,
                         task_id: str = None,
                         agent_name: str = None,
                         priority: int = 0,
                         channels: List[NotificationChannel] = None,
                         metadata: Dict[str, Any] = None) -> str:
        """发送通知"""
        notification_id = f"notif_{uuid.uuid4().hex[:8]}"
        
        notification = Notification(
            notification_id=notification_id,
            type=notification_type,
            title=title,
            message=message,
            timestamp=datetime.now(),
            workflow_id=workflow_id,
            task_id=task_id,
            agent_name=agent_name,
            priority=priority,
            channels=channels or [NotificationChannel.CONSOLE],
            metadata=metadata or {}
        )
        
        # 添加到队列进行异步处理
        self.notification_queue.put(notification)
        
        logger.debug("通知已加入队列", 
                    notification_id=notification_id,
                    type=notification_type.value,
                    title=title)
        
        return notification_id
    
    def send_progress_notification(self, workflow_id: str, task_id: str = None,
                                 progress_percentage: float = None,
                                 stage: str = None, message: str = None,
                                 agent_name: str = None,
                                 metadata: Dict[str, Any] = None):
        """发送进度通知"""
        title = f"进度更新: {workflow_id}"
        if task_id:
            title += f" - {task_id}"
        
        progress_msg = message or f"当前进度: {progress_percentage:.1f}%"
        if stage:
            progress_msg += f" (阶段: {stage})"
        
        progress_metadata = metadata or {}
        progress_metadata.update({
            "progress_percentage": progress_percentage,
            "stage": stage
        })
        
        return self.send_notification(
            NotificationType.PROGRESS,
            title,
            progress_msg,
            workflow_id=workflow_id,
            task_id=task_id,
            agent_name=agent_name,
            priority=0,
            channels=[NotificationChannel.CONSOLE],
            metadata=progress_metadata
        )
    
    def send_alert_notification(self, alert_type: str, message: str,
                              workflow_id: str = None,
                              agent_name: str = None,
                              metadata: Dict[str, Any] = None):
        """发送告警通知"""
        return self.send_notification(
            NotificationType.ALERT,
            f"系统告警: {alert_type}",
            message,
            workflow_id=workflow_id,
            agent_name=agent_name,
            priority=2,  # 高优先级
            channels=[NotificationChannel.CONSOLE],
            metadata=metadata
        )
    
    def _notification_processing_loop(self):
        """通知处理循环"""
        while self.processing_active:
            try:
                # 等待通知
                try:
                    notification = self.notification_queue.get(timeout=1.0)
                    self._process_single_notification(notification)
                except queue.Empty:
                    continue
                    
            except Exception as e:
                logger.error("通知处理循环异常", error=str(e))
                time.sleep(1.0)
    
    def _process_single_notification(self, notification: Notification):
        """处理单个通知"""
        try:
            # 保存通知到历史记录
            self.notifications.append(notification)
            
            # 查找匹配的订阅
            matching_subscriptions = self._find_matching_subscriptions(notification)
            
            if not matching_subscriptions:
                logger.debug("没有找到匹配的订阅", notification_id=notification.notification_id)
                return
            
            # 分发通知
            for subscription in matching_subscriptions:
                for channel in notification.channels:
                    if channel in subscription.channels:
                        self._deliver_notification(notification, subscription, channel)
            
            # 更新统计
            self.notification_stats["total_sent"] += 1
            type_key = notification.type.value
            self.notification_stats["sent_by_type"][type_key] = \
                self.notification_stats["sent_by_type"].get(type_key, 0) + 1
            
            logger.debug("通知处理完成", 
                        notification_id=notification.notification_id,
                        subscriptions_count=len(matching_subscriptions))
                        
        except Exception as e:
            logger.error("处理通知失败", 
                        notification_id=notification.notification_id,
                        error=str(e))
    
    def _find_matching_subscriptions(self, notification: Notification) -> List[NotificationSubscription]:
        """查找匹配的订阅"""
        matching = []
        
        for subscription in self.subscriptions.values():
            if not subscription.active:
                continue
            
            # 检查通知类型
            if notification.type not in subscription.notification_types:
                continue
            
            # 检查优先级阈值
            if notification.priority < subscription.priority_threshold:
                continue
            
            # 检查工作流过滤
            if (subscription.workflow_filters and 
                notification.workflow_id and 
                notification.workflow_id not in subscription.workflow_filters):
                continue
            
            # 检查Agent过滤
            if (subscription.agent_filters and 
                notification.agent_name and 
                notification.agent_name not in subscription.agent_filters):
                continue
            
            matching.append(subscription)
        
        return matching
    
    def _deliver_notification(self, notification: Notification, 
                            subscription: NotificationSubscription,
                            channel: NotificationChannel):
        """分发通知到指定渠道"""
        try:
            if channel == NotificationChannel.CONSOLE:
                self._deliver_to_console(notification)
            elif channel == NotificationChannel.FILE:
                self._deliver_to_file(notification)
            # 其他渠道可以在这里添加
            
            channel_key = channel.value
            self.notification_stats["sent_by_channel"][channel_key] = \
                self.notification_stats["sent_by_channel"].get(channel_key, 0) + 1
            
        except Exception as e:
            self.notification_stats["failed_deliveries"] += 1
            logger.error("通知分发失败", 
                        notification_id=notification.notification_id,
                        channel=channel.value,
                        subscription_id=subscription.subscription_id,
                        error=str(e))
    
    def _deliver_to_console(self, notification: Notification):
        """分发到控制台"""
        level_map = {
            NotificationType.INFO: "INFO",
            NotificationType.SUCCESS: "SUCCESS",
            NotificationType.WARNING: "WARNING",
            NotificationType.ERROR: "ERROR",
            NotificationType.PROGRESS: "PROGRESS",
            NotificationType.ALERT: "ALERT"
        }
        
        level = level_map.get(notification.type, "INFO")
        timestamp = notification.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        console_message = f"[{timestamp}] [{level}] {notification.title}: {notification.message}"
        
        if notification.workflow_id:
            console_message += f" (工作流: {notification.workflow_id})"
        
        if notification.agent_name:
            console_message += f" (Agent: {notification.agent_name})"
        
        print(console_message)
    
    def _deliver_to_file(self, notification: Notification):
        """分发到文件"""
        import json
        
        log_file = f"notifications_{datetime.now().strftime('%Y%m%d')}.log"
        
        log_entry = {
            "timestamp": notification.timestamp.isoformat(),
            "id": notification.notification_id,
            "type": notification.type.value,
            "title": notification.title,
            "message": notification.message,
            "workflow_id": notification.workflow_id,
            "task_id": notification.task_id,
            "agent_name": notification.agent_name,
            "priority": notification.priority,
            "metadata": notification.metadata
        }
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("文件通知写入失败", file=log_file, error=str(e))
    
    def get_notifications(self, limit: int = 100, 
                         notification_types: List[NotificationType] = None,
                         workflow_id: str = None,
                         since: datetime = None) -> List[Notification]:
        """获取通知历史"""
        notifications = list(self.notifications)
        
        # 过滤条件
        if notification_types:
            notifications = [n for n in notifications if n.type in notification_types]
        
        if workflow_id:
            notifications = [n for n in notifications if n.workflow_id == workflow_id]
        
        if since:
            notifications = [n for n in notifications if n.timestamp >= since]
        
        # 按时间倒序排列
        notifications.sort(key=lambda x: x.timestamp, reverse=True)
        
        return notifications[:limit]
    
    def get_subscription(self, subscription_id: str) -> Optional[NotificationSubscription]:
        """获取订阅信息"""
        return self.subscriptions.get(subscription_id)
    
    def list_subscriptions(self, subscriber_id: str = None) -> List[NotificationSubscription]:
        """列出订阅"""
        subscriptions = list(self.subscriptions.values())
        
        if subscriber_id:
            subscriptions = [s for s in subscriptions if s.subscriber_id == subscriber_id]
        
        return subscriptions
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """获取通知统计"""
        return {
            "timestamp": datetime.now(),
            "system_id": self.system_id,
            "total_notifications": len(self.notifications),
            "active_subscriptions": len(self.subscriptions),
            "queue_size": self.notification_queue.qsize(),
            "stats": self.notification_stats.copy()
        }
    
    def stop_processing(self):
        """停止通知处理"""
        self.processing_active = False
        if self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        logger.info("通知系统已停止", system_id=self.system_id)
    
    def __del__(self):
        """析构函数"""
        self.stop_processing()


if __name__ == "__main__":
    # 测试代码
    def test_notification_system():
        print("🚀 测试通知系统")
        
        # 创建通知系统
        notification_system = NotificationSystem("test_system")
        
        # 创建订阅
        subscription_id = notification_system.create_subscription(
            subscriber_id="test_user",
            channels=[NotificationChannel.CONSOLE],
            notification_types=[NotificationType.INFO, NotificationType.PROGRESS, NotificationType.ALERT],
            priority_threshold=0
        )
        
        print(f"✅ 创建订阅: {subscription_id}")
        
        # 发送各种类型的通知
        notification_system.send_notification(
            NotificationType.INFO,
            "系统启动",
            "字幕翻译系统已成功启动",
            priority=1
        )
        
        notification_system.send_progress_notification(
            workflow_id="test_workflow",
            task_id="test_task",
            progress_percentage=50.0,
            stage="translation",
            message="翻译进度50%",
            agent_name="translator"
        )
        
        notification_system.send_alert_notification(
            alert_type="high_cpu",
            message="CPU使用率过高: 85%",
            workflow_id="test_workflow",
            agent_name="system_monitor"
        )
        
        # 等待处理完成
        time.sleep(2)
        
        # 获取统计信息
        stats = notification_system.get_notification_stats()
        print(f"\n📊 通知统计:")
        print(f"  总通知数: {stats['total_notifications']}")
        print(f"  活跃订阅: {stats['active_subscriptions']}")
        print(f"  已发送: {stats['stats']['total_sent']}")
        
        # 获取通知历史
        notifications = notification_system.get_notifications(limit=10)
        print(f"\n📜 通知历史 ({len(notifications)} 条):")
        for notif in notifications:
            timestamp = notif.timestamp.strftime("%H:%M:%S")
            print(f"  [{timestamp}] {notif.type.value}: {notif.title}")
        
        # 停止系统
        notification_system.stop_processing()
        
        print("\n✅ 测试完成!")
    
    test_notification_system()