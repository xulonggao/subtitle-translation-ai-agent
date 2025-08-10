"""
上下文管理 Agent
基于 Strands SDK 构建，集成知识库管理和对话跟踪功能
"""
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from config import get_logger
from models.subtitle_models import SubtitleEntry
from models.story_models import StoryContext, CharacterRelation
from agents.context_manager import get_context_manager
from agents.dynamic_knowledge_manager import get_dynamic_knowledge_manager, KnowledgeQuery
from agents.dialogue_context_tracker import get_dialogue_tracker, DialogueEntry

logger = get_logger("context_agent")


@dataclass
class ContextQuery:
    """上下文查询请求"""
    query_id: str
    project_id: str
    query_type: str  # "speaker_inference", "pronoun_resolution", "cultural_adaptation", "relationship_analysis"
    subtitle_entry: Optional[SubtitleEntry] = None
    dialogue_history: Optional[List[SubtitleEntry]] = None
    target_language: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ContextResponse:
    """上下文查询响应"""
    query_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    confidence: float = 0.0
    processing_time_ms: int = 0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ContextAgent:
    """上下文管理 Agent
    
    主要功能：
    1. 集成知识库管理和对话跟踪
    2. 提供统一的上下文查询接口
    3. 实现上下文推理和分析
    4. 支持多项目的上下文管理
    """
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or f"context_agent_{uuid.uuid4().hex[:8]}"
        
        # 集成现有组件
        self.context_manager = get_context_manager()
        self.dynamic_kb = get_dynamic_knowledge_manager()
        self.context_tracker = get_dialogue_tracker()
        
        # Agent 状态
        self.active_sessions: Dict[str, str] = {}  # session_id -> project_id
        self.query_history: List[ContextQuery] = []
        self.performance_metrics: Dict[str, Any] = {
            "total_queries": 0,
            "successful_queries": 0,
            "average_response_time": 0.0,
            "query_types": {}
        }
        
        # 查询处理器映射
        self.query_processors = {
            "speaker_inference": self._process_speaker_inference,
            "pronoun_resolution": self._process_pronoun_resolution,
            "cultural_adaptation": self._process_cultural_adaptation,
            "relationship_analysis": self._process_relationship_analysis,
            "context_summary": self._process_context_summary,
            "dialogue_analysis": self._process_dialogue_analysis,
            "knowledge_query": self._process_knowledge_query
        }
        
        logger.info("上下文管理 Agent 初始化完成", agent_id=self.agent_id)
    
    def start_session(self, project_id: str) -> str:
        """开始新的上下文会话"""
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = project_id
        
        # 初始化对话跟踪（DialogueHistory 不需要显式会话管理）
        # self.context_tracker 已经在初始化时创建
        
        # 预加载项目上下文
        try:
            self.context_manager.load_project_context(project_id)
            logger.info("上下文会话已启动", session_id=session_id, project_id=project_id)
        except Exception as e:
            logger.error("启动上下文会话失败", session_id=session_id, error=str(e))
            raise
        
        return session_id
    
    def end_session(self, session_id: str):
        """结束上下文会话"""
        if session_id in self.active_sessions:
            project_id = self.active_sessions[session_id]
            
            # DialogueHistory 不需要显式结束会话
            pass
            
            # 清理会话
            del self.active_sessions[session_id]
            
            logger.info("上下文会话已结束", session_id=session_id, project_id=project_id)
        else:
            logger.warning("会话不存在", session_id=session_id)
    
    def process_query(self, query: ContextQuery) -> ContextResponse:
        """处理上下文查询"""
        start_time = datetime.now()
        
        try:
            # 验证查询
            if not self._validate_query(query):
                return ContextResponse(
                    query_id=query.query_id,
                    success=False,
                    error_message="查询验证失败"
                )
            
            # 获取查询处理器
            processor = self.query_processors.get(query.query_type)
            if not processor:
                return ContextResponse(
                    query_id=query.query_id,
                    success=False,
                    error_message=f"不支持的查询类型: {query.query_type}"
                )
            
            # 处理查询
            result, confidence = processor(query)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 更新性能指标
            self._update_performance_metrics(query.query_type, processing_time, True)
            
            # 记录查询历史
            self.query_history.append(query)
            if len(self.query_history) > 1000:  # 保持历史记录在合理范围内
                self.query_history.pop(0)
            
            response = ContextResponse(
                query_id=query.query_id,
                success=True,
                result=result,
                confidence=confidence,
                processing_time_ms=int(processing_time)
            )
            
            logger.debug("上下文查询处理完成", 
                        query_type=query.query_type,
                        confidence=confidence,
                        processing_time=processing_time)
            
            return response
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self._update_performance_metrics(query.query_type, processing_time, False)
            
            logger.error("上下文查询处理失败", 
                        query_type=query.query_type,
                        error=str(e))
            
            return ContextResponse(
                query_id=query.query_id,
                success=False,
                error_message=str(e),
                processing_time_ms=int(processing_time)
            )
    
    def _validate_query(self, query: ContextQuery) -> bool:
        """验证查询请求"""
        if not query.project_id:
            return False
        
        if not query.query_type:
            return False
        
        # 特定查询类型的验证
        if query.query_type in ["speaker_inference", "pronoun_resolution", "dialogue_analysis"]:
            if not query.subtitle_entry:
                return False
        
        return True
    
    def _process_speaker_inference(self, query: ContextQuery) -> Tuple[Dict[str, Any], float]:
        """处理说话人推断查询"""
        entry = query.subtitle_entry
        history = query.dialogue_history or []
        
        # 使用上下文管理器推断说话人
        context = self.context_manager.get_speaker_context(
            query.project_id, entry, history
        )
        
        # 获取推断的说话人
        inferred_speaker = context.get("speaker")
        speaker_info = context.get("speaker_info", {})
        
        # 计算置信度
        confidence = self._calculate_speaker_confidence(entry, inferred_speaker, context)
        
        result = {
            "inferred_speaker": inferred_speaker,
            "speaker_info": speaker_info,
            "context": context,
            "reasoning": self._generate_speaker_reasoning(entry, inferred_speaker, context)
        }
        
        return result, confidence
    
    def _process_pronoun_resolution(self, query: ContextQuery) -> Tuple[Dict[str, Any], float]:
        """处理代词指代解析查询"""
        entry = query.subtitle_entry
        history = query.dialogue_history or []
        
        # 启动或获取对话跟踪会话
        session_id = self._get_or_create_tracking_session(query.project_id)
        
        # 添加对话条目到历史
        dialogue_entry = self.context_tracker.add_dialogue_entry(entry)
        
        # 获取故事上下文
        story_context = self.context_manager.load_project_context(query.project_id)
        
        # 解析代词
        resolved_pronouns = []
        for pronoun_ref in dialogue_entry.pronouns:
            # 这里需要实现具体的代词解析逻辑
            resolved_ref = self._resolve_single_pronoun(
                pronoun_ref, entry, history, story_context
            )
            resolved_pronouns.append({
                "pronoun": pronoun_ref.pronoun,
                "resolved_reference": resolved_ref,
                "confidence": resolved_ref.get("confidence", 0.0) if resolved_ref else 0.0
            })
        
        # 计算整体置信度
        confidence = sum(p["confidence"] for p in resolved_pronouns) / len(resolved_pronouns) if resolved_pronouns else 0.0
        
        result = {
            "resolved_pronouns": resolved_pronouns,
            "dialogue_entry": asdict(dialogue_entry),
            "original_text": entry.text
        }
        
        return result, confidence
    
    def _process_cultural_adaptation(self, query: ContextQuery) -> Tuple[Dict[str, Any], float]:
        """处理文化适配查询"""
        target_language = query.target_language or "en"
        
        # 获取文化适配上下文
        adaptation_context = self.context_manager.get_cultural_adaptation_context(
            query.project_id, target_language
        )
        
        # 查询文化知识库
        cultural_query = KnowledgeQuery(
            query_type="cultural",
            source_text=query.subtitle_entry.text if query.subtitle_entry else "",
            target_language=target_language,
            project_id=query.project_id
        )
        
        kb_result = self.dynamic_kb.query_knowledge(cultural_query)
        
        result = {
            "adaptation_context": adaptation_context,
            "cultural_mappings": kb_result.results if kb_result.success else [],
            "target_language": target_language,
            "recommendations": self._generate_cultural_recommendations(
                adaptation_context, target_language
            )
        }
        
        confidence = kb_result.confidence if kb_result.success else 0.5
        
        return result, confidence
    
    def _process_relationship_analysis(self, query: ContextQuery) -> Tuple[Dict[str, Any], float]:
        """处理人物关系分析查询"""
        entry = query.subtitle_entry
        
        # 获取说话人上下文
        context = self.context_manager.get_speaker_context(
            query.project_id, entry, query.dialogue_history or []
        )
        
        speaker = context.get("speaker")
        addressee = context.get("addressee")
        relationship_info = context.get("relationship", {})
        
        # 获取详细的关系信息
        story_context = self.context_manager.load_project_context(query.project_id)
        detailed_relationship = None
        
        if speaker and addressee:
            detailed_relationship = story_context.get_relationship_between(speaker, addressee)
        
        result = {
            "speaker": speaker,
            "addressee": addressee,
            "relationship_summary": relationship_info,
            "detailed_relationship": asdict(detailed_relationship) if detailed_relationship else None,
            "formality_suggestions": self._generate_formality_suggestions(relationship_info),
            "address_style_recommendations": self._generate_address_recommendations(
                speaker, addressee, story_context
            )
        }
        
        confidence = 0.8 if detailed_relationship else 0.5
        
        return result, confidence
    
    def _process_context_summary(self, query: ContextQuery) -> Tuple[Dict[str, Any], float]:
        """处理上下文摘要查询"""
        # 获取项目统计信息
        stats = self.context_manager.get_context_statistics(query.project_id)
        
        # 获取对话跟踪统计
        tracking_stats = self.context_tracker.get_context_statistics()
        
        # 获取知识库统计
        kb_stats = self.dynamic_kb.get_statistics()
        
        result = {
            "project_context": stats,
            "dialogue_tracking": tracking_stats,
            "knowledge_base": kb_stats,
            "agent_performance": self.performance_metrics
        }
        
        return result, 1.0
    
    def _process_dialogue_analysis(self, query: ContextQuery) -> Tuple[Dict[str, Any], float]:
        """处理对话分析查询"""
        entry = query.subtitle_entry
        history = query.dialogue_history or []
        
        # 启动或获取对话跟踪会话
        session_id = self._get_or_create_tracking_session(query.project_id)
        
        # 分析对话模式
        if history:
            for hist_entry in history:
                self.context_tracker.add_dialogue_entry(hist_entry)
        
        # 跟踪当前条目
        current_context = self.context_tracker.add_dialogue_entry(entry)
        
        # 获取会话分析（简化版本）
        session_patterns = {
            "total_entries": len(self.context_tracker.dialogue_history),
            "current_window_size": len(self.context_tracker.current_window)
        }
        
        # 获取上下文变化（简化版本）
        context_changes = []
        
        result = {
            "current_context": asdict(current_context),
            "session_patterns": session_patterns,
            "context_changes": context_changes,
            "dialogue_flow_analysis": self._analyze_dialogue_flow(history + [entry])
        }
        
        return result, 0.8
    
    def _process_knowledge_query(self, query: ContextQuery) -> Tuple[Dict[str, Any], float]:
        """处理知识库查询"""
        params = query.additional_params or {}
        
        # 构建知识库查询
        kb_query = KnowledgeQuery(
            query_type=params.get("knowledge_type", "terminology"),
            source_text=params.get("source_text", ""),
            target_language=params.get("target_language", "en"),
            project_id=query.project_id,
            context=params.get("context", {})
        )
        
        # 执行查询
        kb_result = self.dynamic_kb.query_knowledge(kb_query)
        
        result = {
            "query_type": kb_query.query_type,
            "results": kb_result.results if kb_result.success else [],
            "metadata": kb_result.metadata,
            "cache_hit": kb_result.cache_hit
        }
        
        return result, kb_result.confidence if kb_result.success else 0.0
    
    def _get_or_create_tracking_session(self, project_id: str) -> str:
        """获取或创建对话跟踪会话"""
        # 查找现有会话
        for session_id, proj_id in self.active_sessions.items():
            if proj_id == project_id:
                return session_id
        
        # 创建新会话
        return self.start_session(project_id)
    
    def _calculate_speaker_confidence(self, entry: SubtitleEntry, 
                                    inferred_speaker: Optional[str], 
                                    context: Dict[str, Any]) -> float:
        """计算说话人推断的置信度"""
        if not inferred_speaker:
            return 0.0
        
        confidence = 0.5  # 基础置信度
        
        # 基于说话人信息的置信度调整
        speaker_info = context.get("speaker_info", {})
        if speaker_info:
            confidence += 0.2
        
        # 基于关系信息的置信度调整
        if context.get("relationship"):
            confidence += 0.2
        
        # 基于对话历史的置信度调整
        dialogue_history = context.get("dialogue_history", {})
        if dialogue_history.get("recent_speakers"):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_speaker_reasoning(self, entry: SubtitleEntry, 
                                  inferred_speaker: Optional[str], 
                                  context: Dict[str, Any]) -> str:
        """生成说话人推断的推理过程"""
        if not inferred_speaker:
            return "无法确定说话人"
        
        reasoning_parts = []
        
        # 基于文本内容的推理
        speaker_info = context.get("speaker_info", {})
        if speaker_info.get("speaking_style"):
            reasoning_parts.append(f"说话风格匹配: {speaker_info['speaking_style']}")
        
        if speaker_info.get("profession"):
            reasoning_parts.append(f"职业相关术语: {speaker_info['profession']}")
        
        # 基于对话历史的推理
        dialogue_history = context.get("dialogue_history", {})
        if dialogue_history.get("recent_speakers"):
            reasoning_parts.append("基于对话轮换模式")
        
        return " | ".join(reasoning_parts) if reasoning_parts else "基于文本分析"
    
    def _resolve_single_pronoun(self, pronoun_ref: Any, 
                               entry: SubtitleEntry, 
                               history: List[SubtitleEntry],
                               story_context: StoryContext) -> Optional[Dict[str, Any]]:
        """解析单个代词"""
        pronoun = pronoun_ref.pronoun if hasattr(pronoun_ref, 'pronoun') else ""
        
        # 简化的代词解析逻辑
        if pronoun in ["他", "她", "它"]:
            # 查找最近提及的相应性别的角色
            for hist_entry in reversed(history[-3:]):  # 检查最近3条
                if hist_entry.speaker:
                    character = story_context.get_character(hist_entry.speaker)
                    if character and hasattr(character, 'gender'):
                        if (pronoun == "他" and character.gender == "male") or \
                           (pronoun == "她" and character.gender == "female"):
                            return {
                                "reference": hist_entry.speaker,
                                "confidence": 0.8,
                                "reasoning": f"基于性别匹配和对话历史"
                            }
        
        elif pronoun == "我":
            if entry.speaker:
                return {
                    "reference": entry.speaker,
                    "confidence": 1.0,
                    "reasoning": "第一人称代词指向说话人"
                }
        
        return None
    
    def _generate_cultural_recommendations(self, adaptation_context: Dict[str, Any], 
                                         target_language: str) -> List[str]:
        """生成文化适配建议"""
        recommendations = []
        
        genre = adaptation_context.get("genre", "")
        cultural_notes = adaptation_context.get("cultural_notes", [])
        
        if "军事题材" in cultural_notes:
            if target_language == "en":
                recommendations.append("注意军事术语的准确翻译")
                recommendations.append("保持军事等级制度的体现")
            elif target_language == "ja":
                recommendations.append("考虑日本的敬语体系")
        
        if "现代背景" in cultural_notes:
            recommendations.append("使用现代语言表达")
            recommendations.append("避免过于正式的古典表达")
        
        return recommendations
    
    def _generate_formality_suggestions(self, relationship_info: Dict[str, Any]) -> List[str]:
        """生成正式程度建议"""
        suggestions = []
        
        formality = relationship_info.get("formality", "medium")
        respect = relationship_info.get("respect", "neutral")
        
        if formality == "very_high":
            suggestions.append("使用非常正式的语言")
            suggestions.append("避免口语化表达")
        elif formality == "high":
            suggestions.append("使用正式语言")
            suggestions.append("保持礼貌用词")
        elif formality == "low":
            suggestions.append("可以使用较为随意的表达")
            suggestions.append("允许口语化用词")
        
        if respect == "high":
            suggestions.append("体现尊敬态度")
        elif respect == "caring":
            suggestions.append("体现关爱情感")
        
        return suggestions
    
    def _generate_address_recommendations(self, speaker: Optional[str], 
                                        addressee: Optional[str],
                                        story_context: StoryContext) -> List[str]:
        """生成称谓建议"""
        recommendations = []
        
        if not speaker or not addressee:
            return recommendations
        
        relationship = story_context.get_relationship_between(speaker, addressee)
        if not relationship:
            return recommendations
        
        address_style = relationship.address_style
        
        if address_style == "formal_title":
            recommendations.append("使用正式职务称谓")
        elif address_style == "brotherhood":
            recommendations.append("使用战友称谓")
        elif address_style == "intimate":
            recommendations.append("使用亲密称谓")
        elif address_style == "family":
            recommendations.append("使用家庭称谓")
        
        return recommendations
    
    def _analyze_dialogue_flow(self, entries: List[SubtitleEntry]) -> Dict[str, Any]:
        """分析对话流程"""
        if not entries:
            return {}
        
        speakers = [entry.speaker for entry in entries if entry.speaker]
        unique_speakers = list(set(speakers))
        
        # 分析对话轮换
        speaker_changes = 0
        for i in range(1, len(speakers)):
            if speakers[i] != speakers[i-1]:
                speaker_changes += 1
        
        # 分析对话长度
        avg_length = sum(len(entry.text) for entry in entries) / len(entries)
        
        return {
            "total_entries": len(entries),
            "unique_speakers": len(unique_speakers),
            "speaker_list": unique_speakers,
            "speaker_changes": speaker_changes,
            "average_text_length": avg_length,
            "dialogue_type": "multi_speaker" if len(unique_speakers) > 2 else "dialogue"
        }
    
    def _update_performance_metrics(self, query_type: str, processing_time: float, success: bool):
        """更新性能指标"""
        self.performance_metrics["total_queries"] += 1
        
        if success:
            self.performance_metrics["successful_queries"] += 1
        
        # 更新平均响应时间
        total_queries = self.performance_metrics["total_queries"]
        current_avg = self.performance_metrics["average_response_time"]
        new_avg = (current_avg * (total_queries - 1) + processing_time) / total_queries
        self.performance_metrics["average_response_time"] = new_avg
        
        # 更新查询类型统计
        if query_type not in self.performance_metrics["query_types"]:
            self.performance_metrics["query_types"][query_type] = {"count": 0, "success_rate": 0.0}
        
        type_stats = self.performance_metrics["query_types"][query_type]
        type_stats["count"] += 1
        
        if success:
            type_stats["success_rate"] = (type_stats.get("successful", 0) + 1) / type_stats["count"]
            type_stats["successful"] = type_stats.get("successful", 0) + 1
        else:
            type_stats["success_rate"] = type_stats.get("successful", 0) / type_stats["count"]
    
    def get_agent_status(self) -> Dict[str, Any]:
        """获取 Agent 状态"""
        return {
            "agent_id": self.agent_id,
            "active_sessions": len(self.active_sessions),
            "session_details": self.active_sessions,
            "query_history_length": len(self.query_history),
            "performance_metrics": self.performance_metrics,
            "supported_query_types": list(self.query_processors.keys())
        }
    
    def reset_metrics(self):
        """重置性能指标"""
        self.performance_metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "average_response_time": 0.0,
            "query_types": {}
        }
        logger.info("性能指标已重置")


