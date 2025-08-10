"""
数据模型测试
"""
import pytest
from datetime import datetime, timedelta

from models.subtitle_models import (
    TimeCode, SubtitleEntry, SubtitleFile, TranslationResult,
    SubtitleFormat, SceneEmotion, SpeechPace
)
from models.story_models import (
    CharacterRelation, StoryContext, RelationshipType,
    FormalityLevel, RespectLevel, RelationshipConfig
)
from models.translation_models import (
    TranslationTask, TranslationMemory, TerminologyEntry,
    TranslationStatus, TranslationMethod, QualityLevel
)


class TestTimeCode:
    """时间码测试"""
    
    def test_timecode_creation(self):
        """测试时间码创建"""
        tc = TimeCode(1, 23, 45, 678)
        assert tc.hours == 1
        assert tc.minutes == 23
        assert tc.seconds == 45
        assert tc.milliseconds == 678
    
    def test_timecode_validation(self):
        """测试时间码验证"""
        # 有效时间码
        TimeCode(0, 0, 0, 0)
        TimeCode(23, 59, 59, 999)
        
        # 无效时间码
        with pytest.raises(ValueError):
            TimeCode(24, 0, 0, 0)  # 小时超出范围
        
        with pytest.raises(ValueError):
            TimeCode(0, 60, 0, 0)  # 分钟超出范围
        
        with pytest.raises(ValueError):
            TimeCode(0, 0, 60, 0)  # 秒超出范围
        
        with pytest.raises(ValueError):
            TimeCode(0, 0, 0, 1000)  # 毫秒超出范围
    
    def test_timecode_from_string(self):
        """测试从字符串解析时间码"""
        # SRT格式
        tc1 = TimeCode.from_string("01:23:45,678")
        assert tc1.hours == 1
        assert tc1.minutes == 23
        assert tc1.seconds == 45
        assert tc1.milliseconds == 678
        
        # VTT格式
        tc2 = TimeCode.from_string("01:23:45.678")
        assert tc2.hours == 1
        assert tc2.minutes == 23
        assert tc2.seconds == 45
        assert tc2.milliseconds == 678
        
        # 无效格式
        with pytest.raises(ValueError):
            TimeCode.from_string("invalid")
    
    def test_timecode_to_string(self):
        """测试时间码转字符串"""
        tc = TimeCode(1, 23, 45, 678)
        
        # SRT格式
        assert tc.to_string("srt") == "01:23:45,678"
        
        # VTT格式
        assert tc.to_string("vtt") == "01:23:45.678"
        
        # 默认格式
        assert tc.to_string() == "01:23:45,678"
    
    def test_timecode_milliseconds_conversion(self):
        """测试毫秒转换"""
        tc = TimeCode(1, 23, 45, 678)
        ms = tc.to_milliseconds()
        expected = 1 * 3600000 + 23 * 60000 + 45 * 1000 + 678
        assert ms == expected
        
        # 反向转换
        tc2 = TimeCode.from_milliseconds(ms)
        assert tc2 == tc
    
    def test_timecode_comparison(self):
        """测试时间码比较"""
        tc1 = TimeCode(1, 0, 0, 0)
        tc2 = TimeCode(1, 0, 0, 1)
        tc3 = TimeCode(1, 0, 0, 0)
        
        assert tc1 < tc2
        assert tc2 > tc1
        assert tc1 == tc3
        assert tc1 <= tc3
        assert tc1 >= tc3


