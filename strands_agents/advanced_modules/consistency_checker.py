"""
一致性检查器
处理翻译一致性检查和术语管理
从agents/consistency_checker.py迁移而来，符合需求6和需求9
"""
import json
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter

from . import AdvancedModule, module_registry

class ConsistencyType(Enum):
    """一致性类型"""
    PERSON_NAME = "person_name"         # 人名一致性
    TERMINOLOGY = "terminology"         # 术语一致性
    TITLE_HONORIFIC = "title_honorific" # 称谓敬语一致性
    PLACE_NAME = "place_name"           # 地名一致性
    ORGANIZATION = "organization"       # 组织机构一致性
    CULTURAL_TERM = "cultural_term"     # 文化术语一致性
    TECHNICAL_TERM = "technical_term"   # 技术术语一致性

class ConflictSeverity(Enum):
    """冲突严重程度"""
    CRITICAL = "critical"    # 严重冲突，必须修复
    HIGH = "high"           # 高优先级冲突，建议修复
    MEDIUM = "medium"       # 中等冲突，可选修复
    LOW = "low"             # 轻微冲突，可忽略

class ResolutionStrategy(Enum):
    """解决策略"""
    USE_MOST_FREQUENT = "use_most_frequent"     # 使用最频繁的版本
    USE_FIRST_OCCURRENCE = "use_first_occurrence" # 使用首次出现的版本
    USE_LATEST = "use_latest"                   # 使用最新的版本
    USE_HIGHEST_CONFIDENCE = "use_highest_confidence" # 使用置信度最高的版本
    MANUAL_REVIEW = "manual_review"             # 需要人工审核
    CONTEXT_DEPENDENT = "context_dependent"     # 根据上下文决定

@dataclass
class ConsistencyRule:
    """一致性规则"""
    rule_id: str
    rule_name: str
    consistency_type: str
    pattern: str                        # 正则表达式模式
    case_sensitive: bool = False
    scope: str = "project"              # project, episode, scene
    severity: str = "medium"
    resolution_strategy: str = "use_most_frequent"
    description: str = ""
    examples: List[str] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []

@dataclass
class ConsistencyViolation:
    """一致性违规"""
    violation_id: str
    rule_id: str
    consistency_type: str
    source_term: str                    # 原始术语
    conflicting_translations: Dict[str, List[Dict[str, Any]]]  # {translation: [occurrences]}
    severity: str
    suggested_resolution: Optional[str] = None
    resolution_strategy: Optional[str] = None
    confidence: float = 1.0
    contexts: List[str] = None
    locations: List[str] = None         # 出现位置
    detected_at: str = None
    
    def __post_init__(self):
        if self.contexts is None:
            self.contexts = []
        if self.locations is None:
            self.locations = []
        if self.detected_at is None:
            self.detected_at = datetime.now().isoformat()

@dataclass
class ConsistencyCheckResult:
    """一致性检查结果"""
    success: bool
    violations_found: List[ConsistencyViolation]
    consistency_score: float            # 0.0-1.0
    total_terms_checked: int
    violations_by_type: Dict[str, int]
    auto_resolved_count: int = 0
    manual_review_required: int = 0
    recommendations: List[str] = None
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []
        if self.metadata is None:
            self.metadata = {}

