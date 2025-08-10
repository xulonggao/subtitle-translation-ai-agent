#!/usr/bin/env python3
"""
使用真实SRT文件测试数据模型
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from models.subtitle_models import TimeCode, SubtitleEntry, SubtitleFile, SubtitleFormat


def parse_srt_file(filepath: str) -> SubtitleFile:
    """解析SRT文件"""
    entries = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # 按空行分割条目
        blocks = content.split('\n\n')
        
        for block in blocks:
            if not block.strip():
                continue
            
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            
            try:
                # 解析索引
                index = int(lines[0])
                
                # 解析时间码
                time_line = lines[1]
                if ' --> ' not in time_line:
                    continue
                
                start_str, end_str = time_line.split(' --> ')
                start_time = TimeCode.from_string(start_str.strip())
                end_time = TimeCode.from_string(end_str.strip())
                
                # 解析文本（可能有多行）
                text = '\n'.join(lines[2:])
                
                entry = SubtitleEntry(
                    index=index,
                    start_time=start_time,
                    end_time=end_time,
                    text=text
                )
                
                entries.append(entry)
                
            except Exception as e:
                print(f"解析条目失败: {block[:50]}... 错误: {e}")
                continue
        
        return SubtitleFile(
            filename=Path(filepath).name,
            format=SubtitleFormat.SRT,
            entries=entries
        )
        
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None


def main():
    """测试真实SRT文件"""
    print("📄 真实SRT文件测试")
    print("=" * 40)
    
    # 查找SRT文件
    srt_files = []
    
    # 检查项目中的SRT文件
    project_dirs = [
        "../Tasks/Agentic_Translation/短剧1-爱上海军蓝",
        "projects/love_navy_blue/episodes"
    ]
    
    for project_dir in project_dirs:
        project_path = Path(project_dir)
        if project_path.exists():
            srt_files.extend(project_path.glob("*.srt"))
    
    if not srt_files:
        print("❌ 未找到SRT文件")
        print("请将SRT文件放在以下位置之一:")
        for dir_path in project_dirs:
            print(f"  - {dir_path}")
        return
    
    # 测试第一个找到的SRT文件
    srt_file = srt_files[0]
    print(f"📁 测试文件: {srt_file}")
    
    # 解析文件
    subtitle_file = parse_srt_file(str(srt_file))
    
    if not subtitle_file:
        print("❌ 解析失败")
        return
    
    print(f"✅ 解析成功!")
    print(f"文件名: {subtitle_file.filename}")
    print(f"条目数: {subtitle_file.total_entries}")
    print(f"总时长: {subtitle_file.total_duration:.2f}秒")
    print(f"平均阅读速度: {subtitle_file.average_reading_speed:.2f} 字符/秒")
    
    # 显示前几个条目
    print(f"\n📝 前5个条目:")
    for i, entry in enumerate(subtitle_file.entries[:5]):
        print(f"  {entry.index}. [{entry.start_time} --> {entry.end_time}]")
        print(f"     {entry.text}")
        print(f"     时长: {entry.duration_seconds:.1f}秒, 字符数: {entry.character_count}, 阅读速度: {entry.calculate_reading_speed():.1f}")
        print()
    
    # 检查阅读速度问题
    problematic = subtitle_file.get_problematic_entries(7.5)
    if problematic:
        print(f"⚠️ 发现 {len(problematic)} 个阅读速度过快的条目:")
        for entry in problematic[:3]:  # 只显示前3个
            print(f"  条目{entry.index}: {entry.calculate_reading_speed():.1f} 字符/秒")
            print(f"    {entry.text[:30]}...")
    else:
        print("✅ 所有条目的阅读速度都合适")
    
    # 获取统计信息
    stats = subtitle_file.get_statistics()
    print(f"\n📊 统计信息:")
    print(f"  总条目数: {stats['total_entries']}")
    print(f"  总时长: {stats['total_duration']:.1f}秒")
    print(f"  平均阅读速度: {stats['average_reading_speed']:.1f} 字符/秒")
    print(f"  情感分布: {stats['emotion_distribution']}")
    
    # 测试SRT输出
    print(f"\n💾 测试SRT输出:")
    output_content = subtitle_file.to_srt_content()
    print(f"输出长度: {len(output_content)} 字符")
    
    # 保存测试输出
    output_file = "test_output.srt"
    subtitle_file.save_to_file(output_file)
    print(f"✅ 已保存到: {output_file}")
    
    print(f"\n🎉 真实SRT文件测试完成!")


if __name__ == "__main__":
    main()