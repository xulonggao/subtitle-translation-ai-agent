#!/usr/bin/env python3
"""
简化测试脚本 - 不依赖外部库
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))


def test_project_structure():
    """测试项目结构"""
    print("📁 测试项目结构...")
    
    required_dirs = [
        "agents",
        "config", 
        "projects",
        "shared_resources",
        "tests",
        "docs"
    ]
    
    required_files = [
        "README.md",
        "requirements.txt",
        "main.py",
        "cli.py",
        ".gitignore",
        ".env.example"
    ]
    
    all_good = True
    
    # 检查目录
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ (缺失)")
            all_good = False
    
    # 检查文件
    for file_name in required_files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"  ✅ {file_name}")
        else:
            print(f"  ❌ {file_name} (缺失)")
            all_good = False
    
    return all_good


def test_config_files():
    """测试配置文件"""
    print("\n⚙️ 测试配置文件...")
    
    config_files = [
        "config/__init__.py",
        "config/config.py",
        "config/logging_config.py"
    ]
    
    all_good = True
    
    for file_name in config_files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"  ✅ {file_name}")
            
            # 检查文件内容
            try:
                content = file_path.read_text(encoding='utf-8')
                if len(content) > 100:  # 基本内容检查
                    print(f"    📄 内容正常 ({len(content)} 字符)")
                else:
                    print(f"    ⚠️ 内容较少 ({len(content)} 字符)")
            except Exception as e:
                print(f"    ❌ 读取失败: {e}")
                all_good = False
        else:
            print(f"  ❌ {file_name} (缺失)")
            all_good = False
    
    return all_good


def test_agent_files():
    """测试Agent文件"""
    print("\n🤖 测试Agent文件...")
    
    agent_files = [
        "agents/__init__.py",
        "agents/model_manager.py",
        "agents/project_manager.py"
    ]
    
    all_good = True
    
    for file_name in agent_files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"  ✅ {file_name}")
            
            # 检查关键类是否存在
            try:
                content = file_path.read_text(encoding='utf-8')
                if "model_manager.py" in file_name:
                    if "ModelFallbackManager" in content:
                        print(f"    📋 包含 ModelFallbackManager 类")
                    else:
                        print(f"    ❌ 缺少 ModelFallbackManager 类")
                        all_good = False
                elif "project_manager.py" in file_name:
                    if "ProjectManager" in content:
                        print(f"    📋 包含 ProjectManager 类")
                    else:
                        print(f"    ❌ 缺少 ProjectManager 类")
                        all_good = False
            except Exception as e:
                print(f"    ❌ 检查失败: {e}")
                all_good = False
        else:
            print(f"  ❌ {file_name} (缺失)")
            all_good = False
    
    return all_good


def test_project_template():
    """测试项目模板"""
    print("\n📋 测试项目模板...")
    
    template_dir = Path("projects/project_template")
    if not template_dir.exists():
        print("  ❌ 项目模板目录不存在")
        return False
    
    template_files = [
        "README.md",
        "story_context.md",
        "character_relations.json",
        "terminology.json"
    ]
    
    all_good = True
    
    for file_name in template_files:
        file_path = template_dir / file_name
        if file_path.exists():
            print(f"  ✅ {file_name}")
            
            # 检查JSON文件格式
            if file_name.endswith('.json'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    print(f"    📄 JSON格式正确")
                except json.JSONDecodeError as e:
                    print(f"    ❌ JSON格式错误: {e}")
                    all_good = False
        else:
            print(f"  ❌ {file_name} (缺失)")
            all_good = False
    
    return all_good


def test_love_navy_blue_project():
    """测试爱上海军蓝项目配置"""
    print("\n🎬 测试爱上海军蓝项目...")
    
    project_dir = Path("projects/love_navy_blue")
    if not project_dir.exists():
        print("  ❌ 爱上海军蓝项目目录不存在")
        return False
    
    project_files = [
        "story_context.md",
        "character_relations.json",
        "terminology.json"
    ]
    
    all_good = True
    
    for file_name in project_files:
        file_path = project_dir / file_name
        if file_path.exists():
            print(f"  ✅ {file_name}")
            
            # 检查特定内容
            try:
                if file_name == "character_relations.json":
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if "characters" in data:
                        characters = list(data["characters"].keys())
                        print(f"    👥 人物: {', '.join(characters[:3])}...")
                    
                    if "project_info" in data:
                        project_info = data["project_info"]
                        print(f"    📋 项目ID: {project_info.get('project_id', 'N/A')}")
                
                elif file_name == "story_context.md":
                    content = file_path.read_text(encoding='utf-8')
                    if "爱上海军蓝" in content:
                        print(f"    📖 包含剧名信息")
                    if "伍肆" in content or "唐歆" in content:
                        print(f"    👤 包含人物信息")
                        
            except Exception as e:
                print(f"    ❌ 内容检查失败: {e}")
                all_good = False
        else:
            print(f"  ❌ {file_name} (缺失)")
            all_good = False
    
    return all_good


def test_shared_resources():
    """测试共享资源"""
    print("\n🌐 测试共享资源...")
    
    shared_files = [
        "shared_resources/__init__.py",
        "shared_resources/global_terminology.json"
    ]
    
    all_good = True
    
    for file_name in shared_files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"  ✅ {file_name}")
            
            if file_name.endswith('.json'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if "global_terminology.json" in file_name:
                        categories = list(data.keys())
                        print(f"    📚 术语类别: {', '.join(categories[:3])}...")
                        
                except Exception as e:
                    print(f"    ❌ JSON检查失败: {e}")
                    all_good = False
        else:
            print(f"  ❌ {file_name} (缺失)")
            all_good = False
    
    return all_good


def main():
    """运行简化测试"""
    print("🧪 影视剧字幕翻译Agent系统 - 简化测试")
    print("=" * 60)
    
    tests = [
        ("项目结构", test_project_structure),
        ("配置文件", test_config_files),
        ("Agent文件", test_agent_files),
        ("项目模板", test_project_template),
        ("爱上海军蓝项目", test_love_navy_blue_project),
        ("共享资源", test_shared_resources)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ 测试 {test_name} 失败: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n📊 测试结果总结:")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！基础架构搭建成功！")
        
        print("\n✅ 已完成的功能:")
        print("  - 项目目录结构")
        print("  - 配置管理系统")
        print("  - 模型容错管理器")
        print("  - 项目管理系统")
        print("  - 项目模板系统")
        print("  - 爱上海军蓝示例项目")
        print("  - 全局术语库")
        print("  - CLI工具")
        
        print("\n🚀 下一步开发:")
        print("  - 安装依赖: pip install -r requirements.txt")
        print("  - 运行完整测试: python run_tests.py")
        print("  - 开始开发核心数据模型")
        
        return 0
    else:
        print("⚠️ 部分测试失败，请检查上述问题")
        return 1


if __name__ == "__main__":
    sys.exit(main())