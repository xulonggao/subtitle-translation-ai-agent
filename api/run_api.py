#!/usr/bin/env python3
"""
API服务启动脚本
"""

import os
import sys
import argparse
import uvicorn
from pathlib import Path

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="字幕翻译系统API服务")
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="启用自动重载")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数")
    parser.add_argument("--log-level", default="info", help="日志级别")
    parser.add_argument("--ssl-keyfile", help="SSL私钥文件")
    parser.add_argument("--ssl-certfile", help="SSL证书文件")
    
    args = parser.parse_args()
    
    # 设置环境变量
    os.environ.setdefault("API_HOST", args.host)
    os.environ.setdefault("API_PORT", str(args.port))
    
    # 启动配置
    config = {
        "app": "main:app",
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "access_log": True,
        "reload": args.reload,
    }
    
    # 生产环境配置
    if not args.reload:
        config["workers"] = args.workers
    
    # SSL配置
    if args.ssl_keyfile and args.ssl_certfile:
        config["ssl_keyfile"] = args.ssl_keyfile
        config["ssl_certfile"] = args.ssl_certfile
        print(f"🔒 启用HTTPS，端口: {args.port}")
    else:
        print(f"🌐 启用HTTP，端口: {args.port}")
    
    print(f"🚀 启动字幕翻译系统API服务...")
    print(f"📍 访问地址: {'https' if args.ssl_keyfile else 'http'}://{args.host}:{args.port}")
    print(f"📚 API文档: {'https' if args.ssl_keyfile else 'http'}://{args.host}:{args.port}/docs")
    print(f"📖 ReDoc文档: {'https' if args.ssl_keyfile else 'http'}://{args.host}:{args.port}/redoc")
    print("按 Ctrl+C 停止服务")
    
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")

if __name__ == "__main__":
    main()