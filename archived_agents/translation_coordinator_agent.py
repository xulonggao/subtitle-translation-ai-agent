"""
翻译协调 Agent
使用 Strands SDK 创建的翻译协调代理，负责整合任务调度、术语管理、质量检查等功能
"""
import json
import uuid
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from strands import Agent, tool
from config import get_logger
from models.subtitle_models import SubtitleEntry
from models.translation_models import TranslationTask, TranslationResult
from agents.translation_scheduler import TranslationScheduler, TaskPriority
from agents.terminology_consistency_manager import (
    TerminologyConsistencyManager, ConsistencyCheckRequest, ConsistencyCheckResult
)
from agents.progress_monitor import MonitoringSystem, ProgressStatus, AlertLevel, MonitoringEvent
from agents.english_translation_agent import EnglishTranslationAgent
from agents.asian_translation_agent import AsianTranslationAgent
from agents.european_arabic_translation_agent import EuropeanArabicTranslationAgent

logger = get_logger("translation_coordinator_agent")


class CoordinationStatus(Enum):
    """协调状态"""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


class QualityThreshold(Enum):
    """质量阈值"""
    MINIMUM = 0.6      # 最低质量要求
    ACCEPTABLE = 0.7   # 可接受质量
    GOOD = 0.8         # 良好质量
    EXCELLENT = 0.9    # 优秀质量


@dataclass
class CoordinationRequest:
    """协调请求"""
    request_id: str
    project_id: str
    subtitle_entries: List[SubtitleEntry]
    target_languages: List[str]
    quality_threshold: float = 0.8
    priority: TaskPriority = TaskPriority.NORMAL
    deadline: Optional[datetime] = None
    special_requirements: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class CoordinationResult:
    """协调结果"""
    request_id: str
    success: bool
    translation_results: Dict[str, List[TranslationResult]]  # {language: results}
    quality_scores: Dict[str, float]  # {language: score}
    consistency_results: Optional[ConsistencyCheckResult] = None
    total_processing_time_ms: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    error_message: Optional[str] = None
    recommendations: List[str] = None
    completed_at: datetime = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []
        if self.completed_at is None:
            self.completed_at = datetime.now()


