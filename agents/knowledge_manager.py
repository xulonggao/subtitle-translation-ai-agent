"""
知识库管理器
负责管理翻译记忆、术语库和文化适配知识
集成上下文管理器的术语提取功能
"""
import json
import hashlib
import re
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from config import get_logger
from models.translation_models import (
    TerminologyEntry, TranslationMemory, TranslationMethod
)
from agents.project_manager import get_project_manager

logger = get_logger("knowledge_manager")


class TerminologyExtractor:
    """术语提取器
    
    从对话文本中提取专业术语和重要词汇
    """
    
    def __init__(self):
        # 军事术语模式
        self.military_patterns = [
            r'(参谋长|司令|旅长|队长|营长|连长|排长)',
            r'(突击队|特种兵|侦察兵|工兵|通信兵)',
            r'(演习|训练|作战|战术|战略|部署)',
            r'(装备|武器|弹药|补给|后勤)',
            r'(指挥部|作战室|训练场|军营|基地)'
        ]
        
        # 职业称谓模式
        self.profession_patterns = [
            r'(医生|护士|教师|律师|工程师|设计师)',
            r'(经理|主管|总监|CEO|董事长)',
            r'(警察|消防员|飞行员|司机|厨师)'
        ]
        
        # 人物关系模式
        self.relationship_patterns = [
            r'(父亲|母亲|儿子|女儿|哥哥|姐姐|弟弟|妹妹)',
            r'(丈夫|妻子|男朋友|女朋友|未婚夫|未婚妻)',
            r'(爷爷|奶奶|外公|外婆|叔叔|阿姨|舅舅|姑姑)'
        ]
        
        # 文化特色词汇模式
        self.cultural_patterns = [
            r'(鸡娃|内卷|躺平|佛系|社恐|社牛)',
            r'(996|007|打工人|社畜|加班狗)',
            r'(直播|网红|UP主|粉丝|流量|热搜)'
        ]
        
        # 编译正则表达式
        self.compiled_patterns = {
            'military': [re.compile(p) for p in self.military_patterns],
            'profession': [re.compile(p) for p in self.profession_patterns],
            'relationship': [re.compile(p) for p in self.relationship_patterns],
            'cultural': [re.compile(p) for p in self.cultural_patterns]
        }
    
    def extract_terms(self, text: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """从文本中提取术语
        
        Args:
            text: 输入文本
            context: 上下文信息（说话人、场景等）
            
        Returns:
            提取的术语列表
        """
        extracted_terms = []
        
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                for match in matches:
                    term_info = {
                        'term': match,
                        'category': category,
                        'context': text,
                        'position': text.find(match),
                        'confidence': self._calculate_confidence(match, category, context)
                    }
                    
                    if context:
                        term_info.update({
                            'speaker': context.get('speaker'),
                            'scene': context.get('scene'),
                            'emotion': context.get('emotion')
                        })
                    
                    extracted_terms.append(term_info)
        
        return extracted_terms
    
    def _calculate_confidence(self, term: str, category: str, context: Dict[str, Any] = None) -> float:
        """计算术语置信度"""
        base_confidence = 0.7
        
        # 根据类别调整置信度
        category_weights = {
            'military': 0.9,
            'profession': 0.8,
            'relationship': 0.85,
            'cultural': 0.75
        }
        
        confidence = base_confidence * category_weights.get(category, 0.7)
        
        # 根据上下文调整
        if context:
            # 如果说话人是军人，军事术语置信度更高
            if context.get('speaker_profession') == 'military' and category == 'military':
                confidence *= 1.2
            
            # 如果在正式场景，职业称谓置信度更高
            if context.get('scene_formality') == 'formal' and category == 'profession':
                confidence *= 1.1
        
        return min(confidence, 1.0)


class KnowledgeBase:
    """知识库基类"""
    
    def __init__(self, name: str, storage_path: str):
        self.name = name
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Any] = {}
        self.metadata = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": "1.0",
            "entry_count": 0
        }
    
    def save(self):
        """保存知识库到文件"""
        try:
            data_file = self.storage_path / f"{self.name}.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "metadata": self.metadata,
                    "data": self.data
                }, f, ensure_ascii=False, indent=2)
            
            self.metadata["updated_at"] = datetime.now().isoformat()
            logger.info(f"知识库已保存", name=self.name, path=str(data_file))
            
        except Exception as e:
            logger.error(f"保存知识库失败", name=self.name, error=str(e))
            raise
    
    def load(self):
        """从文件加载知识库"""
        try:
            data_file = self.storage_path / f"{self.name}.json"
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                
                self.metadata = content.get("metadata", self.metadata)
                self.data = content.get("data", {})
                
                logger.info(f"知识库已加载", name=self.name, 
                           entry_count=self.metadata.get("entry_count", 0))
            else:
                logger.info(f"知识库文件不存在，创建新的知识库", name=self.name)
                
        except Exception as e:
            logger.error(f"加载知识库失败", name=self.name, error=str(e))
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return {
            "name": self.name,
            "entry_count": self.metadata.get("entry_count", 0),
            "created_at": self.metadata.get("created_at"),
            "updated_at": self.metadata.get("updated_at"),
            "version": self.metadata.get("version"),
            "storage_path": str(self.storage_path)
        }


