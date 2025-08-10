#!/usr/bin/env python3
"""
项目管理系统演示脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import setup_logging, get_logger
from agents.project_manager import ProjectManager, get_project_manager


def main():
    """演示项目管理系统功能"""
    
    # 设置日志
    setup_logging()
    logger = get_logger("demo")
    
    print("📁 项目管理系统演示")
    print("=" * 50)
    
    # 获取项目管理器
    manager = get_project_manager()
    
    # 显示当前项目列表
    print("\n📋 当前项目列表:")
    projects = manager.list_projects()
    if projects:
        for project in projects:
            print(f"  📂 {project.project_id}")
            print(f"     标题: {project.project_title}")
            print(f"     类型: {project.genre}")
            print(f"     状态: {project.status}")
            print(f"     创建时间: {project.created_at}")
            print()
    else:
        print("  暂无项目")
    
    # 演示创建新项目
    print("\n🆕 创建演示项目:")
    demo_project_id = "demo_project_2024"
    
    try:
        # 检查项目是否已存在
        existing_project = manager.get_project(demo_project_id)
        if existing_project:
            print(f"  项目 {demo_project_id} 已存在，跳过创建")
        else:
            # 创建新项目
            print(f"  创建项目: {demo_project_id}")
            new_project = manager.create_project(
                project_id=demo_project_id,
                project_title="演示项目2024",
                genre="现代剧",
                description="这是一个用于演示的测试项目"
            )
            
            print(f"  ✅ 项目创建成功!")
            print(f"     ID: {new_project.project_id}")
            print(f"     标题: {new_project.project_title}")
            print(f"     类型: {new_project.genre}")
            print(f"     描述: {new_project.description}")
            
    except Exception as e:
        print(f"  ❌ 创建项目失败: {e}")
    
    # 演示加载项目上下文
    print(f"\n📖 加载项目上下文:")
    try:
        # 使用love_navy_blue项目作为示例
        test_project_id = "love_navy_blue"
        context = manager.load_project_context(test_project_id)
        
        print(f"  项目: {test_project_id}")
        print(f"  上下文组件: {list(context.keys())}")
        
        # 显示人物关系信息
        if "character_relations" in context:
            char_data = context["character_relations"]
            if "characters" in char_data:
                print(f"  主要人物: {list(char_data['characters'].keys())}")
        
        # 显示术语库信息
        if "terminology" in context:
            term_data = context["terminology"]
            term_categories = [k for k in term_data.keys() if k.endswith("_terms")]
            print(f"  术语类别: {term_categories}")
            
    except Exception as e:
        print(f"  ❌ 加载上下文失败: {e}")
        print(f"  这是正常的，如果项目不存在的话")
    
    # 演示项目验证
    print(f"\n🔍 项目结构验证:")
    try:
        validation = manager.validate_project_structure("love_navy_blue")
        print("  love_navy_blue项目结构:")
        for file_name, exists in validation.items():
            status = "✅" if exists else "❌"
            print(f"    {status} {file_name}")
            
    except Exception as e:
        print(f"  ❌ 验证失败: {e}")
    
    # 演示项目管理操作
    print(f"\n⚙️ 项目管理操作演示:")
    if demo_project_id in [p.project_id for p in manager.list_projects()]:
        try:
            # 更新项目
            print("  更新项目描述...")
            updated_project = manager.update_project(
                demo_project_id,
                description="更新后的项目描述 - " + str(len(projects))
            )
            print(f"  ✅ 项目描述已更新: {updated_project.description}")
            
            # 归档项目
            print("  归档项目...")
            manager.archive_project(demo_project_id)
            archived_project = manager.get_project(demo_project_id)
            print(f"  ✅ 项目状态: {archived_project.status}")
            
            # 恢复项目
            print("  恢复项目...")
            manager.restore_project(demo_project_id)
            restored_project = manager.get_project(demo_project_id)
            print(f"  ✅ 项目状态: {restored_project.status}")
            
        except Exception as e:
            print(f"  ❌ 操作失败: {e}")
    
    # 显示项目目录结构
    print(f"\n📁 项目目录结构:")
    projects_root = manager.projects_root
    print(f"  根目录: {projects_root}")
    
    if projects_root.exists():
        for item in projects_root.iterdir():
            if item.is_dir() and item.name != "__pycache__":
                print(f"  📂 {item.name}/")
                # 显示项目文件
                for subitem in item.iterdir():
                    if subitem.is_file():
                        print(f"    📄 {subitem.name}")
                    elif subitem.is_dir():
                        print(f"    📂 {subitem.name}/")
    
    print("\n✅ 演示完成!")
    print("\n💡 使用说明:")
    print("  1. 使用CLI工具: python cli.py create-project <项目名>")
    print("  2. 编辑项目文件: projects/<项目名>/story_context.md")
    print("  3. 上传SRT文件到: projects/<项目名>/episodes/")
    print("  4. 运行翻译任务")


if __name__ == "__main__":
    main()