class ConsistencyChecker(AdvancedModule):
    """一致性检查器
    
    核心功能：
    1. 7种一致性类型检查 (符合需求6: 翻译质量控制)
    2. 4级冲突严重程度评估
    3. 6种解决策略
    4. 跨集数验证 (符合需求9: 翻译记忆和学习)
    """
    
    def __init__(self):
        super().__init__("consistency_checker", "1.0.0")
        
        # 内置规则
        self.built_in_rules = self._initialize_built_in_rules()
        
        # 自定义规则
        self.custom_rules: List[ConsistencyRule] = []
        
        # 术语数据库
        self.term_database: Dict[str, Dict[str, Any]] = defaultdict(lambda: defaultdict(dict))
        
        # 性能统计
        self.performance_stats = {
            "total_checks": 0,
            "violations_found": 0,
            "auto_resolved": 0,
            "manual_reviews": 0,
            "consistency_scores": [],
            "violation_types": defaultdict(int),
            "processing_times": []
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理一致性检查
        
        Args:
            input_data: {
                "entries": "翻译条目JSON字符串",
                "reference_data": "参考数据JSON字符串",
                "target_language": "目标语言代码",
                "check_config": "检查配置JSON字符串"
            }
        
        Returns:
            一致性检查报告
        """
        start_time = time.time()
        
        if not self.validate_input(input_data):
            return self.create_result(
                False,
                error="Invalid input data for consistency check",
                processing_time=time.time() - start_time
            )
        
        try:
            entries = self.from_json(input_data["entries"])
            reference_data = self.from_json(input_data.get("reference_data", "{}"))
            target_language = input_data.get("target_language", "en")
            check_config = self.from_json(input_data.get("check_config", "{}"))
            
            # 提取术语和翻译
            term_occurrences = self._extract_term_occurrences(entries, target_language)
            
            # 检测一致性违规
            violations = self._detect_violations(term_occurrences, target_language)
            
            # 自动解决冲突（如果启用）
            auto_resolved_count = 0
            if check_config.get("auto_resolve", False):
                auto_resolved_count = self._auto_resolve_violations(violations)
            
            # 计算一致性分数
            consistency_score = self._calculate_consistency_score(term_occurrences, violations)
            
            # 生成建议
            recommendations = self._generate_recommendations(violations, term_occurrences)
            
            # 统计违规类型
            violations_by_type = self._count_violations_by_type(violations)
            
            processing_time = time.time() - start_time
            
            # 创建检查结果
            result = ConsistencyCheckResult(
                success=True,
                violations_found=[asdict(v) for v in violations],
                consistency_score=consistency_score,
                total_terms_checked=len(term_occurrences),
                violations_by_type=violations_by_type,
                auto_resolved_count=auto_resolved_count,
                manual_review_required=len([v for v in violations if v.resolution_strategy == "manual_review"]),
                recommendations=recommendations,
                processing_time_ms=int(processing_time * 1000),
                metadata={
                    "target_language": target_language,
                    "rules_applied": len(self.built_in_rules),
                    "check_scope": check_config.get("scope", "project")
                }
            )
            
            # 更新统计信息
            self._update_stats(result, target_language)
            
            return self.create_result(
                True,
                data={
                    "consistency_check": asdict(result),
                    "check_summary": {
                        "consistency_score": consistency_score,
                        "violations_count": len(violations),
                        "auto_resolved": auto_resolved_count,
                        "manual_review_required": result.manual_review_required
                    }
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            return self.create_result(
                False,
                error=f"Consistency check failed: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["entries"]
        return all(field in input_data for field in required_fields)
    
    def _extract_term_occurrences(self, entries: Any, target_language: str) -> Dict[str, Dict[str, List[Dict]]]:
        """提取术语出现情况"""
        term_occurrences = defaultdict(lambda: defaultdict(list))
        
        # 处理单个条目或条目列表
        if isinstance(entries, list):
            entry_list = entries
        else:
            entry_list = [entries]
        
        for i, entry in enumerate(entry_list):
            if isinstance(entry, dict):
                original_text = entry.get("original", "")
                translated_text = entry.get("translated", "")
            else:
                original_text = str(entry)
                translated_text = str(entry)
            
            # 应用所有规则检测术语
            for rule in self.built_in_rules:
                matches = re.findall(rule.pattern, original_text, 
                                   re.IGNORECASE if not rule.case_sensitive else 0)
                
                for match in matches:
                    # 记录术语出现
                    occurrence = {
                        "location": f"entry_{i}",
                        "original_context": original_text,
                        "translated_context": translated_text,
                        "rule_id": rule.rule_id,
                        "confidence": 0.8
                    }
                    
                    term_occurrences[match][translated_text].append(occurrence)
        
        return term_occurrences
    
    def _detect_violations(self, term_occurrences: Dict, target_language: str) -> List[ConsistencyViolation]:
        """检测一致性违规"""
        violations = []
        
        for source_term, translations in term_occurrences.items():
            # 如果一个术语有多个不同的翻译，则可能存在一致性问题
            if len(translations) > 1:
                # 找到对应的规则
                rule = self._find_rule_for_term(source_term)
                if not rule:
                    continue
                
                # 创建违规记录
                violation = ConsistencyViolation(
                    violation_id=f"violation_{int(time.time())}_{len(violations)}",
                    rule_id=rule.rule_id,
                    consistency_type=rule.consistency_type,
                    source_term=source_term,
                    conflicting_translations=translations,
                    severity=rule.severity,
                    resolution_strategy=rule.resolution_strategy,
                    confidence=0.8,
                    contexts=[occ["original_context"] for trans_list in translations.values() 
                             for occ in trans_list],
                    locations=[occ["location"] for trans_list in translations.values() 
                              for occ in trans_list]
                )
                
                # 生成建议解决方案
                violation.suggested_resolution = self._generate_resolution_suggestion(
                    violation, translations
                )
                
                violations.append(violation)
        
        return violations
    
    def _auto_resolve_violations(self, violations: List[ConsistencyViolation]) -> int:
        """自动解决违规"""
        auto_resolved = 0
        
        for violation in violations:
            if violation.resolution_strategy in ["use_most_frequent", "use_first_occurrence", "use_latest"]:
                # 简化的自动解决逻辑
                if violation.resolution_strategy == "use_most_frequent":
                    # 选择出现频率最高的翻译
                    most_frequent = max(violation.conflicting_translations.items(), 
                                      key=lambda x: len(x[1]))
                    violation.suggested_resolution = most_frequent[0]
                    auto_resolved += 1
        
        return auto_resolved
    
    def _calculate_consistency_score(self, term_occurrences: Dict, violations: List[ConsistencyViolation]) -> float:
        """计算一致性分数"""
        if not term_occurrences:
            return 1.0
        
        total_terms = len(term_occurrences)
        violation_count = len(violations)
        
        # 基础分数
        base_score = max(0.0, 1.0 - (violation_count / total_terms))
        
        # 根据违规严重程度调整分数
        severity_penalty = 0.0
        for violation in violations:
            if violation.severity == "critical":
                severity_penalty += 0.1
            elif violation.severity == "high":
                severity_penalty += 0.05
            elif violation.severity == "medium":
                severity_penalty += 0.02
            else:  # low
                severity_penalty += 0.01
        
        final_score = max(0.0, base_score - severity_penalty)
        return min(final_score, 1.0)
    
    def _generate_recommendations(self, violations: List[ConsistencyViolation], 
                                term_occurrences: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if not violations:
            recommendations.append("翻译一致性良好，未发现明显问题")
            return recommendations
        
        # 按严重程度分组
        critical_violations = [v for v in violations if v.severity == "critical"]
        high_violations = [v for v in violations if v.severity == "high"]
        
        if critical_violations:
            recommendations.append(f"发现{len(critical_violations)}个严重一致性问题，需要立即修复")
        
        if high_violations:
            recommendations.append(f"发现{len(high_violations)}个高优先级一致性问题，建议优先处理")
        
        # 按类型统计
        type_counts = Counter([v.consistency_type for v in violations])
        for consistency_type, count in type_counts.most_common(3):
            recommendations.append(f"{consistency_type}类型问题较多({count}个)，建议系统性检查")
        
        return recommendations[:5]  # 限制建议数量
    
    def _count_violations_by_type(self, violations: List[ConsistencyViolation]) -> Dict[str, int]:
        """统计违规类型"""
        return dict(Counter([v.consistency_type for v in violations]))
    
    def _find_rule_for_term(self, term: str) -> Optional[ConsistencyRule]:
        """为术语找到对应的规则"""
        for rule in self.built_in_rules:
            if re.search(rule.pattern, term, re.IGNORECASE if not rule.case_sensitive else 0):
                return rule
        return None
    
    def _generate_resolution_suggestion(self, violation: ConsistencyViolation, 
                                      translations: Dict) -> str:
        """生成解决建议"""
        if violation.resolution_strategy == "use_most_frequent":
            most_frequent = max(translations.items(), key=lambda x: len(x[1]))
            return f"建议统一使用: '{most_frequent[0]}' (出现{len(most_frequent[1])}次)"
        elif violation.resolution_strategy == "use_first_occurrence":
            # 简化实现：使用第一个翻译
            first_translation = list(translations.keys())[0]
            return f"建议统一使用首次出现的翻译: '{first_translation}'"
        elif violation.resolution_strategy == "manual_review":
            return "需要人工审核决定最佳翻译"
        else:
            return "建议统一术语翻译"
    
    def _update_stats(self, result: ConsistencyCheckResult, target_language: str):
        """更新统计信息"""
        self.performance_stats["total_checks"] += 1
        self.performance_stats["violations_found"] += len(result.violations_found)
        self.performance_stats["auto_resolved"] += result.auto_resolved_count
        self.performance_stats["manual_reviews"] += result.manual_review_required
        self.performance_stats["consistency_scores"].append(result.consistency_score)
        self.performance_stats["processing_times"].append(result.processing_time_ms)
        
        # 更新违规类型统计
        for violation_type, count in result.violations_by_type.items():
            self.performance_stats["violation_types"][violation_type] += count
    
    def _initialize_built_in_rules(self) -> List[ConsistencyRule]:
        """初始化内置规则"""
        return [
            # 人名规则
            ConsistencyRule(
                rule_id="person_name_chinese",
                rule_name="中文人名一致性",
                consistency_type="person_name",
                pattern=r"[张李王刘陈杨黄赵周吴徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龯]{1,2}",
                case_sensitive=True,
                severity="high",
                resolution_strategy="use_first_occurrence",
                description="检查中文人名翻译的一致性",
                examples=["张伟", "李明", "王小红"]
            ),
            
            # 军事术语规则
            ConsistencyRule(
                rule_id="military_terms",
                rule_name="军事术语一致性",
                consistency_type="technical_term",
                pattern=r"(司令|队长|士兵|军官|部队|雷达|导弹|战舰|潜艇|飞机|坦克|装备|武器|战略|战术|训练|演习|作战|防御|攻击|指挥|通信|情报)",
                case_sensitive=False,
                severity="critical",
                resolution_strategy="use_most_frequent",
                description="检查军事术语翻译的一致性",
                examples=["司令", "雷达", "战舰"]
            ),
            
            # 称谓敬语规则
            ConsistencyRule(
                rule_id="honorific_titles",
                rule_name="称谓敬语一致性",
                consistency_type="title_honorific",
                pattern=r"(先生|女士|老师|同志|您|请|谢谢|对不起|不好意思)",
                case_sensitive=False,
                severity="medium",
                resolution_strategy="context_dependent",
                description="检查称谓和敬语的一致性",
                examples=["先生", "您", "请"]
            ),
            
            # 地名规则
            ConsistencyRule(
                rule_id="place_names",
                rule_name="地名一致性",
                consistency_type="place_name",
                pattern=r"(北京|上海|广州|深圳|天津|重庆|南京|杭州|苏州|武汉|成都|西安|青岛|大连|厦门|宁波|无锡|佛山|温州|泉州|东莞|中国|美国|日本|韩国|英国|法国|德国)",
                case_sensitive=True,
                severity="high",
                resolution_strategy="use_first_occurrence",
                description="检查地名翻译的一致性",
                examples=["北京", "上海", "中国"]
            ),
            
            # 组织机构规则
            ConsistencyRule(
                rule_id="organizations",
                rule_name="组织机构一致性",
                consistency_type="organization",
                pattern=r"(海军|陆军|空军|政府|公司|学校|医院|银行|部门|机构|组织|团队|小组)",
                case_sensitive=False,
                severity="medium",
                resolution_strategy="use_most_frequent",
                description="检查组织机构名称的一致性",
                examples=["海军", "政府", "公司"]
            ),
            
            # 文化术语规则
            ConsistencyRule(
                rule_id="cultural_terms",
                rule_name="文化术语一致性",
                consistency_type="cultural_term",
                pattern=r"(春节|中秋节|端午节|清明节|国庆节|元旦|中华|传统|文化|习俗|礼仪|茶|功夫|太极|书法|京剧)",
                case_sensitive=False,
                severity="medium",
                resolution_strategy="context_dependent",
                description="检查文化术语翻译的一致性",
                examples=["春节", "功夫", "太极"]
            ),
            
            # 技术术语规则
            ConsistencyRule(
                rule_id="technical_terms",
                rule_name="技术术语一致性",
                consistency_type="technical_term",
                pattern=r"(计算机|软件|硬件|网络|数据库|算法|程序|系统|平台|接口|协议|服务器|客户端)",
                case_sensitive=False,
                severity="high",
                resolution_strategy="use_most_frequent",
                description="检查技术术语翻译的一致性",
                examples=["计算机", "软件", "网络"]
            )
        ]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_stats.copy()
    
    def add_custom_rule(self, rule: ConsistencyRule):
        """添加自定义规则"""
        self.custom_rules.append(rule)
    
    def get_term_database(self) -> Dict[str, Dict[str, Any]]:
        """获取术语数据库"""
        return dict(self.term_database)

# 注册模块
consistency_checker = ConsistencyChecker()
module_registry.register(consistency_checker)