class TranslationCoordinatorAgent(Agent):
    """翻译协调 Agent
    
    主要功能：
    1. 协调多语言翻译任务
    2. 集成任务调度和术语管理
    3. 监控翻译质量和进度
    4. 生成综合报告和建议
    """
    
    def __init__(self, agent_id: str = None):
        super().__init__(
            agent_id=agent_id or f"translation_coordinator_{uuid.uuid4().hex[:8]}",
            name="Translation Coordinator Agent",
            description="协调和管理多语言字幕翻译任务的智能代理"
        )
        
        # 初始化组件
        self.scheduler = TranslationScheduler()
        self.terminology_manager = TerminologyConsistencyManager()
        self.monitoring_system = MonitoringSystem(f"{self.agent_id}_monitor")
        
        # 初始化翻译 Agent
        self.translation_agents = {
            "english": EnglishTranslationAgent(),
            "asian": AsianTranslationAgent(),
            "european_arabic": EuropeanArabicTranslationAgent()
        }
        
        # 状态管理
        self.current_status = CoordinationStatus.IDLE
        self.active_requests: Dict[str, CoordinationRequest] = {}
        self.completed_requests: Dict[str, CoordinationResult] = {}
        
        # 配置参数
        self.max_concurrent_tasks = 5
        self.default_quality_threshold = 0.8
        self.consistency_check_enabled = True
        self.auto_retry_failed_tasks = True
        self.max_retry_attempts = 3
        
        # 性能统计
        self.performance_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0.0,
            "average_quality_score": 0.0,
            "languages_processed": set(),
            "total_subtitles_translated": 0
        }
        
        # 启动监控系统
        self.monitoring_system.start()
        
        logger.info("翻译协调 Agent 初始化完成", agent_id=self.agent_id)
    
    @tool
    async def coordinate_translation(self, request: CoordinationRequest) -> CoordinationResult:
        """协调翻译任务
        
        Args:
            request: 协调请求
            
        Returns:
            CoordinationResult: 协调结果
        """
        start_time = datetime.now()
        self.current_status = CoordinationStatus.PLANNING
        
        logger.info("开始协调翻译任务",
                   request_id=request.request_id,
                   project_id=request.project_id,
                   target_languages=request.target_languages,
                   subtitles_count=len(request.subtitle_entries))
        
        try:
            # 添加到活跃请求
            self.active_requests[request.request_id] = request
            
            # 开始进度跟踪
            self.monitoring_system.progress_tracker.start_tracking(
                project_id=request.project_id,
                task_id=request.request_id,
                total_items=len(request.subtitle_entries) * len(request.target_languages),
                current_stage="规划阶段"
            )
            
            # 1. 规划翻译任务
            translation_plan = await self._create_translation_plan(request)
            
            # 2. 执行翻译任务
            self.current_status = CoordinationStatus.EXECUTING
            translation_results = await self._execute_translation_plan(request, translation_plan)
            
            # 3. 质量检查
            self.current_status = CoordinationStatus.REVIEWING
            quality_scores = await self._perform_quality_check(request, translation_results)
            
            # 4. 术语一致性检查
            consistency_result = None
            if self.consistency_check_enabled:
                consistency_result = await self._check_terminology_consistency(request, translation_results)
            
            # 5. 生成结果和建议
            result = await self._generate_coordination_result(
                request, translation_results, quality_scores, consistency_result, start_time
            )
            
            # 更新统计和状态
            self._update_performance_stats(request, result)
            self.current_status = CoordinationStatus.COMPLETED
            
            # 完成进度跟踪
            self.monitoring_system.progress_tracker.complete_task(
                request.request_id, success=result.success
            )
            
            # 移动到已完成请求
            self.completed_requests[request.request_id] = result
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]
            
            logger.info("翻译协调任务完成",
                       request_id=request.request_id,
                       success=result.success,
                       processing_time_ms=result.total_processing_time_ms,
                       tasks_completed=result.tasks_completed,
                       tasks_failed=result.tasks_failed)
            
            return result
            
        except Exception as e:
            self.current_status = CoordinationStatus.FAILED
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 记录错误
            self.monitoring_system.error_tracker.record_error(
                error_type=type(e).__name__,
                error_message=str(e),
                task_id=request.request_id,
                context={"project_id": request.project_id}
            )
            
            # 创建失败告警
            self.monitoring_system.alert_manager.create_alert(
                level=AlertLevel.ERROR,
                title="翻译协调任务失败",
                message=f"请求 {request.request_id} 处理失败: {str(e)}",
                source="translation_coordinator",
                event_type=MonitoringEvent.TASK_FAILED,
                metadata={"request_id": request.request_id, "error": str(e)}
            )
            
            logger.error("翻译协调任务失败",
                        request_id=request.request_id,
                        error=str(e),
                        processing_time_ms=int(processing_time))
            
            # 完成进度跟踪（失败）
            self.monitoring_system.progress_tracker.complete_task(
                request.request_id, success=False
            )
            
            result = CoordinationResult(
                request_id=request.request_id,
                success=False,
                translation_results={},
                quality_scores={},
                total_processing_time_ms=int(processing_time),
                error_message=str(e)
            )
            
            self.completed_requests[request.request_id] = result
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]
            
            return result
    
    async def _create_translation_plan(self, request: CoordinationRequest) -> Dict[str, Any]:
        """创建翻译计划"""
        logger.debug("创建翻译计划", request_id=request.request_id)
        
        # 更新进度
        self.monitoring_system.progress_tracker.update_progress(
            request.request_id, current_stage="创建翻译计划"
        )
        
        # 分析字幕内容
        content_analysis = self._analyze_subtitle_content(request.subtitle_entries)
        
        # 确定翻译策略
        translation_strategy = self._determine_translation_strategy(
            request.target_languages, content_analysis
        )
        
        # 创建任务分组
        task_groups = self._create_task_groups(
            request.subtitle_entries, request.target_languages, translation_strategy
        )
        
        # 估算资源需求
        resource_requirements = self._estimate_resource_requirements(task_groups)
        
        plan = {
            "request_id": request.request_id,
            "content_analysis": content_analysis,
            "translation_strategy": translation_strategy,
            "task_groups": task_groups,
            "resource_requirements": resource_requirements,
            "estimated_completion_time": self._estimate_completion_time(task_groups),
            "created_at": datetime.now()
        }
        
        logger.debug("翻译计划创建完成",
                    request_id=request.request_id,
                    task_groups_count=len(task_groups),
                    estimated_time=plan["estimated_completion_time"])
        
        return plan
    
    def _analyze_subtitle_content(self, subtitle_entries: List[SubtitleEntry]) -> Dict[str, Any]:
        """分析字幕内容"""
        total_characters = sum(len(entry.text) for entry in subtitle_entries)
        total_duration = sum(entry.duration for entry in subtitle_entries)
        
        # 检测内容类型
        content_types = set()
        for entry in subtitle_entries:
            text = entry.text.lower()
            if any(word in text for word in ["司令", "部队", "军事", "战斗"]):
                content_types.add("military")
            if any(word in text for word in ["医生", "医院", "治疗", "病人"]):
                content_types.add("medical")
            if any(word in text for word in ["法官", "法庭", "律师", "法律"]):
                content_types.add("legal")
            if any(word in text for word in ["爱", "心", "感情", "恋人"]):
                content_types.add("romance")
        
        # 检测说话人数量
        speakers = set()
        for entry in subtitle_entries:
            if entry.speaker:
                speakers.add(entry.speaker)
        
        return {
            "total_entries": len(subtitle_entries),
            "total_characters": total_characters,
            "total_duration": total_duration,
            "average_entry_length": total_characters / len(subtitle_entries) if subtitle_entries else 0,
            "content_types": list(content_types),
            "speakers_count": len(speakers),
            "complexity_score": self._calculate_complexity_score(subtitle_entries)
        }
    
    def _calculate_complexity_score(self, subtitle_entries: List[SubtitleEntry]) -> float:
        """计算内容复杂度分数"""
        score = 0.0
        
        for entry in subtitle_entries:
            text = entry.text
            
            # 长度复杂度
            if len(text) > 50:
                score += 0.1
            
            # 专业术语复杂度
            if any(term in text for term in ["技术", "专业", "系统", "设备"]):
                score += 0.2
            
            # 文化词汇复杂度
            if any(term in text for term in ["传统", "文化", "习俗", "礼仪"]):
                score += 0.15
            
            # 情感表达复杂度
            if any(term in text for term in ["感动", "激动", "愤怒", "悲伤"]):
                score += 0.1
        
        return min(score / len(subtitle_entries) if subtitle_entries else 0, 1.0)
    
    def _determine_translation_strategy(self, target_languages: List[str], 
                                      content_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """确定翻译策略"""
        strategy = {
            "parallel_processing": len(target_languages) > 1,
            "quality_priority": content_analysis["complexity_score"] > 0.7,
            "speed_priority": content_analysis["complexity_score"] < 0.3,
            "cultural_adaptation_required": "romance" in content_analysis["content_types"],
            "technical_accuracy_required": any(t in content_analysis["content_types"] 
                                             for t in ["military", "medical", "legal"]),
            "batch_size": self._determine_batch_size(content_analysis),
            "agent_assignment": self._assign_agents_to_languages(target_languages)
        }
        
        return strategy
    
    def _determine_batch_size(self, content_analysis: Dict[str, Any]) -> int:
        """确定批处理大小"""
        base_size = 20
        
        # 根据复杂度调整
        if content_analysis["complexity_score"] > 0.7:
            return max(5, base_size // 2)  # 复杂内容用小批次
        elif content_analysis["complexity_score"] < 0.3:
            return min(50, base_size * 2)  # 简单内容用大批次
        
        return base_size
    
    def _assign_agents_to_languages(self, target_languages: List[str]) -> Dict[str, str]:
        """为语言分配翻译 Agent"""
        assignment = {}
        
        for language in target_languages:
            if language in ["en"]:
                assignment[language] = "english"
            elif language in ["ja", "ko", "th", "vi", "id", "ms"]:
                assignment[language] = "asian"
            elif language in ["es", "pt", "ar"]:
                assignment[language] = "european_arabic"
            else:
                # 默认使用英语 Agent
                assignment[language] = "english"
        
        return assignment
    
    def _create_task_groups(self, subtitle_entries: List[SubtitleEntry], 
                          target_languages: List[str], 
                          strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建任务分组"""
        task_groups = []
        batch_size = strategy["batch_size"]
        
        # 按批次分组字幕
        for i in range(0, len(subtitle_entries), batch_size):
            batch_entries = subtitle_entries[i:i + batch_size]
            
            for language in target_languages:
                agent_type = strategy["agent_assignment"][language]
                
                task_group = {
                    "group_id": f"group_{i//batch_size}_{language}",
                    "subtitle_entries": batch_entries,
                    "target_language": language,
                    "agent_type": agent_type,
                    "priority": TaskPriority.HIGH if strategy["quality_priority"] else TaskPriority.NORMAL,
                    "special_requirements": {
                        "cultural_adaptation": strategy["cultural_adaptation_required"],
                        "technical_accuracy": strategy["technical_accuracy_required"]
                    }
                }
                
                task_groups.append(task_group)
        
        return task_groups
    
    def _estimate_resource_requirements(self, task_groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """估算资源需求"""
        total_entries = sum(len(group["subtitle_entries"]) for group in task_groups)
        total_languages = len(set(group["target_language"] for group in task_groups))
        
        # 估算处理时间（每个字幕条目平均2秒）
        estimated_time_seconds = total_entries * 2
        
        # 估算内存需求（每个条目约1KB）
        estimated_memory_mb = total_entries * 0.001
        
        return {
            "total_tasks": len(task_groups),
            "total_entries": total_entries,
            "total_languages": total_languages,
            "estimated_time_seconds": estimated_time_seconds,
            "estimated_memory_mb": estimated_memory_mb,
            "concurrent_tasks_recommended": min(self.max_concurrent_tasks, len(task_groups))
        }
    
    def _estimate_completion_time(self, task_groups: List[Dict[str, Any]]) -> datetime:
        """估算完成时间"""
        total_entries = sum(len(group["subtitle_entries"]) for group in task_groups)
        
        # 基础处理时间：每个条目2秒
        base_time_seconds = total_entries * 2
        
        # 并发处理调整
        concurrent_factor = min(self.max_concurrent_tasks, len(task_groups))
        adjusted_time_seconds = base_time_seconds / concurrent_factor
        
        # 添加缓冲时间（20%）
        final_time_seconds = adjusted_time_seconds * 1.2
        
        return datetime.now() + timedelta(seconds=final_time_seconds)
    
    async def _execute_translation_plan(self, request: CoordinationRequest, 
                                       plan: Dict[str, Any]) -> Dict[str, List[TranslationResult]]:
        """执行翻译计划"""
        logger.debug("开始执行翻译计划", request_id=request.request_id)
        
        # 更新进度
        self.monitoring_system.progress_tracker.update_progress(
            request.request_id, current_stage="执行翻译"
        )
        
        translation_results = {}
        task_groups = plan["task_groups"]
        completed_tasks = 0
        failed_tasks = 0
        
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        
        async def process_task_group(group: Dict[str, Any]) -> Tuple[str, List[TranslationResult]]:
            """处理单个任务组"""
            async with semaphore:
                try:
                    agent_type = group["agent_type"]
                    target_language = group["target_language"]
                    subtitle_entries = group["subtitle_entries"]
                    
                    # 获取对应的翻译 Agent
                    translation_agent = self.translation_agents[agent_type]
                    
                    # 创建翻译任务
                    translation_task = TranslationTask(
                        task_id=group["group_id"],
                        project_id=request.project_id,
                        subtitle_entries=subtitle_entries,
                        target_language=target_language,
                        priority=group["priority"],
                        special_requirements=group["special_requirements"]
                    )
                    
                    # 执行翻译
                    results = await translation_agent.translate_batch(translation_task)
                    
                    # 更新进度
                    nonlocal completed_tasks
                    completed_tasks += 1
                    self.monitoring_system.progress_tracker.update_progress(
                        request.request_id,
                        completed_items=completed_tasks * len(subtitle_entries),
                        current_stage=f"翻译进行中 ({completed_tasks}/{len(task_groups)})"
                    )
                    
                    logger.debug("任务组处理完成",
                               group_id=group["group_id"],
                               language=target_language,
                               results_count=len(results))
                    
                    return target_language, results
                    
                except Exception as e:
                    nonlocal failed_tasks
                    failed_tasks += 1
                    
                    # 记录错误
                    self.monitoring_system.error_tracker.record_error(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        task_id=group["group_id"],
                        context={
                            "language": group["target_language"],
                            "agent_type": group["agent_type"]
                        }
                    )
                    
                    logger.error("任务组处理失败",
                               group_id=group["group_id"],
                               language=group["target_language"],
                               error=str(e))
                    
                    # 如果启用自动重试
                    if self.auto_retry_failed_tasks:
                        return await self._retry_task_group(group, e)
                    
                    raise e
        
        # 并发执行所有任务组
        tasks = [process_task_group(group) for group in task_groups]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 整理结果
        for result in results:
            if isinstance(result, Exception):
                logger.error("任务组执行异常", error=str(result))
                continue
            
            language, lang_results = result
            if language not in translation_results:
                translation_results[language] = []
            translation_results[language].extend(lang_results)
        
        logger.info("翻译计划执行完成",
                   request_id=request.request_id,
                   completed_tasks=completed_tasks,
                   failed_tasks=failed_tasks,
                   languages=list(translation_results.keys()))
        
        return translation_results
    
    async def _retry_task_group(self, group: Dict[str, Any], 
                              original_error: Exception) -> Tuple[str, List[TranslationResult]]:
        """重试失败的任务组"""
        max_retries = self.max_retry_attempts
        
        for attempt in range(max_retries):
            try:
                logger.info("重试任务组",
                           group_id=group["group_id"],
                           attempt=attempt + 1,
                           max_retries=max_retries)
                
                # 等待一段时间再重试
                await asyncio.sleep(2 ** attempt)  # 指数退避
                
                # 重新执行任务
                agent_type = group["agent_type"]
                translation_agent = self.translation_agents[agent_type]
                
                translation_task = TranslationTask(
                    task_id=f"{group['group_id']}_retry_{attempt}",
                    project_id=group.get("project_id", "unknown"),
                    subtitle_entries=group["subtitle_entries"],
                    target_language=group["target_language"],
                    priority=group["priority"],
                    special_requirements=group["special_requirements"]
                )
                
                results = await translation_agent.translate_batch(translation_task)
                
                logger.info("任务组重试成功",
                           group_id=group["group_id"],
                           attempt=attempt + 1)
                
                return group["target_language"], results
                
            except Exception as e:
                logger.warning("任务组重试失败",
                             group_id=group["group_id"],
                             attempt=attempt + 1,
                             error=str(e))
                
                if attempt == max_retries - 1:
                    # 最后一次重试也失败了
                    logger.error("任务组重试全部失败",
                               group_id=group["group_id"],
                               original_error=str(original_error),
                               final_error=str(e))
                    raise e
        
        return group["target_language"], []
    
    async def _perform_quality_check(self, request: CoordinationRequest,
                                   translation_results: Dict[str, List[TranslationResult]]) -> Dict[str, float]:
        """执行质量检查"""
        logger.debug("开始质量检查", request_id=request.request_id)
        
        # 更新进度
        self.monitoring_system.progress_tracker.update_progress(
            request.request_id, current_stage="质量检查"
        )
        
        quality_scores = {}
        
        for language, results in translation_results.items():
            try:
                # 计算质量分数
                language_score = await self._calculate_language_quality_score(
                    language, results, request.subtitle_entries
                )
                
                quality_scores[language] = language_score
                
                # 检查是否达到质量阈值
                if language_score < request.quality_threshold:
                    # 创建质量告警
                    self.monitoring_system.alert_manager.create_alert(
                        level=AlertLevel.WARNING,
                        title=f"翻译质量低于阈值",
                        message=f"语言 {language} 的翻译质量分数 {language_score:.2f} 低于要求的 {request.quality_threshold:.2f}",
                        source="quality_checker",
                        event_type=MonitoringEvent.PERFORMANCE_DEGRADED,
                        metadata={
                            "language": language,
                            "quality_score": language_score,
                            "threshold": request.quality_threshold
                        }
                    )
                
                logger.debug("语言质量检查完成",
                           language=language,
                           quality_score=language_score,
                           results_count=len(results))
                
            except Exception as e:
                logger.error("质量检查失败",
                           language=language,
                           error=str(e))
                quality_scores[language] = 0.0
        
        logger.info("质量检查完成",
                   request_id=request.request_id,
                   quality_scores=quality_scores)
        
        return quality_scores
    
    async def _calculate_language_quality_score(self, language: str, 
                                              results: List[TranslationResult],
                                              original_entries: List[SubtitleEntry]) -> float:
        """计算语言质量分数"""
        if not results:
            return 0.0
        
        total_score = 0.0
        valid_results = 0
        
        for result in results:
            if result.success and result.quality_score is not None:
                total_score += result.quality_score
                valid_results += 1
        
        if valid_results == 0:
            return 0.0
        
        base_score = total_score / valid_results
        
        # 应用语言特定的调整
        language_adjustment = self._get_language_quality_adjustment(language, results)
        
        # 应用长度一致性检查
        length_consistency = self._check_length_consistency(results, original_entries)
        
        # 综合计算最终分数
        final_score = base_score * 0.7 + language_adjustment * 0.2 + length_consistency * 0.1
        
        return min(max(final_score, 0.0), 1.0)
    
    def _get_language_quality_adjustment(self, language: str, 
                                       results: List[TranslationResult]) -> float:
        """获取语言特定的质量调整"""
        # 基础分数
        adjustment = 0.8
        
        # 根据语言特点调整
        if language in ["ja", "ko"]:
            # 日韩语言需要检查敬语使用
            adjustment += 0.1 if self._check_honorific_usage(results) else -0.1
        elif language in ["ar"]:
            # 阿拉伯语需要检查文本方向
            adjustment += 0.1 if self._check_rtl_formatting(results) else -0.1
        elif language in ["th", "vi"]:
            # 泰语越南语需要检查声调标记
            adjustment += 0.1 if self._check_tone_marks(results) else -0.1
        
        return min(max(adjustment, 0.0), 1.0)
    
    def _check_honorific_usage(self, results: List[TranslationResult]) -> bool:
        """检查敬语使用（日韩语）"""
        # 简化实现：检查是否包含常见敬语表达
        honorific_patterns = ["です", "ます", "さん", "님", "습니다"]
        
        honorific_count = 0
        for result in results:
            if any(pattern in result.translated_text for pattern in honorific_patterns):
                honorific_count += 1
        
        # 如果超过30%的结果包含敬语，认为使用合适
        return honorific_count / len(results) > 0.3 if results else False
    
    def _check_rtl_formatting(self, results: List[TranslationResult]) -> bool:
        """检查从右到左格式（阿拉伯语）"""
        # 简化实现：检查是否包含阿拉伯字符
        arabic_pattern = r'[\u0600-\u06FF]'
        import re
        
        arabic_count = 0
        for result in results:
            if re.search(arabic_pattern, result.translated_text):
                arabic_count += 1
        
        return arabic_count / len(results) > 0.8 if results else False
    
    def _check_tone_marks(self, results: List[TranslationResult]) -> bool:
        """检查声调标记（泰语越南语）"""
        # 简化实现：检查是否包含声调字符
        tone_patterns = [
            r'[\u0E00-\u0E7F]',  # 泰语
            r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]'  # 越南语
        ]
        
        import re
        tone_count = 0
        for result in results:
            if any(re.search(pattern, result.translated_text) for pattern in tone_patterns):
                tone_count += 1
        
        return tone_count / len(results) > 0.5 if results else False
    
    def _check_length_consistency(self, results: List[TranslationResult],
                                original_entries: List[SubtitleEntry]) -> float:
        """检查长度一致性"""
        if not results or not original_entries:
            return 0.0
        
        consistency_scores = []
        
        for i, result in enumerate(results):
            if i < len(original_entries):
                original_length = len(original_entries[i].text)
                translated_length = len(result.translated_text)
                
                # 计算长度比例
                if original_length > 0:
                    length_ratio = translated_length / original_length
                    # 理想比例在0.8-1.5之间
                    if 0.8 <= length_ratio <= 1.5:
                        consistency_scores.append(1.0)
                    elif 0.6 <= length_ratio <= 2.0:
                        consistency_scores.append(0.7)
                    else:
                        consistency_scores.append(0.3)
                else:
                    consistency_scores.append(0.5)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.0
    
    async def _check_terminology_consistency(self, request: CoordinationRequest,
                                           translation_results: Dict[str, List[TranslationResult]]) -> ConsistencyCheckResult:
        """检查术语一致性"""
        logger.debug("开始术语一致性检查", request_id=request.request_id)
        
        # 更新进度
        self.monitoring_system.progress_tracker.update_progress(
            request.request_id, current_stage="术语一致性检查"
        )
        
        try:
            # 创建一致性检查请求
            consistency_request = ConsistencyCheckRequest(
                request_id=f"{request.request_id}_consistency",
                project_id=request.project_id,
                subtitle_entries=request.subtitle_entries,
                target_languages=list(translation_results.keys()),
                check_scope="project",
                strict_mode=False,
                auto_resolve=True
            )
            
            # 执行一致性检查
            result = self.terminology_manager.check_consistency(consistency_request)
            
            logger.info("术语一致性检查完成",
                       request_id=request.request_id,
                       consistency_score=result.consistency_score,
                       conflicts_found=result.conflicting_terms_count)
            
            return result
            
        except Exception as e:
            logger.error("术语一致性检查失败",
                        request_id=request.request_id,
                        error=str(e))
            
            # 返回默认结果
            return ConsistencyCheckResult(
                request_id=f"{request.request_id}_consistency",
                success=False,
                conflicts_found=[],
                consistency_score=0.0,
                total_terms_checked=0,
                conflicting_terms_count=0,
                error_message=str(e)
            )
    
    async def _generate_coordination_result(self, request: CoordinationRequest,
                                          translation_results: Dict[str, List[TranslationResult]],
                                          quality_scores: Dict[str, float],
                                          consistency_result: Optional[ConsistencyCheckResult],
                                          start_time: datetime) -> CoordinationResult:
        """生成协调结果"""
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # 统计任务完成情况
        tasks_completed = sum(len(results) for results in translation_results.values())
        tasks_failed = sum(1 for results in translation_results.values() 
                          for result in results if not result.success)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            request, translation_results, quality_scores, consistency_result
        )
        
        # 判断整体成功状态
        success = (
            len(translation_results) == len(request.target_languages) and
            all(score >= request.quality_threshold for score in quality_scores.values()) and
            (consistency_result is None or consistency_result.consistency_score >= 0.7)
        )
        
        result = CoordinationResult(
            request_id=request.request_id,
            success=success,
            translation_results=translation_results,
            quality_scores=quality_scores,
            consistency_results=consistency_result,
            total_processing_time_ms=int(processing_time),
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            recommendations=recommendations
        )
        
        return result
    
    def _generate_recommendations(self, request: CoordinationRequest,
                                translation_results: Dict[str, List[TranslationResult]],
                                quality_scores: Dict[str, float],
                                consistency_result: Optional[ConsistencyCheckResult]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 质量相关建议
        for language, score in quality_scores.items():
            if score < request.quality_threshold:
                recommendations.append(
                    f"建议对 {language} 语言的翻译进行人工审核，当前质量分数 {score:.2f} 低于要求的 {request.quality_threshold:.2f}"
                )
            elif score < 0.8:
                recommendations.append(
                    f"建议优化 {language} 语言的翻译质量，当前分数为 {score:.2f}"
                )
        
        # 一致性相关建议
        if consistency_result and consistency_result.consistency_score < 0.8:
            recommendations.append(
                f"建议检查术语一致性，当前一致性分数为 {consistency_result.consistency_score:.2f}"
            )
            
            if consistency_result.conflicting_terms_count > 0:
                recommendations.append(
                    f"发现 {consistency_result.conflicting_terms_count} 个术语冲突，建议进行人工审核"
                )
        
        # 性能相关建议
        avg_quality = sum(quality_scores.values()) / len(quality_scores) if quality_scores else 0
        if avg_quality > 0.9:
            recommendations.append("翻译质量优秀，可以考虑提高处理速度以提升效率")
        elif avg_quality < 0.7:
            recommendations.append("建议降低处理速度，专注于提升翻译质量")
        
        # 语言特定建议
        for language in request.target_languages:
            if language in ["ja", "ko"] and language in quality_scores:
                if quality_scores[language] < 0.8:
                    recommendations.append(f"建议检查 {language} 语言的敬语使用是否恰当")
            elif language == "ar" and language in quality_scores:
                if quality_scores[language] < 0.8:
                    recommendations.append("建议检查阿拉伯语的文本方向和格式是否正确")
        
        return recommendations
    
    def _update_performance_stats(self, request: CoordinationRequest, result: CoordinationResult):
        """更新性能统计"""
        self.performance_stats["total_requests"] += 1
        
        if result.success:
            self.performance_stats["successful_requests"] += 1
        else:
            self.performance_stats["failed_requests"] += 1
        
        # 更新平均处理时间
        total_time = (self.performance_stats["average_processing_time"] * 
                     (self.performance_stats["total_requests"] - 1) + 
                     result.total_processing_time_ms)
        self.performance_stats["average_processing_time"] = total_time / self.performance_stats["total_requests"]
        
        # 更新平均质量分数
        if result.quality_scores:
            avg_quality = sum(result.quality_scores.values()) / len(result.quality_scores)
            total_quality = (self.performance_stats["average_quality_score"] * 
                           (self.performance_stats["total_requests"] - 1) + avg_quality)
            self.performance_stats["average_quality_score"] = total_quality / self.performance_stats["total_requests"]
        
        # 更新语言处理统计
        self.performance_stats["languages_processed"].update(request.target_languages)
        self.performance_stats["total_subtitles_translated"] += len(request.subtitle_entries) * len(request.target_languages)
    
    @tool
    async def get_coordination_status(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """获取协调状态
        
        Args:
            request_id: 可选的请求ID，如果提供则返回特定请求的状态
            
        Returns:
            Dict[str, Any]: 状态信息
        """
        if request_id:
            # 返回特定请求的状态
            if request_id in self.active_requests:
                request = self.active_requests[request_id]
                progress = self.monitoring_system.progress_tracker.get_current_progress(request_id)
                
                return {
                    "request_id": request_id,
                    "status": "active",
                    "project_id": request.project_id,
                    "target_languages": request.target_languages,
                    "progress": {
                        "percentage": progress.progress_percentage if progress else 0,
                        "current_stage": progress.current_stage if progress else "unknown",
                        "processing_rate": progress.processing_rate if progress else 0,
                        "estimated_completion": progress.estimated_completion_time.isoformat() if progress and progress.estimated_completion_time else None
                    },
                    "created_at": request.created_at.isoformat()
                }
            elif request_id in self.completed_requests:
                result = self.completed_requests[request_id]
                return {
                    "request_id": request_id,
                    "status": "completed",
                    "success": result.success,
                    "quality_scores": result.quality_scores,
                    "processing_time_ms": result.total_processing_time_ms,
                    "completed_at": result.completed_at.isoformat()
                }
            else:
                return {
                    "request_id": request_id,
                    "status": "not_found",
                    "error": "Request not found"
                }
        else:
            # 返回整体状态
            return {
                "agent_id": self.agent_id,
                "current_status": self.current_status.value,
                "active_requests_count": len(self.active_requests),
                "completed_requests_count": len(self.completed_requests),
                "performance_stats": self.performance_stats.copy(),
                "system_status": self.monitoring_system.get_system_status()
            }
    
    @tool
    async def get_performance_report(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """获取性能报告
        
        Args:
            time_window_hours: 时间窗口（小时）
            
        Returns:
            Dict[str, Any]: 性能报告
        """
        # 获取监控系统的综合报告
        monitoring_report = self.monitoring_system.create_comprehensive_report(time_window_hours)
        
        # 添加协调器特定的统计
        coordinator_stats = {
            "coordination_stats": self.performance_stats.copy(),
            "active_requests": [
                {
                    "request_id": req_id,
                    "project_id": req.project_id,
                    "target_languages": req.target_languages,
                    "created_at": req.created_at.isoformat()
                }
                for req_id, req in self.active_requests.items()
            ],
            "recent_completions": [
                {
                    "request_id": result.request_id,
                    "success": result.success,
                    "quality_scores": result.quality_scores,
                    "processing_time_ms": result.total_processing_time_ms,
                    "completed_at": result.completed_at.isoformat()
                }
                for result in list(self.completed_requests.values())[-10:]  # 最近10个
            ]
        }
        
        # 合并报告
        monitoring_report.update(coordinator_stats)
        
        return monitoring_report
    
    @tool
    async def cancel_request(self, request_id: str) -> Dict[str, Any]:
        """取消协调请求
        
        Args:
            request_id: 请求ID
            
        Returns:
            Dict[str, Any]: 取消结果
        """
        if request_id not in self.active_requests:
            return {
                "success": False,
                "error": "Request not found or already completed"
            }
        
        try:
            # 标记任务为取消
            self.monitoring_system.progress_tracker.complete_task(request_id, success=False)
            
            # 创建取消告警
            self.monitoring_system.alert_manager.create_alert(
                level=AlertLevel.INFO,
                title="翻译请求已取消",
                message=f"请求 {request_id} 已被用户取消",
                source="translation_coordinator",
                event_type=MonitoringEvent.TASK_CANCELLED,
                metadata={"request_id": request_id}
            )
            
            # 移动到已完成列表
            request = self.active_requests[request_id]
            result = CoordinationResult(
                request_id=request_id,
                success=False,
                translation_results={},
                quality_scores={},
                error_message="Request cancelled by user"
            )
            
            self.completed_requests[request_id] = result
            del self.active_requests[request_id]
            
            logger.info("翻译请求已取消", request_id=request_id)
            
            return {
                "success": True,
                "message": f"Request {request_id} has been cancelled"
            }
            
        except Exception as e:
            logger.error("取消请求失败", request_id=request_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    @tool
    async def update_configuration(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置
        
        Args:
            config_updates: 配置更新
            
        Returns:
            Dict[str, Any]: 更新结果
        """
        try:
            updated_fields = []
            
            # 更新并发任务数
            if "max_concurrent_tasks" in config_updates:
                self.max_concurrent_tasks = config_updates["max_concurrent_tasks"]
                updated_fields.append("max_concurrent_tasks")
            
            # 更新默认质量阈值
            if "default_quality_threshold" in config_updates:
                self.default_quality_threshold = config_updates["default_quality_threshold"]
                updated_fields.append("default_quality_threshold")
            
            # 更新一致性检查开关
            if "consistency_check_enabled" in config_updates:
                self.consistency_check_enabled = config_updates["consistency_check_enabled"]
                updated_fields.append("consistency_check_enabled")
            
            # 更新自动重试开关
            if "auto_retry_failed_tasks" in config_updates:
                self.auto_retry_failed_tasks = config_updates["auto_retry_failed_tasks"]
                updated_fields.append("auto_retry_failed_tasks")
            
            # 更新最大重试次数
            if "max_retry_attempts" in config_updates:
                self.max_retry_attempts = config_updates["max_retry_attempts"]
                updated_fields.append("max_retry_attempts")
            
            logger.info("配置已更新", 
                       agent_id=self.agent_id,
                       updated_fields=updated_fields)
            
            return {
                "success": True,
                "updated_fields": updated_fields,
                "current_config": {
                    "max_concurrent_tasks": self.max_concurrent_tasks,
                    "default_quality_threshold": self.default_quality_threshold,
                    "consistency_check_enabled": self.consistency_check_enabled,
                    "auto_retry_failed_tasks": self.auto_retry_failed_tasks,
                    "max_retry_attempts": self.max_retry_attempts
                }
            }
            
        except Exception as e:
            logger.error("配置更新失败", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    @tool
    async def get_translation_agents_status(self) -> Dict[str, Any]:
        """获取翻译 Agent 状态
        
        Returns:
            Dict[str, Any]: 翻译 Agent 状态
        """
        agents_status = {}
        
        for agent_type, agent in self.translation_agents.items():
            try:
                # 获取 Agent 基本信息
                status = {
                    "agent_id": getattr(agent, 'agent_id', 'unknown'),
                    "agent_type": agent_type,
                    "status": "active",
                    "supported_languages": getattr(agent, 'supported_languages', []),
                }
                
                # 如果 Agent 有性能统计方法，获取统计信息
                if hasattr(agent, 'get_performance_stats'):
                    status["performance_stats"] = agent.get_performance_stats()
                
                agents_status[agent_type] = status
                
            except Exception as e:
                agents_status[agent_type] = {
                    "agent_type": agent_type,
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "total_agents": len(self.translation_agents),
            "agents": agents_status
        }
    
    async def shutdown(self):
        """关闭协调器"""
        logger.info("开始关闭翻译协调器", agent_id=self.agent_id)
        
        try:
            # 取消所有活跃请求
            for request_id in list(self.active_requests.keys()):
                await self.cancel_request(request_id)
            
            # 停止监控系统
            self.monitoring_system.stop()
            
            # 关闭翻译 Agent（如果有关闭方法）
            for agent_type, agent in self.translation_agents.items():
                if hasattr(agent, 'shutdown'):
                    try:
                        await agent.shutdown()
                    except Exception as e:
                        logger.warning(f"关闭 {agent_type} Agent 失败", error=str(e))
            
            self.current_status = CoordinationStatus.IDLE
            
            logger.info("翻译协调器已关闭", agent_id=self.agent_id)
            
        except Exception as e:
            logger.error("关闭翻译协调器失败", error=str(e))
            raise


# 导出主要类
__all__ = [
    'CoordinationStatus', 'QualityThreshold',
    'CoordinationRequest', 'CoordinationResult',
    'TranslationCoordinatorAgent'
]