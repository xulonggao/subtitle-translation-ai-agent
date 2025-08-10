#!/usr/bin/env python3
"""
上下文管理器演示脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import setup_logging, get_logger
from agents.context_manager import get_context_manager
from models.subtitle_models import SubtitleEntry, TimeCode, SceneEmotion


def main():
    """演示上下文管理器功能"""
    
    # 设置日志
    setup_logging()
    logger = get_logger("demo")
    
    print("🧠 上下文管理器演示")
    print("=" * 50)
    
    # 获取上下文管理器
    context_manager = get_context_manager()
    
    # 演示1: 加载项目上下文
    print("\n📖 加载项目上下文:")
    try:
        # 尝试加载love_navy_blue项目
        project_id = "love_navy_blue"
        story_context = context_manager.load_project_context(project_id)
        
        print(f"✅ 成功加载项目: {story_context.title}")
        print(f"类型: {story_context.genre}")
        print(f"背景: {story_context.setting}")
        print(f"主要人物: {list(story_context.main_characters.keys())}")
        print(f"主题: {story_context.key_themes}")
        print(f"文化要点: {story_context.cultural_notes}")
        
        # 显示人物详情
        print(f"\n👥 人物关系详情:")
        for char_name, character in story_context.main_characters.items():
            print(f"  📝 {char_name}:")
            print(f"     角色: {character.role}")
            print(f"     职业: {character.profession}")
            print(f"     性格: {', '.join(character.personality_traits[:3])}")
            print(f"     说话风格: {character.speaking_style}")
            print(f"     称谓: {', '.join(character.titles[:3])}")
            
            # 显示关系
            if character.relationships:
                relationships = []
                for other_char, rel_config in character.relationships.items():
                    rel_desc = f"{other_char}({rel_config.relationship_type.value})"
                    relationships.append(rel_desc)
                print(f"     关系: {', '.join(relationships[:3])}")
            print()
        
    except Exception as e:
        print(f"❌ 加载项目上下文失败: {e}")
        print("这可能是因为项目配置文件不存在或格式不正确")
    
    # 演示2: 说话人上下文分析
    print("\n🎭 说话人上下文分析:")
    try:
        # 创建测试字幕条目
        entries = [
            SubtitleEntry(1, TimeCode(0, 1, 59, 959), TimeCode(0, 2, 0, 760), 
                         "参谋长同志", scene_emotion=SceneEmotion.TENSE),
            SubtitleEntry(2, TimeCode(0, 2, 0, 760), TimeCode(0, 2, 2, 599), 
                         "我部已经到达指定海域", scene_emotion=SceneEmotion.NEUTRAL),
            SubtitleEntry(3, TimeCode(0, 2, 3, 239), TimeCode(0, 2, 6, 0), 
                         "司令 我军各部已经准备就绪", scene_emotion=SceneEmotion.TENSE),
        ]
        
        # 分析每个条目的上下文
        for i, entry in enumerate(entries):
            print(f"  条目 {entry.index}:")
            print(f"    文本: {entry.text}")
            
            # 获取说话人上下文
            context = context_manager.get_speaker_context(project_id, entry, entries[:i])
            
            print(f"    推断说话人: {context.get('speaker', '未知')}")
            print(f"    场景情感: {context['scene_emotion']}")
            print(f"    语速: {context['speech_pace']}")
            
            if context.get('speaker_info'):
                speaker_info = context['speaker_info']
                print(f"    说话人信息: {speaker_info.get('role', '未知')} - {speaker_info.get('profession', '未知')}")
                if speaker_info.get('personality_traits'):
                    print(f"    性格特点: {', '.join(speaker_info['personality_traits'][:2])}")
            
            if context.get('addressee'):
                print(f"    对话对象: {context['addressee']}")
            
            if context.get('relationship'):
                rel = context['relationship']
                print(f"    关系: {rel['type']} (正式程度: {rel['formality']})")
            
            print()
    
    except Exception as e:
        print(f"❌ 上下文分析失败: {e}")
    
    # 演示3: 文化适配上下文
    print("\n🌍 文化适配上下文:")
    try:
        target_languages = ["en", "ja", "ko"]
        
        for lang in target_languages:
            adaptation_context = context_manager.get_cultural_adaptation_context(project_id, lang)
            
            print(f"  🌐 {lang.upper()} 适配:")
            print(f"    类型: {adaptation_context['genre']}")
            print(f"    背景: {adaptation_context['setting']}")
            print(f"    主题: {', '.join(adaptation_context['key_themes'][:3])}")
            print(f"    文化要点: {', '.join(adaptation_context['cultural_notes'][:3])}")
            print()
    
    except Exception as e:
        print(f"❌ 文化适配上下文获取失败: {e}")
    
    # 演示4: 代词解析
    print("\n🔤 代词解析演示:")
    try:
        test_contexts = [
            {
                "text": "他说得对，我们应该立即行动。",
                "speaker": "伍肆",
                "addressee": "参谋长",
                "dialogue_history": {"recent_speakers": ["伍肆", "参谋长"]}
            },
            {
                "text": "她是一位优秀的记者。",
                "speaker": "宗卿",
                "addressee": "唐歆",
                "dialogue_history": {"recent_speakers": ["宗卿", "唐歆"]}
            }
        ]
        
        for i, test_context in enumerate(test_contexts, 1):
            original_text = test_context["text"]
            resolved_text = context_manager.resolve_pronouns(project_id, original_text, test_context)
            
            print(f"  测试 {i}:")
            print(f"    原文: {original_text}")
            print(f"    说话人: {test_context['speaker']}")
            print(f"    对话对象: {test_context['addressee']}")
            print(f"    解析后: {resolved_text}")
            print()
    
    except Exception as e:
        print(f"❌ 代词解析失败: {e}")
    
    # 演示5: 对话上下文更新
    print("\n💬 对话上下文更新:")
    try:
        # 模拟对话序列
        dialogue_entries = [
            SubtitleEntry(1, TimeCode(0, 0, 1, 0), TimeCode(0, 0, 3, 0), "你好，参谋长", speaker="伍肆"),
            SubtitleEntry(2, TimeCode(0, 0, 4, 0), TimeCode(0, 0, 6, 0), "情况如何？", speaker="参谋长"),
            SubtitleEntry(3, TimeCode(0, 0, 7, 0), TimeCode(0, 0, 9, 0), "一切准备就绪", speaker="伍肆"),
        ]
        
        print("  对话序列:")
        for entry in dialogue_entries:
            context_manager.update_dialogue_context(project_id, entry)
            print(f"    {entry.speaker}: {entry.text}")
        
        # 获取对话历史
        if project_id in context_manager.dialogue_histories:
            dialogue_context = context_manager.dialogue_histories[project_id]
            print(f"\n  对话历史:")
            print(f"    参与者: {', '.join(dialogue_context.previous_speakers)}")
            print(f"    上下文窗口长度: {len(dialogue_context.context_window)}")
            print(f"    最近对话: {dialogue_context.get_context_summary()}")
    
    except Exception as e:
        print(f"❌ 对话上下文更新失败: {e}")
    
    # 演示6: 上下文统计
    print("\n📊 上下文统计:")
    try:
        stats = context_manager.get_context_statistics(project_id)
        
        if "error" not in stats:
            print(f"  项目: {stats['title']}")
            print(f"  类型: {stats['genre']}")
            print(f"  人物数量: {stats['characters_count']}")
            print(f"  主要人物: {', '.join(stats['characters'][:5])}")
            print(f"  主题: {', '.join(stats['key_themes'])}")
            print(f"  关键术语数量: {stats['key_terms_count']}")
            
            if stats['professional_vocabulary']:
                print(f"  专业词汇:")
                for category, terms in stats['professional_vocabulary'].items():
                    print(f"    {category}: {len(terms)}个术语")
        else:
            print(f"  ❌ {stats['error']}")
    
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")
    
    print("\n✅ 上下文管理器演示完成!")
    print("\n💡 上下文管理器特点:")
    print("  - 自动加载项目特定的故事上下文")
    print("  - 智能推断说话人和对话对象")
    print("  - 分析人物关系和对话情境")
    print("  - 提供文化适配上下文信息")
    print("  - 支持代词解析和指代消解")
    print("  - 维护对话历史和上下文窗口")
    
    print("\n🚀 下一步开发:")
    print("  - 知识库数据结构设计")
    print("  - SRT文件解析Agent")
    print("  - 翻译Agent群开发")
    print("  - 质量控制Agent")


if __name__ == "__main__":
    main()