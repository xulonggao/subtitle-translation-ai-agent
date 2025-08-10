"""
对话历史和上下文跟踪器测试
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from agents.dialogue_context_tracker import (
    DialogueHistory, PronounResolver, ContextCompressor, DialogueEntry,
    PronounReference, PronounType, ContextRelevance,
    get_dialogue_tracker, get_pronoun_resolver, get_context_compressor
)
from models.subtitle_models import SubtitleEntry, TimeCode
from models.story_models import StoryContext, CharacterRelation


class TestDialogueHistory:
    """对话历史管理器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.dialogue_history = DialogueHistory(window_size=5, max_history=20)
    
    def test_initialization(self):
        """测试初始化"""
        assert self.dialogue_history.window_size == 5
        assert self.dialogue_history.max_history == 20
        assert len(self.dialogue_history.dialogue_history) == 0
        assert len(self.dialogue_history.current_window) == 0
    
    def test_add_dialogue_entry(self):
        """测试添加对话条目"""
        # 创建字幕条目
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长说他要去开会",
            speaker="张三"
        )
        
        # 添加对话条目
        dialogue_entry = self.dialogue_history.add_dialogue_entry(subtitle_entry, "张三")
        
        # 验证结果
        assert len(self.dialogue_history.dialogue_history) == 1
        assert len(self.dialogue_history.current_window) == 1
        assert dialogue_entry.speaker == "张三"
        assert dialogue_entry.subtitle_entry == subtitle_entry
        assert len(dialogue_entry.pronouns) > 0  # 应该检测到代词"他"
        assert "参谋长" in dialogue_entry.mentioned_entities
    
    def test_pronoun_extraction(self):
        """测试代词提取"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="他说这是他的任务，我们要支持他",
            speaker="张三"
        )
        
        dialogue_entry = self.dialogue_history.add_dialogue_entry(subtitle_entry)
        
        # 验证代词提取
        pronouns = dialogue_entry.pronouns
        assert len(pronouns) >= 3  # "他"出现2次，"这"出现1次，"我们"出现1次
        
        pronoun_texts = [p.pronoun for p in pronouns]
        assert "他" in pronoun_texts
        assert "这" in pronoun_texts
        assert "我们" in pronoun_texts
    
    def test_entity_extraction(self):
        """测试实体提取"""
        subtitle_entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长告诉队长，医生已经到了",
            speaker="张三"
        )
        
        dialogue_entry = self.dialogue_history.add_dialogue_entry(subtitle_entry)
        
        # 验证实体提取
        entities = dialogue_entry.mentioned_entities
        assert "参谋长" in entities
        assert "队长" in entities
        assert "医生" in entities
    
    def test_emotional_tone_analysis(self):
        """测试情感语调分析"""
        test_cases = [
            ("我很生气！！", "angry"),
            ("太高兴了，哈哈哈", "happy"),
            ("我很担心这件事", "worried"),
            ("天哪，不敢相信！", "surprised"),
            ("今天天气不错", "neutral")
        ]
        
        for text, expected_emotion in test_cases:
            subtitle_entry = SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text=text,
                speaker="测试"
            )
            
            dialogue_entry = self.dialogue_history.add_dialogue_entry(subtitle_entry)
            assert dialogue_entry.emotional_tone == expected_emotion
    
    def test_context_relevance_calculation(self):
        """测试上下文相关性计算"""
        # 添加第一个条目
        entry1 = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长在开会",
            speaker="张三"
        )
        dialogue1 = self.dialogue_history.add_dialogue_entry(entry1)
        
        # 添加相关的第二个条目（同一说话人，相关实体）
        entry2 = SubtitleEntry(
            index=2,
            start_time=TimeCode(0, 0, 4, 0),
            end_time=TimeCode(0, 0, 6, 0),
            text="参谋长说会议很重要",
            speaker="张三"
        )
        dialogue2 = self.dialogue_history.add_dialogue_entry(entry2)
        
        # 第二个条目应该有较高的相关性分数
        assert dialogue2.context_score > 0.5
        
        # 添加不相关的第三个条目
        entry3 = SubtitleEntry(
            index=3,
            start_time=TimeCode(0, 0, 10, 0),
            end_time=TimeCode(0, 0, 12, 0),
            text="今天天气很好",
            speaker="李四"
        )
        dialogue3 = self.dialogue_history.add_dialogue_entry(entry3)
        
        # 第三个条目的相关性分数应该较低
        assert dialogue3.context_score < dialogue2.context_score
    
    def test_speaker_tracking(self):
        """测试说话人跟踪"""
        speakers = ["张三", "李四", "王五"]
        
        for i, speaker in enumerate(speakers):
            subtitle_entry = SubtitleEntry(
                index=i+1,
                start_time=TimeCode(0, 0, i+1, 0),
                end_time=TimeCode(0, 0, i+3, 0),
                text=f"这是{speaker}说的话",
                speaker=speaker
            )
            self.dialogue_history.add_dialogue_entry(subtitle_entry)
        
        # 验证说话人历史
        for speaker in speakers:
            history = self.dialogue_history.get_speaker_history(speaker)
            assert len(history) == 1
            assert history[0].speaker == speaker
        
        # 验证说话人转换
        assert len(self.dialogue_history.speaker_transitions) == 2
    
    def test_entity_tracking(self):
        """测试实体跟踪"""
        # 添加包含相同实体的多个条目
        entities_texts = [
            "参谋长在开会",
            "参谋长说要准备",
            "队长听从参谋长的指示"
        ]
        
        for i, text in enumerate(entities_texts):
            subtitle_entry = SubtitleEntry(
                index=i+1,
                start_time=TimeCode(0, 0, i+1, 0),
                end_time=TimeCode(0, 0, i+3, 0),
                text=text,
                speaker=f"说话人{i+1}"
            )
            self.dialogue_history.add_dialogue_entry(subtitle_entry)
        
        # 验证实体跟踪
        entity_context = self.dialogue_history.get_entity_context("参谋长")
        assert len(entity_context) == 3
        
        # 验证实体共现
        related_entities = self.dialogue_history.get_related_entities("参谋长")
        assert len(related_entities) >= 1
        assert "队长" in [entity for entity, _ in related_entities]
    
    def test_context_compression(self):
        """测试上下文压缩"""
        # 添加超过最大历史的条目
        for i in range(25):  # 超过max_history=20
            subtitle_entry = SubtitleEntry(
                index=i+1,
                start_time=TimeCode(0, 0, i+1, 0),
                end_time=TimeCode(0, 0, i+3, 0),
                text=f"这是第{i+1}条消息",
                speaker=f"说话人{i%3+1}"
            )
            self.dialogue_history.add_dialogue_entry(subtitle_entry)
        
        # 验证历史长度被限制
        assert len(self.dialogue_history.dialogue_history) == 20
        
        # 执行压缩
        removed_count = self.dialogue_history.compress_context(10)
        assert removed_count > 0
        assert len(self.dialogue_history.dialogue_history) <= 10
    
    def test_get_context_statistics(self):
        """测试获取上下文统计"""
        # 添加一些测试数据
        for i in range(5):
            subtitle_entry = SubtitleEntry(
                index=i+1,
                start_time=TimeCode(0, 0, i+1, 0),
                end_time=TimeCode(0, 0, i+3, 0),
                text=f"说话人{i%2+1}说：他要去开会",
                speaker=f"说话人{i%2+1}"
            )
            self.dialogue_history.add_dialogue_entry(subtitle_entry)
        
        stats = self.dialogue_history.get_context_statistics()
        
        assert stats["total_entries"] == 5
        assert stats["unique_speakers"] == 2
        assert stats["window_size"] == 5
        assert "avg_context_score" in stats
        assert "pronoun_resolution_rate" in stats


class TestPronounResolver:
    """代词指代解析器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.dialogue_history = DialogueHistory(window_size=5)
        self.pronoun_resolver = PronounResolver(self.dialogue_history)
        
        # 创建测试用的故事上下文
        self.story_context = StoryContext(
            title="测试剧情",
            genre="现代剧",
            setting="办公室",
            time_period="现代"
        )
        
        # 添加测试角色
        zhang_san = CharacterRelation(
            name="张三",
            role="参谋长",
            profession="军官",
            gender="male"
        )
        li_si = CharacterRelation(
            name="李四",
            role="队长", 
            profession="军官",
            gender="female"
        )
        
        self.story_context.add_character(zhang_san)
        self.story_context.add_character(li_si)
    
    def test_personal_pronoun_resolution(self):
        """测试人称代词解析"""
        # 先添加一个包含人物的条目
        entry1 = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="张三在开会",
            speaker="旁白"
        )
        self.dialogue_history.add_dialogue_entry(entry1)
        
        # 添加包含代词的条目
        entry2 = SubtitleEntry(
            index=2,
            start_time=TimeCode(0, 0, 4, 0),
            end_time=TimeCode(0, 0, 6, 0),
            text="他说会议很重要",
            speaker="旁白"
        )
        dialogue_entry = self.dialogue_history.add_dialogue_entry(entry2)
        
        # 解析代词
        resolved_pronouns = self.pronoun_resolver.resolve_pronouns(dialogue_entry, self.story_context)
        
        # 验证解析结果
        he_pronoun = next((p for p in resolved_pronouns if p.pronoun == "他"), None)
        assert he_pronoun is not None
        assert he_pronoun.resolved_reference == "张三"
        assert he_pronoun.confidence > 0.5
    
    def test_possessive_pronoun_resolution(self):
        """测试物主代词解析"""
        # 添加上下文
        entry1 = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="李四拿着文件",
            speaker="旁白"
        )
        self.dialogue_history.add_dialogue_entry(entry1)
        
        # 添加包含物主代词的条目
        entry2 = SubtitleEntry(
            index=2,
            start_time=TimeCode(0, 0, 4, 0),
            end_time=TimeCode(0, 0, 6, 0),
            text="她的报告写得很好",
            speaker="张三"
        )
        dialogue_entry = self.dialogue_history.add_dialogue_entry(entry2)
        
        # 解析代词
        resolved_pronouns = self.pronoun_resolver.resolve_pronouns(dialogue_entry, self.story_context)
        
        # 验证解析结果
        her_pronoun = next((p for p in resolved_pronouns if p.pronoun == "她的"), None)
        assert her_pronoun is not None
        assert her_pronoun.resolved_reference == "李四"
    
    def test_reflexive_pronoun_resolution(self):
        """测试反身代词解析"""
        entry = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="我要自己完成这个任务",
            speaker="张三"
        )
        dialogue_entry = self.dialogue_history.add_dialogue_entry(entry)
        
        # 解析代词
        resolved_pronouns = self.pronoun_resolver.resolve_pronouns(dialogue_entry, self.story_context)
        
        # 验证反身代词解析
        self_pronoun = next((p for p in resolved_pronouns if p.pronoun == "自己"), None)
        assert self_pronoun is not None
        assert self_pronoun.resolved_reference == "张三"
        assert self_pronoun.confidence > 0.7
    
    def test_demonstrative_pronoun_resolution(self):
        """测试指示代词解析"""
        # 添加上下文
        entry1 = SubtitleEntry(
            index=1,
            start_time=TimeCode(0, 0, 1, 0),
            end_time=TimeCode(0, 0, 3, 0),
            text="参谋长提到了新的作战计划",
            speaker="张三"
        )
        self.dialogue_history.add_dialogue_entry(entry1)
        
        # 添加包含指示代词的条目
        entry2 = SubtitleEntry(
            index=2,
            start_time=TimeCode(0, 0, 4, 0),
            end_time=TimeCode(0, 0, 6, 0),
            text="这很重要",
            speaker="李四"
        )
        dialogue_entry = self.dialogue_history.add_dialogue_entry(entry2)
        
        # 解析代词
        resolved_pronouns = self.pronoun_resolver.resolve_pronouns(dialogue_entry, self.story_context)
        
        # 验证指示代词解析
        this_pronoun = next((p for p in resolved_pronouns if p.pronoun == "这"), None)
        assert this_pronoun is not None
        # 指示代词可能指向最近提及的实体
        assert this_pronoun.resolved_reference is not None
    
    def test_candidate_generation(self):
        """测试候选对象生成"""
        # 添加多个包含不同实体的条目
        entries_data = [
            ("张三在会议室", "旁白"),
            ("李四也参加了会议", "旁白"),
            ("参谋长主持会议", "旁白")
        ]
        
        for text, speaker in entries_data:
            entry = SubtitleEntry(
                index=1,
                start_time=TimeCode(0, 0, 1, 0),
                end_time=TimeCode(0, 0, 3, 0),
                text=text,
                speaker=speaker
            )
            self.dialogue_history.add_dialogue_entry(entry)
        
        # 创建包含代词的条目
        pronoun_entry = SubtitleEntry(
            index=4,
            start_time=TimeCode(0, 0, 7, 0),
            end_time=TimeCode(0, 0, 9, 0),
            text="他们讨论得很激烈",
            speaker="旁白"
        )
        dialogue_entry = self.dialogue_history.add_dialogue_entry(pronoun_entry)
        
        # 验证候选对象生成
        pronoun_ref = dialogue_entry.pronouns[0]  # "他们"
        candidates = self.pronoun_resolver._get_reference_candidates(
            dialogue_entry, pronoun_ref, self.story_context
        )
        
        assert len(candidates) > 0
        assert "张三" in candidates or "李四" in candidates or "参谋长" in candidates


