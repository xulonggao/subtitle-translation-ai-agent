"""
文件解析Agent测试
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from agents.file_parser import (
    SRTParser, StoryDocumentParser, FileParserAgent, ParseResult,
    get_file_parser_agent
)
from models.subtitle_models import SubtitleEntry, SubtitleFile
from models.story_models import CharacterRelation, StoryContext


class TestSRTParser:
    """SRT解析器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.parser = SRTParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_parse_valid_srt_file(self):
        """测试解析有效的SRT文件"""
        # 创建测试SRT文件
        srt_content = """1
00:00:01,000 --> 00:00:03,000
参谋长：立即集合所有队员

2
00:00:04,000 --> 00:00:06,000
队长：是，长官！

3
00:00:07,000 --> 00:00:10,000
这是一次重要的任务
"""
        
        srt_file = Path(self.temp_dir) / "test.srt"
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        # 解析文件
        result = self.parser.parse_file(str(srt_file))
        
        # 验证结果
        assert result.success is True
        assert isinstance(result.data, SubtitleFile)
        assert len(result.data.entries) == 3
        
        # 验证第一个字幕条目
        first_entry = result.data.entries[0]
        assert first_entry.index == 1
        assert first_entry.text == "立即集合所有队员"
        assert first_entry.speaker == "参谋长"
        assert first_entry.duration_seconds == 2.0
    
    def test_parse_srt_with_formatting(self):
        """测试解析带格式标记的SRT文件"""
        srt_content = """1
00:00:01,000 --> 00:00:03,000
<b>重要通知</b>：{\\an8}所有人员注意
"""
        
        srt_file = Path(self.temp_dir) / "formatted.srt"
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        result = self.parser.parse_file(str(srt_file))
        
        assert result.success is True
        entry = result.data.entries[0]
        # 验证格式标记已被清理
        assert "<b>" not in entry.text
        assert "{\\an8}" not in entry.text
        assert entry.text == "重要通知：所有人员注意"
    
    def test_parse_invalid_time_format(self):
        """测试解析无效时间格式"""
        srt_content = """1
00:00:01 --> 00:00:03
无效的时间格式
"""
        
        srt_file = Path(self.temp_dir) / "invalid_time.srt"
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        result = self.parser.parse_file(str(srt_file))
        
        # 应该有错误但可能部分成功
        assert len(result.errors) > 0
        assert "无效的时间码格式" in result.errors[0]
    
    def test_extract_speaker_patterns(self):
        """测试说话人提取模式"""
        test_cases = [
            ("张三：你好", "张三"),
            ("李四-早上好", "李四"),
            ("[旁白]这是旁白", "旁白"),
            ("(内心独白)我在想什么", "内心独白"),
            ("普通对话", None)
        ]
        
        for text, expected_speaker in test_cases:
            speaker = self.parser._extract_speaker(text)
            assert speaker == expected_speaker
    
    def test_character_counting(self):
        """测试字符计数"""
        test_cases = [
            ("hello", 5),      # 英文
            ("你好", 4),        # 中文（每个中文字符算2个）
            ("hello你好", 9),   # 混合
            ("", 0)            # 空字符串
        ]
        
        for text, expected_count in test_cases:
            count = self.parser._count_characters(text)
            assert count == expected_count
    
    def test_time_validation(self):
        """测试时间序列验证"""
        from models.subtitle_models import TimeCode, SubtitleEntry
        
        # 创建有时间问题的字幕条目
        entries = [
            SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text="正常字幕"
            ),
            SubtitleEntry(
                index=2,
                start_time=TimeCode(0, 0, 2, 0),  # 重叠
                end_time=TimeCode(0, 0, 4, 0),
                text="重叠字幕"
            )
        ]
        
        errors = self.parser._validate_time_sequence(entries)
        assert len(errors) > 0
        assert "时间重叠" in errors[0]


class TestStoryDocumentParser:
    """剧情文档解析器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.parser = StoryDocumentParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_parse_character_info(self):
        """测试解析人物信息"""
        markdown_content = """# 人物介绍

## 主要角色

**李明**：男，28岁，特种部队队长，性格坚毅勇敢
**张华**：女，25岁，军医，温柔善良
**王强**：男，30岁，参谋长，经验丰富

## 人物关系