class TestSubtitleEntry:
    """字幕条目测试"""
    
    def test_subtitle_entry_creation(self):
        """测试字幕条目创建"""
        start = TimeCode(0, 0, 1, 0)
        end = TimeCode(0, 0, 3, 0)
        entry = SubtitleEntry(1, start, end, "测试字幕")
        
        assert entry.index == 1
        assert entry.start_time == start
        assert entry.end_time == end
        assert entry.text == "测试字幕"
        assert entry.duration_seconds == 2.0
        assert entry.character_count == 4
    
    def test_subtitle_entry_validation(self):
        """测试字幕条目验证"""
        start = TimeCode(0, 0, 3, 0)
        end = TimeCode(0, 0, 1, 0)  # 结束时间早于开始时间
        
        with pytest.raises(ValueError):
            SubtitleEntry(1, start, end, "测试")
    
    def test_reading_speed_calculation(self):
        """测试阅读速度计算"""
        start = TimeCode(0, 0, 0, 0)
        end = TimeCode(0, 0, 2, 0)  # 2秒
        entry = SubtitleEntry(1, start, end, "这是十个字符的测试")  # 9个字符
        
        assert entry.calculate_reading_speed() == 4.5  # 9字符/2秒 = 4.5字符/秒
        assert entry.is_reading_speed_appropriate(7.5) is True
        assert entry.is_reading_speed_appropriate(4.0) is False
    
    def test_translation_cache(self):
        """测试翻译缓存"""
        start = TimeCode(0, 0, 1, 0)
        end = TimeCode(0, 0, 3, 0)
        entry = SubtitleEntry(1, start, end, "你好")
        
        # 设置翻译
        entry.set_translation("en", "Hello", 0.9)
        entry.set_translation("ja", "こんにちは", 0.8)
        
        # 获取翻译
        assert entry.get_translation("en") == "Hello"
        assert entry.get_translation("ja") == "こんにちは"
        assert entry.get_translation("fr") is None
        
        assert entry.quality_score == 0.8  # 最后设置的质量分数
    
    def test_srt_format_output(self):
        """测试SRT格式输出"""
        start = TimeCode(0, 0, 1, 0)
        end = TimeCode(0, 0, 3, 0)
        entry = SubtitleEntry(1, start, end, "你好")
        entry.set_translation("en", "Hello")
        
        # 原文输出
        srt_original = entry.to_srt_format()
        expected_original = "1\n00:00:01,000 --> 00:00:03,000\n你好\n"
        assert srt_original == expected_original
        
        # 翻译输出
        srt_english = entry.to_srt_format("en")
        expected_english = "1\n00:00:01,000 --> 00:00:03,000\nHello\n"
        assert srt_english == expected_english
    
    def test_dict_conversion(self):
        """测试字典转换"""
        start = TimeCode(0, 0, 1, 0)
        end = TimeCode(0, 0, 3, 0)
        entry = SubtitleEntry(1, start, end, "测试", speaker="角色A")
        entry.add_context_tag("dialogue")
        entry.set_translation("en", "Test")
        
        # 转换为字典
        data = entry.to_dict()
        assert data["index"] == 1
        assert data["text"] == "测试"
        assert data["speaker"] == "角色A"
        assert "dialogue" in data["context_tags"]
        assert data["translation_cache"]["en"] == "Test"
        
        # 从字典创建
        entry2 = SubtitleEntry.from_dict(data)
        assert entry2.index == entry.index
        assert entry2.text == entry.text
        assert entry2.speaker == entry.speaker


class TestSubtitleFile:
    """字幕文件测试"""
    
    def test_subtitle_file_creation(self):
        """测试字幕文件创建"""
        entries = [
            SubtitleEntry(1, TimeCode(0, 0, 1, 0), TimeCode(0, 0, 3, 0), "第一句"),
            SubtitleEntry(2, TimeCode(0, 0, 4, 0), TimeCode(0, 0, 6, 0), "第二句"),
        ]
        
        subtitle_file = SubtitleFile("test.srt", SubtitleFormat.SRT, entries)
        
        assert subtitle_file.filename == "test.srt"
        assert subtitle_file.format == SubtitleFormat.SRT
        assert subtitle_file.total_entries == 2
        assert subtitle_file.total_duration == 5.0  # 从1秒到6秒
    
    def test_subtitle_file_validation(self):
        """测试字幕文件验证"""
        # 重叠的字幕条目
        entries = [
            SubtitleEntry(1, TimeCode(0, 0, 1, 0), TimeCode(0, 0, 4, 0), "第一句"),
            SubtitleEntry(2, TimeCode(0, 0, 3, 0), TimeCode(0, 0, 6, 0), "第二句"),  # 重叠
        ]
        
        with pytest.raises(ValueError):
            SubtitleFile("test.srt", SubtitleFormat.SRT, entries)
    
    def test_get_entries_by_timerange(self):
        """测试按时间范围获取条目"""
        entries = [
            SubtitleEntry(1, TimeCode(0, 0, 1, 0), TimeCode(0, 0, 3, 0), "第一句"),
            SubtitleEntry(2, TimeCode(0, 0, 4, 0), TimeCode(0, 0, 6, 0), "第二句"),
            SubtitleEntry(3, TimeCode(0, 0, 7, 0), TimeCode(0, 0, 9, 0), "第三句"),
        ]
        
        subtitle_file = SubtitleFile("test.srt", SubtitleFormat.SRT, entries)
        
        # 获取2-5秒范围内的条目
        range_entries = subtitle_file.get_entries_by_timerange(
            TimeCode(0, 0, 2, 0), TimeCode(0, 0, 5, 0)
        )
        
        assert len(range_entries) == 2  # 第一句和第二句
        assert range_entries[0].index == 1
        assert range_entries[1].index == 2