class HierarchicalTerminologyKB(KnowledgeBase):
    """分层术语知识库
    
    支持全局、类型、项目三级术语管理
    """
    
    def __init__(self, storage_path: str = "knowledge_base/terminology"):
        super().__init__("hierarchical_terminology", storage_path)
        self.load()
        
        # 初始化分层结构
        if not self.data:
            self.data = {
                "global": {},      # 全局术语
                "genre": {},       # 按类型分类的术语
                "project": {}      # 项目特定术语
            }
    
    def add_term(self, entry: TerminologyEntry, level: str = "global", 
                 genre: str = None, project_id: str = None) -> bool:
        """添加术语条目
        
        Args:
            entry: 术语条目
            level: 层级 (global/genre/project)
            genre: 剧集类型（level=genre时必需）
            project_id: 项目ID（level=project时必需）
        """
        try:
            key = self._generate_term_key(entry.source_term, entry.target_language)
            
            if level == "global":
                target_dict = self.data["global"]
            elif level == "genre" and genre:
                if genre not in self.data["genre"]:
                    self.data["genre"][genre] = {}
                target_dict = self.data["genre"][genre]
            elif level == "project" and project_id:
                if project_id not in self.data["project"]:
                    self.data["project"][project_id] = {}
                target_dict = self.data["project"][project_id]
            else:
                logger.error("无效的术语层级或缺少必需参数", level=level, 
                           genre=genre, project_id=project_id)
                return False
            
            # 检查是否已存在
            if key in target_dict:
                existing_entry = TerminologyEntry.from_dict(target_dict[key])
                existing_entry.increment_usage()
                existing_entry.update_confidence(entry.confidence_score)
                target_dict[key] = existing_entry.to_dict()
                logger.debug("术语条目已更新", source_term=entry.source_term, 
                           level=level)
            else:
                target_dict[key] = entry.to_dict()
                self.metadata["entry_count"] = self._count_total_entries()
                logger.info("新术语条目已添加", source_term=entry.source_term, 
                           level=level)
            
            return True
            
        except Exception as e:
            logger.error("添加术语条目失败", error=str(e))
            return False
    
    def search_terms(self, source_term: str, target_language: str, 
                    project_id: str = None, genre: str = None) -> List[TerminologyEntry]:
        """搜索术语（按优先级：项目 > 类型 > 全局）"""
        results = []
        
        # 项目级搜索
        if project_id and project_id in self.data["project"]:
            key = self._generate_term_key(source_term, target_language)
            if key in self.data["project"][project_id]:
                entry = TerminologyEntry.from_dict(self.data["project"][project_id][key])
                entry.source_level = "project"
                results.append(entry)
        
        # 类型级搜索
        if genre and genre in self.data["genre"]:
            key = self._generate_term_key(source_term, target_language)
            if key in self.data["genre"][genre]:
                entry = TerminologyEntry.from_dict(self.data["genre"][genre][key])
                entry.source_level = "genre"
                results.append(entry)
        
        # 全局搜索
        key = self._generate_term_key(source_term, target_language)
        if key in self.data["global"]:
            entry = TerminologyEntry.from_dict(self.data["global"][key])
            entry.source_level = "global"
            results.append(entry)
        
        return results
    
    def get_best_term(self, source_term: str, target_language: str,
                     project_id: str = None, genre: str = None) -> Optional[TerminologyEntry]:
        """获取最佳术语（优先级：项目 > 类型 > 全局）"""
        results = self.search_terms(source_term, target_language, project_id, genre)
        return results[0] if results else None
    
    def _generate_term_key(self, source_term: str, target_language: str) -> str:
        """生成术语键"""
        return f"{source_term}#{target_language}"
    
    def _count_total_entries(self) -> int:
        """统计总条目数"""
        count = len(self.data["global"])
        
        for genre_data in self.data["genre"].values():
            count += len(genre_data)
        
        for project_data in self.data["project"].values():
            count += len(project_data)
        
        return count