# 全局上下文 Agent 实例
context_agent = ContextAgent()


def get_context_agent() -> ContextAgent:
    """获取上下文 Agent 实例"""
    return context_agent


# Agent 工具函数，用于与 Strands SDK 集成
def create_context_tools() -> List[Dict[str, Any]]:
    """创建上下文管理工具列表，用于 Strands SDK"""
    return [
        {
            "name": "infer_speaker",
            "description": "推断字幕条目的说话人",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "项目ID"},
                    "subtitle_entry": {"type": "object", "description": "字幕条目"},
                    "dialogue_history": {"type": "array", "description": "对话历史"}
                },
                "required": ["project_id", "subtitle_entry"]
            }
        },
        {
            "name": "resolve_pronouns",
            "description": "解析文本中的代词指代",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "项目ID"},
                    "subtitle_entry": {"type": "object", "description": "字幕条目"},
                    "dialogue_history": {"type": "array", "description": "对话历史"}
                },
                "required": ["project_id", "subtitle_entry"]
            }
        },
        {
            "name": "get_cultural_adaptation",
            "description": "获取文化适配建议",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "项目ID"},
                    "target_language": {"type": "string", "description": "目标语言"},
                    "subtitle_entry": {"type": "object", "description": "字幕条目"}
                },
                "required": ["project_id", "target_language"]
            }
        },
        {
            "name": "analyze_relationship",
            "description": "分析人物关系",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "项目ID"},
                    "subtitle_entry": {"type": "object", "description": "字幕条目"},
                    "dialogue_history": {"type": "array", "description": "对话历史"}
                },
                "required": ["project_id", "subtitle_entry"]
            }
        },
        {
            "name": "get_context_summary",
            "description": "获取项目上下文摘要",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "项目ID"}
                },
                "required": ["project_id"]
            }
        }
    ]


