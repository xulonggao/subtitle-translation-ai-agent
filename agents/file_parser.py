"""
文件解析Agent
负责解析SRT字幕文件和剧情文档
集成上下文管理器的说话人推断和人物关系分析功能
"""
import re
import json
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass

from config import get_logger
from models.subtitle_models import SubtitleEntry, SubtitleFile
from models.story_models import CharacterRelation, StoryContext
from agents.context_manager import get_context_manager

logger = get_logger("file_parser")


@dataclass
class ParseResult:
    """解析结果"""
    success: bool
    data: Any = None
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class SRTParser:
    """SRT字幕文件解析器
    
    支持标准SRT格式解析，处理时间码、文本和格式异常
    """
    
    def __init__(self):
        # SRT时间码正则表达式
        self.time_pattern = re.compile(
            r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})'
        )
        
        # 字幕编号正则表达式
        self.number_pattern = re.compile(r'^\d+$')
        
        # 支持的编码格式
        self.supported_encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'big5']
        
        self.context_manager = get_context_manager()
    
    def parse_file(self, file_path: str, project_id: str = None) -> ParseResult:
        """解析SRT文件
        
        Args:
            file_path: SRT文件路径
            project_id: 项目ID（用于上下文分析）
            
        Returns:
            解析结果
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return ParseResult(
                    success=False,
                    errors=[f"文件不存在: {file_path}"]
                )
            
            # 尝试不同编码读取文件
            content = self._read_file_with_encoding(file_path)
            if content is None:
                return ParseResult(
                    success=False,
                    errors=["无法读取文件，可能是编码问题"]
                )
            
            # 解析SRT内容
            entries, errors, warnings = self._parse_srt_content(content)
            
            # 创建字幕文件对象
            from models.subtitle_models import SubtitleFormat
            subtitle_file = SubtitleFile(
                filename=str(file_path),
                format=SubtitleFormat.SRT,
                entries=entries,
                encoding=self._detect_encoding(file_path),
                created_at=datetime.now()
            )
            
            # 如果有项目ID，进行上下文分析
            if project_id and entries:
                self._analyze_context(subtitle_file, project_id)
            
            return ParseResult(
                success=True,
                data=subtitle_file,
                errors=errors,
                warnings=warnings,
                metadata={
                    "total_entries": len(entries),
                    "duration_seconds": subtitle_file.total_duration,
                    "encoding": subtitle_file.encoding,
                    "has_speaker_info": any(entry.speaker for entry in entries)
                }
            )
            
        except Exception as e:
            logger.error("SRT文件解析失败", file_path=str(file_path), error=str(e))
            return ParseResult(
                success=False,
                errors=[f"解析失败: {str(e)}"]
            )
    
    def _read_file_with_encoding(self, file_path: Path) -> Optional[str]:
        """尝试不同编码读取文件"""
        for encoding in self.supported_encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.debug("文件读取成功", encoding=encoding)
                return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning("读取文件失败", encoding=encoding, error=str(e))
                continue
        
        return None
    
    def _detect_encoding(self, file_path: Path) -> str:
        """检测文件编码"""
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            result = chardet.detect(raw_data)
            return result.get('encoding', 'utf-8')
        except ImportError:
            # 如果没有chardet，使用默认编码
            return 'utf-8'
        except Exception:
            return 'utf-8'
    
    def _parse_srt_content(self, content: str) -> Tuple[List[SubtitleEntry], List[str], List[str]]:
        """解析SRT内容"""
        entries = []
        errors = []
        warnings = []
        
        # 分割字幕块
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for i, block in enumerate(blocks):
            if not block.strip():
                continue
            
            try:
                entry = self._parse_subtitle_block(block, i + 1)
                if entry:
                    entries.append(entry)
                else:
                    warnings.append(f"跳过空白字幕块 {i + 1}")
            except Exception as e:
                errors.append(f"解析字幕块 {i + 1} 失败: {str(e)}")
                continue
        
        # 验证时间序列
        time_errors = self._validate_time_sequence(entries)
        errors.extend(time_errors)
        
        return entries, errors, warnings
    
    def _parse_subtitle_block(self, block: str, block_number: int) -> Optional[SubtitleEntry]:
        """解析单个字幕块"""
        lines = block.strip().split('\n')
        
        if len(lines) < 3:
            return None
        
        # 解析编号
        number_line = lines[0].strip()
        if not self.number_pattern.match(number_line):
            raise ValueError(f"无效的字幕编号: {number_line}")
        
        subtitle_number = int(number_line)
        
        # 解析时间码
        time_line = lines[1].strip()
        time_match = self.time_pattern.match(time_line)
        if not time_match:
            raise ValueError(f"无效的时间码格式: {time_line}")
        
        start_time = self._parse_timestamp(time_match.groups()[:4])
        end_time = self._parse_timestamp(time_match.groups()[4:])
        
        # 解析文本内容
        text_lines = lines[2:]
        text = '\n'.join(text_lines).strip()
        
        # 清理HTML标签和格式标记
        clean_text = self._clean_subtitle_text(text)
        
        # 提取说话人信息（如果有）
        speaker = self._extract_speaker(clean_text)
        if speaker:
            clean_text = self._remove_speaker_prefix(clean_text, speaker)
        
        # 计算字符数（中文按2个字符计算）
        char_count = self._count_characters(clean_text)
        
        # 计算显示时长（使用毫秒数）
        duration = (end_time.to_milliseconds() - start_time.to_milliseconds()) / 1000.0
        
        entry = SubtitleEntry(
            index=subtitle_number,
            start_time=start_time,
            end_time=end_time,
            text=clean_text,
            speaker=speaker
        )
        
        # 添加额外属性
        entry.original_text = text
        entry.reading_speed = char_count / duration if duration > 0 else 0
        
        return entry
    
    def _parse_timestamp(self, time_parts: Tuple[str, str, str, str]) -> 'TimeCode':
        """解析时间戳"""
        from models.subtitle_models import TimeCode
        
        hours, minutes, seconds, milliseconds = time_parts
        
        return TimeCode(
            hours=int(hours),
            minutes=int(minutes),
            seconds=int(seconds),
            milliseconds=int(milliseconds)
        )
    
    def _clean_subtitle_text(self, text: str) -> str:
        """清理字幕文本"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除字幕格式标记
        text = re.sub(r'\{[^}]+\}', '', text)
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_speaker(self, text: str) -> Optional[str]:
        """提取说话人信息"""
        # 常见的说话人格式
        patterns = [
            r'^([^：:]+)[：:]\s*',  # 中文冒号
            r'^([^-]+)-\s*',        # 破折号
            r'^\[([^\]]+)\]\s*',    # 方括号
            r'^\(([^)]+)\)\s*',     # 圆括号
        ]
        
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                speaker = match.group(1).strip()
                # 验证说话人名称的合理性
                if self._is_valid_speaker_name(speaker):
                    return speaker
        
        return None
    
    def _is_valid_speaker_name(self, name: str) -> bool:
        """验证说话人名称的合理性"""
        # 长度检查
        if len(name) > 20 or len(name) < 1:
            return False
        
        # 不应该包含标点符号（除了常见的人名标点）
        invalid_chars = {'.', ',', '!', '?', ';', '(', ')', '[', ']', '{', '}', '"', "'"}
        if any(char in invalid_chars for char in name):
            return False
        
        # 不应该是纯数字
        if name.isdigit():
            return False
        
        # 排除明显不是人名的词汇
        invalid_words = ["重要通知", "通知", "公告", "消息", "新闻", "报告", "声明"]
        if name in invalid_words:
            return False
        
        return True
    
    def _remove_speaker_prefix(self, text: str, speaker: str) -> str:
        """移除说话人前缀"""
        patterns = [
            rf'^{re.escape(speaker)}[：:]\s*',
            rf'^{re.escape(speaker)}-\s*',
            rf'^\[{re.escape(speaker)}\]\s*',
            rf'^\({re.escape(speaker)}\)\s*',
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text)
        
        return text.strip()
    
    def _count_characters(self, text: str) -> int:
        """计算字符数（中文按2个字符计算）"""
        count = 0
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                count += 2
            else:
                count += 1
        return count
    
    def _validate_time_sequence(self, entries: List[SubtitleEntry]) -> List[str]:
        """验证时间序列"""
        errors = []
        
        for i in range(len(entries) - 1):
            current = entries[i]
            next_entry = entries[i + 1]
            
            # 检查时间顺序
            if current.start_time >= current.end_time:
                errors.append(f"字幕 {current.index}: 开始时间不能晚于结束时间")
            
            if current.end_time > next_entry.start_time:
                errors.append(f"字幕 {current.index} 和 {next_entry.index}: 时间重叠")
            
            # 检查显示时长
            if current.duration_seconds < 0.5:
                errors.append(f"字幕 {current.index}: 显示时长过短 ({current.duration_seconds:.2f}秒)")
            elif current.duration_seconds > 10:
                errors.append(f"字幕 {current.index}: 显示时长过长 ({current.duration_seconds:.2f}秒)")
            
            # 检查阅读速度
            reading_speed = current.calculate_reading_speed()
            if reading_speed > 20:  # 每秒超过20个字符
                errors.append(f"字幕 {current.index}: 阅读速度过快 ({reading_speed:.1f} 字符/秒)")
        
        return errors
    
    def _calculate_total_duration(self, entries: List[SubtitleEntry]) -> float:
        """计算总时长"""
        if not entries:
            return 0.0
        
        last_entry = max(entries, key=lambda x: x.end_time.to_milliseconds())
        first_entry = min(entries, key=lambda x: x.start_time.to_milliseconds())
        
        return (last_entry.end_time.to_milliseconds() - first_entry.start_time.to_milliseconds()) / 1000.0
    
    def _analyze_context(self, subtitle_file: SubtitleFile, project_id: str):
        """分析字幕上下文"""
        try:
            # 推断说话人
            self._infer_speakers(subtitle_file, project_id)
            
            # 分析场景情感
            self._analyze_scene_emotion(subtitle_file)
            
            logger.info("字幕上下文分析完成", project_id=project_id, 
                       entries_count=len(subtitle_file.entries))
            
        except Exception as e:
            logger.error("字幕上下文分析失败", project_id=project_id, error=str(e))
    
    def _infer_speakers(self, subtitle_file: SubtitleFile, project_id: str):
        """推断说话人"""
        # 获取项目的人物关系信息
        character_relations = self.context_manager.get_character_relations(project_id)
        
        if not character_relations:
            return
        
        # 为没有说话人信息的字幕推断说话人
        for i, entry in enumerate(subtitle_file.entries):
            if not entry.speaker:
                # 获取上下文
                context_entries = self._get_context_entries(subtitle_file.entries, i, window_size=3)
                
                # 使用上下文管理器推断说话人
                inferred_speaker = self.context_manager.infer_speaker(
                    entry.text, context_entries, character_relations
                )
                
                if inferred_speaker:
                    entry.speaker = inferred_speaker
                    entry.speaker_confidence = 0.7  # 推断的置信度
                    logger.debug("推断说话人", entry_number=entry.number, 
                               speaker=inferred_speaker)
    
    def _get_context_entries(self, entries: List[SubtitleEntry], current_index: int, 
                           window_size: int = 3) -> List[SubtitleEntry]:
        """获取上下文字幕条目"""
        start_index = max(0, current_index - window_size)
        end_index = min(len(entries), current_index + window_size + 1)
        
        return entries[start_index:end_index]
    
    def _analyze_scene_emotion(self, subtitle_file: SubtitleFile):
        """分析场景情感"""
        # 情感关键词
        emotion_keywords = {
            "angry": ["生气", "愤怒", "气死", "混蛋", "该死"],
            "sad": ["难过", "伤心", "哭", "眼泪", "痛苦"],
            "happy": ["高兴", "开心", "笑", "快乐", "兴奋"],
            "nervous": ["紧张", "担心", "害怕", "恐惧", "焦虑"],
            "serious": ["严肃", "重要", "关键", "紧急", "危险"]
        }
        
        for entry in subtitle_file.entries:
            emotions = []
            
            for emotion, keywords in emotion_keywords.items():
                if any(keyword in entry.text for keyword in keywords):
                    emotions.append(emotion)
            
            if emotions:
                entry.emotion = emotions[0]  # 取第一个匹配的情感
                entry.emotion_confidence = 0.6