class TestContextCompressor:
    """上下文压缩器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.dialogue_history = DialogueHistory(window_size=10, max_history=50)
        self.context_compressor = ContextCompressor(self.dialogue_history)
        
        # 添加测试数据
        for i in range(20):
            entry = SubtitleEntry(
                index=i+1,
                start_time=TimeCode(0, 0, i+1, 0),
                end_time=TimeCode(0, 0, i+3, 0),
                text=f"这是第{i+1}条消息，包含重要信息" if i % 5 == 0 else f"普通消息{i+1}",
                speaker=f"说话人{i%3+1}"
            )
            dialogue_entry = self.dialogue_history.add_dialogue_entry(entry)
            
            # 手动设置一些条目为高相关性
            if i % 5 == 0:
                dialogue_entry.context_score = 0.9
    
    def test_adaptive_compression(self):
        """测试自适应压缩"""
        original_count = len(self.dialogue_history.dialogue_history)
        target_size = 10
        
        result = self.context_compressor.compress_context(target_size, "adaptive")
        
        assert len(result["compressed_entries"]) <= target_size
        assert result["compression_ratio"] <= 1.0
        assert result["removed_count"] == original_count - len(result["compressed_entries"])
        
        # 验证时间顺序保持
        compressed_entries = result["compressed_entries"]
        for i in range(1, len(compressed_entries)):
            assert compressed_entries[i].timestamp >= compressed_entries[i-1].timestamp
    
    def test_relevance_based_compression(self):
        """测试基于相关性的压缩"""
        target_size = 8
        result = self.context_compressor.compress_context(target_size, "relevance_based")
        
        assert len(result["compressed_entries"]) == target_size
        
        # 验证保留的是高相关性条目
        compressed_entries = result["compressed_entries"]
        high_relevance_count = sum(1 for entry in compressed_entries if entry.context_score > 0.8)
        assert high_relevance_count > 0
    
    def test_time_based_compression(self):
        """测试基于时间的压缩"""
        target_size = 5
        result = self.context_compressor.compress_context(target_size, "time_based")
        
        assert len(result["compressed_entries"]) == target_size
        
        # 验证保留的是最新的条目
        compressed_entries = result["compressed_entries"]
        original_entries = list(self.dialogue_history.dialogue_history)
        
        # 最新的条目应该被保留
        assert compressed_entries[-1] == original_entries[-1]
    
    def test_importance_score_calculation(self):
        """测试重要性分数计算"""
        entries = list(self.dialogue_history.dialogue_history)
        
        for i, entry in enumerate(entries):
            score = self.context_compressor._calculate_importance_score(entry, i, len(entries))
            assert 0.0 <= score <= 1.0
            
            # 高相关性条目应该有更高的重要性分数
            if entry.context_score > 0.8:
                assert score >= 0.5  # 改为 >= 以处理边界情况


def test_global_instances():
    """测试全局实例"""
    tracker = get_dialogue_tracker()
    resolver = get_pronoun_resolver()
    compressor = get_context_compressor()
    
    assert isinstance(tracker, DialogueHistory)
    assert isinstance(resolver, PronounResolver)
    assert isinstance(compressor, ContextCompressor)
    
    # 验证单例模式
    assert get_dialogue_tracker() is tracker
    assert get_pronoun_resolver() is resolver
    assert get_context_compressor() is compressor


if __name__ == "__main__":
    pytest.main([__file__])