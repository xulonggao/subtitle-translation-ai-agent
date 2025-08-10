#!/usr/bin/env python3
"""
数据模型演示脚本
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from models.subtitle_models import (
    TimeCode, SubtitleEntry, SubtitleFile, TranslationResult,
    SubtitleFormat, SceneEmotion, SpeechPace
)
from models.story_models import (
    CharacterRelation, StoryContext, RelationshipType,
    FormalityLevel, RespectLevel
)
from models.translation_models import (
    TranslationTask, TranslationMemory, TerminologyEntry,
    TranslationStatus, TranslationMethod
)


def demo_timecode():
    """演示时间码功能"""
    print("⏰ 时间码演示")
    print("-" * 30)
    
    # 创建时间码
    tc1 = TimeCode(1, 23, 45, 678)
    print(f"时间码1: {tc1}")
    
    # 从字符串解析
    tc2 = TimeCode.from_string("00:01:30,500")
    print(f"时间码2: {tc2}")
    
    # 时间码比较
    print(f"tc1 > tc2: {tc1 > tc2}")
    
    # 毫秒转换
    ms = tc1.to_milliseconds()
    print(f"tc1转毫秒: {ms}")
    
    tc3 = TimeCode.from_milliseconds(ms)
    print(f"从毫秒恢复: {tc3}")
    print(f"是否相等: {tc1 == tc3}")
    print()


def demo_subtitle_entry():
    """演示字幕条目功能"""
    print("📝 字幕条目演示")
    print("-" * 30)
    
    # 创建字幕条目
    start = TimeCode(0, 0, 1, 0)
    end = TimeCode(0, 0, 3, 500)
    entry = SubtitleEntry(
        index=1,
        start_time=start,
        end_time=end,
        text="参谋长同志，我部已经到达指定海域",
        speaker="伍肆",
        scene_emotion=SceneEmotion.TENSE,
        speech_pace=SpeechPace.NORMAL
    )
    
    print(f"字幕条目: {entry.index}")
    print(f"时间: {entry.start_time} --> {entry.end_time}")
    print(f"文本: {entry.text}")
    print(f"说话人: {entry.speaker}")
    print(f"时长: {entry.duration_seconds}秒")
    print(f"字符数: {entry.character_count}")
    print(f"阅读速度: {entry.calculate_reading_speed():.2f} 字符/秒")
    print(f"阅读速度合适: {entry.is_reading_speed_appropriate()}")
    
    # 添加翻译
    entry.set_translation("en", "Chief of Staff, our unit has reached the designated waters", 0.9)
    entry.set_translation("ja", "参謀長同志、我が部隊は指定海域に到達しました", 0.8)
    
    print(f"英语翻译: {entry.get_translation('en')}")
    print(f"日语翻译: {entry.get_translation('ja')}")
    
    # SRT格式输出
    print("\nSRT格式:")
    print(entry.to_srt_format())
    print("英语SRT格式:")
    print(entry.to_srt_format("en"))
    print()


def demo_subtitle_file():
    """演示字幕文件功能"""
    print("📄 字幕文件演示")
    print("-" * 30)
    
    # 创建多个字幕条目
    entries = [
        SubtitleEntry(1, TimeCode(0, 1, 59, 959), TimeCode(0, 2, 0, 760), "参谋长同志"),
        SubtitleEntry(2, TimeCode(0, 2, 0, 760), TimeCode(0, 2, 2, 599), "我部已经到达指定海域"),
        SubtitleEntry(3, TimeCode(0, 2, 3, 239), TimeCode(0, 2, 6, 0), "司令 我军各部已经准备就绪"),
    ]
    
    # 创建字幕文件
    subtitle_file = SubtitleFile(
        filename="爱上海军蓝_01.srt",
        format=SubtitleFormat.SRT,
        entries=entries,
        title="爱上海军蓝 第1集",
        language="zh"
    )
    
    print(f"文件名: {subtitle_file.filename}")
    print(f"格式: {subtitle_file.format.value}")
    print(f"条目数: {subtitle_file.total_entries}")
    print(f"总时长: {subtitle_file.total_duration:.2f}秒")
    print(f"平均阅读速度: {subtitle_file.average_reading_speed:.2f} 字符/秒")
    
    # 获取统计信息
    stats = subtitle_file.get_statistics()
    print(f"统计信息: {stats}")
    
    # 按时间范围获取条目
    range_entries = subtitle_file.get_entries_by_timerange(
        TimeCode(0, 2, 0, 0), TimeCode(0, 2, 3, 0)
    )
    print(f"2:00-2:03时间段条目数: {len(range_entries)}")
    print()


def demo_character_relation():
    """演示人物关系功能"""
    print("👥 人物关系演示")
    print("-" * 30)
    
    # 创建人物
    wusi = CharacterRelation(
        name="伍肆",
        role="海军陆战队中队长",
        profession="军人",
        personality_traits=["责任感强", "担当", "军人作风"],
        speaking_style="简洁有力，军人风格"
    )
    
    tangxin = CharacterRelation(
        name="唐歆",
        role="职场女记者",
        profession="记者",
        personality_traits=["独立自主", "追求英雄主义", "职业敏感"],
        speaking_style="直接坦率，职业化表达"
    )
    
    # 设置名称翻译
    wusi.set_name_translation("en", "Wu Si")
    wusi.set_name_translation("ja", "ウー・スー")
    tangxin.set_name_translation("en", "Tang Xin")
    tangxin.set_name_translation("ja", "タン・シン")
    
    # 建立关系
    wusi.add_relationship(
        "唐歆", 
        RelationshipType.SOCIAL_LOVER,
        FormalityLevel.LOW,
        RespectLevel.EQUAL,
        "intimate"
    )
    
    tangxin.add_relationship(
        "伍肆",
        RelationshipType.SOCIAL_LOVER,
        FormalityLevel.LOW,
        RespectLevel.EQUAL,
        "intimate"
    )
    
    print(f"人物1: {wusi.name} ({wusi.role})")
    print(f"性格: {', '.join(wusi.personality_traits)}")
    print(f"说话风格: {wusi.speaking_style}")
    print(f"英文名: {wusi.get_name_translation('en')}")
    print(f"日文名: {wusi.get_name_translation('ja')}")
    
    print(f"\n人物2: {tangxin.name} ({tangxin.role})")
    print(f"性格: {', '.join(tangxin.personality_traits)}")
    
    # 查看关系
    relationship = wusi.get_relationship("唐歆")
    if relationship:
        print(f"\n{wusi.name}与{tangxin.name}的关系:")
        print(f"关系类型: {relationship.relationship_type.value}")
        print(f"正式程度: {relationship.formality_level.value}")
        print(f"尊敬程度: {relationship.respect_level.value}")
        print(f"称谓风格: {relationship.address_style}")
    print()


def demo_story_context():
    """演示故事上下文功能"""
    print("📖 故事上下文演示")
    print("-" * 30)
    
    # 创建故事上下文
    context = StoryContext(
        title="爱上海军蓝",
        genre="现代军旅剧",
        setting="现代中国海军",
        time_period="当代",
        episode_summary="海军陆战队演习中的救援行动",
        key_themes=["军旅生活", "职场恋情", "个人成长"],
        cultural_notes=["军事题材", "职场恋情", "军民融合"]
    )
    
    # 添加人物
    wusi = CharacterRelation("伍肆", "海军陆战队中队长", "军人")
    wusi.titles = ["队长", "中队长", "伍队"]
    context.add_character(wusi)
    
    canyuzhang = CharacterRelation("参谋长", "参谋长", "高级军官")
    canyuzhang.titles = ["参谋长", "首长"]
    context.add_character(canyuzhang)
    
    # 建立关系
    wusi.add_relationship("参谋长", RelationshipType.MILITARY_SUBORDINATE, 
                         FormalityLevel.VERY_HIGH, RespectLevel.HIGH)
    canyuzhang.add_relationship("伍肆", RelationshipType.MILITARY_COMMANDER,
                               FormalityLevel.HIGH, RespectLevel.MEDIUM)
    
    print(f"剧集: {context.title}")
    print(f"类型: {context.genre}")
    print(f"背景: {context.setting}")
    print(f"主题: {', '.join(context.key_themes)}")
    print(f"主要人物: {list(context.main_characters.keys())}")
    
    # 分析对话上下文
    dialogue_context = context.analyze_dialogue_context("伍肆", "参谋长")
    print(f"\n对话上下文分析:")
    print(f"说话人: {dialogue_context['speaker']['name']} ({dialogue_context['speaker']['role']})")
    if 'addressee' in dialogue_context:
        print(f"对话对象: {dialogue_context['addressee']['name']} ({dialogue_context['addressee']['role']})")
    if 'relationship' in dialogue_context:
        rel = dialogue_context['relationship']
        print(f"关系: {rel['type']} (正式程度: {rel['formality']}, 尊敬程度: {rel['respect']})")
    
    # 获取文化适配提示
    cultural_hints = context.get_cultural_adaptation_hints("en")
    print(f"\n文化适配提示:")
    print(f"类型: {cultural_hints['genre']}")
    print(f"背景: {cultural_hints['setting']}")
    print()


def demo_translation_models():
    """演示翻译模型功能"""
    print("🔄 翻译模型演示")
    print("-" * 30)
    
    # 术语条目
    term = TerminologyEntry(
        source_term="参谋长",
        target_language="en",
        target_term="Chief of Staff",
        context="军事指挥层级",
        domain="military"
    )
    
    print(f"术语: {term.source_term} -> {term.target_term}")
    print(f"领域: {term.domain}")
    print(f"使用次数: {term.usage_count}")
    print(f"置信度: {term.confidence_score}")
    
    # 增加使用次数
    term.increment_usage()
    print(f"使用后次数: {term.usage_count}")
    
    # 翻译记忆
    memory = TranslationMemory(
        source_text="我部已经到达指定海域",
        target_language="en",
        target_text="Our unit has reached the designated waters",
        speaker="伍肆",
        quality_score=0.9
    )
    
    print(f"\n翻译记忆:")
    print(f"原文: {memory.source_text}")
    print(f"译文: {memory.target_text}")
    print(f"说话人: {memory.speaker}")
    print(f"质量分数: {memory.quality_score}")
    
    # 相似度测试
    similar_text = "我部已经到达指定区域"
    similarity = memory.calculate_similarity(similar_text)
    print(f"与'{similar_text}'的相似度: {similarity:.2f}")
    print(f"是否模糊匹配: {memory.is_fuzzy_match(similar_text)}")
    
    # 翻译任务
    entries = [
        SubtitleEntry(1, TimeCode(0, 1, 59, 959), TimeCode(0, 2, 0, 760), "参谋长同志"),
        SubtitleEntry(2, TimeCode(0, 2, 0, 760), TimeCode(0, 2, 2, 599), "我部已经到达指定海域"),
    ]
    
    context = StoryContext("爱上海军蓝", "现代军旅剧", "现代中国海军", "当代")
    
    task = TranslationTask(
        task_id="task_001",
        project_id="love_navy_blue",
        source_language="zh",
        target_languages=["en", "ja"],
        subtitle_entries=entries,
        story_context=context,
        quality_threshold=0.8
    )
    
    print(f"\n翻译任务:")
    print(f"任务ID: {task.task_id}")
    print(f"项目ID: {task.project_id}")
    print(f"源语言: {task.source_language}")
    print(f"目标语言: {', '.join(task.target_languages)}")
    print(f"条目数: {task.total_entries}")
    print(f"状态: {task.status.value}")
    print(f"进度: {task.progress:.1%}")
    
    # 模拟任务进展
    task.start_task()
    print(f"任务开始: {task.status.value}")
    
    task.update_progress(1, 0)
    task.add_quality_score(0.9)
    print(f"进度更新: {task.progress:.1%}, 平均质量: {task.average_quality_score}")
    
    task.complete_task()
    print(f"任务完成: {task.status.value}")
    
    # 获取统计信息
    stats = task.get_statistics()
    print(f"任务统计: 完成{stats['completed_entries']}/{stats['total_entries']}条目")
    print()


def main():
    """主演示函数"""
    print("🎬 影视剧字幕翻译Agent系统 - 数据模型演示")
    print("=" * 60)
    
    try:
        demo_timecode()
        demo_subtitle_entry()
        demo_subtitle_file()
        demo_character_relation()
        demo_story_context()
        demo_translation_models()
        
        print("✅ 数据模型演示完成!")
        print("\n💡 数据模型特点:")
        print("  - 完整的时间码处理和验证")
        print("  - 字幕条目的阅读速度计算")
        print("  - 多语言翻译缓存支持")
        print("  - 复杂的人物关系建模")
        print("  - 上下文感知的对话分析")
        print("  - 翻译记忆和术语管理")
        print("  - 任务状态和进度跟踪")
        
        print("\n🚀 下一步开发:")
        print("  - 文件解析Agent (SRT解析器)")
        print("  - 上下文管理Agent")
        print("  - 翻译Agent群")
        print("  - 质量控制Agent")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()