class ContextAwareTranslationMemory(KnowledgeBase):
    """上下文感知的翻译记忆库"""
    
    def __init__(self, storage_path: str = "knowledge_base/translation_memory"):
        super().__init__("context_aware_memory", storage_path)
        self.load()
        
        # 初始化结构
        if not self.data:
            self.data = {
                "memories": {},           # 翻译记忆
                "context_patterns": {},   # 上下文模式
                "similarity_cache": {}    # 相似度缓存
            }
    
    def add_memory(self, memory: TranslationMemory, context: Dict[str, Any] = None) -> bool:
        """添加翻译记忆"""
        try:
            key = self._generate_memory_key(memory.source_text, memory.target_language)
            
            # 增强记忆对象的上下文信息
            memory_dict = memory.to_dict()
            if context:
                memory_dict["context"] = {
                    "speaker": context.get("speaker"),
                    "scene": context.get("scene"),
                    "emotion": context.get("emotion"),
                    "formality": context.get("formality"),
                    "genre": context.get("genre")
                }
            
            # 检查是否已存在相似记忆
            similar_key = self._find_similar_memory_key(memory.source_text, memory.target_language)
            
            if similar_key:
                # 更新现有记忆
                existing_memory = TranslationMemory.from_dict(self.data["memories"][similar_key])
                existing_memory.increment_usage()
                
                if memory.quality_score > existing_memory.quality_score:
                    existing_memory.target_text = memory.target_text
                    existing_memory.quality_score = memory.quality_score
                
                self.data["memories"][similar_key] = existing_memory.to_dict()
                logger.debug("翻译记忆已更新", source_text=memory.source_text[:30])
            else:
                # 添加新记忆
                self.data["memories"][key] = memory_dict
                self.metadata["entry_count"] = len(self.data["memories"])
                logger.info("新翻译记忆已添加", source_text=memory.source_text[:30])
            
            # 更新上下文模式
            if context:
                self._update_context_patterns(memory.source_text, context)
            
            return True
            
        except Exception as e:
            logger.error("添加翻译记忆失败", error=str(e))
            return False
    
    def search_memory_with_context(self, source_text: str, target_language: str,
                                  context: Dict[str, Any] = None,
                                  fuzzy_threshold: float = 0.8) -> List[Tuple[TranslationMemory, float, float]]:
        """基于上下文搜索翻译记忆
        
        Returns:
            List of (memory, text_similarity, context_similarity)
        """
        results = []
        
        for key, memory_data in self.data["memories"].items():
            memory = TranslationMemory.from_dict(memory_data)
            
            if memory.target_language != target_language:
                continue
            
            # 计算文本相似度
            text_similarity = memory.calculate_similarity(source_text)
            
            if text_similarity < fuzzy_threshold:
                continue
            
            # 计算上下文相似度
            context_similarity = 1.0
            if context and "context" in memory_data:
                context_similarity = self._calculate_context_similarity(
                    context, memory_data["context"]
                )
            
            results.append((memory, text_similarity, context_similarity))
        
        # 按综合相似度排序
        results.sort(key=lambda x: (x[1] * 0.7 + x[2] * 0.3), reverse=True)
        return results
    
    def _calculate_context_similarity(self, context1: Dict[str, Any], 
                                    context2: Dict[str, Any]) -> float:
        """计算上下文相似度"""
        if not context1 or not context2:
            return 0.5
        
        similarity_scores = []
        
        # 比较各个上下文维度
        for key in ["speaker", "scene", "emotion", "formality", "genre"]:
            val1 = context1.get(key)
            val2 = context2.get(key)
            
            if val1 and val2:
                if val1 == val2:
                    similarity_scores.append(1.0)
                else:
                    similarity_scores.append(0.0)
            else:
                similarity_scores.append(0.5)  # 缺失信息给中等分
        
        return sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.5
    
    def _update_context_patterns(self, source_text: str, context: Dict[str, Any]):
        """更新上下文模式"""
        # 提取文本特征
        text_features = self._extract_text_features(source_text)
        
        # 更新模式统计
        for feature in text_features:
            if feature not in self.data["context_patterns"]:
                self.data["context_patterns"][feature] = defaultdict(int)
            
            for key, value in context.items():
                if value:
                    self.data["context_patterns"][feature][f"{key}:{value}"] += 1
    
    def _extract_text_features(self, text: str) -> List[str]:
        """提取文本特征"""
        features = []
        
        # 长度特征
        if len(text) < 10:
            features.append("short_text")
        elif len(text) > 50:
            features.append("long_text")
        else:
            features.append("medium_text")
        
        # 标点特征
        if "？" in text or "?" in text:
            features.append("question")
        if "！" in text or "!" in text:
            features.append("exclamation")
        
        # 语气特征
        if any(word in text for word in ["请", "麻烦", "谢谢"]):
            features.append("polite")
        if any(word in text for word in ["快", "赶紧", "立即"]):
            features.append("urgent")
        
        return features
    
    def _find_similar_memory_key(self, source_text: str, target_language: str) -> Optional[str]:
        """查找相似的翻译记忆键"""
        for key, memory_data in self.data["memories"].items():
            memory = TranslationMemory.from_dict(memory_data)
            if (memory.target_language == target_language and 
                memory.calculate_similarity(source_text) > 0.9):
                return key
        return None
    
    def _generate_memory_key(self, source_text: str, target_language: str) -> str:
        """生成翻译记忆键"""
        text_hash = hashlib.md5(source_text.encode('utf-8')).hexdigest()[:8]
        return f"{text_hash}#{target_language}"


