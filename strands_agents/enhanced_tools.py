#!/usr/bin/env python3
"""
基于Strands SDK的增强工具集
严格遵循AWS Bedrock Strands Agent SDK最佳实践
"""
import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import structlog

# Strands Agent SDK imports
from strands import tool

# 导入高级模块
from advanced_modules.creative_adapter import creative_adapter

logger = structlog.get_logger()

# 数据模型定义
@dataclass
class SubtitleEntry:
    """字幕条目数据模型"""
    sequence: int
    start_time: str
    end_time: str
    original_text: str
    translated_text: str = ""
    speaker: Optional[str] = None
    confidence_score: float = 0.0
    translation_notes: str = ""
    duration_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，确保JSON可序列化"""
        return asdict(self)
    
    def validate(self) -> List[str]:
        """验证条目有效性"""
        issues = []
        if self.sequence <= 0:
            issues.append("sequence必须大于0")
        if not self.start_time or not self.end_time:
            issues.append("时间码不能为空")
        if not self.original_text.strip():
            issues.append("原文不能为空")
        return issues

@dataclass
class StoryContext:
    """故事上下文数据模型"""
    title: str = ""
    genre: str = ""
    setting: str = ""
    characters: List[Dict[str, str]] = None
    cultural_background: str = ""
    tone_style: str = ""
    target_audience: str = ""
    relationships: Dict[str, List[str]] = None
    key_themes: List[str] = None
    
    def __post_init__(self):
        if self.characters is None:
            self.characters = []
        if self.relationships is None:
            self.relationships = {}
        if self.key_themes is None:
            self.key_themes = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，确保JSON可序列化"""
        return asdict(self)

