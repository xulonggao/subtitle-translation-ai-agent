#!/usr/bin/env python3
"""
快速开始：字幕翻译Agent
最简单的使用示例
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "strands_agents"))

def quick_translate():
    """快速翻译示例"""
    
    print("🚀 快速字幕翻译")
    print("=" * 30)
    
    # 导入Agent
    try:
        from strands_agents.subtitle_translation_agent import create_subtitle_translation_agent
        print("✅ 导入成功")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return
    
    # 创建Agent
    try:
        print("📝 创建Agent...")
        agent = create_subtitle_translation_agent()
        print("✅ Agent创建成功")
    except Exception as e:
        print(f"❌ Agent创建失败: {e}")
        print("请检查AWS配置和网络连接")
        return
    
    # 示例SRT内容
    srt_content = """1
00:00:01,000 --> 00:00:03,000
参谋长同志，我部已经到达指定海域

2
00:00:04,000 --> 00:00:06,000
现在的家长都在鸡娃，内卷太严重了"""
    
    # 执行翻译
    try:
        print("🔄 开始翻译...")
        result = agent.translate_subtitle_file(
            srt_content=srt_content,
            target_language="en",
            additional_context="现代军旅剧《爱上海军蓝》"
        )
        
        if result["success"]:
            print("✅ 翻译成功！")
            print("\n📄 结果预览:")
            print("-" * 20)
            # 显示翻译结果的前200个字符
            if "exported_srt" in result:
                preview = result["exported_srt"][:200]
                print(preview + "..." if len(result["exported_srt"]) > 200 else preview)
        else:
            print(f"❌ 翻译失败: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ 翻译错误: {e}")

if __name__ == "__main__":
    quick_translate()