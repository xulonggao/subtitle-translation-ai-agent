"""
字幕优化 Agent
处理字幕时长、节奏分析和阅读速度优化
"""
import json
import uuid
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from config import get_logger
from models.subtitle_models import SubtitleEntry, TimeCode
from models.translation_models import TranslationTask

logger = get_logger("subtitle_optimization_agent")


class ReadingSpeedStandard(Enum):
    """阅读速度标准"""
    SLOW = "slow"           # 慢速：8-10 字/秒
    NORMAL = "normal"       # 正常：10-12 字/秒
    FAST = "fast"           # 快速：12-15 字/秒
    VERY_FAST = "very_fast" # 极快：15-18 字/秒


class SceneType(Enum):
    """场景类型"""
    DIALOGUE = "dialogue"       # 对话场景
    ACTION = "action"           # 动作场景
    EMOTIONAL = "emotional"     # 情感场景
    EXPOSITION = "exposition"   # 说明场景
    COMEDY = "comedy"           # 喜剧场景
    DRAMATIC = "dramatic"       # 戏剧场景


class OptimizationStrategy(Enum):
    """优化策略"""
    COMPRESS = "compress"       # 压缩文本
    SPLIT = "split"             # 分割字幕
    EXTEND = "extend"           # 延长显示时间
    MERGE = "merge"             # 合并字幕
    REWRITE = "rewrite"         # 重写文本


@dataclass
class TimingAnalysis:
    """时长分析结果"""
    subtitle_entry: SubtitleEntry
    duration_seconds: float
    character_count: int
    reading_speed_cps: float  # 字符每秒
    is_optimal: bool
    recommended_duration: Optional[float] = None
    optimization_needed: Optional[OptimizationStrategy] = None
    quality_score: float = 0.0
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass
class RhythmAnalysis:
    """节奏分析结果"""
    subtitle_entries: List[SubtitleEntry]
    scene_type: SceneType
    average_duration: float
    duration_variance: float
    pace_score: float  # 节奏评分 0-1
    rhythm_consistency: float  # 节奏一致性 0-1
    scene_transitions: List[int]  # 场景转换位置
    recommendations: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class OptimizationResult:
    """优化结果"""
    original_entry: SubtitleEntry
    optimized_entry: Optional[SubtitleEntry] = None
    strategy_used: Optional[OptimizationStrategy] = None
    improvement_score: float = 0.0
    before_analysis: Optional[TimingAnalysis] = None
    after_analysis: Optional[TimingAnalysis] = None
    success: bool = False
    error_message: Optional[str] = None


