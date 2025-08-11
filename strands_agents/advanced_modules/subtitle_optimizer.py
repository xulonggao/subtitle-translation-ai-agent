"""
字幕优化器
处理字幕时长、节奏分析和阅读速度优化
从agents/subtitle_optimization_agent.py迁移而来，符合需求6和需求8
"""
import json
import time
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

from . import AdvancedModule, module_registry

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
    duration_seconds: float
    character_count: int
    reading_speed_cps: float  # 字符每秒
    is_optimal: bool
    recommended_duration: Optional[float] = None
    optimization_needed: Optional[str] = None
    quality_score: float = 0.0
    issues: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []

@dataclass
class OptimizationResult:
    """优化结果"""
    original_text: str
    optimized_text: Optional[str] = None
    original_timing: Optional[Dict[str, float]] = None
    optimized_timing: Optional[Dict[str, float]] = None
    strategy_used: Optional[str] = None
    improvement_score: float = 0.0
    before_analysis: Optional[TimingAnalysis] = None
    after_analysis: Optional[TimingAnalysis] = None
    success: bool = False
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.original_timing is None:
            self.original_timing = {}
        if self.optimized_timing is None:
            self.optimized_timing = {}

class SubtitleOptimizer(AdvancedModule):
    """字幕优化器
    
    核心功能：
    1. 阅读速度标准分析 (符合需求6: 翻译质量控制)
    2. 场景类型分析
    3. 优化策略选择
    4. 时长分析算法 (符合需求8: 结果导出和格式化)
    """
    
    def __init__(self):
        super().__init__("subtitle_optimizer", "1.0.0")
        
        # 语言特定的阅读速度配置（字符每秒）
        self.language_reading_speeds = self._initialize_reading_speeds()
        
        # 时长限制
        self.min_display_time = 0.8  # 最小显示时间（秒）
        self.max_display_time = 6.0  # 最大显示时间（秒）
        self.min_gap_time = 0.1      # 字幕间隔时间（秒）
        
        # 性能统计
        self.performance_stats = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "average_improvement": 0.0,
            "strategy_usage": {
                "compress": 0,
                "split": 0,
                "extend": 0,
                "merge": 0,
                "rewrite": 0
            },
            "processing_times": []
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理字幕优化
        
        Args:
            input_data: {
                "entries": "字幕条目JSON字符串",
                "target_language": "目标语言代码",
                "optimization_config": "优化配置JSON字符串"
            }
        
        Returns:
            优化后的字幕条目和分析报告
        """
        start_time = time.time()
        
        if not self.validate_input(input_data):
            return self.create_result(
                False,
                error="Invalid input data for subtitle optimization",
                processing_time=time.time() - start_time
            )
        
        try:
            entries = self.from_json(input_data["entries"])
            target_language = input_data.get("target_language", "en")
            optimization_config = self.from_json(input_data.get("optimization_config", "{}"))
            
            # 获取配置参数
            reading_speed = optimization_config.get("reading_speed", "normal")
            scene_type = optimization_config.get("scene_type", "dialogue")
            auto_optimize = optimization_config.get("auto_optimize", True)
            
            # 处理单个条目或条目列表
            if isinstance(entries, list):
                entry_list = entries
            else:
                entry_list = [entries]
            
            # 优化每个字幕条目
            optimization_results = []
            total_improvement = 0.0
            
            for entry in entry_list:
                result = self._optimize_single_entry(
                    entry, target_language, reading_speed, scene_type, auto_optimize
                )
                optimization_results.append(result)
                if result.success:
                    total_improvement += result.improvement_score
            
            # 计算整体统计
            successful_count = sum(1 for r in optimization_results if r.success)
            average_improvement = total_improvement / len(optimization_results) if optimization_results else 0.0
            
            # 生成优化建议
            recommendations = self._generate_optimization_recommendations(optimization_results)
            
            processing_time = time.time() - start_time
            
            # 更新统计信息
            self._update_stats(optimization_results, processing_time)
            
            return self.create_result(
                True,
                data={
                    "optimization_results": [asdict(r) for r in optimization_results],
                    "optimization_summary": {
                        "total_entries": len(optimization_results),
                        "successful_optimizations": successful_count,
                        "average_improvement": average_improvement,
                        "target_language": target_language,
                        "reading_speed": reading_speed
                    },
                    "recommendations": recommendations
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            return self.create_result(
                False,
                error=f"Subtitle optimization failed: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["entries"]
        return all(field in input_data for field in required_fields)
    
    def _optimize_single_entry(self, entry: Any, target_language: str, 
                              reading_speed: str, scene_type: str, auto_optimize: bool) -> OptimizationResult:
        """优化单个字幕条目"""
        try:
            # 解析条目数据
            if isinstance(entry, dict):
                text = entry.get("text", "")
                start_time = entry.get("start_time", 0.0)
                end_time = entry.get("end_time", 2.0)
            else:
                text = str(entry)
                start_time = 0.0
                end_time = 2.0
            
            # 分析当前时长
            before_analysis = self._analyze_timing(text, start_time, end_time, target_language, reading_speed)
            
            if before_analysis.is_optimal and not auto_optimize:
                return OptimizationResult(
                    original_text=text,
                    optimized_text=text,
                    original_timing={"start": start_time, "end": end_time, "duration": end_time - start_time},
                    optimized_timing={"start": start_time, "end": end_time, "duration": end_time - start_time},
                    strategy_used=None,
                    improvement_score=1.0,
                    before_analysis=before_analysis,
                    after_analysis=before_analysis,
                    success=True
                )
            
            # 执行优化
            if auto_optimize and before_analysis.optimization_needed:
                optimized_text, optimized_timing = self._apply_optimization_strategy(
                    text, start_time, end_time, before_analysis.optimization_needed, 
                    before_analysis.recommended_duration, target_language
                )
                
                # 分析优化后的结果
                after_analysis = self._analyze_timing(
                    optimized_text, optimized_timing["start"], optimized_timing["end"], 
                    target_language, reading_speed
                )
                
                # 计算改进分数
                improvement_score = self._calculate_improvement_score(before_analysis, after_analysis)
                
                return OptimizationResult(
                    original_text=text,
                    optimized_text=optimized_text,
                    original_timing={"start": start_time, "end": end_time, "duration": end_time - start_time},
                    optimized_timing=optimized_timing,
                    strategy_used=before_analysis.optimization_needed,
                    improvement_score=improvement_score,
                    before_analysis=before_analysis,
                    after_analysis=after_analysis,
                    success=True
                )
            else:
                return OptimizationResult(
                    original_text=text,
                    optimized_text=text,
                    original_timing={"start": start_time, "end": end_time, "duration": end_time - start_time},
                    before_analysis=before_analysis,
                    success=True,
                    improvement_score=before_analysis.quality_score
                )
                
        except Exception as e:
            return OptimizationResult(
                original_text=str(entry),
                success=False,
                error_message=str(e)
            )
    
    def _analyze_timing(self, text: str, start_time: float, end_time: float, 
                       language: str, reading_speed: str) -> TimingAnalysis:
        """分析字幕时长"""
        # 计算显示时长
        duration = end_time - start_time
        
        # 计算字符数
        char_count = len(text.strip())
        
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
        quality_score = self._calculate_timing_quality(duration, char_count, language, reading_speed)
        
        # 识别问题
        issues = self._identify_timing_issues(duration, char_count, actual_speed, recommended_speed)
        
        return TimingAnalysis(
            duration_seconds=duration,
            character_count=char_count,
            reading_speed_cps=actual_speed,
            is_optimal=is_optimal,
            recommended_duration=recommended_duration,
            optimization_needed=optimization_strategy,
            quality_score=quality_score,
            issues=issues
        )
    
    def _apply_optimization_strategy(self, text: str, start_time: float, end_time: float,
                                   strategy: str, recommended_duration: float, 
                                   language: str) -> Tuple[str, Dict[str, float]]:
        """应用优化策略"""
        duration = end_time - start_time
        
        if strategy == "extend":
            # 延长显示时间
            new_end_time = start_time + recommended_duration
            return text, {"start": start_time, "end": new_end_time, "duration": recommended_duration}
        
        elif strategy == "compress":
            # 压缩文本
            compressed_text = self._compress_text(text, language)
            return compressed_text, {"start": start_time, "end": end_time, "duration": duration}
        
        elif strategy == "split":
            # 分割字幕（简化实现：返回原文本）
            return text, {"start": start_time, "end": end_time, "duration": duration}
        
        elif strategy == "merge":
            # 合并字幕（简化实现：返回原文本）
            return text, {"start": start_time, "end": end_time, "duration": duration}
        
        elif strategy == "rewrite":
            # 重写文本（简化实现：压缩文本）
            rewritten_text = self._compress_text(text, language)
            return rewritten_text, {"start": start_time, "end": end_time, "duration": duration}
        
        else:
            return text, {"start": start_time, "end": end_time, "duration": duration}
    
    def _compress_text(self, text: str, language: str) -> str:
        """压缩文本"""
        # 简化的文本压缩逻辑
        compressed = text.strip()
        
        # 移除多余的空格
        compressed = " ".join(compressed.split())
        
        # 简化常见词汇（针对中文）
        if language == "zh":
            replacements = {
                "非常": "很",
                "特别": "很",
                "尤其": "特",
                "因为": "因",
                "所以": "所以",
                "但是": "但",
                "然后": "然后",
                "现在": "现在",
                "已经": "已",
                "正在": "在"
            }
            for old, new in replacements.items():
                compressed = compressed.replace(old, new)
        
        return compressed
    
    def _get_reading_speed(self, language: str, speed_level: str) -> float:
        """获取阅读速度"""
        lang_speeds = self.language_reading_speeds.get(language, self.language_reading_speeds["en"])
        speed_enum = ReadingSpeedStandard(speed_level)
        return lang_speeds.get(speed_enum, lang_speeds[ReadingSpeedStandard.NORMAL])
    
    def _is_timing_optimal(self, duration: float, char_count: int, language: str, reading_speed: str) -> bool:
        """判断时长是否最优"""
        if duration < self.min_display_time or duration > self.max_display_time:
            return False
        
        recommended_speed = self._get_reading_speed(language, reading_speed)
        actual_speed = char_count / duration if duration > 0 else 0
        
        # 允许20%的误差范围
        speed_ratio = actual_speed / recommended_speed if recommended_speed > 0 else 1
        return 0.8 <= speed_ratio <= 1.2
    
    def _determine_optimization_strategy(self, duration: float, char_count: int, 
                                       recommended_duration: float) -> Optional[str]:
        """确定优化策略"""
        if duration < self.min_display_time:
            return "extend"
        elif duration > self.max_display_time:
            if char_count > 50:  # 文本较长
                return "compress"
            else:
                return "split"
        elif duration < recommended_duration * 0.8:
            return "extend"
        elif duration > recommended_duration * 1.5:
            return "compress"
        else:
            return None
    
    def _calculate_timing_quality(self, duration: float, char_count: int, 
                                language: str, reading_speed: str) -> float:
        """计算时长质量评分"""
        # 基础分数
        score = 0.8
        
        # 时长范围检查
        if self.min_display_time <= duration <= self.max_display_time:
            score += 0.1
        
        # 阅读速度检查
        recommended_speed = self._get_reading_speed(language, reading_speed)
        actual_speed = char_count / duration if duration > 0 else 0
        
        if recommended_speed > 0:
            speed_ratio = actual_speed / recommended_speed
            if 0.8 <= speed_ratio <= 1.2:
                score += 0.1
            elif 0.6 <= speed_ratio <= 1.5:
                score += 0.05
        
        return min(score, 1.0)
    
    def _identify_timing_issues(self, duration: float, char_count: int, 
                              actual_speed: float, recommended_speed: float) -> List[str]:
        """识别时长问题"""
        issues = []
        
        if duration < self.min_display_time:
            issues.append(f"显示时间过短 ({duration:.1f}s < {self.min_display_time}s)")
        
        if duration > self.max_display_time:
            issues.append(f"显示时间过长 ({duration:.1f}s > {self.max_display_time}s)")
        
        if recommended_speed > 0:
            speed_ratio = actual_speed / recommended_speed
            if speed_ratio > 1.5:
                issues.append(f"阅读速度过快 ({actual_speed:.1f} > {recommended_speed:.1f} 字符/秒)")
            elif speed_ratio < 0.6:
                issues.append(f"阅读速度过慢 ({actual_speed:.1f} < {recommended_speed:.1f} 字符/秒)")
        
        if char_count == 0:
            issues.append("字幕内容为空")
        
        return issues
    
    def _calculate_improvement_score(self, before: TimingAnalysis, after: TimingAnalysis) -> float:
        """计算改进分数"""
        if not before or not after:
            return 0.0
        
        # 质量评分改进
        quality_improvement = after.quality_score - before.quality_score
        
        # 问题数量改进
        issue_improvement = (len(before.issues) - len(after.issues)) / max(len(before.issues), 1)
        
        # 综合改进分数
        improvement = (quality_improvement + issue_improvement) / 2
        return max(0.0, min(improvement + 0.5, 1.0))  # 基础分数0.5，改进可达1.0
    
    def _generate_optimization_recommendations(self, results: List[OptimizationResult]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if not results:
            return recommendations
        
        # 统计策略使用情况
        strategy_counts = {}
        successful_count = 0
        total_improvement = 0.0
        
        for result in results:
            if result.success:
                successful_count += 1
                total_improvement += result.improvement_score
                
                if result.strategy_used:
                    strategy_counts[result.strategy_used] = strategy_counts.get(result.strategy_used, 0) + 1
        
        # 生成建议
        if successful_count > 0:
            avg_improvement = total_improvement / successful_count
            recommendations.append(f"成功优化 {successful_count}/{len(results)} 个字幕条目")
            recommendations.append(f"平均改进分数: {avg_improvement:.2f}")
        
        # 策略建议
        if strategy_counts:
            most_used_strategy = max(strategy_counts.items(), key=lambda x: x[1])
            recommendations.append(f"主要优化策略: {most_used_strategy[0]} (使用{most_used_strategy[1]}次)")
        
        # 问题建议
        failed_count = len(results) - successful_count
        if failed_count > 0:
            recommendations.append(f"{failed_count} 个条目需要人工检查")
        
        return recommendations[:5]  # 限制建议数量
    
    def _update_stats(self, results: List[OptimizationResult], processing_time: float):
        """更新统计信息"""
        self.performance_stats["total_optimizations"] += len(results)
        self.performance_stats["processing_times"].append(processing_time)
        
        successful_results = [r for r in results if r.success]
        self.performance_stats["successful_optimizations"] += len(successful_results)
        
        if successful_results:
            total_improvement = sum(r.improvement_score for r in successful_results)
            current_avg = self.performance_stats["average_improvement"]
            total_successful = self.performance_stats["successful_optimizations"]
            
            # 更新平均改进分数
            self.performance_stats["average_improvement"] = (
                (current_avg * (total_successful - len(successful_results)) + total_improvement) / total_successful
            )
            
            # 更新策略使用统计
            for result in successful_results:
                if result.strategy_used:
                    self.performance_stats["strategy_usage"][result.strategy_used] += 1
    
    def _initialize_reading_speeds(self) -> Dict[str, Dict[ReadingSpeedStandard, float]]:
        """初始化阅读速度配置"""
        return {
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
            "ar": {  # 阿拉伯文
                ReadingSpeedStandard.SLOW: 8,
                ReadingSpeedStandard.NORMAL: 11,
                ReadingSpeedStandard.FAST: 14,
                ReadingSpeedStandard.VERY_FAST: 17
            }
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_stats.copy()

# 注册模块
subtitle_optimizer = SubtitleOptimizer()
module_registry.register(subtitle_optimizer)