class StoryDocumentParser:
    """剧情文档解析器
    
    解析Markdown格式的剧情简介，提取人物关系和故事设定
    """
    
    def __init__(self):
        self.context_manager = get_context_manager()
    
    def parse_story_document(self, file_path: str, project_id: str) -> ParseResult:
        """解析剧情文档
        
        Args:
            file_path: 文档文件路径
            project_id: 项目ID
            
        Returns:
            解析结果
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return ParseResult(
                    success=False,
                    errors=[f"文件不存在: {file_path}"]
                )
            
            # 读取文档内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析文档结构
            story_context = self._parse_markdown_content(content, project_id)
            
            return ParseResult(
                success=True,
                data=story_context,
                metadata={
                    "characters_count": len(story_context.main_characters),
                    "relationships_count": sum(len(char.relationships) for char in story_context.main_characters.values()),
                    "has_plot_summary": bool(story_context.episode_summary)
                }
            )
            
        except Exception as e:
            logger.error("剧情文档解析失败", file_path=str(file_path), error=str(e))
            return ParseResult(
                success=False,
                errors=[f"解析失败: {str(e)}"]
            )
    
    def _parse_markdown_content(self, content: str, project_id: str) -> StoryContext:
        """解析Markdown内容"""
        story_context = StoryContext(
            title=project_id,
            genre="",
            setting="",
            time_period="现代",
            episode_summary="",
            key_themes=[],
            cultural_notes=[],
            created_at=datetime.now()
        )
        
        # 分割内容为段落
        sections = self._split_into_sections(content)
        
        for section_title, section_content in sections.items():
            if "人物" in section_title or "角色" in section_title:
                characters = self._extract_characters(section_content)
                for name, char_info in characters.items():
                    character = CharacterRelation(
                        name=name,
                        role=char_info.get("role", ""),
                        profession=char_info.get("profession", ""),
                        personality_traits=char_info.get("personality", "").split("、") if char_info.get("personality") else [],
                        speaking_style=char_info.get("speaking_style", ""),
                        age_group=char_info.get("age_group"),
                        gender=char_info.get("gender")
                    )
                    story_context.add_character(character)
            
            elif "关系" in section_title:
                relationships = self._extract_relationships(section_content)
                # 将关系添加到相应的角色中
                for relationship in relationships:
                    char1 = story_context.get_character(relationship["character1"])
                    char2 = story_context.get_character(relationship["character2"])
                    if char1 and char2:
                        # 这里需要将关系类型映射到RelationshipType枚举
                        from models.story_models import RelationshipType, FormalityLevel, RespectLevel
                        rel_type = self._map_relation_type(relationship["relation_type"])
                        char1.add_relationship(relationship["character2"], rel_type)
                        char2.add_relationship(relationship["character1"], rel_type)
            
            elif "剧情" in section_title or "简介" in section_title:
                story_context.episode_summary = section_content.strip()
            
            elif "背景" in section_title or "设定" in section_title:
                story_context.setting = section_content.strip()
            
            elif "类型" in section_title or "题材" in section_title:
                story_context.genre = section_content.strip()
        
        # 如果没有明确的关系信息，尝试从人物描述中推断
        if not any(char.relationships for char in story_context.main_characters.values()):
            self._infer_relationships_from_characters(story_context)
        
        return story_context
    
    def _split_into_sections(self, content: str) -> Dict[str, str]:
        """将内容分割为章节"""
        sections = {}
        current_section = ""
        current_content = []
        
        lines = content.split('\n')
        
        for line in lines:
            # 检查是否是标题行
            if line.startswith('#') or (line.strip() and 
                                      any(keyword in line for keyword in 
                                          ["人物", "角色", "关系", "剧情", "简介", "背景", "设定", "类型", "题材"])):
                # 保存前一个章节
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # 开始新章节
                current_section = line.strip('#').strip()
                current_content = []
            else:
                current_content.append(line)
        
        # 保存最后一个章节
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _extract_characters(self, content: str) -> Dict[str, Dict[str, Any]]:
        """提取人物信息"""
        characters = {}
        
        # 查找人物信息的模式
        patterns = [
            r'([^：:\n]+)[：:]\s*([^\n]+)',  # 姓名：描述
            r'\*\*([^*]+)\*\*[：:]?\s*([^\n]+)',  # **姓名**：描述
            r'(\d+)\.\s*([^：:\n]+)[：:]?\s*([^\n]+)',  # 1. 姓名：描述
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if len(match) == 2:
                    name, description = match
                elif len(match) == 3:
                    _, name, description = match
                else:
                    continue
                
                name = name.strip().strip('*')  # 移除markdown格式的星号
                description = description.strip()
                
                if self._is_valid_character_name(name):
                    character_info = self._parse_character_description(description)
                    character_info["name"] = name
                    character_info["description"] = description
                    characters[name] = character_info
        
        return characters
    
    def _is_valid_character_name(self, name: str) -> bool:
        """验证人物名称的合理性"""
        if len(name) > 20 or len(name) < 1:
            return False
        
        # 排除明显不是人名的词汇
        invalid_words = ["剧情", "背景", "设定", "简介", "类型", "题材", "演员", "导演"]
        if any(word in name for word in invalid_words):
            return False
        
        return True
    
    def _parse_character_description(self, description: str) -> Dict[str, Any]:
        """解析人物描述"""
        character_info = {
            "profession": "",
            "age": "",
            "personality": "",
            "background": ""
        }
        
        # 提取职业信息
        profession_patterns = [
            r'(军官|士兵|参谋|司令|队长|医生|护士|教师|学生|工程师)',
            r'职业[：:]?\s*([^\s，,。.]+)',
            r'工作[：:]?\s*([^\s，,。.]+)'
        ]
        
        for pattern in profession_patterns:
            match = re.search(pattern, description)
            if match:
                character_info["profession"] = match.group(1)
                break
        
        # 提取年龄信息
        age_match = re.search(r'(\d+)岁|年龄[：:]?\s*(\d+)', description)
        if age_match:
            character_info["age"] = age_match.group(1) or age_match.group(2)
        
        # 提取性格特征
        personality_keywords = ["开朗", "内向", "严肃", "幽默", "温柔", "坚强", "勇敢", "聪明"]
        found_traits = [trait for trait in personality_keywords if trait in description]
        if found_traits:
            character_info["personality"] = "、".join(found_traits)
        
        character_info["background"] = description
        
        return character_info
    
    def _extract_relationships(self, content: str) -> List[Dict[str, str]]:
        """提取人物关系"""
        relationships = []
        
        # 关系模式
        relation_patterns = [
            r'([^和与\s]+)和([^是的\s]+)是([^。\n]+)',
            r'([^是\s]+)是([^的\s]+)的([^。\n]+)',
            r'([^与\s]+)与([^关系\s]+)关系[：:]?\s*([^\n]+)'
        ]
        
        for pattern in relation_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if len(match) >= 3:
                    char1, char2, relation_type = match[:3]
                    
                    char1 = char1.strip()
                    char2 = char2.strip()
                    relation_type = relation_type.strip()
                    
                    if (self._is_valid_character_name(char1) and 
                        self._is_valid_character_name(char2)):
                        
                        relationship = {
                            "character1": char1,
                            "character2": char2,
                            "relation_type": relation_type,
                            "description": f"{char1}和{char2}是{relation_type}",
                            "confidence": 0.8
                        }
                        relationships.append(relationship)
        
        return relationships
    
    def _infer_relationships_from_characters(self, story_context: StoryContext):
        """从人物描述中推断关系"""
        from models.story_models import RelationshipType, FormalityLevel, RespectLevel
        
        char_names = list(story_context.main_characters.keys())
        
        for i, char1_name in enumerate(char_names):
            for char2_name in char_names[i+1:]:
                char1 = story_context.main_characters[char1_name]
                char2 = story_context.main_characters[char2_name]
                
                # 基于职业推断关系
                if ("军官" in char1.profession and "士兵" in char2.profession):
                    char1.add_relationship(char2_name, RelationshipType.MILITARY_COMMANDER)
                    char2.add_relationship(char1_name, RelationshipType.MILITARY_SUBORDINATE)
                elif ("参谋" in char1.profession and "队长" in char2.profession):
                    char1.add_relationship(char2_name, RelationshipType.PROFESSIONAL_SUPERIOR)
                    char2.add_relationship(char1_name, RelationshipType.PROFESSIONAL_SUBORDINATE)
    
    def _map_relation_type(self, relation_str: str):
        """映射关系类型字符串到枚举"""
        from models.story_models import RelationshipType
        
        relation_mapping = {
            "恋人": RelationshipType.SOCIAL_LOVER,
            "恋人关系": RelationshipType.SOCIAL_LOVER,
            "上级": RelationshipType.PROFESSIONAL_SUPERIOR,
            "下级": RelationshipType.PROFESSIONAL_SUBORDINATE,
            "同事": RelationshipType.PROFESSIONAL_COLLEAGUE,
            "朋友": RelationshipType.SOCIAL_FRIEND,
            "父子": RelationshipType.FAMILY_PARENT,
            "母子": RelationshipType.FAMILY_PARENT,
            "夫妻": RelationshipType.FAMILY_SPOUSE,
            "兄弟": RelationshipType.FAMILY_SIBLING,
            "姐妹": RelationshipType.FAMILY_SIBLING,
        }
        
        return relation_mapping.get(relation_str, RelationshipType.SOCIAL_FRIEND)


class FileParserAgent:
    """文件解析Agent
    
    集成SRT解析器和剧情解析器，提供统一的文件解析接口
    """
    
    def __init__(self):
        self.srt_parser = SRTParser()
        self.story_parser = StoryDocumentParser()
        self.context_manager = get_context_manager()
        
        logger.info("文件解析Agent初始化完成")
    
    def parse_subtitle_file(self, file_path: str, project_id: str = None) -> ParseResult:
        """解析字幕文件"""
        logger.info("开始解析字幕文件", file_path=file_path, project_id=project_id)
        
        result = self.srt_parser.parse_file(file_path, project_id)
        
        if result.success:
            logger.info("字幕文件解析成功", 
                       entries_count=result.metadata.get("total_entries", 0),
                       duration=result.metadata.get("duration_seconds", 0))
        else:
            logger.error("字幕文件解析失败", errors=result.errors)
        
        return result
    
    def parse_story_document(self, file_path: str, project_id: str) -> ParseResult:
        """解析剧情文档"""
        logger.info("开始解析剧情文档", file_path=file_path, project_id=project_id)
        
        result = self.story_parser.parse_story_document(file_path, project_id)
        
        if result.success:
            # 将解析结果存储到上下文管理器
            story_context = result.data
            self.context_manager.update_story_context(project_id, story_context)
            
            logger.info("剧情文档解析成功",
                       characters_count=result.metadata.get("characters_count", 0),
                       relationships_count=result.metadata.get("relationships_count", 0))
        else:
            logger.error("剧情文档解析失败", errors=result.errors)
        
        return result
    
    def batch_parse_files(self, file_paths: List[str], project_id: str) -> Dict[str, ParseResult]:
        """批量解析文件"""
        results = {}
        
        logger.info("开始批量解析文件", files_count=len(file_paths), project_id=project_id)
        
        for file_path in file_paths:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() == '.srt':
                result = self.parse_subtitle_file(str(file_path), project_id)
            elif file_path.suffix.lower() in ['.md', '.txt']:
                result = self.parse_story_document(str(file_path), project_id)
            else:
                result = ParseResult(
                    success=False,
                    errors=[f"不支持的文件格式: {file_path.suffix}"]
                )
            
            results[str(file_path)] = result
        
        # 统计结果
        success_count = sum(1 for r in results.values() if r.success)
        logger.info("批量解析完成", 
                   total_files=len(file_paths),
                   success_count=success_count,
                   failed_count=len(file_paths) - success_count)
        
        return results
    
    def validate_subtitle_file(self, subtitle_file: SubtitleFile) -> List[str]:
        """验证字幕文件质量"""
        issues = []
        
        # 检查基本质量指标
        for entry in subtitle_file.entries:
            # 检查显示时长
            if entry.duration_seconds < 1.0:
                issues.append(f"字幕 {entry.index}: 显示时长过短 ({entry.duration_seconds:.2f}秒)")
            elif entry.duration_seconds > 8.0:
                issues.append(f"字幕 {entry.index}: 显示时长过长 ({entry.duration_seconds:.2f}秒)")
            
            # 检查阅读速度
            reading_speed = entry.calculate_reading_speed()
            if reading_speed > 15:
                issues.append(f"字幕 {entry.index}: 阅读速度过快 ({reading_speed:.1f} 字符/秒)")
            
            # 检查文本长度
            if len(entry.text) > 50:
                issues.append(f"字幕 {entry.index}: 文本过长 ({len(entry.text)} 字符)")
            
            # 检查空白字幕
            if not entry.text.strip():
                issues.append(f"字幕 {entry.index}: 空白字幕")
        
        return issues
    
    def get_parsing_statistics(self, results: Dict[str, ParseResult]) -> Dict[str, Any]:
        """获取解析统计信息"""
        stats = {
            "total_files": len(results),
            "successful_files": 0,
            "failed_files": 0,
            "total_subtitle_entries": 0,
            "total_characters": 0,
            "total_relationships": 0,
            "file_types": {},
            "errors": []
        }
        
        for file_path, result in results.items():
            file_ext = Path(file_path).suffix.lower()
            stats["file_types"][file_ext] = stats["file_types"].get(file_ext, 0) + 1
            
            if result.success:
                stats["successful_files"] += 1
                
                if result.metadata:
                    stats["total_subtitle_entries"] += result.metadata.get("total_entries", 0)
                    stats["total_characters"] += result.metadata.get("characters_count", 0)
                    stats["total_relationships"] += result.metadata.get("relationships_count", 0)
            else:
                stats["failed_files"] += 1
                stats["errors"].extend(result.errors)
        
        return stats


# 全局文件解析Agent实例
file_parser_agent = FileParserAgent()


def get_file_parser_agent() -> FileParserAgent:
    """获取文件解析Agent实例"""
    return file_parser_agent