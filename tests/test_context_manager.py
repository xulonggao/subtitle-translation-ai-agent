"""
上下文管理器测试
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from agents.context_manager import ContextManager, get_context_manager
from models.subtitle_models import SubtitleEntry, TimeCode, SceneEmotion
from models.story_models import StoryContext, RelationshipType


class TestContextManager:
    """上下文管理器测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.context_manager = ContextManager()
    
    def test_initialization(self):
        """测试初始化"""
        assert self.context_manager.project_manager is not None
        assert isinstance(self.context_manager.loaded_contexts, dict)
        assert isinstance(self.context_manager.dialogue_histories, dict)
    
    @patch('agents.context_manager.get_project_manager')
    def test_load_project_context(self, mock_get_project_manager):
        """测试加载项目上下文"""
        # 模拟项目管理器
        mock_project_manager = Mock()
        mock_get_project_manager.return_value = mock_project_manager
        
        # 模拟项目数据
        mock_context_data = {
            "character_relations": {
                "project_info": {
                    "project_title": "测试剧集",
                    "genre": "现代剧",
                    "description": "测试描述"
                },
                "characters": {
                    "张三": {
                        "role": "主角",
                        "profession": "医生",
                        "personality_traits": ["善良", "专业"],
                        "speaking_style": "温和专业",
                        "name_translations": {"en": "Zhang San"},
                        "titles": ["张医生"],
                        "relationships": {
                            "李四": "同事"
                        }
                    },
                    "李四": {
                        "role": "配角",
                        "profession": "护士",
                        "personality_traits": ["细心"],
                        "speaking_style": "亲切",
                        "relationships": {
                            "张三": "同事"
                        }
                    }
                }
            },
            "story_context": "这是一个关于医院的故事，讲述了医生和护士的日常工作。",
            "terminology": {
                "medical_terms": {
                    "手术": {"en": "surgery"},
                    "病人": {"en": "patient"}
                }
            }
        }
        
        mock_project_manager.load_project_context.return_value = mock_context_data
        
        # 重新创建上下文管理器以使用模拟的项目管理器
        context_manager = ContextManager()
        context_manager.project_manager = mock_project_manager
        
        # 加载项目上下文
        story_context = context_manager.load_project_context("test_project")
        
        # 验证结果
        assert isinstance(story_context, StoryContext)
        assert story_context.title == "测试剧集"
        assert story_context.genre == "现代剧"
        assert len(story_context.main_characters) == 2
        
        # 验证人物信息
        zhang_san = story_context.get_character("张三")
        assert zhang_san is not None
        assert zhang_san.role == "主角"
        assert zhang_san.profession == "医生"
        assert "善良" in zhang_san.personality_traits
        assert zhang_san.get_name_translation("en") == "Zhang San"
        
        # 验证关系
        relationship = zhang_san.get_relationship("李四")
        assert relationship is not None
        assert relationship.relationship_type == RelationshipType.PROFESSIONAL_COLLEAGUE
        
        # 验证缓存
        assert "test_project" in context_manager.loaded_contexts
        
        # 第二次加载应该使用缓存
        story_context2 = context_manager.load_project_context("test_project")
        assert story_context2 is story_context
    
    def test_infer_relationship_type(self):
        """测试关系类型推断"""
        context_manager = ContextManager()
        
        # 测试各种关系类型
        assert context_manager._infer_relationship_type("恋人") == RelationshipType.SOCIAL_LOVER
        assert context_manager._infer_relationship_type("夫妻") == RelationshipType.FAMILY_SPOUSE
        assert context_manager._infer_relationship_type("战友") == RelationshipType.MILITARY_COMRADE
        assert context_manager._infer_relationship_type("上级") == RelationshipType.MILITARY_COMMANDER
        assert context_manager._infer_relationship_type("同事") == RelationshipType.PROFESSIONAL_COLLEAGUE
        assert context_manager._infer_relationship_type("朋友") == RelationshipType.SOCIAL_FRIEND
        assert context_manager._infer_relationship_type("未知关系") == RelationshipType.SOCIAL_STRANGER
    
    def test_extract_themes_from_text(self):
        """测试主题提取"""
        context_manager = ContextManager()
        
        # 测试军旅主题
        military_text = "这是一个关于海军部队演习的故事，讲述了战友之间的情谊。"
        themes = context_manager._extract_themes_from_text(military_text)
        assert "军旅" in themes
        
        # 测试爱情主题
        romance_text = "男女主角通过相亲相识，最终结婚的爱情故事。"
        themes = context_manager._extract_themes_from_text(romance_text)
        assert "爱情" in themes
        
        # 测试职场主题
        workplace_text = "记者在职场中的工作经历和挑战。"
        themes = context_manager._extract_themes_from_text(workplace_text)
        assert "职场" in themes
    
    def test_extract_cultural_notes(self):
        """测试文化要点提取"""
        context_manager = ContextManager()
        
        text = "现代中国海军的军事题材作品"
        cultural_notes = context_manager._extract_cultural_notes_from_text(text)
        
        assert "军事题材" in cultural_notes
        assert "现代背景" in cultural_notes
        assert "中国军队" in cultural_notes
    
    def test_speaker_inference(self):
        """测试说话人推断"""
        context_manager = ContextManager()
        
        # 创建测试故事上下文
        story_context = StoryContext("测试", "现代剧", "医院", "当代")
        
        # 添加角色
        from models.story_models import CharacterRelation
        doctor = CharacterRelation("张医生", "医生", "医生")
        doctor.speaking_style = "专业温和"
        doctor.titles = ["张医生", "医生"]
        story_context.add_character(doctor)
        
        nurse = CharacterRelation("李护士", "护士", "护士")
        nurse.speaking_style = "亲切"
        story_context.add_character(nurse)
        
        # 测试基于专业术语的推断
        entry1 = SubtitleEntry(1, TimeCode(0, 0, 1, 0), TimeCode(0, 0, 3, 0), "病人的情况如何？需要立即手术。")
        speaker1 = context_manager._infer_speaker(entry1, [], story_context)
        # 由于包含医疗术语，可能推断为医生
        
        # 测试基于说话风格的推断
        entry2 = SubtitleEntry(2, TimeCode(0, 0, 4, 0), TimeCode(0, 0, 6, 0), "请您放心，我们会照顾好病人的。")
        speaker2 = context_manager._infer_speaker(entry2, [], story_context)
        # 基于温和的语气，可能推断为医生或护士
    
    def test_addressee_inference(self):
        """测试对话对象推断"""
        context_manager = ContextManager()
        
        # 创建测试故事上下文
        story_context = StoryContext("测试", "现代剧", "医院", "当代")
        
        from models.story_models import CharacterRelation
        doctor = CharacterRelation("张医生", "医生", "医生")
        doctor.titles = ["张医生", "医生"]
        story_context.add_character(doctor)
        
        # 测试直接称呼
        entry = SubtitleEntry(1, TimeCode(0, 0, 1, 0), TimeCode(0, 0, 3, 0), "张医生，病人情况怎么样？")
        addressee = context_manager._infer_addressee(entry, [], story_context)
        assert addressee == "张医生"
    
    def test_get_speaker_context(self):
        """测试获取说话人上下文"""
        # 这个测试需要完整的项目上下文，比较复杂
        # 可以创建一个简化版本的测试
        context_manager = ContextManager()
        
        # 模拟加载项目上下文
        with patch.object(context_manager, 'load_project_context') as mock_load:
            story_context = StoryContext("测试", "现代剧", "医院", "当代")
            mock_load.return_value = story_context
            
            entry = SubtitleEntry(1, TimeCode(0, 0, 1, 0), TimeCode(0, 0, 3, 0), "测试对话")
            context = context_manager.get_speaker_context("test_project", entry, [])
            
            assert "speaker" in context
            assert "entry_index" in context
            assert "text" in context
            assert context["entry_index"] == 1
            assert context["text"] == "测试对话"
    
    def test_pronoun_resolution(self):
        """测试代词解析"""
        context_manager = ContextManager()
        
        # 模拟加载项目上下文
        with patch.object(context_manager, 'load_project_context') as mock_load:
            story_context = StoryContext("测试", "现代剧", "医院", "当代")
            mock_load.return_value = story_context
            
            context = {
                "speaker": "张三",
                "addressee": "李四",
                "dialogue_history": {"recent_speakers": ["张三", "李四"]}
            }
            
            text = "他说得对，我们应该这样做。"
            resolved_text = context_manager.resolve_pronouns("test_project", text, context)
            
            # 基本的代词解析测试
            assert isinstance(resolved_text, str)
    
    def test_cultural_adaptation_context(self):
        """测试文化适配上下文"""
        context_manager = ContextManager()
        
        # 模拟加载项目上下文
        with patch.object(context_manager, 'load_project_context') as mock_load:
            story_context = StoryContext("测试剧集", "现代剧", "现代都市", "当代")
            story_context.cultural_notes = ["现代背景", "都市生活"]
            story_context.key_themes = ["爱情", "职场"]
            mock_load.return_value = story_context
            
            adaptation_context = context_manager.get_cultural_adaptation_context("test_project", "en")
            
            assert adaptation_context["genre"] == "现代剧"
            assert adaptation_context["setting"] == "现代都市"
            assert adaptation_context["target_language"] == "en"
            assert "现代背景" in adaptation_context["cultural_notes"]
            assert "爱情" in adaptation_context["key_themes"]
    
    def test_dialogue_context_update(self):
        """测试对话上下文更新"""
        context_manager = ContextManager()
        
        entry1 = SubtitleEntry(1, TimeCode(0, 0, 1, 0), TimeCode(0, 0, 3, 0), "你好", speaker="张三")
        entry2 = SubtitleEntry(2, TimeCode(0, 0, 4, 0), TimeCode(0, 0, 6, 0), "你好", speaker="李四")
        
        # 更新对话上下文
        context_manager.update_dialogue_context("test_project", entry1)
        context_manager.update_dialogue_context("test_project", entry2)
        
        # 验证对话历史
        assert "test_project" in context_manager.dialogue_histories
        dialogue_context = context_manager.dialogue_histories["test_project"]
        
        assert "张三" in dialogue_context.previous_speakers
        assert "李四" in dialogue_context.previous_speakers
        assert len(dialogue_context.context_window) == 2
    
    def test_cache_management(self):
        """测试缓存管理"""
        context_manager = ContextManager()
        
        # 模拟加载上下文
        with patch.object(context_manager, 'load_project_context') as mock_load:
            story_context = StoryContext("测试", "现代剧", "医院", "当代")
            mock_load.return_value = story_context
            
            # 手动添加到缓存
            context_manager.loaded_contexts["test_project"] = story_context
            context_manager.dialogue_histories["test_project"] = Mock()
            
            # 验证缓存存在
            assert "test_project" in context_manager.loaded_contexts
            assert "test_project" in context_manager.dialogue_histories
            
            # 清除缓存
            context_manager.clear_project_cache("test_project")
            
            # 验证缓存已清除
            assert "test_project" not in context_manager.loaded_contexts
            assert "test_project" not in context_manager.dialogue_histories
    
    def test_context_statistics(self):
        """测试上下文统计"""
        context_manager = ContextManager()
        
        # 测试未加载的项目
        stats = context_manager.get_context_statistics("nonexistent_project")
        assert "error" in stats
        
        # 测试已加载的项目
        story_context = StoryContext("测试剧集", "现代剧", "现代都市", "当代")
        story_context.key_themes = ["爱情", "职场"]
        story_context.cultural_notes = ["现代背景"]
        story_context.key_terms = {"医生": "doctor", "护士": "nurse"}
        
        from models.story_models import CharacterRelation
        character = CharacterRelation("张三", "主角", "医生")
        story_context.add_character(character)
        
        context_manager.loaded_contexts["test_project"] = story_context
        
        stats = context_manager.get_context_statistics("test_project")
        
        assert stats["project_id"] == "test_project"
        assert stats["title"] == "测试剧集"
        assert stats["genre"] == "现代剧"
        assert stats["characters_count"] == 1
        assert "张三" in stats["characters"]
        assert "爱情" in stats["key_themes"]
        assert "现代背景" in stats["cultural_notes"]
        assert stats["key_terms_count"] == 2


def test_global_context_manager():
    """测试全局上下文管理器"""
    manager = get_context_manager()
    assert isinstance(manager, ContextManager)
    
    # 多次调用应该返回同一个实例
    manager2 = get_context_manager()
    assert manager is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])