class CulturalAdaptationKB(KnowledgeBase):
    """文化适配知识库"""
    
    def __init__(self, storage_path: str = "knowledge_base/cultural"):
        super().__init__("cultural_adaptation", storage_path)
        self.load()
        
        # 初始化文化适配规则
        if not self.data:
            self._initialize_cultural_rules()
    
    def _initialize_cultural_rules(self):
        """初始化文化适配规则"""
        self.data = {
            "cultural_terms": {
                # 现代网络文化词汇
                "鸡娃": {
                    "en": {"term": "helicopter parenting", "explanation": "Intensive parenting style"},
                    "ja": {"term": "教育ママ", "explanation": "Education-focused parenting"},
                    "ko": {"term": "헬리콥터 육아", "explanation": "Helicopter parenting"}
                },
                "内卷": {
                    "en": {"term": "rat race", "explanation": "Intense competition"},
                    "ja": {"term": "過当競争", "explanation": "Excessive competition"},
                    "ko": {"term": "과도한 경쟁", "explanation": "Excessive competition"}
                },
                "躺平": {
                    "en": {"term": "lying flat", "explanation": "Giving up on ambition"},
                    "ja": {"term": "寝そべり族", "explanation": "Lying flat lifestyle"},
                    "ko": {"term": "눕기 족", "explanation": "Lying flat generation"}
                },
                "社恐": {
                    "en": {"term": "social anxiety", "explanation": "Social phobia"},
                    "ja": {"term": "社交不安", "explanation": "Social anxiety"},
                    "ko": {"term": "사회공포증", "explanation": "Social phobia"}
                }
            },
            "formality_mapping": {
                "en": {
                    "very_high": "formal",
                    "high": "polite", 
                    "medium": "neutral",
                    "low": "casual",
                    "very_low": "informal"
                },
                "ja": {
                    "very_high": "keigo",
                    "high": "teineigo",
                    "medium": "neutral", 
                    "low": "casual",
                    "very_low": "tameguchi"
                },
                "ko": {
                    "very_high": "jondaetmal",
                    "high": "polite",
                    "medium": "neutral",
                    "low": "casual", 
                    "very_low": "banmal"
                }
            },
            "genre_adaptations": {
                "现代军旅剧": {
                    "tone": "serious_professional",
                    "formality_default": "high",
                    "key_terms": ["军事", "训练", "作战", "纪律"]
                },
                "现代都市剧": {
                    "tone": "contemporary_casual",
                    "formality_default": "medium", 
                    "key_terms": ["工作", "生活", "感情", "家庭"]
                },
                "古装剧": {
                    "tone": "classical_formal",
                    "formality_default": "very_high",
                    "key_terms": ["朝廷", "江湖", "武功", "情义"]
                }
            }
        }
        
        self.metadata["entry_count"] = len(self.data)
        logger.info("文化适配规则已初始化")
    
    def get_cultural_adaptation(self, term: str, target_language: str, 
                               context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """获取文化适配信息"""
        if term in self.data["cultural_terms"]:
            term_data = self.data["cultural_terms"][term]
            if target_language in term_data:
                adaptation = term_data[target_language].copy()
                
                # 根据上下文调整
                if context:
                    genre = context.get("genre")
                    if genre and genre in self.data["genre_adaptations"]:
                        genre_info = self.data["genre_adaptations"][genre]
                        adaptation["genre_context"] = genre_info
                
                return adaptation
        
        return None
    
    def add_cultural_term(self, source_term: str, target_language: str,
                         target_term: str, explanation: str = ""):
        """添加文化术语"""
        if source_term not in self.data["cultural_terms"]:
            self.data["cultural_terms"][source_term] = {}
        
        self.data["cultural_terms"][source_term][target_language] = {
            "term": target_term,
            "explanation": explanation,
            "added_at": datetime.now().isoformat()
        }
        
        logger.info("文化术语已添加", source_term=source_term,
                   target_language=target_language, target_term=target_term)


class KnowledgeManager:
    """知识库管理器
    
    统一管理分层术语库、上下文感知翻译记忆和文化适配知识库
    集成术语提取功能
    """
    
    def __init__(self, storage_root: str = "knowledge_base"):
        self.storage_root = Path(storage_root)
        self.storage_root.mkdir(parents=True, exist_ok=True)
        
        # 初始化各个知识库
        self.terminology_kb = HierarchicalTerminologyKB(str(self.storage_root / "terminology"))
        self.translation_memory_kb = ContextAwareTranslationMemory(str(self.storage_root / "translation_memory"))
        self.cultural_kb = CulturalAdaptationKB(str(self.storage_root / "cultural"))
        
        # 术语提取器
        self.term_extractor = TerminologyExtractor()
        
        self.project_manager = get_project_manager()
        
        logger.info("知识库管理器初始化完成", storage_root=str(self.storage_root))
    
    def extract_and_store_terms(self, text: str, target_language: str,
                               context: Dict[str, Any] = None,
                               project_id: str = None, genre: str = None) -> List[TerminologyEntry]:
        """提取并存储术语"""
        extracted_terms = self.term_extractor.extract_terms(text, context)
        stored_entries = []
        
        for term_info in extracted_terms:
            # 创建术语条目
            entry = TerminologyEntry(
                source_term=term_info['term'],
                target_language=target_language,
                target_term="",  # 待翻译
                domain=term_info['category'],
                context=term_info['context'],
                confidence_score=term_info['confidence'],
                created_by="auto_extracted"
            )
            
            # 确定存储层级
            if project_id:
                level = "project"
                self.terminology_kb.add_term(entry, level, project_id=project_id)
            elif genre:
                level = "genre"
                self.terminology_kb.add_term(entry, level, genre=genre)
            else:
                level = "global"
                self.terminology_kb.add_term(entry, level)
            
            stored_entries.append(entry)
            
            logger.debug("术语已提取并存储", term=term_info['term'], 
                        category=term_info['category'], level=level)
        
        return stored_entries
    
    def search_translation_suggestions(self, source_text: str, target_language: str,
                                     context: Dict[str, Any] = None,
                                     project_id: str = None) -> Dict[str, Any]:
        """搜索翻译建议（集成上下文感知）"""
        suggestions = {
            "exact_match": None,
            "fuzzy_matches": [],
            "terminology_matches": [],
            "cultural_adaptations": [],
            "extracted_terms": []
        }
        
        # 搜索翻译记忆（上下文感知）
        memory_results = self.translation_memory_kb.search_memory_with_context(
            source_text, target_language, context
        )
        
        if memory_results:
            best_match = memory_results[0]
            memory, text_sim, context_sim = best_match
            
            if text_sim > 0.95:  # 精确匹配
                suggestions["exact_match"] = {
                    "translation": memory.target_text,
                    "quality_score": memory.quality_score,
                    "text_similarity": text_sim,
                    "context_similarity": context_sim,
                    "method": TranslationMethod.MEMORY.value
                }
            else:  # 模糊匹配
                for memory, text_sim, context_sim in memory_results[:5]:
                    suggestions["fuzzy_matches"].append({
                        "source_text": memory.source_text,
                        "translation": memory.target_text,
                        "text_similarity": text_sim,
                        "context_similarity": context_sim,
                        "quality_score": memory.quality_score
                    })
        
        # 提取术语并搜索术语库
        extracted_terms = self.term_extractor.extract_terms(source_text, context)
        suggestions["extracted_terms"] = extracted_terms
        
        for term_info in extracted_terms:
            term = term_info['term']
            
            # 搜索分层术语库
            genre = context.get('genre') if context else None
            term_results = self.terminology_kb.search_terms(
                term, target_language, project_id, genre
            )
            
            for term_entry in term_results:
                suggestions["terminology_matches"].append({
                    "source_term": term_entry.source_term,
                    "target_term": term_entry.target_term,
                    "confidence": term_entry.confidence_score,
                    "domain": term_entry.domain,
                    "level": getattr(term_entry, 'source_level', 'unknown')
                })
            
            # 搜索文化适配
            cultural_adaptation = self.cultural_kb.get_cultural_adaptation(
                term, target_language, context
            )
            if cultural_adaptation:
                suggestions["cultural_adaptations"].append({
                    "source_term": term,
                    "adaptation": cultural_adaptation
                })
        
        return suggestions
    
    def add_translation_feedback(self, source_text: str, target_language: str,
                               translation: str, quality_score: float,
                               context: Dict[str, Any] = None,
                               project_id: str = None):
        """添加翻译反馈（增强版）"""
        # 创建翻译记忆
        memory = TranslationMemory(
            source_text=source_text,
            target_language=target_language,
            target_text=translation,
            quality_score=quality_score,
            project_id=project_id,
            speaker=context.get('speaker') if context else None
        )
        
        # 添加到上下文感知翻译记忆库
        self.translation_memory_kb.add_memory(memory, context)
        
        # 提取并更新术语
        self._extract_and_update_terms(source_text, translation, target_language,
                                     context, project_id)
    
    def _extract_and_update_terms(self, source_text: str, translation: str,
                                target_language: str, context: Dict[str, Any] = None,
                                project_id: str = None):
        """从翻译对中提取并更新术语"""
        # 提取源文本中的术语
        extracted_terms = self.term_extractor.extract_terms(source_text, context)
        
        for term_info in extracted_terms:
            source_term = term_info['term']
            
            # 尝试从翻译中找到对应的目标术语
            target_term = self._find_target_term(source_term, translation, target_language)
            
            if target_term:
                # 创建或更新术语条目
                entry = TerminologyEntry(
                    source_term=source_term,
                    target_language=target_language,
                    target_term=target_term,
                    domain=term_info['category'],
                    context=source_text,
                    confidence_score=term_info['confidence'],
                    created_by=f"extracted_from_feedback_{project_id}" if project_id else "extracted_from_feedback"
                )
                
                # 根据项目情况选择存储层级
                if project_id:
                    genre = context.get('genre') if context else None
                    if genre:
                        self.terminology_kb.add_term(entry, "project", project_id=project_id)
                    else:
                        self.terminology_kb.add_term(entry, "global")
                else:
                    self.terminology_kb.add_term(entry, "global")
    
    def _find_target_term(self, source_term: str, translation: str, target_language: str) -> Optional[str]:
        """从翻译中找到对应的目标术语"""
        # 简化的术语对应查找逻辑
        # 实际应用中可以使用更复杂的对齐算法
        
        # 预定义的术语映射
        term_mappings = {
            "en": {
                "参谋长": "Chief of Staff",
                "司令": "Commander", 
                "旅长": "Brigade Commander",
                "队长": "Captain",
                "突击队": "Assault Team"
            },
            "ja": {
                "参谋长": "参謀長",
                "司令": "司令官",
                "旅长": "旅団長", 
                "队长": "隊長",
                "突击队": "突撃隊"
            },
            "ko": {
                "参谋长": "참모장",
                "司令": "사령관",
                "旅长": "여단장",
                "队长": "대장",
                "突击队": "돌격대"
            }
        }
        
        if target_language in term_mappings and source_term in term_mappings[target_language]:
            expected_term = term_mappings[target_language][source_term]
            if expected_term in translation:
                return expected_term
        
        # 如果没有预定义映射，尝试简单的词汇提取
        # 这里可以集成更复杂的NLP技术
        words = translation.split()
        if len(words) <= 3:  # 简单情况下，整个翻译可能就是术语
            return translation.strip()
        
        return None
    
    def save_all_knowledge_bases(self):
        """保存所有知识库"""
        try:
            self.terminology_kb.save()
            self.translation_memory_kb.save()
            self.cultural_kb.save()
            logger.info("所有知识库已保存")
        except Exception as e:
            logger.error("保存知识库失败", error=str(e))
            raise
    
    def get_knowledge_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return {
            "terminology": self.terminology_kb.get_statistics(),
            "translation_memory": self.translation_memory_kb.get_statistics(),
            "cultural": self.cultural_kb.get_statistics(),
            "storage_root": str(self.storage_root)
        }
    
    def load_project_knowledge(self, project_id: str):
        """加载项目特定知识"""
        try:
            # 从项目配置加载术语
            context_data = self.project_manager.load_project_context(project_id)
            terminology_data = context_data.get("terminology", {})
            
            # 添加项目特定术语到知识库
            self._import_project_terminology(project_id, terminology_data)
            
            logger.info("项目知识已加载", project_id=project_id)
            
        except Exception as e:
            logger.error("加载项目知识失败", project_id=project_id, error=str(e))
    
    def _import_project_terminology(self, project_id: str, terminology_data: Dict[str, Any]):
        """导入项目术语"""
        for category, terms in terminology_data.items():
            if not isinstance(terms, dict):
                continue
            
            for source_term, translations in terms.items():
                if not isinstance(translations, dict):
                    continue
                
                for lang, target_term in translations.items():
                    if lang in ["context", "notes", "explanation"]:
                        continue
                    
                    # 创建术语条目
                    entry = TerminologyEntry(
                        source_term=source_term,
                        target_language=lang,
                        target_term=target_term,
                        domain=category.replace("_terms", ""),
                        context=translations.get("context", ""),
                        created_by=f"project_{project_id}"
                    )
                    
                    self.terminology_kb.add_term(entry, "project", project_id=project_id)


# 全局知识库管理器实例
knowledge_manager = KnowledgeManager()


def get_knowledge_manager() -> KnowledgeManager:
    """获取知识库管理器实例"""
    return knowledge_manager