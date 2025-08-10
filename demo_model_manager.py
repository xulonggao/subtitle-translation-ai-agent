#!/usr/bin/env python3
"""
模型容错管理器演示脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import setup_logging, get_logger
from agents.model_manager import ModelFallbackManager, get_model, get_model_info


def main():
    """演示模型容错管理器功能"""
    
    # 设置日志
    setup_logging()
    logger = get_logger("demo")
    
    print("🤖 模型容错管理器演示")
    print("=" * 50)
    
    # 创建模型管理器
    manager = ModelFallbackManager()
    
    # 显示初始状态
    print("\n📊 初始状态:")
    info = manager.get_current_model_info()
    print(f"  当前模型类型: {info['model_type']}")
    print(f"  模型ID: {info['model_id']}")
    print(f"  区域: {info['region']}")
    print(f"  主模型失败次数: {info['primary_failure_count']}")
    
    # 演示获取模型
    print("\n🔄 获取模型:")
    try:
        # 注意：这里可能会失败，因为需要真实的AWS凭证和Bedrock访问权限
        print("  尝试获取模型...")
        model = get_model()
        print(f"  ✅ 成功获取模型: {type(model).__name__}")
        
        # 显示当前模型信息
        current_info = get_model_info()
        print(f"  当前使用: {current_info['model_type']} 模型")
        
    except Exception as e:
        print(f"  ❌ 获取模型失败: {e}")
        print("  这是正常的，因为需要配置AWS凭证和Bedrock访问权限")
    
    # 演示容错机制
    print("\n🔧 容错机制演示:")
    
    # 模拟主模型失败
    print("  模拟主模型失败...")
    test_error = Exception("模拟的429限流错误")
    manager._handle_primary_failure(test_error)
    
    info_after_failure = manager.get_current_model_info()
    print(f"  失败后状态 - 失败次数: {info_after_failure['primary_failure_count']}")
    
    # 测试重试逻辑
    should_retry = manager._should_retry_primary()
    print(f"  是否应该重试主模型: {should_retry}")
    
    # 强制切换到备用模型
    print("  强制切换到备用模型...")
    manager.force_fallback()
    info_fallback = manager.get_current_model_info()
    print(f"  切换后模型类型: {info_fallback['model_type']}")
    
    # 重置状态
    print("  重置失败状态...")
    manager.reset_failure_state()
    info_reset = manager.get_current_model_info()
    print(f"  重置后模型类型: {info_reset['model_type']}")
    print(f"  重置后失败次数: {info_reset['primary_failure_count']}")
    
    print("\n✅ 演示完成!")
    print("\n💡 使用说明:")
    print("  1. 配置AWS凭证: aws configure")
    print("  2. 确保有Bedrock访问权限")
    print("  3. 确保Claude 4 Sonnet和Claude 3.7 Sonnet模型可用")
    print("  4. 在实际使用中，系统会自动处理模型切换")


if __name__ == "__main__":
    main()