class SubtitleTimingOptimizer:
    """字幕时长优化器
    
    主要功能：
    1. 分析字幕显示时长是否合理
    2. 根据阅读速度标准优化时长
    3. 处理过长或过短的字幕
    4. 支持多语言的阅读速度适配
    """
    
    def __init__(self):
        # 语言特定的阅读速度配置（字符每秒）
        self.language_reading_speeds = {
            "zh": {  # 中文
                ReadingSpeedStandard.SLOW: 8,
                ReadingSpeedStandard.NORMAL: 10,
                ReadingSpeedStandard.FAST: 12,
                ReadingSpeedStandard.VERY_FAST: 15
            },
            "en": {  # 英文
                ReadingSpeedStandard.SLOW: 12,
                ReadingSpeedStandard.NORMAL: 15,
                ReadingSpeedStandard.FAST: 18,
                ReadingSpeedStandard.VERY_FAST: 22
            },
            "ja": {  # 日文
                ReadingSpeedStandard.SLOW: 6,
                ReadingSpeedStandard.NORMAL: 8,
                ReadingSpeedStandard.FAST: 10,
                ReadingSpeedStandard.VERY_FAST: 12
            },
            "ko": {  # 韩文
                ReadingSpeedStandard.SLOW: 7,
                ReadingSpeedStandard.NORMAL: 9,
                ReadingSpeedStandard.FAST: 11,
                ReadingSpeedStandard.VERY_FAST: 14
            },
            "fr": {  # 法文
                ReadingSpeedStandard.SLOW: 10,
                ReadingSpeedStandard.NORMAL: 13,
                ReadingSpeedStandard.FAST: 16,
                ReadingSpeedStandard.VERY_FAST: 20
            },
            "de": {  # 德文
                ReadingSpeedStandard.SLOW: 9,
                ReadingSpeedStandard.NORMAL: 12,
                ReadingSpeedStandard.FAST: 15,
                ReadingSpeedStandard.VERY_FAST: 18
            },
            "es": {  # 西班牙文
                ReadingSpeedStandard.SLOW: 11,
                ReadingSpeedStandard.NORMAL: 14,
                ReadingSpeedStandard.FAST: 17,
                ReadingSpeedStandard.VERY_FAST: 21
            },
            "ru": {  # 俄文
                ReadingSpeedStandard.SLOW: 8,
                ReadingSpeedStandard.NORMAL: 11,
                ReadingSpeedStandard.FAST: 14,
                ReadingSpeedStandard.VERY_FAST: 17
            }
        }
        
        # 最小和最大显示时间（秒）
        self.min_display_time = 0.8
        self.max_display_time = 6.0
        
        # 字幕间隔时间（秒）
        self.min_gap_time = 0.1
        
        logger.info("字幕时长优化器初始化完成")
    
    def analyze_timing(self, subtitle_entry: SubtitleEntry, 
                      language: str = "zh",
                      reading_speed: ReadingSpeedStandard = ReadingSpeedStandard.NORMAL) -> TimingAnalysis:
        """分析字幕时长"""
        try:
            # 计算显示时长
            duration = self._calculate_duration(subtitle_entry.start_time, subtitle_entry.end_time)
            
            # 计算字符数
            char_count = len(subtitle_entry.text.strip())
            
            # 计算实际阅读速度
            actual_speed = char_count / duration if duration > 0 else 0
            
            # 获取推荐阅读速度
            recommended_speed = self._get_reading_speed(language, reading_speed)
            
            # 计算推荐时长
            recommended_duration = char_count / recommended_speed if recommended_speed > 0 else duration
            
            # 判断是否需要优化
            is_optimal = self._is_timing_optimal(duration, char_count, language, reading_speed)
            
            # 确定优化策略
            optimization_strategy = self._determine_optimization_strategy(
                duration, char_count, recommended_duration
            )
            
            # 计算质量评分
            quality_score = self._calculate_timing_quality(
                duration, char_count, language, reading_speed
            )
            
            # 识别问题
            issues = self._identify_timing_issues(
                duration, char_count, actual_speed, recommended_speed
            )
            
            return TimingAnalysis(
                subtitle_entry=subtitle_entry,
                duration_seconds=duration,
                character_count=char_count,
                reading_speed_cps=actual_speed,
                is_optimal=is_optimal,
                recommended_duration=recommended_duration,
                optimization_needed=optimization_strategy,
                quality_score=quality_score,
                issues=issues
            )
            
        except Exception as e:
            logger.error("时长分析失败", subtitle_index=subtitle_entry.index, error=str(e))
            return TimingAnalysis(
                subtitle_entry=subtitle_entry,
                duration_seconds=0,
                character_count=0,
                reading_speed_cps=0,
                is_optimal=False,
                quality_score=0.0,
                issues=[f"分析失败: {str(e)}"]
            )
    
    def optimize_timing(self, subtitle_entry: SubtitleEntry,
                       language: str = "zh",
                       reading_speed: ReadingSpeedStandard = ReadingSpeedStandard.NORMAL,
                       context_entries: Optional[List[SubtitleEntry]] = None) -> OptimizationResult:
        """优化字幕时长"""
        try:
            # 分析当前时长
            before_analysis = self.analyze_timing(subtitle_entry, language, reading_speed)
            
            if before_analysis.is_optimal:
                return OptimizationResult(
                    original_entry=subtitle_entry,
                    optimized_entry=subtitle_entry,
                    strategy_used=None,
                    improvement_score=1.0,
                    before_analysis=before_analysis,
                    after_analysis=before_analysis,
                    success=True
                )
            
            # 执行优化
            optimized_entry = self._apply_optimization_strategy(
                subtitle_entry, before_analysis.optimization_needed, 
                before_analysis.recommended_duration, context_entries
            )
            
            if optimized_entry:
                # 分析优化后的时长
                after_analysis = self.analyze_timing(optimized_entry, language, reading_speed)
                
                # 计算改进分数
                improvement_score = self._calculate_improvement_score(
                    before_analysis, after_analysis
                )
                
                return OptimizationResult(
                    original_entry=subtitle_entry,
                    optimized_entry=optimized_entry,
                    strategy_used=before_analysis.optimization_needed,
                    improvement_score=improvement_score,
                    before_analysis=before_analysis,
                    after_analysis=after_analysis,
                    success=True
                )
            else:
                return OptimizationResult(
                    original_entry=subtitle_entry,
                    before_analysis=before_analysis,
                    success=False,
                    error_message="优化策略执行失败"
                )
                
        except Exception as e:
            logger.error("时长优化失败", subtitle_index=subtitle_entry.index, error=str(e))
            return OptimizationResult(
                original_entry=subtitle_entry,
                success=False,
                error_message=str(e)
            )
    
    def _calculate_duration(self, start_time: TimeCode, end_time: TimeCode) -> float:
        """计算时长（秒）"""
        start_seconds = (start_time.hours * 3600 + 
                        start_time.minutes * 60 + 
                        start_time.seconds + 
                        start_time.milliseconds / 1000)
        
        end_seconds = (end_time.hours * 3600 + 
                      end_time.minutes * 60 + 
                      end_time.seconds + 
                      end_time.milliseconds / 1000)
        
        return end_seconds - start_seconds
    
    def _get_reading_speed(self, language: str, speed_standard: ReadingSpeedStandard) -> float:
        """获取阅读速度"""
        lang_speeds = self.language_reading_speeds.get(language, self.language_reading_speeds["zh"])
        return lang_speeds.get(speed_standard, lang_speeds[ReadingSpeedStandard.NORMAL])
    
    def _is_timing_optimal(self, duration: float, char_count: int, 
                          language: str, reading_speed: ReadingSpeedStandard) -> bool:
        """判断时长是否最优"""
        if duration < self.min_display_time or duration > self.max_display_time:
            return False
        
        recommended_speed = self._get_reading_speed(language, reading_speed)
        actual_speed = char_count / duration if duration > 0 else 0
        
        # 允许20%的误差范围
        speed_ratio = actual_speed / recommended_speed if recommended_speed > 0 else 0
        return 0.8 <= speed_ratio <= 1.2
    
    def _determine_optimization_strategy(self, duration: float, char_count: int, 
                                       recommended_duration: float) -> Optional[OptimizationStrategy]:
        """确定优化策略"""
        if duration < self.min_display_time:
            return OptimizationStrategy.EXTEND
        elif duration > self.max_display_time:
            if char_count > 30:  # 文本过长
                return OptimizationStrategy.SPLIT
            else:
                return OptimizationStrategy.COMPRESS
        elif duration < recommended_duration * 0.8:
            return OptimizationStrategy.EXTEND
        elif duration > recommended_duration * 1.2:
            if char_count > 25:
                return OptimizationStrategy.COMPRESS
            else:
                return OptimizationStrategy.EXTEND
        
        return None
    
    def _calculate_timing_quality(self, duration: float, char_count: int,
                                language: str, reading_speed: ReadingSpeedStandard) -> float:
        """计算时长质量评分"""
        score = 1.0
        
        # 检查最小/最大时长
        if duration < self.min_display_time:
            score *= 0.5
        elif duration > self.max_display_time:
            score *= 0.6
        
        # 检查阅读速度
        recommended_speed = self._get_reading_speed(language, reading_speed)
        actual_speed = char_count / duration if duration > 0 else 0
        
        if recommended_speed > 0:
            speed_ratio = actual_speed / recommended_speed
            if speed_ratio < 0.5:  # 太慢
                score *= 0.7
            elif speed_ratio > 2.0:  # 太快
                score *= 0.4
            elif 0.8 <= speed_ratio <= 1.2:  # 理想范围
                score *= 1.0
            else:
                score *= 0.8
        
        return max(0.0, min(1.0, score))
    
    def _identify_timing_issues(self, duration: float, char_count: int,
                              actual_speed: float, recommended_speed: float) -> List[str]:
        """识别时长问题"""
        issues = []
        
        if duration < self.min_display_time:
            issues.append(f"显示时间过短 ({duration:.1f}s < {self.min_display_time}s)")
        
        if duration > self.max_display_time:
            issues.append(f"显示时间过长 ({duration:.1f}s > {self.max_display_time}s)")
        
        if actual_speed > recommended_speed * 1.5:
            issues.append(f"阅读速度过快 ({actual_speed:.1f} > {recommended_speed * 1.5:.1f} 字符/秒)")
        
        if actual_speed < recommended_speed * 0.5:
            issues.append(f"阅读速度过慢 ({actual_speed:.1f} < {recommended_speed * 0.5:.1f} 字符/秒)")
        
        if char_count > 30:
            issues.append(f"文本过长 ({char_count} > 30 字符)")
        
        if char_count < 3 and duration > 2.0:
            issues.append(f"短文本显示时间过长 ({char_count} 字符显示 {duration:.1f}s)")
        
        return issues
    
    def _apply_optimization_strategy(self, subtitle_entry: SubtitleEntry,
                                   strategy: Optional[OptimizationStrategy],
                                   recommended_duration: float,
                                   context_entries: Optional[List[SubtitleEntry]] = None) -> Optional[SubtitleEntry]:
        """应用优化策略"""
        if not strategy:
            return subtitle_entry
        
        try:
            if strategy == OptimizationStrategy.EXTEND:
                return self._extend_duration(subtitle_entry, recommended_duration, context_entries)
            elif strategy == OptimizationStrategy.COMPRESS:
                return self._compress_text(subtitle_entry)
            elif strategy == OptimizationStrategy.SPLIT:
                # 分割策略需要返回多个字幕，这里简化处理
                return self._compress_text(subtitle_entry)
            else:
                return subtitle_entry
                
        except Exception as e:
            logger.error("优化策略应用失败", strategy=strategy.value, error=str(e))
            return None
    
    def _extend_duration(self, subtitle_entry: SubtitleEntry, 
                        recommended_duration: float,
                        context_entries: Optional[List[SubtitleEntry]] = None) -> SubtitleEntry:
        """延长显示时间"""
        current_duration = self._calculate_duration(subtitle_entry.start_time, subtitle_entry.end_time)
        extension_needed = recommended_duration - current_duration
        
        # 限制最大延长时间
        extension_needed = min(extension_needed, 2.0)
        
        # 计算新的结束时间
        start_seconds = (subtitle_entry.start_time.hours * 3600 + 
                        subtitle_entry.start_time.minutes * 60 + 
                        subtitle_entry.start_time.seconds + 
                        subtitle_entry.start_time.milliseconds / 1000)
        
        new_end_seconds = start_seconds + recommended_duration
        
        # 检查是否与下一个字幕冲突
        if context_entries:
            next_entry = self._find_next_entry(subtitle_entry, context_entries)
            if next_entry:
                next_start_seconds = (next_entry.start_time.hours * 3600 + 
                                    next_entry.start_time.minutes * 60 + 
                                    next_entry.start_time.seconds + 
                                    next_entry.start_time.milliseconds / 1000)
                
                # 保持最小间隔
                max_end_seconds = next_start_seconds - self.min_gap_time
                new_end_seconds = min(new_end_seconds, max_end_seconds)
        
        # 转换回TimeCode
        new_end_time = self._seconds_to_timecode(new_end_seconds)
        
        # 创建新的字幕条目
        optimized_entry = SubtitleEntry(
            index=subtitle_entry.index,
            start_time=subtitle_entry.start_time,
            end_time=new_end_time,
            text=subtitle_entry.text,
            speaker=subtitle_entry.speaker
        )
        
        return optimized_entry
    
    def _compress_text(self, subtitle_entry: SubtitleEntry) -> SubtitleEntry:
        """压缩文本"""
        text = subtitle_entry.text
        
        # 简单的文本压缩策略
        # 1. 移除多余空格
        text = " ".join(text.split())
        
        # 2. 替换常见的长词组
        compressions = {
            "非常": "很",
            "特别": "很",
            "实在是": "真",
            "的话": "",
            "这样的": "这",
            "那样的": "那",
            "什么的": "等",
            "之类的": "等"
        }
        
        for long_form, short_form in compressions.items():
            text = text.replace(long_form, short_form)
        
        # 3. 如果还是太长，截断并添加省略号
        if len(text) > 25:
            text = text[:22] + "..."
        
        # 创建新的字幕条目
        optimized_entry = SubtitleEntry(
            index=subtitle_entry.index,
            start_time=subtitle_entry.start_time,
            end_time=subtitle_entry.end_time,
            text=text,
            speaker=subtitle_entry.speaker
        )
        
        return optimized_entry
    
    def _find_next_entry(self, current_entry: SubtitleEntry, 
                        context_entries: List[SubtitleEntry]) -> Optional[SubtitleEntry]:
        """查找下一个字幕条目"""
        current_index = current_entry.index
        next_entries = [entry for entry in context_entries if entry.index > current_index]
        
        if next_entries:
            return min(next_entries, key=lambda x: x.index)
        
        return None
    
    def _seconds_to_timecode(self, seconds: float) -> TimeCode:
        """将秒数转换为TimeCode"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return TimeCode(hours, minutes, secs, milliseconds)
    
    def _calculate_improvement_score(self, before: TimingAnalysis, 
                                   after: TimingAnalysis) -> float:
        """计算改进分数"""
        if before.quality_score == 0:
            return 1.0 if after.quality_score > 0 else 0.0
        
        improvement = (after.quality_score - before.quality_score) / before.quality_score
        return max(0.0, min(2.0, 1.0 + improvement))


class RhythmAnalyzer:
    """节奏分析器
    
    主要功能：
    1. 分析字幕序列的节奏模式
    2. 识别场景类型和转换点
    3. 评估节奏一致性
    4. 提供节奏优化建议
    """
    
    def __init__(self):
        # 场景类型的节奏特征
        self.scene_rhythm_patterns = {
            SceneType.DIALOGUE: {
                "avg_duration_range": (1.5, 3.5),
                "variance_threshold": 0.8,
                "pace_preference": "moderate"
            },
            SceneType.ACTION: {
                "avg_duration_range": (0.8, 2.0),
                "variance_threshold": 1.2,
                "pace_preference": "fast"
            },
            SceneType.EMOTIONAL: {
                "avg_duration_range": (2.0, 4.0),
                "variance_threshold": 0.6,
                "pace_preference": "slow"
            },
            SceneType.EXPOSITION: {
                "avg_duration_range": (2.5, 4.5),
                "variance_threshold": 0.5,
                "pace_preference": "slow"
            },
            SceneType.COMEDY: {
                "avg_duration_range": (1.0, 2.5),
                "variance_threshold": 1.0,
                "pace_preference": "varied"
            },
            SceneType.DRAMATIC: {
                "avg_duration_range": (1.8, 3.8),
                "variance_threshold": 0.9,
                "pace_preference": "moderate"
            }
        }
        
        logger.info("节奏分析器初始化完成")
    
    def analyze_rhythm(self, subtitle_entries: List[SubtitleEntry],
                      scene_type: Optional[SceneType] = None) -> RhythmAnalysis:
        """分析字幕节奏"""
        try:
            if not subtitle_entries:
                return RhythmAnalysis(
                    subtitle_entries=[],
                    scene_type=SceneType.DIALOGUE,
                    average_duration=0,
                    duration_variance=0,
                    pace_score=0,
                    rhythm_consistency=0,
                    scene_transitions=[]
                )
            
            # 计算时长统计
            durations = []
            timing_optimizer = SubtitleTimingOptimizer()
            
            for entry in subtitle_entries:
                duration = timing_optimizer._calculate_duration(entry.start_time, entry.end_time)
                durations.append(duration)
            
            avg_duration = sum(durations) / len(durations)
            duration_variance = self._calculate_variance(durations, avg_duration)
            
            # 推断场景类型（如果未提供）
            if scene_type is None:
                scene_type = self._infer_scene_type(subtitle_entries, avg_duration, duration_variance)
            
            # 计算节奏评分
            pace_score = self._calculate_pace_score(avg_duration, duration_variance, scene_type)
            
            # 计算节奏一致性
            rhythm_consistency = self._calculate_rhythm_consistency(durations, scene_type)
            
            # 识别场景转换
            scene_transitions = self._identify_scene_transitions(subtitle_entries, durations)
            
            # 生成建议
            recommendations = self._generate_rhythm_recommendations(
                avg_duration, duration_variance, pace_score, rhythm_consistency, scene_type
            )
            
            return RhythmAnalysis(
                subtitle_entries=subtitle_entries,
                scene_type=scene_type,
                average_duration=avg_duration,
                duration_variance=duration_variance,
                pace_score=pace_score,
                rhythm_consistency=rhythm_consistency,
                scene_transitions=scene_transitions,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error("节奏分析失败", error=str(e))
            return RhythmAnalysis(
                subtitle_entries=subtitle_entries,
                scene_type=SceneType.DIALOGUE,
                average_duration=0,
                duration_variance=0,
                pace_score=0,
                rhythm_consistency=0,
                scene_transitions=[],
                recommendations=[f"分析失败: {str(e)}"]
            )
    
    def _calculate_variance(self, values: List[float], mean: float) -> float:
        """计算方差"""
        if not values:
            return 0.0
        
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)  # 返回标准差
    
    def _infer_scene_type(self, subtitle_entries: List[SubtitleEntry],
                         avg_duration: float, duration_variance: float) -> SceneType:
        """推断场景类型"""
        # 基于时长特征推断场景类型
        if avg_duration < 1.5 and duration_variance > 1.0:
            return SceneType.ACTION
        elif avg_duration > 3.5 and duration_variance < 0.6:
            return SceneType.EXPOSITION
        elif duration_variance > 1.2:
            return SceneType.COMEDY
        elif avg_duration > 2.5:
            return SceneType.EMOTIONAL
        else:
            return SceneType.DIALOGUE
    
    def _calculate_pace_score(self, avg_duration: float, duration_variance: float,
                            scene_type: SceneType) -> float:
        """计算节奏评分"""
        pattern = self.scene_rhythm_patterns.get(scene_type, 
                                                self.scene_rhythm_patterns[SceneType.DIALOGUE])
        
        # 检查平均时长是否在理想范围内
        duration_range = pattern["avg_duration_range"]
        if duration_range[0] <= avg_duration <= duration_range[1]:
            duration_score = 1.0
        else:
            # 计算偏离程度
            if avg_duration < duration_range[0]:
                deviation = (duration_range[0] - avg_duration) / duration_range[0]
            else:
                deviation = (avg_duration - duration_range[1]) / duration_range[1]
            
            duration_score = max(0.0, 1.0 - deviation)
        
        # 检查方差是否合理
        variance_threshold = pattern["variance_threshold"]
        if duration_variance <= variance_threshold:
            variance_score = 1.0
        else:
            variance_score = max(0.0, 1.0 - (duration_variance - variance_threshold) / variance_threshold)
        
        # 综合评分
        return (duration_score + variance_score) / 2
    
    def _calculate_rhythm_consistency(self, durations: List[float], 
                                    scene_type: SceneType) -> float:
        """计算节奏一致性"""
        if len(durations) < 2:
            return 1.0
        
        # 计算相邻字幕时长的变化率
        changes = []
        for i in range(1, len(durations)):
            if durations[i-1] > 0:
                change_rate = abs(durations[i] - durations[i-1]) / durations[i-1]
                changes.append(change_rate)
        
        if not changes:
            return 1.0
        
        # 计算平均变化率
        avg_change_rate = sum(changes) / len(changes)
        
        # 根据场景类型调整一致性标准
        if scene_type in [SceneType.ACTION, SceneType.COMEDY]:
            # 动作和喜剧场景允许更大的变化
            consistency_threshold = 0.5
        else:
            # 其他场景要求更高的一致性
            consistency_threshold = 0.3
        
        if avg_change_rate <= consistency_threshold:
            return 1.0
        else:
            return max(0.0, 1.0 - (avg_change_rate - consistency_threshold) / consistency_threshold)
    
    def _identify_scene_transitions(self, subtitle_entries: List[SubtitleEntry],
                                  durations: List[float]) -> List[int]:
        """识别场景转换点"""
        transitions = []
        
        if len(durations) < 5:  # 需要足够的数据点
            return transitions
        
        # 使用滑动窗口检测节奏变化
        window_size = 3
        threshold = 0.6  # 变化阈值
        
        for i in range(window_size, len(durations) - window_size):
            # 计算前后窗口的平均时长
            before_avg = sum(durations[i-window_size:i]) / window_size
            after_avg = sum(durations[i:i+window_size]) / window_size
            
            # 计算变化率
            if before_avg > 0:
                change_rate = abs(after_avg - before_avg) / before_avg
                
                if change_rate > threshold:
                    transitions.append(subtitle_entries[i].index)
        
        return transitions
    
    def _generate_rhythm_recommendations(self, avg_duration: float, duration_variance: float,
                                       pace_score: float, rhythm_consistency: float,
                                       scene_type: SceneType) -> List[str]:
        """生成节奏优化建议"""
        recommendations = []
        
        pattern = self.scene_rhythm_patterns.get(scene_type,
                                               self.scene_rhythm_patterns[SceneType.DIALOGUE])
        
        # 平均时长建议
        duration_range = pattern["avg_duration_range"]
        if avg_duration < duration_range[0]:
            recommendations.append(f"建议延长字幕显示时间，当前平均 {avg_duration:.1f}s，建议 {duration_range[0]}-{duration_range[1]}s")
        elif avg_duration > duration_range[1]:
            recommendations.append(f"建议缩短字幕显示时间，当前平均 {avg_duration:.1f}s，建议 {duration_range[0]}-{duration_range[1]}s")
        
        # 节奏一致性建议
        if rhythm_consistency < 0.7:
            recommendations.append("节奏变化过大，建议保持更一致的字幕时长")
        
        # 场景特定建议
        if scene_type == SceneType.ACTION and avg_duration > 2.0:
            recommendations.append("动作场景建议使用更短的字幕以保持紧张感")
        elif scene_type == SceneType.EMOTIONAL and avg_duration < 2.0:
            recommendations.append("情感场景建议使用更长的字幕以增强感染力")
        elif scene_type == SceneType.COMEDY and duration_variance < 0.5:
            recommendations.append("喜剧场景建议增加节奏变化以增强幽默效果")
        
        # 整体质量建议
        if pace_score < 0.6:
            recommendations.append("整体节奏需要优化，建议调整字幕时长分布")
        
        return recommendations


class SubtitleOptimizationAgent:
    """字幕优化 Agent
    
    集成时长优化和节奏分析功能
    """
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or f"optimization_agent_{uuid.uuid4().hex[:8]}"
        self.timing_optimizer = SubtitleTimingOptimizer()
        self.rhythm_analyzer = RhythmAnalyzer()
        
        # 性能统计
        self.performance_stats = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "average_improvement_score": 0.0,
            "rhythm_analyses": 0,
            "scene_type_distribution": {},
            "optimization_strategy_distribution": {}
        }
        
        logger.info("字幕优化 Agent 初始化完成", agent_id=self.agent_id)
    
    def optimize_subtitle_sequence(self, subtitle_entries: List[SubtitleEntry],
                                 language: str = "zh",
                                 reading_speed: ReadingSpeedStandard = ReadingSpeedStandard.NORMAL,
                                 scene_type: Optional[SceneType] = None) -> Dict[str, Any]:
        """优化字幕序列"""
        try:
            results = {
                "optimization_results": [],
                "rhythm_analysis": None,
                "overall_improvement": 0.0,
                "success": True,
                "error_message": None
            }
            
            # 节奏分析
            rhythm_analysis = self.rhythm_analyzer.analyze_rhythm(subtitle_entries, scene_type)
            rhythm_dict = asdict(rhythm_analysis)
            # 转换枚举值为字符串
            rhythm_dict["scene_type"] = rhythm_analysis.scene_type.value
            results["rhythm_analysis"] = rhythm_dict
            self.performance_stats["rhythm_analyses"] += 1
            
            # 更新场景类型分布统计
            scene_name = rhythm_analysis.scene_type.value
            if scene_name not in self.performance_stats["scene_type_distribution"]:
                self.performance_stats["scene_type_distribution"][scene_name] = 0
            self.performance_stats["scene_type_distribution"][scene_name] += 1
            
            # 逐个优化字幕
            optimization_results = []
            total_improvement = 0.0
            successful_optimizations = 0
            
            for entry in subtitle_entries:
                optimization_result = self.timing_optimizer.optimize_timing(
                    entry, language, reading_speed, subtitle_entries
                )
                
                # 转换优化结果，处理枚举值
                opt_dict = asdict(optimization_result)
                if optimization_result.strategy_used:
                    opt_dict["strategy_used"] = optimization_result.strategy_used.value
                if optimization_result.before_analysis and optimization_result.before_analysis.optimization_needed:
                    opt_dict["before_analysis"]["optimization_needed"] = optimization_result.before_analysis.optimization_needed.value
                if optimization_result.after_analysis and optimization_result.after_analysis.optimization_needed:
                    opt_dict["after_analysis"]["optimization_needed"] = optimization_result.after_analysis.optimization_needed.value
                optimization_results.append(opt_dict)
                
                if optimization_result.success:
                    successful_optimizations += 1
                    total_improvement += optimization_result.improvement_score
                    
                    # 更新策略分布统计
                    if optimization_result.strategy_used:
                        strategy_name = optimization_result.strategy_used.value
                        if strategy_name not in self.performance_stats["optimization_strategy_distribution"]:
                            self.performance_stats["optimization_strategy_distribution"][strategy_name] = 0
                        self.performance_stats["optimization_strategy_distribution"][strategy_name] += 1
                
                self.performance_stats["total_optimizations"] += 1
            
            results["optimization_results"] = optimization_results
            
            # 计算整体改进分数
            if successful_optimizations > 0:
                results["overall_improvement"] = total_improvement / successful_optimizations
                self.performance_stats["successful_optimizations"] += successful_optimizations
                
                # 更新平均改进分数
                total_successful = self.performance_stats["successful_optimizations"]
                current_avg = self.performance_stats["average_improvement_score"]
                new_avg = (current_avg * (total_successful - successful_optimizations) + 
                          total_improvement) / total_successful
                self.performance_stats["average_improvement_score"] = new_avg
            
            logger.info("字幕序列优化完成",
                       total_entries=len(subtitle_entries),
                       successful_optimizations=successful_optimizations,
                       overall_improvement=results["overall_improvement"])
            
            return results
            
        except Exception as e:
            logger.error("字幕序列优化失败", error=str(e))
            return {
                "optimization_results": [],
                "rhythm_analysis": None,
                "overall_improvement": 0.0,
                "success": False,
                "error_message": str(e)
            }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """获取 Agent 状态"""
        return {
            "agent_id": self.agent_id,
            "performance_stats": self.performance_stats,
            "supported_languages": list(self.timing_optimizer.language_reading_speeds.keys()),
            "reading_speed_standards": [speed.value for speed in ReadingSpeedStandard],
            "scene_types": [scene.value for scene in SceneType],
            "optimization_strategies": [strategy.value for strategy in OptimizationStrategy]
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.performance_stats = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "average_improvement_score": 0.0,
            "rhythm_analyses": 0,
            "scene_type_distribution": {},
            "optimization_strategy_distribution": {}
        }
        logger.info("性能统计已重置")


# 全局字幕优化 Agent 实例
subtitle_optimization_agent = SubtitleOptimizationAgent()


def get_subtitle_optimization_agent() -> SubtitleOptimizationAgent:
    """获取字幕优化 Agent 实例"""
    return subtitle_optimization_agent


# 便捷函数
def optimize_subtitle_timing(subtitle_entry: SubtitleEntry,
                           language: str = "zh",
                           reading_speed: ReadingSpeedStandard = ReadingSpeedStandard.NORMAL) -> OptimizationResult:
    """便捷的字幕时长优化函数"""
    agent = get_subtitle_optimization_agent()
    return agent.timing_optimizer.optimize_timing(subtitle_entry, language, reading_speed)


def analyze_subtitle_rhythm(subtitle_entries: List[SubtitleEntry],
                          scene_type: Optional[SceneType] = None) -> RhythmAnalysis:
    """便捷的字幕节奏分析函数"""
    agent = get_subtitle_optimization_agent()
    return agent.rhythm_analyzer.analyze_rhythm(subtitle_entries, scene_type)