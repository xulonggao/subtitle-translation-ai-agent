"""
动态知识库管理器
支持项目特定知识加载、优先级查询和实时更新
"""
import json
import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import threading
import time

from config import get_logger
from models.translation_models import TerminologyEntry, TranslationMemory
from models.story_models import StoryContext, CharacterRelation
from agents.knowledge_manager import get_knowledge_manager
from agents.project_manager import get_project_manager

logger = get_logger("dynamic_knowledge_manager")


class KnowledgeLevel(Enum):
    """知识库层级枚举"""
    PROJECT = "project"      # 项目特定
    GENRE = "genre"         # 类型特定
    GLOBAL = "global"       # 全局通用


class CacheStrategy(Enum):
    """缓存策略枚举"""
    LRU = "lru"             # 最近最少使用
    LFU = "lfu"             # 最少使用频率
    TTL = "ttl"             # 时间过期
    ADAPTIVE = "adaptive"    # 自适应


@dataclass
class KnowledgeQuery:
    """知识查询请求"""
    query_type: str  # terminology, translation_memory, cultural, context
    source_text: str
    target_language: str
    project_id: Optional[str] = None
    genre: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    priority_levels: List[KnowledgeLevel] = field(default_factory=lambda: [
        KnowledgeLevel.PROJECT, KnowledgeLevel.GENRE, KnowledgeLevel.GLOBAL
    ])