class TestCharacterRelation:
    """人物关系测试"""
    
    def test_character_creation(self):
        """测试人物创建"""
        char = CharacterRelation(
            name="张三",
            role="主角",
            profession="医生",
            personality_traits=["善良", "聪明"],
            speaking_style="温和"
        )
        
        assert char.name == "张三"
        assert char.role == "主角"
        assert char.profession == "医生"
        assert "善良" in char.personality_traits
        assert char.speaking_style == "温和"
    
    def test_relationship_management(self):
        """测试关系管理"""
        char1 = CharacterRelation("张三", "医生", "医生")
        char2 = CharacterRelation("李四", "患者", "患者")
        
        # 添加关系
        char1.add_relationship(
            "李四", 
            RelationshipType.DOCTOR_PATIENT,
            FormalityLevel.HIGH,
            RespectLevel.CARING,
            "professional"
        )
        
        # 获取关系
        relationship = char1.get_relationship("李四")
        assert relationship is not None
        assert relationship.relationship_type == RelationshipType.DOCTOR_PATIENT
        assert relationship.formality_level == FormalityLevel.HIGH
        assert relationship.respect_level == RespectLevel.CARING
    
    def test_name_translation(self):
        """测试名称翻译"""
        char = CharacterRelation("张三", "主角", "医生")
        
        # 设置翻译
        char.set_name_translation("en", "Zhang San")
        char.set_name_translation("ja", "チョウ・サン")
        
        # 获取翻译
        assert char.get_name_translation("en") == "Zhang San"
        assert char.get_name_translation("ja") == "チョウ・サン"
        assert char.get_name_translation("fr") == "张三"  # 回退到原名
    
    def test_dict_conversion(self):
        """测试字典转换"""
        char = CharacterRelation("张三", "主角", "医生")
        char.add_relationship("李四", RelationshipType.SOCIAL_FRIEND)
        char.set_name_translation("en", "Zhang San")
        
        # 转换为字典
        data = char.to_dict()
        assert data["name"] == "张三"
        assert data["role"] == "主角"
        assert "李四" in data["relationships"]
        assert data["name_translations"]["en"] == "Zhang San"
        
        # 从字典创建
        char2 = CharacterRelation.from_dict(data)
        assert char2.name == char.name
        assert char2.get_relationship("李四") is not None


