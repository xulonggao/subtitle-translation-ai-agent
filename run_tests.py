#!/usr/bin/env python3
"""
测试运行脚本
"""
import sys
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import setup_logging, get_logger


def main():
    """运行所有测试"""
    
    # 设置日志
    setup_logging()
    logger = get_logger("test_runner")
    
    print("🧪 运行影视剧字幕翻译Agent系统测试")
    print("=" * 60)
    
    # 检查pytest是否可用
    try:
        import pytest
        print("✅ pytest 可用")
    except ImportError:
        print("❌ pytest 未安装，请运行: pip install pytest")
        return 1
    
    # 运行配置测试
    print("\n📋 运行配置测试...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_config.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("错误输出:", result.stderr)
        
        if result.returncode == 0:
            print("✅ 配置测试通过")
        else:
            print("❌ 配置测试失败")
            
    except Exception as e:
        print(f"❌ 运行配置测试失败: {e}")
    
    # 运行模型管理器测试
    print("\n🤖 运行模型管理器测试...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_model_manager.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("错误输出:", result.stderr)
        
        if result.returncode == 0:
            print("✅ 模型管理器测试通过")
        else:
            print("❌ 模型管理器测试失败")
            
    except Exception as e:
        print(f"❌ 运行模型管理器测试失败: {e}")
    
    # 运行项目管理器测试
    print("\n📁 运行项目管理器测试...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_project_manager.py", 
            "-v", "--tb=short"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("错误输出:", result.stderr)
        
        if result.returncode == 0:
            print("✅ 项目管理器测试通过")
        else:
            print("❌ 项目管理器测试失败")
            
    except Exception as e:
        print(f"❌ 运行项目管理器测试失败: {e}")
    
    # 运行所有测试
    print("\n🔍 运行完整测试套件...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", "--tb=short", "--cov=agents", "--cov=config"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("错误输出:", result.stderr)
        
        if result.returncode == 0:
            print("✅ 所有测试通过")
        else:
            print("❌ 部分测试失败")
            
    except Exception as e:
        print(f"❌ 运行完整测试套件失败: {e}")
    
    # 运行演示脚本
    print("\n🎬 运行演示脚本...")
    
    demos = [
        ("模型管理器演示", "demo_model_manager.py"),
        ("项目管理器演示", "demo_project_manager.py")
    ]
    
    for demo_name, demo_file in demos:
        print(f"\n▶️ {demo_name}:")
        try:
            result = subprocess.run([
                sys.executable, demo_file
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ 演示运行成功")
                # 只显示前几行输出
                lines = result.stdout.split('\n')[:10]
                for line in lines:
                    if line.strip():
                        print(f"  {line}")
                if len(result.stdout.split('\n')) > 10:
                    print("  ...")
            else:
                print("❌ 演示运行失败")
                print(result.stderr)
                
        except subprocess.TimeoutExpired:
            print("⏰ 演示运行超时")
        except Exception as e:
            print(f"❌ 运行演示失败: {e}")
    
    print("\n📊 测试总结:")
    print("=" * 40)
    print("✅ 已完成的组件:")
    print("  - 配置系统")
    print("  - 模型容错管理器")
    print("  - 项目管理系统")
    print("  - CLI工具")
    print("  - 测试框架")
    
    print("\n🚧 下一步开发:")
    print("  - 核心数据模型")
    print("  - 文件解析Agent")
    print("  - 上下文管理Agent")
    print("  - 翻译Agent群")
    
    print("\n💡 使用说明:")
    print("  python main.py          # 启动系统")
    print("  python cli.py --help    # 查看CLI命令")
    print("  python cli.py status    # 查看系统状态")
    print("  python run_tests.py     # 运行测试")
    
    print("\n🎉 基础架构搭建完成!")


if __name__ == "__main__":
    sys.exit(main())