李明和张华是恋人关系
王强是李明的上级
"""
        
        doc_file = Path(self.temp_dir) / "story.md"
        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        result = self.parser.parse_story_document(str(doc_file), "test_project")
        
        assert result.success is True
        story_context = result.data
        
        # 验证人物信息
        assert "李明" in story_context.main_characters
        assert "张华" in story_context.main_characters
        assert "王强" in story_context.main_characters
        
        # 验证人物详情
        li_ming = story_context.main_characters["李明"]
        assert "队长" in li_ming.profession
        # 注意：age_group可能不是直接的年龄字符串
        
        # 验证关系信息
        total_relationships = sum(len(char.relationships) for char in story_context.main_characters.values())
        assert total_relationships > 0
    
    def test_extract_characters_various_formats(self):
        """测试提取不同格式的人物信息"""
        content = """
李明：特种部队队长
**张华**：军医
1. 王强：参谋长
"""
        
        characters = self.parser._extract_characters(content)
        
        assert "李明" in characters
        assert "张华" in characters
        assert "王强" in characters
        
        assert characters["李明"]["description"] == "特种部队队长"
    
    def test_character_description_parsing(self):
        """测试人物描述解析"""
        description = "男，28岁，特种部队队长，性格坚毅勇敢，有丰富的作战经验"
        
        char_info = self.parser._parse_character_description(description)
        
        assert char_info["age"] == "28"
        assert "队长" in char_info["profession"]
        assert "坚毅" in char_info["personality"] or "勇敢" in char_info["personality"]
    
    def test_relationship_extraction(self):
        """测试关系提取"""
        content = """
李明和张华是恋人关系
王强是李明的上级
张华与李明关系：恋人
"""
        
        relationships = self.parser._extract_relationships(content)
        
        assert len(relationships) >= 2
        
        # 验证关系内容
        relation_descriptions = [r["description"] for r in relationships]
        assert any("恋人" in desc for desc in relation_descriptions)
        assert any("上级" in desc for desc in relation_descriptions)


class TestFileParserAgent:
    """文件解析Agent测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock context manager
        self.mock_context_manager = Mock()
        
        with patch('agents.file_parser.get_context_manager', 
                  return_value=self.mock_context_manager):
            self.agent = FileParserAgent()
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_parse_subtitle_file(self):
        """测试解析字幕文件"""
        # 创建测试SRT文件
        srt_content = """1
00:00:01,000 --> 00:00:03,000
参谋长：准备行动

2
00:00:04,000 --> 00:00:06,000
队员们立即集合
"""
        
        srt_file = Path(self.temp_dir) / "test.srt"
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        result = self.agent.parse_subtitle_file(str(srt_file), "test_project")
        
        assert result.success is True
        assert isinstance(result.data, SubtitleFile)
        assert len(result.data.entries) == 2
    
    def test_parse_story_document(self):
        """测试解析剧情文档"""
        markdown_content = """# 剧情简介

这是一部现代军旅剧

## 人物介绍

**李明**：特种部队队长
**张华**：军医
"""
        
        doc_file = Path(self.temp_dir) / "story.md"
        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        result = self.agent.parse_story_document(str(doc_file), "test_project")
        
        assert result.success is True
        assert isinstance(result.data, StoryContext)
        
        # 验证上下文管理器被调用
        self.mock_context_manager.update_story_context.assert_called_once()
    
    def test_batch_parse_files(self):
        """测试批量解析文件"""
        # 创建测试文件
        srt_content = """1
00:00:01,000 --> 00:00:03,000
测试字幕
"""
        
        md_content = """# 测试剧情
**主角**：测试角色
"""
        
        srt_file = Path(self.temp_dir) / "test.srt"
        md_file = Path(self.temp_dir) / "test.md"
        
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        file_paths = [str(srt_file), str(md_file)]
        results = self.agent.batch_parse_files(file_paths, "test_project")
        
        assert len(results) == 2
        assert all(result.success for result in results.values())
    
    def test_validate_subtitle_file(self):
        """测试字幕文件验证"""
        # 创建有问题的字幕文件
        from models.subtitle_models import TimeCode, SubtitleEntry
        
        entries = [
            SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 1, 500),  # 时长过短
                text="短字幕"
            ),
            SubtitleEntry(
                index=2,
                start_time=TimeCode(0, 0, 2, 0),
                end_time=TimeCode(0, 0, 12, 0),  # 时长过长
                text="这是一个非常非常长的字幕，超过了正常的显示时长限制，会导致阅读困难"
            )
        ]
        
        from models.subtitle_models import SubtitleFormat
        subtitle_file = SubtitleFile(
            filename="test.srt",
            format=SubtitleFormat.SRT,
            entries=entries
        )
        
        issues = self.agent.validate_subtitle_file(subtitle_file)
        
        assert len(issues) >= 2
        assert any("显示时长过短" in issue for issue in issues)
        assert any("显示时长过长" in issue for issue in issues)
    
    def test_get_parsing_statistics(self):
        """测试获取解析统计信息"""
        results = {
            "file1.srt": ParseResult(
                success=True,
                metadata={"total_entries": 10, "duration_seconds": 60}
            ),
            "file2.md": ParseResult(
                success=True,
                metadata={"characters_count": 3, "relationships_count": 2}
            ),
            "file3.srt": ParseResult(
                success=False,
                errors=["解析失败"]
            )
        }
        
        stats = self.agent.get_parsing_statistics(results)
        
        assert stats["total_files"] == 3
        assert stats["successful_files"] == 2
        assert stats["failed_files"] == 1
        assert stats["total_subtitle_entries"] == 10
        assert stats["total_characters"] == 3
        assert stats["total_relationships"] == 2
        assert ".srt" in stats["file_types"]
        assert ".md" in stats["file_types"]