@dataclass
class KnowledgeResult:
    """知识查询结果"""
    query: KnowledgeQuery
    results: List[Any]
    source_level: KnowledgeLevel
    confidence: float
    cache_hit: bool = False
    response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl: Optional[timedelta] = None
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return datetime.now() - self.created_at > self.ttl
    
    def touch(self):
        """更新访问时间和次数"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class KnowledgeCache:
    """知识库缓存管理器"""
    
    def __init__(self, max_size: int = 1000, strategy: CacheStrategy = CacheStrategy.ADAPTIVE):
        self.max_size = max_size
        self.strategy = strategy
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # LRU用
        self.lock = threading.RLock()
        
        # 统计信息
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        logger.info("知识库缓存初始化", max_size=max_size, strategy=strategy.value)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            entry = self.cache[key]
            
            # 检查是否过期
            if entry.is_expired():
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
                self.misses += 1
                return None
            
            # 更新访问信息
            entry.touch()
            
            # 更新LRU顺序
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            
            self.hits += 1
            return entry.value
    
    def put(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        """存储缓存值"""
        with self.lock:
            # 如果缓存已满，执行淘汰策略
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict()
            
            # 创建缓存条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                ttl=ttl
            )
            
            self.cache[key] = entry
            
            # 更新LRU顺序
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
    
    def _evict(self):
        """执行缓存淘汰"""
        if not self.cache:
            return
        
        evict_key = None
        
        if self.strategy == CacheStrategy.LRU:
            # 淘汰最近最少使用的
            evict_key = self.access_order[0]
        
        elif self.strategy == CacheStrategy.LFU:
            # 淘汰使用频率最低的
            min_count = min(entry.access_count for entry in self.cache.values())
            for key, entry in self.cache.items():
                if entry.access_count == min_count:
                    evict_key = key
                    break
        
        elif self.strategy == CacheStrategy.TTL:
            # 淘汰最早过期的
            now = datetime.now()
            earliest_expire = None
            for key, entry in self.cache.items():
                if entry.ttl:
                    expire_time = entry.created_at + entry.ttl
                    if earliest_expire is None or expire_time < earliest_expire:
                        earliest_expire = expire_time
                        evict_key = key
        
        elif self.strategy == CacheStrategy.ADAPTIVE:
            # 自适应策略：结合LRU和LFU
            scores = {}
            now = datetime.now()
            for key, entry in self.cache.items():
                age_score = (now - entry.last_accessed).total_seconds() / 3600  # 小时
                freq_score = 1.0 / (entry.access_count + 1)
                scores[key] = age_score + freq_score
            
            evict_key = min(scores.keys(), key=lambda k: scores[k])
        
        if evict_key:
            del self.cache[evict_key]
            if evict_key in self.access_order:
                self.access_order.remove(evict_key)
            self.evictions += 1
            logger.debug("缓存条目已淘汰", key=evict_key, strategy=self.strategy.value)
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
            logger.info("缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_rate": hit_rate,
                "strategy": self.strategy.value
            }


class DynamicKnowledgeBase:
    """动态知识库管理器
    
    支持项目特定知识加载、优先级查询和实时更新
    """
    
    def __init__(self, cache_size: int = 1000, cache_strategy: CacheStrategy = CacheStrategy.ADAPTIVE):
        self.knowledge_manager = get_knowledge_manager()
        self.project_manager = get_project_manager()
        
        # 缓存管理
        self.cache = KnowledgeCache(cache_size, cache_strategy)
        
        # 项目知识加载状态
        self.loaded_projects: Set[str] = set()
        self.project_load_times: Dict[str, datetime] = {}
        
        # 知识库更新监控
        self.last_update_check = datetime.now()
        self.update_interval = timedelta(minutes=5)  # 5分钟检查一次更新
        
        # 性能统计
        self.query_stats = defaultdict(int)
        self.response_times = defaultdict(list)
        
        # 后台更新线程
        self.update_thread = None
        self.stop_update = threading.Event()
        
        logger.info("动态知识库管理器初始化完成", cache_size=cache_size)
    
    def start_background_updates(self):
        """启动后台更新线程"""
        if self.update_thread is None or not self.update_thread.is_alive():
            self.stop_update.clear()
            self.update_thread = threading.Thread(target=self._background_update_loop, daemon=True)
            self.update_thread.start()
            logger.info("后台更新线程已启动")
    
    def stop_background_updates(self):
        """停止后台更新线程"""
        if self.update_thread and self.update_thread.is_alive():
            self.stop_update.set()
            self.update_thread.join(timeout=5)
            logger.info("后台更新线程已停止")
    
    def _background_update_loop(self):
        """后台更新循环"""
        while not self.stop_update.is_set():
            try:
                self._check_and_update_knowledge()
                time.sleep(self.update_interval.total_seconds())
            except Exception as e:
                logger.error("后台更新出错", error=str(e))
                time.sleep(60)  # 出错后等待1分钟再重试
    
    def _check_and_update_knowledge(self):
        """检查并更新知识库"""
        now = datetime.now()
        
        # 检查项目知识是否需要重新加载
        for project_id in list(self.loaded_projects):
            load_time = self.project_load_times.get(project_id)
            if load_time and now - load_time > timedelta(hours=1):  # 1小时后重新加载
                try:
                    self._reload_project_knowledge(project_id)
                except Exception as e:
                    logger.error("重新加载项目知识失败", project_id=project_id, error=str(e))
        
        # 清理过期缓存
        self._cleanup_expired_cache()
        
        self.last_update_check = now
    
    def _reload_project_knowledge(self, project_id: str):
        """重新加载项目知识"""
        logger.info("重新加载项目知识", project_id=project_id)
        
        # 清除相关缓存
        self._clear_project_cache(project_id)
        
        # 重新加载
        self.load_project_knowledge(project_id)
    
    def _clear_project_cache(self, project_id: str):
        """清除项目相关缓存"""
        keys_to_remove = []
        for key in self.cache.cache.keys():
            if project_id in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self.cache.cache:
                del self.cache.cache[key]
            if key in self.cache.access_order:
                self.cache.access_order.remove(key)
        
        logger.debug("项目缓存已清除", project_id=project_id, cleared_keys=len(keys_to_remove))
    
    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        expired_keys = []
        for key, entry in self.cache.cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            if key in self.cache.cache:
                del self.cache.cache[key]
            if key in self.cache.access_order:
                self.cache.access_order.remove(key)
        
        if expired_keys:
            logger.debug("过期缓存已清理", count=len(expired_keys))
    
    def load_project_knowledge(self, project_id: str, force_reload: bool = False):
        """加载项目特定知识"""
        if project_id in self.loaded_projects and not force_reload:
            logger.debug("项目知识已加载", project_id=project_id)
            return
        
        try:
            logger.info("开始加载项目知识", project_id=project_id)
            
            # 使用知识库管理器加载项目知识
            self.knowledge_manager.load_project_knowledge(project_id)
            
            # 标记为已加载
            self.loaded_projects.add(project_id)
            self.project_load_times[project_id] = datetime.now()
            
            logger.info("项目知识加载完成", project_id=project_id)
            
        except Exception as e:
            logger.error("加载项目知识失败", project_id=project_id, error=str(e))
            raise
    
    def query_knowledge(self, query: KnowledgeQuery) -> KnowledgeResult:
        """查询知识库（支持优先级和缓存）"""
        start_time = time.time()
        
        # 生成缓存键
        cache_key = self._generate_cache_key(query)
        
        # 尝试从缓存获取
        cached_result = self.cache.get(cache_key)
        if cached_result:
            cached_result.cache_hit = True
            cached_result.response_time = time.time() - start_time
            self.query_stats[f"{query.query_type}_cache_hit"] += 1
            self.query_stats[f"{query.query_type}_query"] += 1  # 也算作一次查询
            return cached_result
        
        # 确保项目知识已加载
        if query.project_id:
            self.load_project_knowledge(query.project_id)
        
        # 按优先级查询
        result = self._query_by_priority(query)
        
        # 计算响应时间
        result.response_time = time.time() - start_time
        
        # 缓存结果（包括空结果，避免重复查询）
        cache_ttl = self._get_cache_ttl(query.query_type)
        self.cache.put(cache_key, result, cache_ttl)
        
        # 更新统计
        self.query_stats[f"{query.query_type}_query"] += 1
        self.response_times[query.query_type].append(result.response_time)
        
        return result
    
    def _generate_cache_key(self, query: KnowledgeQuery) -> str:
        """生成缓存键"""
        key_parts = [
            query.query_type,
            query.source_text,
            query.target_language,
            query.project_id or "no_project",
            query.genre or "no_genre"
        ]
        
        # 添加重要的上下文信息
        if query.context:
            context_key = "_".join(f"{k}:{v}" for k, v in sorted(query.context.items()) 
                                 if k in ["speaker", "scene", "emotion"])
            if context_key:
                key_parts.append(context_key)
        
        return "|".join(key_parts)
    
    def _get_cache_ttl(self, query_type: str) -> timedelta:
        """获取缓存TTL"""
        ttl_mapping = {
            "terminology": timedelta(hours=2),
            "translation_memory": timedelta(hours=1),
            "cultural": timedelta(hours=4),
            "context": timedelta(minutes=30)
        }
        return ttl_mapping.get(query_type, timedelta(hours=1))
    
    def _query_by_priority(self, query: KnowledgeQuery) -> KnowledgeResult:
        """按优先级查询知识库"""
        for level in query.priority_levels:
            try:
                results = self._query_at_level(query, level)
                if results:
                    confidence = self._calculate_confidence(results, level)
                    return KnowledgeResult(
                        query=query,
                        results=results,
                        source_level=level,
                        confidence=confidence,
                        metadata={"level": level.value}
                    )
            except Exception as e:
                logger.warning("查询知识库失败", level=level.value, error=str(e))
                continue
        
        # 没有找到结果
        return KnowledgeResult(
            query=query,
            results=[],
            source_level=KnowledgeLevel.GLOBAL,
            confidence=0.0,
            metadata={"no_results": True}
        )
    
    def _query_at_level(self, query: KnowledgeQuery, level: KnowledgeLevel) -> List[Any]:
        """在指定层级查询知识库"""
        if query.query_type == "terminology":
            return self._query_terminology(query, level)
        elif query.query_type == "translation_memory":
            return self._query_translation_memory(query, level)
        elif query.query_type == "cultural":
            return self._query_cultural(query, level)
        elif query.query_type == "context":
            return self._query_context(query, level)
        else:
            logger.warning("未知的查询类型", query_type=query.query_type)
            return []
    
    def _query_terminology(self, query: KnowledgeQuery, level: KnowledgeLevel) -> List[Any]:
        """查询术语库"""
        try:
            if level == KnowledgeLevel.PROJECT and query.project_id:
                return self.knowledge_manager.terminology_kb.search_terms(
                    query.source_text, query.target_language, 
                    project_id=query.project_id, genre=query.genre
                )
            elif level == KnowledgeLevel.GENRE and query.genre:
                return self.knowledge_manager.terminology_kb.search_terms(
                    query.source_text, query.target_language, genre=query.genre
                )
            elif level == KnowledgeLevel.GLOBAL:
                return self.knowledge_manager.terminology_kb.search_terms(
                    query.source_text, query.target_language
                )
        except Exception as e:
            logger.warning("术语查询失败", level=level.value, error=str(e))
        return []
    
    def _query_translation_memory(self, query: KnowledgeQuery, level: KnowledgeLevel) -> List[Any]:
        """查询翻译记忆库"""
        # 翻译记忆主要在全局层级，但可以根据项目过滤
        results = self.knowledge_manager.translation_memory_kb.search_memory_with_context(
            query.source_text, query.target_language, query.context
        )
        
        if level == KnowledgeLevel.PROJECT and query.project_id:
            # 过滤项目相关的记忆
            filtered_results = []
            for memory, text_sim, context_sim in results:
                if hasattr(memory, 'project_id') and memory.project_id == query.project_id:
                    filtered_results.append((memory, text_sim, context_sim))
            return filtered_results
        
        return results
    
    def _query_cultural(self, query: KnowledgeQuery, level: KnowledgeLevel) -> List[Any]:
        """查询文化适配库"""
        adaptation = self.knowledge_manager.cultural_kb.get_cultural_adaptation(
            query.source_text, query.target_language, query.context
        )
        return [adaptation] if adaptation else []
    
    def _query_context(self, query: KnowledgeQuery, level: KnowledgeLevel) -> List[Any]:
        """查询上下文信息"""
        # 这里可以查询故事上下文、人物关系等
        if query.project_id:
            try:
                # 获取项目的故事上下文
                project_config = self.project_manager.get_project(query.project_id)
                if project_config:
                    return [project_config]
            except Exception as e:
                logger.warning("获取项目上下文失败", project_id=query.project_id, error=str(e))
        
        return []
    
    def _calculate_confidence(self, results: List[Any], level: KnowledgeLevel) -> float:
        """计算结果置信度"""
        if not results:
            return 0.0
        
        # 基础置信度根据层级确定
        base_confidence = {
            KnowledgeLevel.PROJECT: 0.9,
            KnowledgeLevel.GENRE: 0.7,
            KnowledgeLevel.GLOBAL: 0.5
        }.get(level, 0.5)
        
        # 根据结果数量和质量调整
        result_count_factor = min(len(results) / 3.0, 1.0)  # 最多3个结果时达到满分
        
        # 如果结果有置信度信息，使用平均置信度
        confidences = []
        for result in results:
            if hasattr(result, 'confidence_score'):
                confidences.append(result.confidence_score)
            elif hasattr(result, 'quality_score'):
                confidences.append(result.quality_score)
        
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            return min(base_confidence * result_count_factor * avg_confidence, 1.0)
        
        return min(base_confidence * result_count_factor, 1.0)
    
    def update_knowledge(self, knowledge_type: str, data: Any, project_id: str = None):
        """更新知识库"""
        try:
            if knowledge_type == "terminology" and isinstance(data, TerminologyEntry):
                if project_id:
                    self.knowledge_manager.terminology_kb.add_term(data, "project", project_id=project_id)
                else:
                    self.knowledge_manager.terminology_kb.add_term(data, "global")
            
            elif knowledge_type == "translation_memory" and isinstance(data, TranslationMemory):
                self.knowledge_manager.translation_memory_kb.add_memory(data)
            
            elif knowledge_type == "cultural":
                # 处理文化适配数据更新
                pass
            
            # 清除相关缓存
            self._invalidate_cache(knowledge_type, project_id)
            
            logger.info("知识库已更新", type=knowledge_type, project_id=project_id)
            
        except Exception as e:
            logger.error("更新知识库失败", type=knowledge_type, error=str(e))
            raise
    
    def _invalidate_cache(self, knowledge_type: str, project_id: str = None):
        """使相关缓存失效"""
        keys_to_remove = []
        
        for key in self.cache.cache.keys():
            if knowledge_type in key:
                if project_id is None or project_id in key:
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self.cache.cache:
                del self.cache.cache[key]
            if key in self.cache.access_order:
                self.cache.access_order.remove(key)
        
        logger.debug("缓存已失效", type=knowledge_type, project_id=project_id, 
                    invalidated_keys=len(keys_to_remove))
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        cache_stats = self.cache.get_stats()
        
        # 计算平均响应时间
        avg_response_times = {}
        for query_type, times in self.response_times.items():
            if times:
                avg_response_times[query_type] = sum(times) / len(times)
        
        return {
            "cache": cache_stats,
            "queries": dict(self.query_stats),
            "avg_response_times": avg_response_times,
            "loaded_projects": len(self.loaded_projects),
            "last_update_check": self.last_update_check.isoformat()
        }
    
    def optimize_performance(self):
        """性能优化"""
        # 清理长时间未访问的响应时间记录
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for query_type in list(self.response_times.keys()):
            # 只保留最近的100个记录
            if len(self.response_times[query_type]) > 100:
                self.response_times[query_type] = self.response_times[query_type][-100:]
        
        # 调整缓存策略
        cache_stats = self.cache.get_stats()
        if cache_stats["hit_rate"] < 0.3:  # 命中率过低
            logger.info("缓存命中率过低，调整策略", hit_rate=cache_stats["hit_rate"])
            # 可以考虑调整缓存大小或策略
        
        logger.info("性能优化完成")
    
    def shutdown(self):
        """关闭动态知识库管理器"""
        logger.info("正在关闭动态知识库管理器")
        
        # 停止后台更新
        self.stop_background_updates()
        
        # 保存知识库
        try:
            self.knowledge_manager.save_all_knowledge_bases()
        except Exception as e:
            logger.error("保存知识库失败", error=str(e))
        
        # 清空缓存
        self.cache.clear()
        
        logger.info("动态知识库管理器已关闭")


# 全局动态知识库管理器实例
dynamic_knowledge_manager = DynamicKnowledgeBase()


def get_dynamic_knowledge_manager() -> DynamicKnowledgeBase:
    """获取动态知识库管理器实例"""
    return dynamic_knowledge_manager