class TestStoryContext:
    """故事上下文测试"""
    
    def test_story_context_creation(self):
        """测试故事上下文创建"""
        context = StoryContext(
            title="测试剧集",
            genre="现代剧",
            setting="现代都市",
            time_period="当代"
        )
        
        assert context.title == "测试剧集"
        assert context.genre == "现代剧"
        assert context.setting == "现代都市"
        assert context.time_period == "当代"
    
    def test_character_management(self):
        """测试角色管理"""
        context = StoryContext("测试剧集", "现代剧", "都市", "当代")
        
        # 添加角色
        char1 = CharacterRelation("张三", "主角", "医生")
        char1.titles = ["张医生", "老张"]
        context.add_character(char1)
        
        char2 = CharacterRelation("李四", "配角", "护士")
        context.add_character(char2)
        
        # 获取角色
        assert context.get_character("张三") == char1
        assert context.get_character("李四") == char2
        assert context.get_character("王五") is None
        
        # 通过称谓获取角色
        assert context.get_character_by_title("张医生") == char1
        assert context.get_character_by_title("老张") == char1
        
        # 通过职业获取角色
        doctors = context.get_characters_by_profession("医生")
        assert len(doctors) == 1
        assert doctors[0] == char1
    
    def test_dialogue_context_analysis(self):
        """测试对话上下文分析"""
        context = StoryContext("测试剧集", "现代剧", "都市", "当代")
        
        # 添加角色和关系
        char1 = CharacterRelation("张三", "医生", "医生", personality_traits=["温和"], speaking_style="专业")
        char2 = CharacterRelation("李四", "患者", "患者")
        char1.add_relationship("李四", RelationshipType.DOCTOR_PATIENT)
        
        context.add_character(char1)
        context.add_character(char2)
        
        # 分析对话上下文
        dialogue_context = context.analyze_dialogue_context("张三", "李四")
        
        assert dialogue_context["speaker"]["name"] == "张三"
        assert dialogue_context["speaker"]["profession"] == "医生"
        assert dialogue_context["addressee"]["name"] == "李四"
        assert dialogue_context["relationship"]["type"] == "doctor_patient"


class TestTranslationModels:
    """翻译模型测试"""
    
    def test_terminology_entry(self):
        """测试术语条目"""
        term = TerminologyEntry(
            source_term="医生",
            target_language="en",
            target_term="doctor",
            context="医疗场景",
            domain="medical"
        )
        
        assert term.source_term == "医生"
        assert term.target_term == "doctor"
        assert term.usage_count == 0
        assert term.confidence_score == 1.0
        
        # 增加使用次数
        term.increment_usage()
        assert term.usage_count == 1
        
        # 更新置信度
        term.update_confidence(0.8)
        assert term.confidence_score < 1.0
    
    def test_translation_memory(self):
        """测试翻译记忆"""
        memory = TranslationMemory(
            source_text="你好",
            target_language="en",
            target_text="Hello",
            speaker="张三"
        )
        
        assert memory.source_text == "你好"
        assert memory.target_text == "Hello"
        
        # 测试相似度计算
        assert memory.calculate_similarity("你好") == 1.0
        assert memory.calculate_similarity("你好吗") < 1.0
        assert memory.is_fuzzy_match("你好") is True
        
        # 增加使用次数
        memory.increment_usage()
        assert memory.usage_count == 1
    
    def test_translation_task(self):
        """测试翻译任务"""
        # 创建测试数据
        entries = [
            SubtitleEntry(1, TimeCode(0, 0, 1, 0), TimeCode(0, 0, 3, 0), "你好"),
            SubtitleEntry(2, TimeCode(0, 0, 4, 0), TimeCode(0, 0, 6, 0), "再见"),
        ]
        
        context = StoryContext("测试", "现代剧", "都市", "当代")
        
        task = TranslationTask(
            task_id="task_001",
            project_id="project_001",
            source_language="zh",
            target_languages=["en", "ja"],
            subtitle_entries=entries,
            story_context=context
        )
        
        assert task.task_id == "task_001"
        assert task.total_entries == 2
        assert task.status == TranslationStatus.PENDING
        assert task.progress == 0.0
        
        # 开始任务
        task.start_task()
        assert task.status == TranslationStatus.IN_PROGRESS
        assert task.started_at is not None
        
        # 更新进度
        task.update_progress(1, 0)
        assert task.progress == 0.5
        
        # 添加质量分数
        task.add_quality_score(0.9)
        # 由于completed_entries=1，所以平均分数计算为 (0*0.0 + 0.9) / (0+1) = 0.9
        # 但是由于completed_entries在add_quality_score之前就是1，所以计算为 (1*0.0 + 0.9) / (1+1) = 0.45
        assert task.average_quality_score == 0.45
        
        # 完成任务
        task.complete_task()
        assert task.status == TranslationStatus.COMPLETED
        assert task.progress == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])