class TestIntegration:
    """集成测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock context manager
        self.mock_context_manager = Mock()
        self.mock_context_manager.get_character_relations.return_value = [
            CharacterRelation(
                name="李明",
                role="主角",
                profession="军官"
            )
        ]
        self.mock_context_manager.infer_speaker.return_value = "李明"
        
        with patch('agents.file_parser.get_context_manager', 
                  return_value=self.mock_context_manager):
            self.agent = FileParserAgent()
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_end_to_end_parsing_workflow(self):
        """测试端到端解析工作流"""
        # 1. 创建剧情文档
        story_content = """# 爱上海军蓝

## 剧情简介
这是一部现代军旅爱情剧

## 人物介绍
**李明**：男，28岁，特种部队队长
**张华**：女，25岁，军医

## 人物关系
李明和张华是恋人关系
"""
        
        story_file = Path(self.temp_dir) / "story.md"
        with open(story_file, 'w', encoding='utf-8') as f:
            f.write(story_content)
        
        # 2. 创建字幕文件
        srt_content = """1
00:00:01,000 --> 00:00:03,000
我们必须完成这次任务

2
00:00:04,000 --> 00:00:06,000
张华：我会支持你的决定

3
00:00:07,000 --> 00:00:09,000
谢谢你，我知道你理解我
"""
        
        srt_file = Path(self.temp_dir) / "episode1.srt"
        with open(srt_file, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        # 3. 解析剧情文档
        story_result = self.agent.parse_story_document(str(story_file), "test_project")
        assert story_result.success is True
        
        # 4. 解析字幕文件
        srt_result = self.agent.parse_subtitle_file(str(srt_file), "test_project")
        assert srt_result.success is True
        
        # 5. 验证解析结果
        story_context = story_result.data
        assert len(story_context.main_characters) >= 2
        assert "李明" in story_context.main_characters
        assert "张华" in story_context.main_characters
        
        subtitle_file = srt_result.data
        assert len(subtitle_file.entries) == 3
        
        # 验证说话人识别
        second_entry = subtitle_file.entries[1]
        assert second_entry.speaker == "张华"
        
        # 6. 批量处理
        batch_results = self.agent.batch_parse_files(
            [str(story_file), str(srt_file)], 
            "test_project"
        )
        
        assert len(batch_results) == 2
        assert all(result.success for result in batch_results.values())
        
        # 7. 获取统计信息
        stats = self.agent.get_parsing_statistics(batch_results)
        assert stats["successful_files"] == 2
        assert stats["total_subtitle_entries"] == 3
        assert stats["total_characters"] >= 2


def test_get_file_parser_agent():
    """测试获取文件解析Agent实例"""
    agent = get_file_parser_agent()
    assert isinstance(agent, FileParserAgent)
    
    # 验证单例模式
    agent2 = get_file_parser_agent()
    assert agent is agent2


if __name__ == "__main__":
    pytest.main([__file__])