#!/usr/bin/env python3
"""
字幕显示验证器
实现字幕时长、字符数、重叠检测、格式验证等功能
"""
import re
import uuid
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

from config import get_logger
from models.subtitle_models import SubtitleEntry

logger = get_logger("subtitle_display_validator")


class ValidationSeverity(Enum):
    """验证问题严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ValidationType(Enum):
    """验证类型"""
    DURATION = "duration"
    CHARACTER_COUNT = "character_count"
    OVERLAP = "overlap"
    GAP = "gap"
    FORMAT = "format"
    READING_SPEED = "reading_speed"
    LINE_COUNT = "line_count"
    TIMING = "timing"


class FixStrategy(Enum):
    """修复策略"""
    AUTO_FIX = "auto_fix"
    SUGGEST_FIX = "suggest_fix"
    MANUAL_REVIEW = "manual_review"
    IGNORE = "ignore"


@dataclass
class ValidationRule:
    """验证规则"""
    rule_id: str
    rule_name: str
    validation_type: ValidationType
    severity: ValidationSeverity
    fix_strategy: FixStrategy = FixStrategy.SUGGEST_FIX
    description: str = ""
    parameters: Dict[str, Any] = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class ValidationIssue:
    """验证问题"""
    issue_id: str
    rule_id: str
    validation_type: ValidationType
    severity: ValidationSeverity
    subtitle_index: int
    subtitle_id: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = None
    suggested_fix: Optional[str] = None
    fix_strategy: FixStrategy = FixStrategy.SUGGEST_FIX
    can_auto_fix: bool = False
    detected_at: datetime = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.detected_at is None:
            self.detected_at = datetime.now()


@dataclass
class ValidationRequest:
    """验证请求"""
    request_id: str
    subtitle_entries: List[SubtitleEntry]
    target_language: str = "en"
    validation_rules: Optional[List[ValidationRule]] = None
    auto_fix: bool = False
    fix_threshold: ValidationSeverity = ValidationSeverity.HIGH
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.validation_rules is None:
            self.validation_rules = []


@dataclass
class ValidationResult:
    """验证结果"""
    request_id: str
    success: bool
    issues_found: List[ValidationIssue]
    fixed_issues: List[ValidationIssue] = None
    fixed_subtitles: Optional[List[SubtitleEntry]] = None
    validation_score: float = 1.0
    issues_by_type: Dict[ValidationType, int] = None
    issues_by_severity: Dict[ValidationSeverity, int] = None
    processing_time_ms: int = 0
    recommendations: List[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.fixed_issues is None:
            self.fixed_issues = []
        if self.issues_by_type is None:
            self.issues_by_type = {}
        if self.issues_by_severity is None:
            self.issues_by_severity = {}
        if self.recommendations is None:
            self.recommendations = []
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


class SubtitleDisplayValidator:
    """字幕显示验证器"""
    
    def __init__(self, validator_id: str = None):
        self.validator_id = validator_id or f"display_validator_{uuid.uuid4().hex[:8]}"
        self.language_configs = self._initialize_language_configs()
        self.built_in_rules = self._initialize_built_in_rules()
        self.custom_rules: List[ValidationRule] = []
        self.validation_stats = {
            "total_validations": 0,
            "issues_found": 0,
            "issues_fixed": 0,
            "validation_scores": [],
            "issue_types": defaultdict(int),
            "processing_times": []
        }
        logger.info("字幕显示验证器初始化完成", validator_id=self.validator_id)
    
    def _initialize_language_configs(self) -> Dict[str, Dict[str, Any]]:
        """初始化语言配置"""
        return {
            "en": {
                "max_chars_per_line": 42,
                "max_lines": 2,
                "min_duration_ms": 1000,
                "max_duration_ms": 7000,
                "reading_speed_cps": 17,
                "min_gap_ms": 250,
                "max_chars_total": 84
            },
            "zh": {
                "max_chars_per_line": 20,
                "max_lines": 2,
                "min_duration_ms": 1000,
                "max_duration_ms": 6000,
                "reading_speed_cps": 8,
                "min_gap_ms": 250,
                "max_chars_total": 40
            },
            "ja": {
                "max_chars_per_line": 18,
                "max_lines": 2,
                "min_duration_ms": 1200,
                "max_duration_ms": 6000,
                "reading_speed_cps": 9,
                "min_gap_ms": 300,
                "max_chars_total": 36
            }
        }
    
    def _initialize_built_in_rules(self) -> List[ValidationRule]:
        """初始化内置验证规则"""
        return [
            ValidationRule(
                rule_id="min_duration",
                rule_name="最小显示时长",
                validation_type=ValidationType.DURATION,
                severity=ValidationSeverity.HIGH,
                fix_strategy=FixStrategy.AUTO_FIX,
                description="检查字幕显示时长是否达到最小要求",
                parameters={"min_duration_ms": 1000}
            ),
            ValidationRule(
                rule_id="max_chars_per_line",
                rule_name="每行最大字符数",
                validation_type=ValidationType.CHARACTER_COUNT,
                severity=ValidationSeverity.HIGH,
                fix_strategy=FixStrategy.AUTO_FIX,
                description="检查每行字符数是否超过限制",
                parameters={"max_chars": 42}
            ),
            ValidationRule(
                rule_id="overlap_detection",
                rule_name="字幕重叠检测",
                validation_type=ValidationType.OVERLAP,
                severity=ValidationSeverity.CRITICAL,
                fix_strategy=FixStrategy.AUTO_FIX,
                description="检测字幕时间重叠问题"
            ),
            ValidationRule(
                rule_id="text_format",
                rule_name="文本格式",
                validation_type=ValidationType.FORMAT,
                severity=ValidationSeverity.MEDIUM,
                fix_strategy=FixStrategy.AUTO_FIX,
                description="检查文本格式问题"
            ),
            ValidationRule(
                rule_id="reading_speed",
                rule_name="阅读速度",
                validation_type=ValidationType.READING_SPEED,
                severity=ValidationSeverity.HIGH,
                fix_strategy=FixStrategy.AUTO_FIX,
                description="检查字幕阅读速度是否合理",
                parameters={"max_cps": 20}
            )
        ]

    async def validate_subtitles(self, request: ValidationRequest) -> ValidationResult:
        """验证字幕"""
        start_time = datetime.now()
        
        logger.info("开始字幕显示验证",
                   request_id=request.request_id,
                   subtitles_count=len(request.subtitle_entries),
                   target_language=request.target_language)
        
        try:
            all_rules = self.built_in_rules + self.custom_rules + (request.validation_rules or [])
            enabled_rules = [rule for rule in all_rules if rule.enabled]
            lang_config = self.language_configs.get(request.target_language, self.language_configs["en"])
            
            issues = []
            
            # 执行各种验证
            issues.extend(self._validate_duration_and_characters(request.subtitle_entries, enabled_rules, lang_config))
            issues.extend(self._validate_overlaps_and_gaps(request.subtitle_entries, enabled_rules, lang_config))
            issues.extend(self._validate_format(request.subtitle_entries, enabled_rules))
            issues.extend(self._validate_reading_speed(request.subtitle_entries, enabled_rules, lang_config))
            issues.extend(self._validate_timing_sequence(request.subtitle_entries, enabled_rules))
            
            # 自动修复
            fixed_issues = []
            fixed_subtitles = None
            if request.auto_fix:
                fixed_subtitles, fixed_issues = await self._auto_fix_issues(
                    request.subtitle_entries, issues, request.fix_threshold
                )
            
            validation_score = self._calculate_validation_score(issues, len(request.subtitle_entries))
            issues_by_type = self._count_issues_by_type(issues)
            issues_by_severity = self._count_issues_by_severity(issues)
            recommendations = self._generate_recommendations(issues)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = ValidationResult(
                request_id=request.request_id,
                success=True,
                issues_found=issues,
                fixed_issues=fixed_issues,
                fixed_subtitles=fixed_subtitles,
                validation_score=validation_score,
                issues_by_type=issues_by_type,
                issues_by_severity=issues_by_severity,
                processing_time_ms=int(processing_time),
                recommendations=recommendations,
                metadata={
                    "subtitles_count": len(request.subtitle_entries),
                    "rules_applied": len(enabled_rules),
                    "language": request.target_language
                }
            )
            
            self._update_validation_stats(request, result)
            
            logger.info("字幕显示验证完成",
                       request_id=request.request_id,
                       validation_score=validation_score,
                       issues_count=len(issues),
                       processing_time_ms=int(processing_time))
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.error("字幕显示验证失败",
                        request_id=request.request_id,
                        error=str(e),
                        processing_time_ms=int(processing_time))
            
            return ValidationResult(
                request_id=request.request_id,
                success=False,
                issues_found=[],
                validation_score=0.0,
                processing_time_ms=int(processing_time),
                recommendations=[f"验证过程中发生错误: {str(e)}"]
            )

    def _validate_duration_and_characters(self, subtitles: List[SubtitleEntry], 
                                         rules: List[ValidationRule],
                                         lang_config: Dict[str, Any]) -> List[ValidationIssue]:
        """验证时长和字符数"""
        issues = []
        
        for i, subtitle in enumerate(subtitles):
            duration_ms = subtitle.duration_seconds * 1000
            lines = subtitle.text.split('\n')
            
            # 检查最小时长
            min_duration_rule = next((r for r in rules if r.rule_id == "min_duration"), None)
            if min_duration_rule and min_duration_rule.enabled:
                min_duration = lang_config.get("min_duration_ms", 1000)
                if duration_ms < min_duration:
                    issues.append(ValidationIssue(
                        issue_id=f"min_duration_{i}",
                        rule_id=min_duration_rule.rule_id,
                        validation_type=ValidationType.DURATION,
                        severity=min_duration_rule.severity,
                        subtitle_index=i,
                        message=f"显示时长过短: {duration_ms}ms < {min_duration}ms",
                        details={
                            "current_duration_ms": duration_ms,
                            "min_duration_ms": min_duration
                        },
                        suggested_fix=f"建议延长显示时间至 {min_duration}ms",
                        fix_strategy=min_duration_rule.fix_strategy,
                        can_auto_fix=True
                    ))
            
            # 检查每行字符数
            max_chars_rule = next((r for r in rules if r.rule_id == "max_chars_per_line"), None)
            if max_chars_rule and max_chars_rule.enabled:
                max_chars = lang_config.get("max_chars_per_line", 42)
                for line_idx, line in enumerate(lines):
                    if len(line) > max_chars:
                        issues.append(ValidationIssue(
                            issue_id=f"max_chars_line_{i}_{line_idx}",
                            rule_id=max_chars_rule.rule_id,
                            validation_type=ValidationType.CHARACTER_COUNT,
                            severity=max_chars_rule.severity,
                            subtitle_index=i,
                            message=f"第{line_idx+1}行字符数过多: {len(line)} > {max_chars}",
                            details={
                                "line_index": line_idx,
                                "line_length": len(line),
                                "max_chars": max_chars
                            },
                            suggested_fix=f"建议将该行分割或缩短至 {max_chars} 字符以内",
                            fix_strategy=max_chars_rule.fix_strategy,
                            can_auto_fix=True
                        ))
        
        return issues

    def _validate_overlaps_and_gaps(self, subtitles: List[SubtitleEntry],
                                   rules: List[ValidationRule],
                                   lang_config: Dict[str, Any]) -> List[ValidationIssue]:
        """验证重叠和间隔"""
        issues = []
        
        if len(subtitles) < 2:
            return issues
        
        overlap_rule = next((r for r in rules if r.rule_id == "overlap_detection"), None)
        
        for i in range(len(subtitles) - 1):
            current = subtitles[i]
            next_subtitle = subtitles[i + 1]
            
            # 检查重叠
            if overlap_rule and overlap_rule.enabled:
                if current.end_time > next_subtitle.start_time:
                    overlap_ms = (current.end_time - next_subtitle.start_time) * 1000
                    issues.append(ValidationIssue(
                        issue_id=f"overlap_{i}_{i+1}",
                        rule_id=overlap_rule.rule_id,
                        validation_type=ValidationType.OVERLAP,
                        severity=overlap_rule.severity,
                        subtitle_index=i,
                        message=f"字幕重叠: 第{i+1}条与第{i+2}条重叠 {overlap_ms:.0f}ms",
                        details={
                            "current_end": current.end_time,
                            "next_start": next_subtitle.start_time,
                            "overlap_ms": overlap_ms,
                            "next_index": i + 1
                        },
                        suggested_fix=f"建议调整第{i+1}条结束时间至 {next_subtitle.start_time}s",
                        fix_strategy=overlap_rule.fix_strategy,
                        can_auto_fix=True
                    ))
        
        return issues

    def _validate_format(self, subtitles: List[SubtitleEntry],
                        rules: List[ValidationRule]) -> List[ValidationIssue]:
        """验证格式"""
        issues = []
        
        format_rule = next((r for r in rules if r.rule_id == "text_format"), None)
        if not format_rule or not format_rule.enabled:
            return issues
        
        for i, subtitle in enumerate(subtitles):
            text = subtitle.text
            
            # 检查多余的空格
            if "  " in text:
                issues.append(ValidationIssue(
                    issue_id=f"double_space_{i}",
                    rule_id=format_rule.rule_id,
                    validation_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.LOW,
                    subtitle_index=i,
                    message="文本包含多余的空格",
                    details={"text": text},
                    suggested_fix="建议清理多余的空格",
                    fix_strategy=FixStrategy.AUTO_FIX,
                    can_auto_fix=True
                ))
            
            # 检查开头或结尾的空格
            if text.startswith(" ") or text.endswith(" "):
                issues.append(ValidationIssue(
                    issue_id=f"trim_space_{i}",
                    rule_id=format_rule.rule_id,
                    validation_type=ValidationType.FORMAT,
                    severity=ValidationSeverity.LOW,
                    subtitle_index=i,
                    message="文本开头或结尾有多余空格",
                    details={"text": text},
                    suggested_fix="建议去除开头和结尾的空格",
                    fix_strategy=FixStrategy.AUTO_FIX,
                    can_auto_fix=True
                ))
        
        return issues

    def _validate_reading_speed(self, subtitles: List[SubtitleEntry],
                               rules: List[ValidationRule],
                               lang_config: Dict[str, Any]) -> List[ValidationIssue]:
        """验证阅读速度"""
        issues = []
        
        reading_rule = next((r for r in rules if r.rule_id == "reading_speed"), None)
        if not reading_rule or not reading_rule.enabled:
            return issues
        
        max_cps = lang_config.get("reading_speed_cps", 17)
        
        for i, subtitle in enumerate(subtitles):
            text_length = len(subtitle.text.replace("\n", ""))
            duration_seconds = subtitle.duration_seconds
            
            if duration_seconds > 0:
                current_cps = text_length / duration_seconds
                
                if current_cps > max_cps:
                    issues.append(ValidationIssue(
                        issue_id=f"reading_speed_{i}",
                        rule_id=reading_rule.rule_id,
                        validation_type=ValidationType.READING_SPEED,
                        severity=reading_rule.severity,
                        subtitle_index=i,
                        message=f"阅读速度过快: {current_cps:.1f} > {max_cps} 字符/秒",
                        details={
                            "text_length": text_length,
                            "duration_seconds": duration_seconds,
                            "current_cps": current_cps,
                            "max_cps": max_cps
                        },
                        suggested_fix=f"建议延长显示时间至 {text_length / max_cps:.1f}秒",
                        fix_strategy=reading_rule.fix_strategy,
                        can_auto_fix=True
                    ))
        
        return issues

    def _validate_timing_sequence(self, subtitles: List[SubtitleEntry],
                                 rules: List[ValidationRule]) -> List[ValidationIssue]:
        """验证时间序列"""
        issues = []
        
        for i, subtitle in enumerate(subtitles):
            # 检查开始时间是否大于等于结束时间
            if subtitle.start_time >= subtitle.end_time:
                issues.append(ValidationIssue(
                    issue_id=f"invalid_duration_{i}",
                    rule_id="time_sequence",
                    validation_type=ValidationType.TIMING,
                    severity=ValidationSeverity.CRITICAL,
                    subtitle_index=i,
                    message=f"无效的时间范围: 开始时间 {subtitle.start_time}s >= 结束时间 {subtitle.end_time}s",
                    details={
                        "start_time": subtitle.start_time,
                        "end_time": subtitle.end_time
                    },
                    suggested_fix="建议检查并修正时间设置",
                    fix_strategy=FixStrategy.MANUAL_REVIEW,
                    can_auto_fix=False
                ))
        
        return issues

    async def _auto_fix_issues(self, subtitles: List[SubtitleEntry],
                              issues: List[ValidationIssue],
                              fix_threshold: ValidationSeverity) -> Tuple[List[SubtitleEntry], List[ValidationIssue]]:
        """自动修复问题"""
        fixed_subtitles = [subtitle.copy() for subtitle in subtitles]
        fixed_issues = []
        
        severity_order = {
            ValidationSeverity.CRITICAL: 0,
            ValidationSeverity.HIGH: 1,
            ValidationSeverity.MEDIUM: 2,
            ValidationSeverity.LOW: 3,
            ValidationSeverity.INFO: 4
        }
        
        fixable_issues = [
            issue for issue in issues 
            if issue.can_auto_fix and severity_order.get(issue.severity, 4) <= severity_order.get(fix_threshold, 4)
        ]
        
        for issue in fixable_issues:
            try:
                if self._apply_fix(fixed_subtitles, issue):
                    fixed_issues.append(issue)
            except Exception as e:
                logger.warning("自动修复失败", issue_id=issue.issue_id, error=str(e))
        
        return fixed_subtitles, fixed_issues

    def _apply_fix(self, subtitles: List[SubtitleEntry], issue: ValidationIssue) -> bool:
        """应用修复"""
        if issue.subtitle_index >= len(subtitles):
            return False
        
        subtitle = subtitles[issue.subtitle_index]
        
        try:
            if issue.validation_type == ValidationType.DURATION:
                if issue.rule_id == "min_duration":
                    min_duration_s = issue.details["min_duration_ms"] / 1000
                    subtitle.end_time = subtitle.start_time + min_duration_s
                    return True
            
            elif issue.validation_type == ValidationType.FORMAT:
                if "double_space" in issue.issue_id:
                    subtitle.text = re.sub(r'\s+', ' ', subtitle.text)
                    return True
                elif "trim_space" in issue.issue_id:
                    subtitle.text = subtitle.text.strip()
                    return True
            
            elif issue.validation_type == ValidationType.OVERLAP:
                next_start = issue.details["next_start"]
                subtitle.end_time = next_start - 0.001
                return True
            
            elif issue.validation_type == ValidationType.READING_SPEED:
                text_length = issue.details["text_length"]
                max_cps = issue.details["max_cps"]
                new_duration = text_length / max_cps
                subtitle.end_time = subtitle.start_time + new_duration
                return True
            
        except Exception as e:
            logger.error("应用修复时出错", issue_id=issue.issue_id, error=str(e))
            return False
        
        return False

    def _calculate_validation_score(self, issues: List[ValidationIssue], subtitle_count: int) -> float:
        """计算验证分数"""
        if not issues:
            return 1.0
        
        severity_weights = {
            ValidationSeverity.CRITICAL: 0.3,
            ValidationSeverity.HIGH: 0.2,
            ValidationSeverity.MEDIUM: 0.1,
            ValidationSeverity.LOW: 0.05,
            ValidationSeverity.INFO: 0.01
        }
        
        total_penalty = sum(severity_weights.get(issue.severity, 0.1) for issue in issues)
        normalized_penalty = total_penalty / max(subtitle_count, 1)
        score = max(0.0, 1.0 - normalized_penalty)
        
        return score

    def _count_issues_by_type(self, issues: List[ValidationIssue]) -> Dict[ValidationType, int]:
        """按类型统计问题"""
        counts = defaultdict(int)
        for issue in issues:
            counts[issue.validation_type] += 1
        return dict(counts)

    def _count_issues_by_severity(self, issues: List[ValidationIssue]) -> Dict[ValidationSeverity, int]:
        """按严重程度统计问题"""
        counts = defaultdict(int)
        for issue in issues:
            counts[issue.severity] += 1
        return dict(counts)

    def _generate_recommendations(self, issues: List[ValidationIssue]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if not issues:
            recommendations.append("恭喜！所有字幕都符合显示标准。")
            return recommendations
        
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        high_issues = [i for i in issues if i.severity == ValidationSeverity.HIGH]
        
        if critical_issues:
            recommendations.append(f"发现 {len(critical_issues)} 个严重问题，必须立即修复")
        
        if high_issues:
            recommendations.append(f"发现 {len(high_issues)} 个高优先级问题，建议优先处理")
        
        auto_fixable = len([i for i in issues if i.can_auto_fix])
        if auto_fixable > 0:
            recommendations.append(f"其中 {auto_fixable} 个问题可以自动修复")
        
        return recommendations

    def _update_validation_stats(self, request: ValidationRequest, result: ValidationResult):
        """更新验证统计"""
        self.validation_stats["total_validations"] += 1
        self.validation_stats["issues_found"] += len(result.issues_found)
        self.validation_stats["issues_fixed"] += len(result.fixed_issues)
        self.validation_stats["validation_scores"].append(result.validation_score)
        self.validation_stats["processing_times"].append(result.processing_time_ms)

    def get_validation_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        stats = self.validation_stats.copy()
        
        if stats["validation_scores"]:
            stats["average_validation_score"] = sum(stats["validation_scores"]) / len(stats["validation_scores"])
        else:
            stats["average_validation_score"] = 0.0
        
        if stats["processing_times"]:
            stats["average_processing_time_ms"] = sum(stats["processing_times"]) / len(stats["processing_times"])
        else:
            stats["average_processing_time_ms"] = 0.0
        
        stats["total_rules"] = len(self.built_in_rules) + len(self.custom_rules)
        
        return stats

    def add_custom_rule(self, rule: ValidationRule):
        """添加自定义规则"""
        self.custom_rules.append(rule)
        logger.info("添加自定义验证规则", rule_id=rule.rule_id, rule_name=rule.rule_name)

    def remove_custom_rule(self, rule_id: str) -> bool:
        """移除自定义规则"""
        for i, rule in enumerate(self.custom_rules):
            if rule.rule_id == rule_id:
                removed_rule = self.custom_rules.pop(i)
                logger.info("移除自定义验证规则", rule_id=removed_rule.rule_id)
                return True
        return False

    def get_rule_by_id(self, rule_id: str) -> Optional[ValidationRule]:
        """根据ID获取规则"""
        all_rules = self.built_in_rules + self.custom_rules
        return next((rule for rule in all_rules if rule.rule_id == rule_id), None)