def execute_context_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """执行上下文管理工具"""
    agent = get_context_agent()
    
    try:
        if tool_name == "infer_speaker":
            query = ContextQuery(
                query_id=str(uuid.uuid4()),
                project_id=parameters["project_id"],
                query_type="speaker_inference",
                subtitle_entry=parameters["subtitle_entry"],
                dialogue_history=parameters.get("dialogue_history", [])
            )
            
        elif tool_name == "resolve_pronouns":
            query = ContextQuery(
                query_id=str(uuid.uuid4()),
                project_id=parameters["project_id"],
                query_type="pronoun_resolution",
                subtitle_entry=parameters["subtitle_entry"],
                dialogue_history=parameters.get("dialogue_history", [])
            )
            
        elif tool_name == "get_cultural_adaptation":
            query = ContextQuery(
                query_id=str(uuid.uuid4()),
                project_id=parameters["project_id"],
                query_type="cultural_adaptation",
                target_language=parameters["target_language"],
                subtitle_entry=parameters.get("subtitle_entry")
            )
            
        elif tool_name == "analyze_relationship":
            query = ContextQuery(
                query_id=str(uuid.uuid4()),
                project_id=parameters["project_id"],
                query_type="relationship_analysis",
                subtitle_entry=parameters["subtitle_entry"],
                dialogue_history=parameters.get("dialogue_history", [])
            )
            
        elif tool_name == "get_context_summary":
            query = ContextQuery(
                query_id=str(uuid.uuid4()),
                project_id=parameters["project_id"],
                query_type="context_summary"
            )
            
        else:
            return {"error": f"未知的工具: {tool_name}"}
        
        # 处理查询
        response = agent.process_query(query)
        
        return {
            "success": response.success,
            "result": response.result,
            "confidence": response.confidence,
            "processing_time_ms": response.processing_time_ms,
            "error": response.error_message
        }
        
    except Exception as e:
        logger.error("工具执行失败", tool_name=tool_name, error=str(e))
        return {"error": str(e)}