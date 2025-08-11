"""
术语管理器
处理术语库管理、一致性检查和跨语言术语映射
从agents/terminology_consistency_manager.py迁移而来，符合需求9
"""
import json
import time
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter

from . import AdvancedModule, module_registry

class TermType(Enum):
    """术语类型"""
    PERSON_NAME = "person_name"         # 人名
    PLACE_NAME = "place_name"           # 地名
    ORGANIZATION = "organization"       # 组织机构
    TECHNICAL_TERM = "technical_term"   # 技术术语
    MILITARY_TERM = "military_term"     # 军事术语
    MEDICAL_TERM = "medical_term"       # 医学术语
    LEGAL_TERM = "legal_term"           # 法律术语
    BRAND_NAME = "brand_name"           # 品牌名称
    TITLE = "title"                     # 称谓/头衔
    CULTURAL_TERM = "cultural_term"     # 文化术语

class ConsistencyLevel(Enum):
    """一致性级别"""
    STRICT = "strict"           # 严格一致（必须完全相同）
    MODERATE = "moderate"       # 适度一致（允许轻微变化）
    FLEXIBLE = "flexible"       # 灵活一致（允许合理变化）
    CONTEXTUAL = "contextual"   # 上下文相关（根据语境调整）

class ConflictSeverity(Enum):
    """冲突严重程度"""
    CRITICAL = "critical"       # 严重冲突（必须解决）
    HIGH = "high"              # 高级冲突（建议解决）
    MEDIUM = "medium"          # 中级冲突（可选解决）
    LOW = "low"                # 低级冲突（可忽略）

@dataclass
class TermEntry:
    """术语条目"""
    term_id: str
    source_text: str                    # 源语言术语
    term_type: str                      # 术语类型
    consistency_level: str              # 一致性要求
    translations: Dict[str, str]        # 各语言翻译 {language: translation}
    aliases: List[str]                  # 别名/变体
    context_examples: List[str]         # 上下文示例
    usage_frequency: int = 0            # 使用频率
    last_updated: str = None            # 最后更新时间
    created_by: str = "system"          # 创建者
    approved: bool = False              # 是否已审核
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class TermConflict:
    """术语冲突"""
    conflict_id: str
    term_id: str
    source_text: str
    conflicting_translations: Dict[str, List[str]]  # {language: [conflicting_versions]}
    severity: str
    contexts: List[str]                 # 冲突出现的上下文
    suggested_resolution: Optional[str] = None
    resolution_strategy: Optional[str] = None
    detected_at: str = None
    resolved: bool = False
    resolution_notes: Optional[str] = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now().isoformat()

@dataclass
class TerminologyManagementResult:
    """术语管理结果"""
    success: bool
    terms_processed: int
    conflicts_found: List[TermConflict]
    consistency_score: float            # 0.0-1.0
    total_terms_checked: int
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

