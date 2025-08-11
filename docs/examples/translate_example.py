#!/usr/bin/env python3
"""
字幕翻译Agent使用示例
演示如何使用Strands Agent SDK进行字幕翻译
"""

import os
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "strands_agents"))

from strands_agents.subtitle_translation_agent import create_subtitle_translation_agent

def main():
    """主函数：演示字幕翻译流程"""
    
    print("🎬 字幕翻译Agent演示")
    print("=" * 50)
    
    # 第一步：创建Agent
    print("\n📝 步骤1: 创建字幕翻译Agent...")
    try:
        agent = create_subtitle_translation_agent()
        print("✅ Agent创建成功！")
        
        # 显示Agent信息
        info = agent.get_agent_info()
        print(f"   - Agent版本: {info['version']}")
        print(f"   - 主模型: {info['primary_model']['model_id']}")
        print(f"   - 备用模型: {info['fallback_model']['model_id']}")
        print(f"   - 支持语言: {len(info['supported_languages'])}种")
        
    except Exception as e:
        print(f"❌ Agent创建失败: {e}")
        print("\n🔧 请检查:")
        print("   1. AWS凭证是否配置正确")
        print("   2. 是否有Bedrock模型访问权限")
        print("   3. 网络连接是否正常")
        return
    
    # 第二步：读取SRT文件
    print("\n📝 步骤2: 读取示例SRT文件...")
    srt_file = "example_subtitle.srt"
    
    if not os.path.exists(srt_file):
        print(f"❌ 找不到文件: {srt_file}")
        return
    
    with open(srt_file, 'r', encoding='utf-8') as f:
        srt_content = f.read()
    
    print(f"✅ 成功读取文件: {srt_file}")
    print(f"   - 文件大小: {len(srt_content)} 字符")
    
    # 第三步：选择目标语言
    print("\n📝 步骤3: 选择目标语言...")
    supported_languages = agent.get_supported_languages()
    
    print("支持的语言:")
    for code, name in supported_languages.items():
        print(f"   {code}: {name}")
    
    # 默认翻译到英语
    target_language = "en"
    print(f"\n🎯 目标语言: {target_language} ({supported_languages[target_language]})")
    
    # 第四步：设置翻译上下文
    print("\n📝 步骤4: 设置翻译上下文...")
    additional_context = """
    剧集信息：《爱上海军蓝》
    类型：现代军旅浪漫剧
    背景：现代中国海军生活
    主要角色：
    - 张伟：海军队长，严肃负责
    - 李小红：军医，温柔专业
    特殊词汇：包含军事术语和现代网络词汇
    """
    
    translation_config = {
        "genre": "military_romance",
        "audience": "adult",
        "cultural_adaptation_level": "high",
        "preserve_military_terminology": True
    }
    
    print("✅ 上下文配置完成")
    
    # 第五步：执行翻译
    print("\n📝 步骤5: 执行翻译...")
    print("⏳ 正在翻译，请稍候...")
    
    try:
        result = agent.translate_subtitle_file(
            srt_content=srt_content,
            target_language=target_language,
            additional_context=additional_context,
            translation_config=translation_config
        )
        
        if result["success"]:
            print("✅ 翻译成功完成！")
            
            # 第六步：保存结果
            print("\n📝 步骤6: 保存翻译结果...")
            
            output_file = f"example_subtitle_{target_language}.srt"
            
            # 从结果中提取SRT内容
            if "exported_srt" in result:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result["exported_srt"])
                print(f"✅ 翻译结果已保存到: {output_file}")
            
            # 显示翻译质量报告
            if "quality_report" in result:
                print("\n📊 翻译质量报告:")
                print(result["quality_report"])
            
            # 显示部分翻译结果
            print("\n🎬 翻译预览:")
            print("-" * 40)
            if "translation_result" in result:
                print(result["translation_result"][:500] + "..." if len(result["translation_result"]) > 500 else result["translation_result"])
            
        else:
            print(f"❌ 翻译失败: {result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 翻译过程中发生错误: {e}")
        print("\n🔧 可能的解决方案:")
        print("   1. 检查网络连接")
        print("   2. 验证AWS Bedrock权限")
        print("   3. 确认模型可用性")
        return
    
    print("\n🎉 演示完成！")
    print("\n📚 更多功能:")
    print("   - 批量多语言翻译: agent.batch_translate_multiple_languages()")
    print("   - 翻译策略优化: agent.optimize_translation_strategy()")
    print("   - 支持的语言列表: agent.get_supported_languages()")

def test_agent_creation():
    """测试Agent创建"""
    print("🧪 测试Agent创建...")
    
    try:
        agent = create_subtitle_translation_agent()
        print("✅ Agent创建测试通过")
        
        info = agent.get_agent_info()
        print(f"   Agent版本: {info['version']}")
        
        languages = agent.get_supported_languages()
        print(f"   支持语言数量: {len(languages)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent创建测试失败: {e}")
        return False

if __name__ == "__main__":
    # 可以选择运行完整演示或仅测试Agent创建
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_agent_creation()
    else:
        main()