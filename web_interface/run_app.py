#!/usr/bin/env python3
"""
字幕翻译系统 Web 应用启动脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """启动Web应用"""
    # 获取当前脚本目录
    current_dir = Path(__file__).parent
    app_path = current_dir / "app.py"
    
    # 检查Streamlit是否安装
    try:
        import streamlit
    except ImportError:
        print("错误: 未安装 Streamlit")
        print("请运行: pip install streamlit")
        sys.exit(1)
    
    # 检查其他依赖
    required_packages = ['plotly', 'pandas']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"错误: 缺少依赖包: {', '.join(missing_packages)}")
        print(f"请运行: pip install {' '.join(missing_packages)}")
        sys.exit(1)
    
    # 启动Streamlit应用
    print("启动字幕翻译系统 Web 界面...")
    print("访问地址: http://localhost:8501")
    print("按 Ctrl+C 停止服务")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n服务已停止")
    except Exception as e:
        print(f"启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()