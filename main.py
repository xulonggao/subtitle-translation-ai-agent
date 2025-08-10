#!/usr/bin/env python3
"""
影视剧字幕翻译Agent系统主程序
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import setup_logging, get_logger, system_config
from config.logging_config import system_logger


def main():
    """主程序入口"""
    
    # 设置日志
    setup_logging()
    system_logger.info("系统启动", environment=system_config.environment)
    
    try:
        # 检查环境配置
        check_environment()
        
        # 启动系统
        if system_config.environment == "local":
            start_local_development()
        else:
            start_production()
            
    except Exception as e:
        system_logger.error("系统启动失败", error=str(e))
        sys.exit(1)


def check_environment():
    """检查环境配置"""
    system_logger.info("检查环境配置...")
    
    # 检查AWS凭证
    try:
        import boto3
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            raise ValueError("AWS凭证未配置")
        system_logger.info("AWS凭证检查通过")
    except Exception as e:
        system_logger.error("AWS凭证检查失败", error=str(e))
        raise
    
    # 检查必要目录
    required_dirs = ["logs", "cache", "uploads"]
    for dir_name in required_dirs:
        Path(dir_name).mkdir(exist_ok=True)
    
    system_logger.info("环境检查完成")


def start_local_development():
    """启动本地开发环境"""
    system_logger.info("启动本地开发环境...")
    
    print("=" * 60)
    print("🎬 影视剧字幕翻译Agent系统")
    print("=" * 60)
    print(f"环境: {system_config.environment}")
    print(f"调试模式: {system_config.debug}")
    print(f"最大并发数: {system_config.max_concurrent_translations}")
    print("=" * 60)
    
    # 显示可用功能
    print("\n可用功能:")
    print("1. Web界面 - 运行: python -m uvicorn web.app:app --reload")
    print("2. API服务 - 运行: python -m uvicorn api.main:app --reload")
    print("3. 命令行工具 - 运行: python cli.py --help")
    print("4. 测试套件 - 运行: pytest")
    
    print("\n系统已准备就绪！")
    print("请选择要启动的服务或查看文档: docs/development.md")


def start_production():
    """启动生产环境"""
    system_logger.info("启动生产环境...")
    
    # 生产环境启动逻辑
    # TODO: 实现生产环境启动
    print("生产环境启动功能待实现")


if __name__ == "__main__":
    main()