@dataclass
class QualityMetrics:
    """翻译质量指标"""
    accuracy_score: float = 0.0
    fluency_score: float = 0.0
    consistency_score: float = 0.0
    cultural_adaptation_score: float = 0.0
    timing_score: float = 0.0
    overall_score: float = 0.0
    issues: List[str] = None
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.recommendations is None:
            self.recommendations = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，确保JSON可序列化"""
        return asdict(self)

class TranslationStyle(Enum):
    """翻译风格枚举"""
    FORMAL = "formal"
    CASUAL = "casual"
    MILITARY = "military"
    ROMANTIC = "romantic"
    DRAMATIC = "dramatic"
    TECHNICAL = "technical"
    HUMOROUS = "humorous"

# Strands Agent工具函数实现
@tool
def parse_srt_file(file_content: str, detect_speakers: bool = True) -> str:
    """
    解析SRT字幕文件，支持说话人识别
    
    Args:
        file_content: SRT文件的文本内容
        detect_speakers: 是否检测说话人信息
    
    Returns:
        JSON字符串，包含解析后的字幕条目列表和统计信息
    """
    start_time = time.time()
    
    # 输入验证
    if not file_content or not isinstance(file_content, str):
        return json.dumps({
            "success": False,
            "error": "Invalid input: file_content must be a non-empty string",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    try:
        entries = []
        blocks = file_content.strip().split('\n\n')
        
        # 说话人检测模式
        speaker_patterns = [
            r'^([^:：]+)[：:](.+)$',  # 标准格式：说话人：内容
            r'^-\s*([^:：]+)[：:](.+)$',  # 带破折号：- 说话人：内容
            r'^\[([^\]]+)\](.+)$',  # 方括号格式：[说话人]内容
            r'^《([^》]+)》(.+)$',  # 书名号格式：《说话人》内容
        ]
        
        for block_idx, block in enumerate(blocks):
            if not block.strip():
                continue
                
            lines = block.strip().split('\n')
            if len(lines) < 3:
                logger.warning(f"跳过无效的字幕块 {block_idx}: 行数不足", block=block[:50])
                continue
            
            try:
                # 解析序号
                sequence = int(lines[0].strip())
                
                # 解析时间码
                time_line = lines[1].strip()
                if ' --> ' not in time_line:
                    logger.warning(f"跳过无效的时间码格式: {time_line}")
                    continue
                    
                start_time_str, end_time_str = time_line.split(' --> ')
                start_time_str = start_time_str.strip()
                end_time_str = end_time_str.strip()
                
                # 计算持续时间
                duration_ms = _calculate_duration(start_time_str, end_time_str)
                
                # 合并文本行
                text_lines = lines[2:]
                original_text = '\n'.join(text_lines).strip()
                
                # 说话人检测
                speaker = None
                if detect_speakers and original_text:
                    for pattern in speaker_patterns:
                        match = re.match(pattern, original_text)
                        if match:
                            speaker = match.group(1).strip()
                            original_text = match.group(2).strip()
                            break
                
                # 创建字幕条目
                entry = SubtitleEntry(
                    sequence=sequence,
                    start_time=start_time_str,
                    end_time=end_time_str,
                    original_text=original_text,
                    speaker=speaker,
                    duration_ms=duration_ms
                )
                
                # 验证条目
                validation_issues = entry.validate()
                if validation_issues:
                    logger.warning(f"字幕条目 {sequence} 存在问题", issues=validation_issues)
                    # 继续处理，但记录问题
                
                entries.append(entry.to_dict())
                
            except (ValueError, IndexError) as e:
                logger.warning(f"跳过无效的字幕块 {block_idx}", error=str(e), block=block[:100])
                continue
        
        processing_time = time.time() - start_time
        
        # 统计信息
        speakers_found = len(set(entry.get('speaker') for entry in entries if entry.get('speaker')))
        total_duration = sum(entry.get('duration_ms', 0) for entry in entries)
        
        result = {
            "success": True,
            "data": {
                "entries": entries,
                "statistics": {
                    "total_entries": len(entries),
                    "speakers_detected": speakers_found,
                    "total_duration_ms": total_duration,
                    "average_duration_ms": total_duration / len(entries) if entries else 0,
                    "speaker_detection_enabled": detect_speakers
                }
            },
            "message": f"成功解析 {len(entries)} 个字幕条目",
            "processing_time": processing_time,
            "blocks_processed": len(blocks),
            "blocks_skipped": len(blocks) - len(entries)
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"SRT文件解析失败: {str(e)}",
            "processing_time": time.time() - start_time,
            "error_type": type(e).__name__
        }, ensure_ascii=False)

@tool
def analyze_story_context(entries: str, additional_context: str = "", analysis_depth: str = "standard") -> str:
    """
    分析故事上下文，提取人物关系和故事背景
    
    Args:
        entries: 字幕条目列表的JSON字符串
        additional_context: 额外的上下文信息（JSON格式或纯文本）
        analysis_depth: 分析深度 ("basic", "standard", "deep")
    
    Returns:
        JSON字符串，包含分析得到的故事上下文
    """
    start_time = time.time()
    
    # 输入验证
    try:
        entries_data = json.loads(entries) if isinstance(entries, str) else entries
    except json.JSONDecodeError:
        return json.dumps({
            "success": False,
            "error": "Invalid entries format: must be valid JSON",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    # 如果entries_data是一个包含"data"字段的结果对象，提取实际的条目列表
    if isinstance(entries_data, dict) and "data" in entries_data and "entries" in entries_data["data"]:
        entries_data = entries_data["data"]["entries"]
    
    if not entries_data or not isinstance(entries_data, list):
        return json.dumps({
            "success": False,
            "error": "Invalid input: entries must be a non-empty list",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    valid_depths = ["basic", "standard", "deep"]
    if analysis_depth not in valid_depths:
        return json.dumps({
            "success": False,
            "error": f"Invalid analysis_depth: must be one of {valid_depths}",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    try:
        # 提取文本和说话人信息
        all_texts = []
        speakers = set()
        speaker_texts = {}
        
        for entry in entries_data:
            if not isinstance(entry, dict):
                continue
                
            text = entry.get('original_text', '').strip()
            speaker = entry.get('speaker', '').strip()
            
            if text:
                all_texts.append(text)
            if speaker:
                speakers.add(speaker)
                if speaker not in speaker_texts:
                    speaker_texts[speaker] = []
                speaker_texts[speaker].append(text)
        
        combined_text = ' '.join(all_texts)
        
        # 初始化上下文对象
        context = StoryContext()
        
        # 基础分析
        context = _analyze_genre_and_tone(context, combined_text)
        context = _analyze_characters(context, speakers, speaker_texts)
        
        # 标准分析
        if analysis_depth in ["standard", "deep"]:
            context = _analyze_relationships(context, combined_text, speaker_texts)
            context = _analyze_themes(context, combined_text)
        
        # 深度分析
        if analysis_depth == "deep":
            context = _analyze_cultural_elements(context, combined_text)
            context = _analyze_emotional_patterns(context, all_texts)
        
        # 处理额外上下文
        if additional_context:
            context = _merge_additional_context(context, additional_context)
        
        processing_time = time.time() - start_time
        
        result = {
            "success": True,
            "data": {
                "context": context.to_dict(),
                "analysis_summary": {
                    "total_texts_analyzed": len(all_texts),
                    "speakers_found": len(speakers),
                    "analysis_depth": analysis_depth,
                    "key_insights": _generate_insights(context)
                }
            },
            "message": f"故事上下文分析完成 (深度: {analysis_depth})",
            "processing_time": processing_time,
            "text_length": len(combined_text),
            "speakers_analyzed": list(speakers)
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"上下文分析失败: {str(e)}",
            "processing_time": time.time() - start_time,
            "error_type": type(e).__name__
        }, ensure_ascii=False)

@tool
def translate_with_context(entries: str, target_language: str, story_context: str, translation_config: str = "{}") -> str:
    """
    基于上下文的高精度翻译
    
    Args:
        entries: 字幕条目列表的JSON字符串
        target_language: 目标语言代码 (如: "en", "ja", "ko")
        story_context: 故事上下文信息的JSON字符串
        translation_config: 翻译配置选项的JSON字符串
    
    Returns:
        JSON字符串，包含翻译后的字幕条目
    """
    start_time = time.time()
    
    # 输入验证
    try:
        entries_data = json.loads(entries) if isinstance(entries, str) else entries
        context_data = json.loads(story_context) if isinstance(story_context, str) else story_context
        config_data = json.loads(translation_config) if translation_config else {}
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid JSON format: {str(e)}",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    # 如果entries_data是一个包含"data"字段的结果对象，提取实际的条目列表
    if isinstance(entries_data, dict) and "data" in entries_data and "entries" in entries_data["data"]:
        entries_data = entries_data["data"]["entries"]
    
    # 如果context_data是一个包含"data"字段的结果对象，提取实际的上下文
    if isinstance(context_data, dict) and "data" in context_data and "context" in context_data["data"]:
        context_data = context_data["data"]["context"]
    
    if not entries_data or not isinstance(entries_data, list):
        return json.dumps({
            "success": False,
            "error": "Invalid input: entries must be a non-empty list",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    if not target_language or not isinstance(target_language, str):
        return json.dumps({
            "success": False,
            "error": "Invalid input: target_language must be a non-empty string",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    # 默认配置
    config = {
        "quality_level": config_data.get("quality_level", "high"),
        "preserve_timing": config_data.get("preserve_timing", True),
        "cultural_adaptation": config_data.get("cultural_adaptation", True),
        "maintain_speaker_style": config_data.get("maintain_speaker_style", True),
        "batch_size": config_data.get("batch_size", 10)
    }
    
    try:
        # 获取语言特定配置
        lang_config = _get_language_config(target_language)
        if not lang_config:
            return json.dumps({
                "success": False,
                "error": f"Unsupported target language: {target_language}",
                "processing_time": time.time() - start_time
            }, ensure_ascii=False)
        
        # 构建翻译策略
        translation_strategy = _build_translation_strategy(
            target_language, context_data, config, lang_config
        )
        
        # 批量翻译处理
        translated_entries = []
        batch_size = config["batch_size"]
        total_batches = (len(entries_data) + batch_size - 1) // batch_size
        
        for batch_idx in range(0, len(entries_data), batch_size):
            batch = entries_data[batch_idx:batch_idx + batch_size]
            
            # 翻译批次
            batch_results = _translate_batch(
                batch, target_language, translation_strategy, lang_config
            )
            translated_entries.extend(batch_results)
        
        # 后处理：一致性检查和优化
        translated_entries = _post_process_translations(
            translated_entries, context_data, lang_config
        )
        
        processing_time = time.time() - start_time
        
        # 计算统计信息
        avg_confidence = sum(
            entry.get('confidence_score', 0) for entry in translated_entries
        ) / len(translated_entries) if translated_entries else 0
        
        result = {
            "success": True,
            "data": {
                "translated_entries": translated_entries,
                "translation_summary": {
                    "total_entries": len(entries_data),
                    "target_language": target_language,
                    "average_confidence": avg_confidence,
                    "translation_strategy": translation_strategy["name"],
                    "batches_processed": total_batches
                },
                "language_config": lang_config
            },
            "message": f"成功翻译 {len(entries_data)} 个条目到 {lang_config['name']}",
            "processing_time": processing_time,
            "target_language": target_language,
            "config_used": config
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"翻译处理失败: {str(e)}",
            "processing_time": time.time() - start_time,
            "error_type": type(e).__name__,
            "target_language": target_language
        }, ensure_ascii=False)

@tool
def validate_translation_quality(original_entries: str, translated_entries: str, target_language: str, validation_config: str = "{}") -> str:
    """
    多维度翻译质量评估
    
    Args:
        original_entries: 原始字幕条目列表的JSON字符串
        translated_entries: 翻译后的字幕条目列表的JSON字符串
        target_language: 目标语言代码
        validation_config: 验证配置选项的JSON字符串
    
    Returns:
        JSON字符串，包含详细的质量评估结果
    """
    start_time = time.time()
    
    # 输入验证
    try:
        orig_data = json.loads(original_entries) if isinstance(original_entries, str) else original_entries
        trans_data = json.loads(translated_entries) if isinstance(translated_entries, str) else translated_entries
        config_data = json.loads(validation_config) if validation_config else {}
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid JSON format: {str(e)}",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    # 如果是包含"data"字段的结果对象，提取实际的条目列表
    if isinstance(orig_data, dict) and "data" in orig_data and "entries" in orig_data["data"]:
        orig_data = orig_data["data"]["entries"]
    if isinstance(trans_data, dict) and "data" in trans_data and "translated_entries" in trans_data["data"]:
        trans_data = trans_data["data"]["translated_entries"]
    
    if not orig_data or not trans_data:
        return json.dumps({
            "success": False,
            "error": "Invalid input: both original_entries and translated_entries must be non-empty lists",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    if len(orig_data) != len(trans_data):
        return json.dumps({
            "success": False,
            "error": f"Entry count mismatch: original={len(orig_data)}, translated={len(trans_data)}",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    # 默认验证配置
    config = {
        "check_accuracy": config_data.get("check_accuracy", True),
        "check_fluency": config_data.get("check_fluency", True),
        "check_consistency": config_data.get("check_consistency", True),
        "check_timing": config_data.get("check_timing", True),
        "check_cultural_adaptation": config_data.get("check_cultural_adaptation", True),
        "detailed_analysis": config_data.get("detailed_analysis", True)
    }
    
    try:
        # 获取语言特定的验证规则
        lang_rules = _get_validation_rules(target_language)
        
        # 初始化质量指标
        quality_metrics = QualityMetrics()
        entry_scores = []
        detailed_issues = []
        
        # 逐条目验证
        for i, (orig, trans) in enumerate(zip(orig_data, trans_data)):
            entry_result = _validate_single_entry(
                orig, trans, lang_rules, config
            )
            entry_scores.append(entry_result["scores"])
            
            if entry_result["issues"]:
                detailed_issues.extend([
                    {
                        "entry_index": i,
                        "sequence": orig.get("sequence", i + 1),
                        "issue_type": issue["type"],
                        "description": issue["description"],
                        "severity": issue["severity"],
                        "suggestion": issue.get("suggestion", "")
                    }
                    for issue in entry_result["issues"]
                ])
        
        # 计算总体质量分数
        if entry_scores:
            quality_metrics.accuracy_score = sum(s["accuracy"] for s in entry_scores) / len(entry_scores)
            quality_metrics.fluency_score = sum(s["fluency"] for s in entry_scores) / len(entry_scores)
            quality_metrics.consistency_score = sum(s["consistency"] for s in entry_scores) / len(entry_scores)
            quality_metrics.cultural_adaptation_score = sum(s["cultural"] for s in entry_scores) / len(entry_scores)
            quality_metrics.timing_score = sum(s["timing"] for s in entry_scores) / len(entry_scores)
            
            # 计算加权总分
            weights = {"accuracy": 0.3, "fluency": 0.25, "consistency": 0.2, "cultural": 0.15, "timing": 0.1}
            quality_metrics.overall_score = (
                quality_metrics.accuracy_score * weights["accuracy"] +
                quality_metrics.fluency_score * weights["fluency"] +
                quality_metrics.consistency_score * weights["consistency"] +
                quality_metrics.cultural_adaptation_score * weights["cultural"] +
                quality_metrics.timing_score * weights["timing"]
            )
        
        # 生成改进建议
        quality_metrics.recommendations = _generate_quality_recommendations(
            quality_metrics, detailed_issues, target_language
        )
        
        # 问题分类统计
        issue_stats = _categorize_issues(detailed_issues)
        
        processing_time = time.time() - start_time
        
        result = {
            "success": True,
            "data": {
                "quality_metrics": quality_metrics.to_dict(),
                "detailed_issues": detailed_issues,
                "issue_statistics": issue_stats,
                "entry_scores": entry_scores,
                "validation_summary": {
                    "total_entries_validated": len(orig_data),
                    "issues_found": len(detailed_issues),
                    "overall_quality_level": _get_quality_level(quality_metrics.overall_score),
                    "target_language": target_language
                }
            },
            "message": f"质量验证完成，总体评分: {quality_metrics.overall_score:.2f}",
            "processing_time": processing_time,
            "validation_config": config,
            "language_rules_applied": lang_rules["name"]
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"质量验证失败: {str(e)}",
            "processing_time": time.time() - start_time,
            "error_type": type(e).__name__
        }, ensure_ascii=False)

@tool
def export_translated_srt(translated_entries: str, export_config: str = "{}") -> str:
    """
    标准化SRT文件导出
    
    Args:
        translated_entries: 翻译后的字幕条目列表的JSON字符串
        export_config: 导出配置选项的JSON字符串
    
    Returns:
        JSON字符串，包含SRT格式的文本内容和导出信息
    """
    start_time = time.time()
    
    # 输入验证
    try:
        entries_data = json.loads(translated_entries) if isinstance(translated_entries, str) else translated_entries
        config_data = json.loads(export_config) if export_config else {}
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid JSON format: {str(e)}",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    # 如果entries_data是一个包含"data"字段的结果对象，提取实际的条目列表
    if isinstance(entries_data, dict) and "data" in entries_data and "translated_entries" in entries_data["data"]:
        entries_data = entries_data["data"]["translated_entries"]
    
    if not entries_data or not isinstance(entries_data, list):
        return json.dumps({
            "success": False,
            "error": "Invalid input: translated_entries must be a non-empty list",
            "processing_time": time.time() - start_time
        }, ensure_ascii=False)
    
    # 默认导出配置
    config = {
        "include_speaker_names": config_data.get("include_speaker_names", False),
        "speaker_name_format": config_data.get("speaker_name_format", "{speaker}: {text}"),
        "line_break_handling": config_data.get("line_break_handling", "preserve"),
        "encoding": config_data.get("encoding", "utf-8"),
        "add_metadata": config_data.get("add_metadata", True),
        "validate_timing": config_data.get("validate_timing", True)
    }
    
    try:
        srt_lines = []
        export_stats = {
            "total_entries": len(entries_data),
            "entries_with_speakers": 0,
            "total_duration_ms": 0,
            "timing_issues": []
        }
        
        # 如果需要添加元数据注释
        if config["add_metadata"]:
            srt_lines.extend([
                f"# Generated by Subtitle Translation Agent",
                f"# Export time: {datetime.now().isoformat()}",
                f"# Total entries: {len(entries_data)}",
                f"# Configuration: {json.dumps(config, ensure_ascii=False)}",
                ""
            ])
        
        # 处理每个字幕条目
        for entry in entries_data:
            if not isinstance(entry, dict):
                continue
                
            sequence = entry.get('sequence', 1)
            start_time_str = entry.get('start_time', '00:00:00,000')
            end_time_str = entry.get('end_time', '00:00:01,000')
            translated_text = entry.get('translated_text', '')
            speaker = entry.get('speaker', '')
            
            # 验证时间码
            if config["validate_timing"]:
                timing_issue = _validate_timing(start_time_str, end_time_str, sequence)
                if timing_issue:
                    export_stats["timing_issues"].append(timing_issue)
            
            # 计算持续时间
            duration_ms = _calculate_duration(start_time_str, end_time_str)
            export_stats["total_duration_ms"] += duration_ms
            
            # 处理说话人信息
            if speaker and config["include_speaker_names"]:
                export_stats["entries_with_speakers"] += 1
                display_text = config["speaker_name_format"].format(
                    speaker=speaker, text=translated_text
                )
            else:
                display_text = translated_text
            
            # 处理换行
            if config["line_break_handling"] == "normalize":
                display_text = display_text.replace('\\n', '\n')
            elif config["line_break_handling"] == "remove":
                display_text = display_text.replace('\n', ' ').replace('\\n', ' ')
            
            # 生成SRT格式
            srt_lines.append(str(sequence))
            srt_lines.append(f"{start_time_str} --> {end_time_str}")
            srt_lines.append(display_text)
            srt_lines.append("")  # 空行分隔
        
        # 生成最终内容
        srt_content = '\n'.join(srt_lines)
        
        # 计算文件信息
        file_size = len(srt_content.encode(config["encoding"]))
        
        # 生成建议的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_filename = f"translated_subtitles_{timestamp}.srt"
        
        processing_time = time.time() - start_time
        
        result = {
            "success": True,
            "data": {
                "srt_content": srt_content,
                "export_info": {
                    "suggested_filename": suggested_filename,
                    "file_size_bytes": file_size,
                    "encoding": config["encoding"],
                    "export_timestamp": datetime.now().isoformat()
                },
                "statistics": export_stats
            },
            "message": f"成功导出 {len(entries_data)} 个字幕条目",
            "processing_time": processing_time,
            "config_used": config,
            "content_preview": srt_content[:200] + "..." if len(srt_content) > 200 else srt_content
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"SRT导出失败: {str(e)}",
            "processing_time": time.time() - start_time,
            "error_type": type(e).__name__
        }, ensure_ascii=False)

# 辅助函数实现
def _calculate_duration(start_time: str, end_time: str) -> int:
    """计算字幕持续时间（毫秒）"""
    try:
        def time_to_ms(time_str):
            # 格式: HH:MM:SS,mmm
            time_part, ms_part = time_str.split(',')
            h, m, s = map(int, time_part.split(':'))
            ms = int(ms_part)
            return (h * 3600 + m * 60 + s) * 1000 + ms
        
        start_ms = time_to_ms(start_time)
        end_ms = time_to_ms(end_time)
        return max(0, end_ms - start_ms)
    except:
        return 0

def _analyze_genre_and_tone(context: StoryContext, text: str) -> StoryContext:
    """分析类型和语调"""
    # 类型关键词映射
    genre_keywords = {
        "romance": ["爱情", "恋爱", "喜欢", "心动", "亲爱的", "爱你", "浪漫"],
        "military": ["军官", "司令", "部队", "训练", "任务", "参谋长", "队长"],
        "comedy": ["搞笑", "哈哈", "笑死", "好玩", "幽默", "逗乐"],
        "drama": ["感动", "眼泪", "痛苦", "悲伤", "激动", "震撼"],
        "thriller": ["紧张", "危险", "快跑", "小心", "恐怖", "惊险"]
    }
    
    # 语调关键词映射
    tone_keywords = {
        "formal": ["请", "您", "敬请", "恭敬", "正式"],
        "casual": ["哥们", "兄弟", "姐妹", "随便", "轻松"],
        "romantic": ["甜蜜", "温柔", "柔情", "深情", "浪漫"],
        "humorous": ["开玩笑", "逗你玩", "搞笑", "幽默", "好笑"]
    }
    
    text_lower = text.lower()
    
    # 分析类型
    genre_scores = {}
    for genre, keywords in genre_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            genre_scores[genre] = score
    
    if genre_scores:
        context.genre = max(genre_scores, key=genre_scores.get)
    
    # 分析语调
    tone_scores = {}
    for tone, keywords in tone_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            tone_scores[tone] = score
    
    if tone_scores:
        context.tone_style = max(tone_scores, key=tone_scores.get)
    else:
        context.tone_style = "neutral"
    
    return context

def _analyze_characters(context: StoryContext, speakers: set, speaker_texts: dict) -> StoryContext:
    """分析角色信息"""
    characters = []
    
    for speaker in speakers:
        if not speaker:
            continue
            
        character_info = {
            "name": speaker,
            "role": "unknown",
            "speaking_frequency": len(speaker_texts.get(speaker, [])),
            "characteristics": []
        }
        
        # 基于说话内容分析角色特征
        texts = speaker_texts.get(speaker, [])
        combined_text = ' '.join(texts).lower()
        
        # 角色类型推断
        if any(word in combined_text for word in ["司令", "参谋长", "队长", "长官"]):
            character_info["role"] = "military_officer"
        elif any(word in combined_text for word in ["亲爱的", "宝贝", "爱你"]):
            character_info["role"] = "romantic_lead"
        elif any(word in combined_text for word in ["哈哈", "搞笑", "开玩笑"]):
            character_info["role"] = "comic_relief"
        
        characters.append(character_info)
    
    # 按说话频率排序
    characters.sort(key=lambda x: x["speaking_frequency"], reverse=True)
    context.characters = characters[:10]  # 限制最多10个主要角色
    
    return context

def _analyze_relationships(context: StoryContext, text: str, speaker_texts: dict) -> StoryContext:
    """分析人物关系"""
    relationships = {}
    
    # 关系关键词
    relationship_patterns = {
        "romantic": ["男朋友", "女朋友", "老公", "老婆", "亲爱的", "宝贝"],
        "family": ["爸爸", "妈妈", "儿子", "女儿", "哥哥", "姐姐", "弟弟", "妹妹"],
        "professional": ["老板", "同事", "下属", "合作伙伴", "客户"],
        "friendship": ["朋友", "好友", "兄弟", "姐妹", "哥们"]
    }
    
    # 简单的关系推断（实际实现会更复杂）
    for speaker, texts in speaker_texts.items():
        combined_text = ' '.join(texts).lower()
        speaker_relationships = []
        
        for rel_type, keywords in relationship_patterns.items():
            if any(keyword in combined_text for keyword in keywords):
                speaker_relationships.append(rel_type)
        
        if speaker_relationships:
            relationships[speaker] = speaker_relationships
    
    context.relationships = relationships
    return context

def _analyze_themes(context: StoryContext, text: str) -> StoryContext:
    """分析主题"""
    theme_keywords = {
        "love": ["爱情", "恋爱", "感情", "浪漫"],
        "friendship": ["友谊", "朋友", "友情", "陪伴"],
        "family": ["家庭", "亲情", "家人", "血缘"],
        "career": ["工作", "事业", "职场", "成功"],
        "growth": ["成长", "学习", "进步", "改变"],
        "conflict": ["冲突", "矛盾", "争执", "对立"]
    }
    
    text_lower = text.lower()
    themes = []
    
    for theme, keywords in theme_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            themes.append(theme)
    
    context.key_themes = themes
    return context

def _analyze_cultural_elements(context: StoryContext, text: str) -> StoryContext:
    """分析文化元素"""
    cultural_indicators = {
        "chinese": ["中国", "中华", "汉语", "普通话", "春节", "中秋"],
        "japanese": ["日本", "日语", "和服", "樱花", "武士", "茶道"],
        "korean": ["韩国", "韩语", "泡菜", "K-pop", "韩流"],
        "western": ["西方", "欧美", "英语", "圣诞节", "感恩节"],
        "modern": ["现代", "都市", "科技", "互联网", "手机", "电脑"],
        "traditional": ["传统", "古代", "历史", "文化", "习俗"]
    }
    
    text_lower = text.lower()
    cultural_elements = []
    
    for culture, indicators in cultural_indicators.items():
        if any(indicator in text_lower for indicator in indicators):
            cultural_elements.append(culture)
    
    if cultural_elements:
        context.cultural_background = ", ".join(cultural_elements)
    
    return context

def _analyze_emotional_patterns(context: StoryContext, texts: List[str]) -> StoryContext:
    """分析情感模式"""
    emotion_keywords = {
        "happy": ["开心", "高兴", "快乐", "兴奋", "愉快"],
        "sad": ["伤心", "难过", "悲伤", "痛苦", "失落"],
        "angry": ["生气", "愤怒", "恼火", "气愤", "暴怒"],
        "surprised": ["惊讶", "震惊", "意外", "吃惊", "惊奇"],
        "fearful": ["害怕", "恐惧", "担心", "紧张", "焦虑"]
    }
    
    emotion_counts = {emotion: 0 for emotion in emotion_keywords}
    
    for text in texts:
        text_lower = text.lower()
        for emotion, keywords in emotion_keywords.items():
            emotion_counts[emotion] += sum(1 for keyword in keywords if keyword in text_lower)
    
    # 找出主要情感
    if any(count > 0 for count in emotion_counts.values()):
        dominant_emotion = max(emotion_counts, key=emotion_counts.get)
        if context.tone_style == "neutral":
            context.tone_style = dominant_emotion
    
    return context

def _merge_additional_context(context: StoryContext, additional_context: str) -> StoryContext:
    """合并额外上下文信息"""
    try:
        # 尝试解析为JSON
        extra_context = json.loads(additional_context)
        if isinstance(extra_context, dict):
            for key, value in extra_context.items():
                if hasattr(context, key) and value:
                    setattr(context, key, value)
    except json.JSONDecodeError:
        # 如果不是JSON，作为文化背景处理
        if additional_context.strip():
            context.cultural_background = additional_context.strip()
    
    return context

def _generate_insights(context: StoryContext) -> List[str]:
    """生成关键洞察"""
    insights = []
    
    if context.genre:
        insights.append(f"故事类型: {context.genre}")
    if context.tone_style:
        insights.append(f"语调风格: {context.tone_style}")
    if context.characters:
        insights.append(f"主要角色数量: {len(context.characters)}")
    if context.key_themes:
        insights.append(f"主要主题: {', '.join(context.key_themes)}")
    if context.relationships:
        insights.append(f"人物关系复杂度: {len(context.relationships)} 个角色有明确关系")
    
    return insights

def _get_language_config(language_code: str) -> Optional[Dict[str, Any]]:
    """获取语言特定配置"""
    language_configs = {
        "en": {
            "name": "English",
            "max_chars_per_line": 42,
            "reading_speed_cps": 17,
            "honorific_system": False,
            "rtl_text": False,
            "cultural_notes": ["Western cultural references", "Idiomatic expressions"],
            "max_length_ratio": 1.2
        },
        "ja": {
            "name": "Japanese",
            "max_chars_per_line": 20,
            "reading_speed_cps": 8,
            "honorific_system": True,
            "rtl_text": False,
            "cultural_notes": ["Keigo system", "Confucian values", "Seasonal references"],
            "max_length_ratio": 1.1
        },
        "ko": {
            "name": "Korean",
            "max_chars_per_line": 18,
            "reading_speed_cps": 9,
            "honorific_system": True,
            "rtl_text": False,
            "cultural_notes": ["Honorific levels", "Age hierarchy", "Confucian values"],
            "max_length_ratio": 1.15
        },
        "ar": {
            "name": "Arabic",
            "max_chars_per_line": 35,
            "reading_speed_cps": 15,
            "honorific_system": False,
            "rtl_text": True,
            "cultural_notes": ["Islamic values", "Religious sensitivity", "RTL text direction"],
            "max_length_ratio": 1.3
        },
        "th": {
            "name": "Thai",
            "max_chars_per_line": 25,
            "reading_speed_cps": 12,
            "honorific_system": True,
            "rtl_text": False,
            "cultural_notes": ["Buddhist culture", "Royal respect", "Theravada Buddhism"],
            "max_length_ratio": 1.25
        },
        "vi": {
            "name": "Vietnamese",
            "max_chars_per_line": 30,
            "reading_speed_cps": 14,
            "honorific_system": True,
            "rtl_text": False,
            "cultural_notes": ["Confucian influence", "Family hierarchy", "Tone markers"],
            "max_length_ratio": 1.2
        },
        "id": {
            "name": "Indonesian",
            "max_chars_per_line": 35,
            "reading_speed_cps": 16,
            "honorific_system": False,
            "rtl_text": False,
            "cultural_notes": ["Islamic influence", "Pancasila values", "Diverse cultures"],
            "max_length_ratio": 1.2
        },
        "ms": {
            "name": "Malay",
            "max_chars_per_line": 35,
            "reading_speed_cps": 16,
            "honorific_system": False,
            "rtl_text": False,
            "cultural_notes": ["Islamic influence", "Malay customs", "Multicultural society"],
            "max_length_ratio": 1.2
        },
        "es": {
            "name": "Spanish",
            "max_chars_per_line": 38,
            "reading_speed_cps": 18,
            "honorific_system": False,
            "rtl_text": False,
            "cultural_notes": ["Hispanic culture", "Regional variations", "Catholic influence"],
            "max_length_ratio": 1.25
        },
        "pt": {
            "name": "Portuguese",
            "max_chars_per_line": 38,
            "reading_speed_cps": 18,
            "honorific_system": False,
            "rtl_text": False,
            "cultural_notes": ["Lusophone culture", "Brazilian vs European", "Catholic influence"],
            "max_length_ratio": 1.25
        }
    }
    
    return language_configs.get(language_code)

def _build_translation_strategy(target_language: str, story_context: Dict[str, Any], 
                               config: Dict[str, Any], lang_config: Dict[str, Any]) -> Dict[str, Any]:
    """构建翻译策略"""
    strategy = {
        "name": f"{lang_config['name']}_context_aware",
        "target_language": target_language,
        "honorific_handling": lang_config["honorific_system"],
        "cultural_adaptation": config["cultural_adaptation"],
        "preserve_timing": config["preserve_timing"],
        "quality_level": config["quality_level"]
    }
    
    # 根据故事类型调整策略
    genre = story_context.get("genre", "")
    if genre == "military":
        strategy["formality_level"] = "high"
        strategy["terminology_focus"] = "military"
    elif genre == "romance":
        strategy["formality_level"] = "medium"
        strategy["emotional_emphasis"] = "high"
    elif genre == "comedy":
        strategy["humor_adaptation"] = "enabled"
        strategy["cultural_localization"] = "high"
    
    return strategy

def _translate_batch(batch: List[Dict[str, Any]], target_language: str, 
                    strategy: Dict[str, Any], lang_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """翻译批次处理"""
    # 这里是模拟实现，实际会调用LLM进行翻译
    translated_batch = []
    
    # 术语映射表
    terminology_mappings = {
        "en": {
            "参谋长": "Chief of Staff", "司令": "Commander", "队长": "Captain",
            "鸡娃": "helicopter parenting", "内卷": "rat race", "躺平": "lying flat",
            "哥": "bro", "姐": "sis", "老板": "boss", "朋友": "friend"
        },
        "ja": {
            "参谋长": "参謀長", "司令": "司令官", "队长": "隊長",
            "鸡娃": "教育ママ", "内卷": "過当競争", "躺平": "寝そべり族",
            "哥": "お兄さん", "姐": "お姉さん", "老板": "社長", "朋友": "友達"
        },
        "ko": {
            "参谋长": "참모장", "司令": "사령관", "队长": "대장",
            "鸡娃": "헬리콥터 부모", "内卷": "과도한 경쟁", "躺平": "눕기족",
            "哥": "오빠/형", "姐": "언니/누나", "老板": "사장님", "朋友": "친구"
        }
    }
    
    terminology = terminology_mappings.get(target_language, {})
    
    for entry in batch:
        original_text = entry.get('original_text', '')
        
        # 简单的术语替换（实际实现会更复杂）
        translated_text = original_text
        for chinese_term, target_term in terminology.items():
            if chinese_term in original_text:
                translated_text = translated_text.replace(chinese_term, target_term)
        
        # 长度检查
        max_length = int(len(original_text) * lang_config.get("max_length_ratio", 1.3))
        if len(translated_text) > max_length:
            translated_text = translated_text[:max_length-3] + "..."
        
        # 创建翻译结果
        translated_entry = entry.copy()
        translated_entry['translated_text'] = translated_text
        translated_entry['confidence_score'] = 0.85  # 模拟置信度
        translated_entry['translation_notes'] = f"使用{strategy['name']}策略翻译"
        
        translated_batch.append(translated_entry)
    
    return translated_batch

def _post_process_translations(entries: List[Dict[str, Any]], 
                              story_context: Dict[str, Any], 
                              lang_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """后处理翻译结果"""
    # 一致性检查和优化
    processed_entries = []
    
    # 收集所有翻译的术语
    term_usage = {}
    
    for entry in entries:
        translated_text = entry.get('translated_text', '')
        # 术语一致性检查（简化实现）
        # 实际实现会更复杂，包括上下文相关的术语选择
        processed_entries.append(entry)
    
    return processed_entries

def _get_validation_rules(target_language: str) -> Dict[str, Any]:
    """获取语言特定的验证规则"""
    validation_rules = {
        "en": {
            "name": "English Validation Rules",
            "max_chars_per_line": 42,
            "reading_speed_cps": 17,
            "common_endings": [".", "!", "?"],
            "avoid_patterns": [r"[待翻译]", r"\[.*\]"],
            "punctuation_rules": {
                "question_marks": ["?"],
                "exclamation_marks": ["!"],
                "periods": ["."]
            }
        },
        "ja": {
            "name": "Japanese Validation Rules",
            "max_chars_per_line": 20,
            "reading_speed_cps": 8,
            "common_endings": ["。", "！", "？", "です", "ます"],
            "avoid_patterns": [r"[待翻译]", r"\[.*\]"],
            "honorific_check": True
        },
        "ko": {
            "name": "Korean Validation Rules",
            "max_chars_per_line": 18,
            "reading_speed_cps": 9,
            "common_endings": [".", "!", "?", "다", "요", "습니다"],
            "avoid_patterns": [r"[待翻译]", r"\[.*\]"],
            "honorific_check": True
        },
        "ar": {
            "name": "Arabic Validation Rules",
            "max_chars_per_line": 35,
            "reading_speed_cps": 15,
            "common_endings": [".", "!", "?", "。"],
            "avoid_patterns": [r"[待翻译]", r"\[.*\]"],
            "rtl_check": True
        }
    }
    
    return validation_rules.get(target_language, validation_rules["en"])

def _validate_single_entry(original: Dict[str, Any], translated: Dict[str, Any], 
                          rules: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """验证单个条目"""
    scores = {
        "accuracy": 1.0,
        "fluency": 1.0,
        "consistency": 1.0,
        "cultural": 1.0,
        "timing": 1.0
    }
    issues = []
    
    orig_text = original.get('original_text', '')
    trans_text = translated.get('translated_text', '')
    
    # 长度检查
    if len(trans_text) > rules["max_chars_per_line"] * 2:
        issues.append({
            "type": "length",
            "description": "翻译文本过长",
            "severity": "medium",
            "suggestion": "考虑缩短翻译或分行显示"
        })
        scores["timing"] -= 0.2
    
    # 标点符号检查
    if '?' in orig_text and not any(p in trans_text for p in rules.get("punctuation_rules", {}).get("question_marks", ["?"])):
        issues.append({
            "type": "punctuation",
            "description": "疑问句标点丢失",
            "severity": "low",
            "suggestion": "添加适当的疑问标点"
        })
        scores["accuracy"] -= 0.1
    
    # 未翻译内容检查
    for pattern in rules.get("avoid_patterns", []):
        if re.search(pattern, trans_text):
            issues.append({
                "type": "incomplete",
                "description": "包含未翻译标记",
                "severity": "high",
                "suggestion": "完成翻译"
            })
            scores["accuracy"] -= 0.5
            break
    
    # 时间码一致性检查
    if original.get('start_time') != translated.get('start_time'):
        issues.append({
            "type": "timing",
            "description": "时间码不一致",
            "severity": "high",
            "suggestion": "确保时间码保持一致"
        })
        scores["consistency"] -= 0.3
    
    # 语言特定检查
    if rules.get("rtl_check") and re.search(r'^[a-zA-Z]', trans_text):
        issues.append({
            "type": "direction",
            "description": "可能需要RTL文本方向调整",
            "severity": "low",
            "suggestion": "检查文本方向设置"
        })
        scores["cultural"] -= 0.1
    
    return {
        "scores": scores,
        "issues": issues
    }

def _generate_quality_recommendations(metrics: QualityMetrics, 
                                    issues: List[Dict[str, Any]], 
                                    target_language: str) -> List[str]:
    """生成质量改进建议"""
    recommendations = []
    
    if metrics.accuracy_score < 0.8:
        recommendations.append("建议重新检查翻译准确性，特别是专业术语和人名")
    
    if metrics.fluency_score < 0.8:
        recommendations.append("建议优化翻译流畅性，使其更符合目标语言习惯")
    
    if metrics.consistency_score < 0.8:
        recommendations.append("建议检查术语和人名的一致性")
    
    if metrics.cultural_adaptation_score < 0.8:
        recommendations.append("建议加强文化适配，考虑目标语言的文化背景")
    
    if metrics.timing_score < 0.8:
        recommendations.append("建议检查字幕时长和阅读速度")
    
    # 基于问题类型的建议
    issue_types = [issue["issue_type"] for issue in issues]
    if "length" in issue_types:
        recommendations.append("建议缩短过长的翻译文本")
    if "punctuation" in issue_types:
        recommendations.append("建议检查标点符号的使用")
    if "incomplete" in issue_types:
        recommendations.append("建议完成所有未翻译的内容")
    
    return recommendations

def _categorize_issues(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """问题分类统计"""
    issue_stats = {}
    
    for issue in issues:
        issue_type = issue.get("issue_type", "unknown")
        severity = issue.get("severity", "unknown")
        
        if issue_type not in issue_stats:
            issue_stats[issue_type] = {"total": 0, "high": 0, "medium": 0, "low": 0}
        
        issue_stats[issue_type]["total"] += 1
        issue_stats[issue_type][severity] += 1
    
    return issue_stats

def _get_quality_level(score: float) -> str:
    """获取质量等级"""
    if score >= 0.9:
        return "excellent"
    elif score >= 0.8:
        return "good"
    elif score >= 0.7:
        return "acceptable"
    elif score >= 0.6:
        return "needs_improvement"
    else:
        return "poor"

def _validate_timing(start_time: str, end_time: str, sequence: int) -> Optional[Dict[str, Any]]:
    """验证时间码"""
    try:
        start_ms = _calculate_duration("00:00:00,000", start_time)
        end_ms = _calculate_duration("00:00:00,000", end_time)
        
        if end_ms <= start_ms:
            return {
                "sequence": sequence,
                "issue": "end_time_before_start",
                "description": "结束时间早于或等于开始时间"
            }
        
        duration = end_ms - start_ms
        if duration < 500:  # 少于0.5秒
            return {
                "sequence": sequence,
                "issue": "too_short",
                "description": "字幕显示时间过短"
            }
        
        if duration > 10000:  # 超过10秒
            return {
                "sequence": sequence,
                "issue": "too_long",
                "description": "字幕显示时间过长"
            }
        
        return None
        
    except Exception:
        return {
            "sequence": sequence,
            "issue": "invalid_format",
            "description": "时间码格式无效"
        }

# 获取所有工具函数的列表
def get_all_tools():
    """获取所有Strands Agent工具函数"""
    return [
        parse_srt_file,
        analyze_story_context,
        translate_with_context,
        validate_translation_quality,
        export_translated_srt
    ]

if __name__ == "__main__":
    # 测试工具函数
    print("Strands Agent工具集已加载")
    print("可用工具:")
    for tool_func in get_all_tools():
        print(f"- {tool_func.__name__}: {tool_func.__doc__.split('Args:')[0].strip()}")
# ==================== 高级功能工具函数 ====================

@tool
def localize_cultural_terms(text: str, target_language: str, cultural_context: str = "{}") -> str:
    """
    文化词汇本土化
    
    处理现代网络词汇、文化概念的跨文化转换，如"鸡娃"、"内卷"、"躺平"等
    
    Args:
        text: 待处理的文本内容
        target_language: 目标语言代码 (en, ja, ko, th, vi, id, ms, es, pt, ar)
        cultural_context: 文化背景配置JSON字符串，默认"{}"
    
    Returns:
        JSON字符串，包含本土化处理结果和文化适配分析
    """
    start_time = time.time()
    
    try:
        # 导入文化本土化引擎
        from advanced_modules.cultural_localizer import cultural_localizer
        
        # 调用文化本土化引擎
        result = cultural_localizer.process({
            "text": text,
            "target_language": target_language,
            "cultural_context": cultural_context
        })
        
        # 添加工具函数的元数据
        if result["success"]:
            result["tool_info"] = {
                "tool_name": "localize_cultural_terms",
                "version": "1.0.0",
                "processing_time": time.time() - start_time
            }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Cultural localization failed: {str(e)}",
            "processing_time": time.time() - start_time,
            "tool_info": {
                "tool_name": "localize_cultural_terms",
                "version": "1.0.0"
            }
        }, ensure_ascii=False)

@tool
def analyze_translation_quality_advanced(original: str, translated: str, target_language: str, analysis_config: str = "{}") -> str:
    """
    高级翻译质量分析
    
    进行7种维度的翻译质量评估：准确性、流畅性、文化适配性、一致性、完整性、可读性、时间同步性
    
    Args:
        original: 原文JSON字符串
        translated: 译文JSON字符串
        target_language: 目标语言代码 (en, ja, ko, zh, ar等)
        analysis_config: 分析配置JSON字符串，默认"{}"
    
    Returns:
        JSON字符串，包含详细质量分析报告和改进建议
    """
    start_time = time.time()
    
    try:
        # 导入高级质量分析器
        from advanced_modules.quality_analyzer import quality_analyzer
        
        # 调用质量分析器
        result = quality_analyzer.process({
            "original": original,
            "translated": translated,
            "target_language": target_language,
            "analysis_config": analysis_config
        })
        
        # 添加工具函数的元数据
        if result["success"]:
            result["tool_info"] = {
                "tool_name": "analyze_translation_quality_advanced",
                "version": "1.0.0",
                "processing_time": time.time() - start_time
            }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Advanced quality analysis failed: {str(e)}",
            "processing_time": time.time() - start_time,
            "tool_info": {
                "tool_name": "analyze_translation_quality_advanced",
                "version": "1.0.0"
            }
        }, ensure_ascii=False)

@tool
def check_translation_consistency(entries: str, reference_data: str = "", target_language: str = "en", check_config: str = "{}") -> str:
    """
    翻译一致性检查
    
    检查人名、术语、称谓的一致性，支持跨集数验证和自动修复建议
    
    Args:
        entries: 翻译条目JSON字符串
        reference_data: 参考数据JSON字符串，默认""
        target_language: 目标语言代码，默认"en"
        check_config: 检查配置JSON字符串，默认"{}"
    
    Returns:
        JSON字符串，包含一致性检查报告和修复建议
    """
    start_time = time.time()
    
    try:
        # 导入一致性检查器
        from advanced_modules.consistency_checker import consistency_checker
        
        # 调用一致性检查器
        result = consistency_checker.process({
            "entries": entries,
            "reference_data": reference_data,
            "target_language": target_language,
            "check_config": check_config
        })
        
        # 添加工具函数的元数据
        if result["success"]:
            result["tool_info"] = {
                "tool_name": "check_translation_consistency",
                "version": "1.0.0",
                "processing_time": time.time() - start_time
            }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Consistency check failed: {str(e)}",
            "processing_time": time.time() - start_time,
            "tool_info": {
                "tool_name": "check_translation_consistency",
                "version": "1.0.0"
            }
        }, ensure_ascii=False)

@tool
def optimize_subtitle_timing(entries: str, target_language: str = "en", optimization_config: str = "{}") -> str:
    """
    字幕时长优化
    
    分析和优化字幕显示时长，确保符合阅读速度标准和场景要求
    
    Args:
        entries: 字幕条目JSON字符串
        target_language: 目标语言代码，默认"en"
        optimization_config: 优化配置JSON字符串，默认"{}"
    
    Returns:
        JSON字符串，包含优化后的字幕条目和分析报告
    """
    start_time = time.time()
    
    try:
        # 导入字幕优化器
        from advanced_modules.subtitle_optimizer import subtitle_optimizer
        
        # 调用字幕优化器
        result = subtitle_optimizer.process({
            "entries": entries,
            "target_language": target_language,
            "optimization_config": optimization_config
        })
        
        # 添加工具函数的元数据
        if result["success"]:
            result["tool_info"] = {
                "tool_name": "optimize_subtitle_timing",
                "version": "1.0.0",
                "processing_time": time.time() - start_time
            }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Subtitle optimization failed: {str(e)}",
            "processing_time": time.time() - start_time,
            "tool_info": {
                "tool_name": "optimize_subtitle_timing",
                "version": "1.0.0"
            }
        }, ensure_ascii=False)

@tool
def manage_terminology(entries: str, target_language: str = "en", terminology_config: str = "{}") -> str:
    """
    术语管理和一致性维护
    
    动态学习术语、检查一致性、解决冲突，维护多级术语库
    
    Args:
        entries: 翻译条目JSON字符串
        target_language: 目标语言代码，默认"en"
        terminology_config: 术语配置JSON字符串，默认"{}"
    
    Returns:
        JSON字符串，包含术语管理结果和建议
    """
    start_time = time.time()
    
    try:
        # 导入术语管理器
        from advanced_modules.terminology_manager import terminology_manager
        
        # 调用术语管理器
        result = terminology_manager.process({
            "entries": entries,
            "target_language": target_language,
            "terminology_config": terminology_config
        })
        
        # 添加工具函数的元数据
        if result["success"]:
            result["tool_info"] = {
                "tool_name": "manage_terminology",
                "version": "1.0.0",
                "processing_time": time.time() - start_time
            }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Terminology management failed: {str(e)}",
            "processing_time": time.time() - start_time,
            "tool_info": {
                "tool_name": "manage_terminology",
                "version": "1.0.0"
            }
        }, ensure_ascii=False)

@tool
def enhance_creative_translation(entries: str, context: str, style_config: str = "{}") -> str:
    """
    创作性翻译增强
    
    根据场景情感和人物性格调整翻译风格，提供更具艺术性和观赏性的翻译
    
    Args:
        entries: 翻译条目列表的JSON字符串
        context: 故事上下文信息的JSON字符串
        style_config: 风格配置选项的JSON字符串，默认"{}"
    
    Returns:
        JSON字符串，包含增强后的翻译结果和风格分析
    """
    start_time = time.time()
    
    try:
        # 调用创作性翻译适配器
        result = creative_adapter.process({
            "entries": entries,
            "context": context,
            "config": style_config
        })
        
        # 添加工具函数的元数据
        if result["success"]:
            result["tool_info"] = {
                "tool_name": "enhance_creative_translation",
                "version": "1.0.0",
                "processing_time": time.time() - start_time
            }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Creative translation enhancement failed: {str(e)}",
            "processing_time": time.time() - start_time,
            "tool_info": {
                "tool_name": "enhance_creative_translation",
                "version": "1.0.0"
            }
        }, ensure_ascii=False)