class TerminologyManager(AdvancedModule):
    """术语管理器
    
    核心功能：
    1. 动态术语学习 (符合需求9: 翻译记忆和学习)
    2. 多级术语库管理
    3. 术语冲突解决
    4. 上下文相关性分析
    """
    
    def __init__(self):
        super().__init__("terminology_manager", "1.0.0")
        
        # 术语数据库
        self.term_database: Dict[str, TermEntry] = {}
        self.term_index: Dict[str, Set[str]] = defaultdict(set)  # source_text -> term_ids
        self.language_index: Dict[str, Dict[str, str]] = defaultdict(dict)  # lang -> {translation: term_id}
        
        # 冲突管理
        self.active_conflicts: Dict[str, TermConflict] = {}
        self.resolved_conflicts: Dict[str, TermConflict] = {}
        
        # 配置参数
        self.similarity_threshold = 0.8    # 相似度阈值
        self.frequency_weight = 0.3        # 频率权重
        self.recency_weight = 0.2          # 时效性权重
        self.authority_weight = 0.5        # 权威性权重
        
        # 性能统计
        self.performance_stats = {
            "total_terms": 0,
            "total_checks": 0,
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
            "average_consistency_score": 0.0,
            "language_coverage": defaultdict(int),
            "term_type_distribution": defaultdict(int),
            "conflict_severity_distribution": defaultdict(int)
        }
        
        # 初始化核心术语
        self._initialize_core_terms()
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理术语管理
        
        Args:
            input_data: {
                "entries": "翻译条目JSON字符串",
                "target_language": "目标语言代码",
                "terminology_config": "术语配置JSON字符串"
            }
        
        Returns:
            术语管理结果和建议
        """
        start_time = time.time()
        
        if not self.validate_input(input_data):
            return self.create_result(
                False,
                error="Invalid input data for terminology management",
                processing_time=time.time() - start_time
            )
        
        try:
            entries = self.from_json(input_data["entries"])
            target_language = input_data.get("target_language", "en")
            terminology_config = self.from_json(input_data.get("terminology_config", "{}"))
            
            # 获取配置参数
            auto_learn = terminology_config.get("auto_learn", True)
            check_consistency = terminology_config.get("check_consistency", True)
            auto_resolve = terminology_config.get("auto_resolve", False)
            
            # 处理单个条目或条目列表
            if isinstance(entries, list):
                entry_list = entries
            else:
                entry_list = [entries]
            
            # 提取和学习术语
            extracted_terms = []
            if auto_learn:
                extracted_terms = self._extract_and_learn_terms(entry_list, target_language)
            
            # 检查术语一致性
            conflicts = []
            consistency_score = 1.0
            if check_consistency:
                conflicts = self._check_terminology_consistency(entry_list, target_language)
                consistency_score = self._calculate_consistency_score(entry_list, conflicts)
            
            # 自动解决冲突
            auto_resolved_count = 0
            if auto_resolve and conflicts:
                auto_resolved_count = self._auto_resolve_conflicts(conflicts)
            
            # 生成建议
            recommendations = self._generate_terminology_recommendations(
                extracted_terms, conflicts, target_language
            )
            
            processing_time = time.time() - start_time
            
            # 创建管理结果
            result = TerminologyManagementResult(
                success=True,
                terms_processed=len(entry_list),
                conflicts_found=[asdict(c) for c in conflicts],
                consistency_score=consistency_score,
                total_terms_checked=len(self.term_database),
                auto_resolved_count=auto_resolved_count,
                manual_review_required=len([c for c in conflicts if not c.resolved]),
                recommendations=recommendations,
                processing_time_ms=int(processing_time * 1000),
                metadata={
                    "target_language": target_language,
                    "extracted_terms": len(extracted_terms),
                    "auto_learn": auto_learn,
                    "check_consistency": check_consistency
                }
            )
            
            # 更新统计信息
            self._update_stats(result, target_language)
            
            return self.create_result(
                True,
                data={
                    "terminology_management": asdict(result),
                    "management_summary": {
                        "terms_processed": result.terms_processed,
                        "consistency_score": result.consistency_score,
                        "conflicts_found": len(result.conflicts_found),
                        "auto_resolved": result.auto_resolved_count,
                        "recommendations_count": len(result.recommendations)
                    }
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            return self.create_result(
                False,
                error=f"Terminology management failed: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["entries"]
        return all(field in input_data for field in required_fields)
    
    def _extract_and_learn_terms(self, entries: List[Any], target_language: str) -> List[TermEntry]:
        """提取和学习术语"""
        extracted_terms = []
        
        for entry in entries:
            if isinstance(entry, dict):
                original_text = entry.get("original", "")
                translated_text = entry.get("translated", "")
            else:
                original_text = str(entry)
                translated_text = ""
            
            # 提取潜在术语
            potential_terms = self._extract_potential_terms(original_text)
            
            for term_text in potential_terms:
                # 检查是否已存在
                if not self._term_exists(term_text):
                    # 创建新术语条目
                    term_entry = self._create_term_entry(term_text, translated_text, target_language)
                    if term_entry:
                        extracted_terms.append(term_entry)
                        self.add_term(term_entry)
                else:
                    # 更新现有术语的使用频率
                    self._update_term_frequency(term_text)
        
        return extracted_terms
    
    def _check_terminology_consistency(self, entries: List[Any], target_language: str) -> List[TermConflict]:
        """检查术语一致性"""
        conflicts = []
        term_translations = defaultdict(list)
        
        # 收集术语翻译
        for entry in entries:
            if isinstance(entry, dict):
                original_text = entry.get("original", "")
                translated_text = entry.get("translated", "")
            else:
                original_text = str(entry)
                translated_text = ""
            
            # 查找已知术语
            for term_text in self.term_index.keys():
                if term_text in original_text and translated_text:
                    term_translations[term_text].append(translated_text)
        
        # 检测冲突
        for term_text, translations in term_translations.items():
            if len(set(translations)) > 1:  # 有多个不同的翻译
                term_ids = self.term_index[term_text]
                if term_ids:
                    term_id = list(term_ids)[0]
                    conflict = TermConflict(
                        conflict_id=f"conflict_{int(time.time())}_{len(conflicts)}",
                        term_id=term_id,
                        source_text=term_text,
                        conflicting_translations={target_language: list(set(translations))},
                        severity="medium",
                        contexts=[f"Found in {len(translations)} different contexts"],
                        suggested_resolution=self._suggest_conflict_resolution(translations),
                        resolution_strategy="use_most_frequent"
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _auto_resolve_conflicts(self, conflicts: List[TermConflict]) -> int:
        """自动解决冲突"""
        resolved_count = 0
        
        for conflict in conflicts:
            if conflict.resolution_strategy == "use_most_frequent":
                # 选择最频繁的翻译
                all_translations = []
                for lang_translations in conflict.conflicting_translations.values():
                    all_translations.extend(lang_translations)
                
                if all_translations:
                    most_frequent = Counter(all_translations).most_common(1)[0][0]
                    conflict.suggested_resolution = most_frequent
                    conflict.resolved = True
                    resolved_count += 1
        
        return resolved_count
    
    def _calculate_consistency_score(self, entries: List[Any], conflicts: List[TermConflict]) -> float:
        """计算一致性分数"""
        if not entries:
            return 1.0
        
        total_terms = len(self.term_database)
        conflict_count = len(conflicts)
        
        if total_terms == 0:
            return 1.0
        
        # 基础分数
        base_score = max(0.0, 1.0 - (conflict_count / total_terms))
        
        # 根据冲突严重程度调整
        severity_penalty = 0.0
        for conflict in conflicts:
            if conflict.severity == "critical":
                severity_penalty += 0.1
            elif conflict.severity == "high":
                severity_penalty += 0.05
            elif conflict.severity == "medium":
                severity_penalty += 0.02
            else:  # low
                severity_penalty += 0.01
        
        final_score = max(0.0, base_score - severity_penalty)
        return min(final_score, 1.0)
    
    def _generate_terminology_recommendations(self, extracted_terms: List[TermEntry], 
                                            conflicts: List[TermConflict], 
                                            target_language: str) -> List[str]:
        """生成术语管理建议"""
        recommendations = []
        
        if extracted_terms:
            recommendations.append(f"学习了 {len(extracted_terms)} 个新术语")
        
        if conflicts:
            critical_conflicts = [c for c in conflicts if c.severity == "critical"]
            if critical_conflicts:
                recommendations.append(f"发现 {len(critical_conflicts)} 个严重术语冲突，需要立即处理")
            
            unresolved_conflicts = [c for c in conflicts if not c.resolved]
            if unresolved_conflicts:
                recommendations.append(f"{len(unresolved_conflicts)} 个术语冲突需要人工审核")
        
        # 术语库统计建议
        total_terms = len(self.term_database)
        if total_terms > 0:
            recommendations.append(f"术语库包含 {total_terms} 个术语")
            
            # 语言覆盖建议
            lang_coverage = self.performance_stats["language_coverage"]
            if target_language in lang_coverage:
                recommendations.append(f"{target_language} 语言术语覆盖: {lang_coverage[target_language]} 个")
        
        return recommendations[:5]  # 限制建议数量
    
    def _extract_potential_terms(self, text: str) -> List[str]:
        """提取潜在术语"""
        potential_terms = []
        
        # 简化的术语提取逻辑
        # 人名模式
        person_names = re.findall(r'[张李王刘陈杨黄赵周吴徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龯]{1,2}', text)
        potential_terms.extend(person_names)
        
        # 军事术语模式
        military_terms = re.findall(r'(司令|队长|士兵|军官|部队|雷达|导弹|战舰|潜艇|飞机|坦克|装备|武器|战略|战术|训练|演习|作战|防御|攻击|指挥|通信|情报)', text)
        potential_terms.extend(military_terms)
        
        # 地名模式
        place_names = re.findall(r'(北京|上海|广州|深圳|天津|重庆|南京|杭州|苏州|武汉|成都|西安|青岛|大连|厦门|宁波|无锡|佛山|温州|泉州|东莞|中国|美国|日本|韩国|英国|法国|德国)', text)
        potential_terms.extend(place_names)
        
        # 技术术语模式
        tech_terms = re.findall(r'(计算机|软件|硬件|网络|数据库|算法|程序|系统|平台|接口|协议|服务器|客户端)', text)
        potential_terms.extend(tech_terms)
        
        return list(set(potential_terms))  # 去重
    
    def _create_term_entry(self, term_text: str, translated_text: str, target_language: str) -> Optional[TermEntry]:
        """创建术语条目"""
        if not term_text.strip():
            return None
        
        # 确定术语类型
        term_type = self._determine_term_type(term_text)
        
        # 创建术语条目
        term_entry = TermEntry(
            term_id=f"term_{int(time.time())}_{hash(term_text) % 10000}",
            source_text=term_text,
            term_type=term_type,
            consistency_level="moderate",
            translations={target_language: translated_text} if translated_text else {},
            aliases=[],
            context_examples=[],
            usage_frequency=1,
            created_by="auto_learn",
            approved=False
        )
        
        return term_entry
    
    def _determine_term_type(self, term_text: str) -> str:
        """确定术语类型"""
        # 简化的类型判断逻辑
        if re.match(r'[张李王刘陈杨黄赵周吴徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龯]{1,2}', term_text):
            return "person_name"
        elif term_text in ["司令", "队长", "士兵", "军官", "部队", "雷达", "导弹", "战舰", "潜艇", "飞机", "坦克", "装备", "武器", "战略", "战术", "训练", "演习", "作战", "防御", "攻击", "指挥", "通信", "情报"]:
            return "military_term"
        elif term_text in ["北京", "上海", "广州", "深圳", "天津", "重庆", "南京", "杭州", "苏州", "武汉", "成都", "西安", "青岛", "大连", "厦门", "宁波", "无锡", "佛山", "温州", "泉州", "东莞", "中国", "美国", "日本", "韩国", "英国", "法国", "德国"]:
            return "place_name"
        elif term_text in ["计算机", "软件", "硬件", "网络", "数据库", "算法", "程序", "系统", "平台", "接口", "协议", "服务器", "客户端"]:
            return "technical_term"
        else:
            return "technical_term"  # 默认类型
    
    def _term_exists(self, term_text: str) -> bool:
        """检查术语是否已存在"""
        return term_text in self.term_index
    
    def _update_term_frequency(self, term_text: str):
        """更新术语使用频率"""
        term_ids = self.term_index.get(term_text, set())
        for term_id in term_ids:
            if term_id in self.term_database:
                self.term_database[term_id].usage_frequency += 1
    
    def _suggest_conflict_resolution(self, translations: List[str]) -> str:
        """建议冲突解决方案"""
        if not translations:
            return "无可用翻译"
        
        # 选择最频繁的翻译
        most_frequent = Counter(translations).most_common(1)[0][0]
        return f"建议使用: '{most_frequent}' (出现{translations.count(most_frequent)}次)"
    
    def _update_stats(self, result: TerminologyManagementResult, target_language: str):
        """更新统计信息"""
        self.performance_stats["total_checks"] += 1
        self.performance_stats["conflicts_detected"] += len(result.conflicts_found)
        self.performance_stats["conflicts_resolved"] += result.auto_resolved_count
        self.performance_stats["language_coverage"][target_language] += result.terms_processed
        
        # 更新平均一致性分数
        current_avg = self.performance_stats["average_consistency_score"]
        total_checks = self.performance_stats["total_checks"]
        self.performance_stats["average_consistency_score"] = (
            (current_avg * (total_checks - 1) + result.consistency_score) / total_checks
        )
    
    def add_term(self, term: TermEntry) -> bool:
        """添加术语"""
        try:
            # 添加到主数据库
            self.term_database[term.term_id] = term
            
            # 更新索引
            self.term_index[term.source_text].add(term.term_id)
            
            # 更新语言索引
            for language, translation in term.translations.items():
                self.language_index[language][translation] = term.term_id
            
            # 更新统计
            self.performance_stats["total_terms"] += 1
            self.performance_stats["term_type_distribution"][term.term_type] += 1
            
            return True
        except Exception as e:
            return False
    
    def _initialize_core_terms(self):
        """初始化核心术语"""
        core_terms = [
            # 人名术语
            TermEntry(
                term_id="person_zhang_wei",
                source_text="张伟",
                term_type="person_name",
                consistency_level="strict",
                translations={
                    "en": "Zhang Wei",
                    "ja": "張偉",
                    "ko": "장위",
                    "fr": "Zhang Wei",
                    "de": "Zhang Wei"
                },
                aliases=["小张", "张队长"],
                context_examples=["张伟是我们的队长", "张伟同志"],
                approved=True
            ),
            
            # 军事术语
            TermEntry(
                term_id="military_commander",
                source_text="司令",
                term_type="military_term",
                consistency_level="moderate",
                translations={
                    "en": "Commander",
                    "ja": "司令官",
                    "ko": "사령관",
                    "fr": "Commandant",
                    "de": "Kommandant"
                },
                aliases=["司令员", "指挥官"],
                context_examples=["司令下达了命令", "海军司令"],
                approved=True
            ),
            
            # 技术术语
            TermEntry(
                term_id="tech_radar",
                source_text="雷达",
                term_type="technical_term",
                consistency_level="strict",
                translations={
                    "en": "radar",
                    "ja": "レーダー",
                    "ko": "레이더",
                    "fr": "radar",
                    "de": "Radar"
                },
                aliases=["雷达系统"],
                context_examples=["雷达显示有目标", "雷达探测"],
                approved=True
            ),
            
            # 称谓术语
            TermEntry(
                term_id="title_captain",
                source_text="队长",
                term_type="title",
                consistency_level="contextual",
                translations={
                    "en": "Captain",
                    "ja": "隊長",
                    "ko": "대장",
                    "fr": "Capitaine",
                    "de": "Hauptmann"
                },
                aliases=["队长同志", "小队长"],
                context_examples=["队长，有情况", "我们的队长"],
                approved=True
            ),
            
            # 地名术语
            TermEntry(
                term_id="place_beijing",
                source_text="北京",
                term_type="place_name",
                consistency_level="strict",
                translations={
                    "en": "Beijing",
                    "ja": "北京",
                    "ko": "베이징",
                    "fr": "Pékin",
                    "de": "Peking"
                },
                aliases=["首都", "京城"],
                context_examples=["我来自北京", "北京的天气"],
                approved=True
            )
        ]
        
        # 添加到数据库
        for term in core_terms:
            self.add_term(term)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return dict(self.performance_stats)
    
    def get_term_database(self) -> Dict[str, TermEntry]:
        """获取术语数据库"""
        return self.term_database.copy()

# 注册模块
terminology_manager = TerminologyManager()
module_registry.register(terminology_manager)